# src/app/agents/policy_sync_agent.py
"""LangGraph 기반 정책 공고 AI 분석 Self-Correction 에이전트.

계층 원칙:
  Router → Service → Agent → Service → Repository

  이 Agent는 '분석' 전용 계층이다. DB에 직접 접근하지 않으며,
  파싱·AI 구조화·검증 결과를 담은 최종 State를 Service에 반환한다.

Self-Correction 전략:
  - Parser  단계: 다운로드·파싱 실패 시 최대 2회 재시도 (parse_retry_count, 독립)
  - Extractor/Validator 단계: AI 출력 검증 실패 시 최대 2회 재시도 (analysis_retry_count, 독립)
  - 두 단계의 카운터를 완전히 분리하여 서로 간섭하지 않는다.

Debug 모드:
  debug_mode=True 일 때만 로컬에 3개 파일을 생성한다.
    debug_1_api_raw.json      — API 원본 응답
    debug_2_extracted_text.txt — 파서 추출 텍스트
    debug_3_ai_result.json    — AI 구조화 결과
  대량 작업(with_ai=True, debug_mode=False)에서는 파일을 생성하지 않는다.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from langgraph.graph import END, StateGraph
from openai import AsyncOpenAI
from typing_extensions import TypedDict

from src.app.core.config import OPENAI_API_KEY
from src.app.domains.policy.infrastructure import DocumentParserFactory

logger = logging.getLogger(__name__)

# ── 공통 HTTP 헤더 ────────────────────────────────────────────────────────────
_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

# ── 검증 필수 필드: 이 중 하나라도 누락/null이면 ANALYSIS_ERROR 대상 ─────────
_REQUIRED_AI_FIELDS = ("ai_summary", "target_logic", "content_raw")


# ─────────────────────────────────────────────────────────────────────────────
# State
# ─────────────────────────────────────────────────────────────────────────────


class PolicySyncState(TypedDict):
    """LangGraph 그래프 전역 상태.

    parse_retry_count와 analysis_retry_count를 분리하여
    두 단계의 재시도 횟수가 서로 간섭하지 않도록 설계한다.
    """

    raw_api_data: dict          # 기업마당 API 원본 응답
    file_url: str               # 첨부파일 다운로드 URL
    filename_hint: str          # 파일명 힌트 (파서 결정용)
    original_summary: str       # HTML 정제된 bsnsSumryCn (fallback)
    doc_result: dict            # {"type": "text"/"images", "data": ...}
    extracted_text: str         # 파서 추출 텍스트 (로그·검증 참조용)
    structured_data: dict       # GPT-4o 구조화 결과
    validation_errors: list[str]
    parse_retry_count: int      # Parser 단계 재시도 카운터 (독립)
    analysis_retry_count: int   # Extractor/Validator 단계 재시도 카운터 (독립)
    origin_id: str              # 로그 추적용 공고 ID
    status: str                 # 최종 상태: SUCCESS / PARSE_ERROR / ANALYSIS_ERROR
    debug_mode: bool


# ─────────────────────────────────────────────────────────────────────────────
# Agent
# ─────────────────────────────────────────────────────────────────────────────


class PolicySyncAgent:
    """정책 공고 파일을 파싱하고 GPT-4o로 구조화하는 Self-Correction 에이전트.

    - 그래프는 __init__ 시 1회만 컴파일된다 (인스턴스 재사용 가능).
    - DB 접근 없음. 순수 분석·반환 역할.
    """

    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self._graph = self._build_graph()

    # ─────────────────────────────────────────────────────────────────────
    # [공개 API]
    # ─────────────────────────────────────────────────────────────────────

    async def run(
        self,
        *,
        raw_api_data: dict,
        file_url: str,
        filename_hint: str,
        original_summary: str,
        origin_id: str,
        debug_mode: bool = False,
    ) -> PolicySyncState:
        """에이전트 그래프를 실행하고 최종 State를 반환한다.

        Args:
            raw_api_data:     기업마당 API 원본 응답 (debug_1_api_raw.json 저장용)
            file_url:         첨부파일 다운로드 URL (없으면 빈 문자열)
            filename_hint:    printFileNm 값 (ZIP→HWPX 구분 힌트)
            original_summary: HTML 정제된 bsnsSumryCn (fallback 및 GPT 컨텍스트)
            origin_id:        공고 고유 ID (로그 추적용)
            debug_mode:       True이면 3개의 디버그 파일 생성

        Returns:
            최종 PolicySyncState. status 필드로 SUCCESS / PARSE_ERROR / ANALYSIS_ERROR 판별.
        """
        initial_state: PolicySyncState = {
            "raw_api_data": raw_api_data,
            "file_url": file_url,
            "filename_hint": filename_hint,
            "original_summary": original_summary,
            "doc_result": {},
            "extracted_text": "",
            "structured_data": {},
            "validation_errors": [],
            "parse_retry_count": 0,
            "analysis_retry_count": 0,
            "origin_id": origin_id,
            "status": "",
            "debug_mode": debug_mode,
        }
        result: PolicySyncState = await self._graph.ainvoke(initial_state)
        return result

    # ─────────────────────────────────────────────────────────────────────
    # [그래프 빌드]
    # ─────────────────────────────────────────────────────────────────────

    def _build_graph(self) -> Any:
        """LangGraph StateGraph를 조립하고 컴파일한다."""
        builder = StateGraph(PolicySyncState)

        builder.add_node("parser", self._parser_node)
        builder.add_node("extractor", self._extractor_node)
        builder.add_node("validator", self._validator_node)
        builder.add_node("set_parse_error", self._set_parse_error_node)
        builder.add_node("set_analysis_error", self._set_analysis_error_node)
        builder.add_node("set_success", self._set_success_node)

        builder.set_entry_point("parser")

        builder.add_conditional_edges(
            "parser",
            self._route_after_parser,
            {
                "retry_parser": "parser",
                "extractor": "extractor",
                "parse_error": "set_parse_error",
            },
        )

        builder.add_edge("extractor", "validator")

        builder.add_conditional_edges(
            "validator",
            self._route_after_validator,
            {
                "retry_extractor": "extractor",
                "analysis_error": "set_analysis_error",
                "success": "set_success",
            },
        )

        builder.add_edge("set_parse_error", END)
        builder.add_edge("set_analysis_error", END)
        builder.add_edge("set_success", END)

        return builder.compile()

    # ─────────────────────────────────────────────────────────────────────
    # [터미널 상태 노드] 최종 status 기록
    # ─────────────────────────────────────────────────────────────────────

    async def _set_parse_error_node(self, state: PolicySyncState) -> dict:
        logger.warning(
            "[%s] PARSE_ERROR — 텍스트 추출 최대 재시도(%d회) 초과",
            state["origin_id"],
            state["parse_retry_count"],
        )
        return {"status": "PARSE_ERROR"}

    async def _set_analysis_error_node(self, state: PolicySyncState) -> dict:
        logger.warning(
            "[%s] ANALYSIS_ERROR — AI 검증 최대 재시도(%d회) 초과 | 누락 필드: %s",
            state["origin_id"],
            state["analysis_retry_count"],
            state["validation_errors"],
        )
        return {"status": "ANALYSIS_ERROR"}

    async def _set_success_node(self, state: PolicySyncState) -> dict:
        if state["debug_mode"]:
            self._write_debug_file(
                "debug_3_ai_result.json",
                json.dumps(state["structured_data"], ensure_ascii=False, indent=4),
            )
            logger.info("[%s] [DEBUG] debug_3_ai_result.json 저장 완료", state["origin_id"])
        logger.info("[%s] SUCCESS — AI 구조화 완료", state["origin_id"])
        return {"status": "SUCCESS"}

    # ─────────────────────────────────────────────────────────────────────
    # [라우팅 함수] 조건부 엣지 결정 (상태 수정 없음)
    # ─────────────────────────────────────────────────────────────────────

    def _route_after_parser(self, state: PolicySyncState) -> str:
        """Parser 단계 이후 분기 결정.

        Returns:
            "retry_parser"  — 파싱 실패 & parse_retry_count < 2
            "parse_error"   — 파싱 실패 & parse_retry_count >= 2
            "extractor"     — 파싱 성공
        """
        if state["doc_result"]:
            return "extractor"
        if state["parse_retry_count"] < 2:
            return "retry_parser"
        return "parse_error"

    def _route_after_validator(self, state: PolicySyncState) -> str:
        """Validator 단계 이후 분기 결정.

        Returns:
            "retry_extractor" — 검증 실패 & analysis_retry_count < 2
            "analysis_error"  — 검증 실패 & analysis_retry_count >= 2
            "success"         — 검증 통과
        """
        if not state["validation_errors"]:
            return "success"
        if state["analysis_retry_count"] < 2:
            return "retry_extractor"
        return "analysis_error"

    # ─────────────────────────────────────────────────────────────────────
    # [노드: Parser] 파일 다운로드 + 텍스트/이미지 추출
    # ─────────────────────────────────────────────────────────────────────

    async def _parser_node(self, state: PolicySyncState) -> dict:
        """파일 다운로드 → Magic Number 기반 파서 결정 → 텍스트/이미지 추출.

        모든 예외를 try-except로 포착하여 LangGraph 그래프가 중단되지 않도록 한다.
        실패 시 parse_retry_count를 증가시키고 doc_result를 빈 dict로 유지한다.
        """
        origin_id = state["origin_id"]
        file_url = state["file_url"]

        # debug_mode: API 원본을 첫 번째 시도(retry 0)에서만 저장
        if state["debug_mode"] and state["parse_retry_count"] == 0:
            self._write_debug_file(
                "debug_1_api_raw.json",
                json.dumps(state["raw_api_data"], ensure_ascii=False, indent=4),
            )
            logger.info("[%s] [DEBUG] debug_1_api_raw.json 저장 완료", origin_id)

        # 파일 URL이 없으면 파싱 불가 → 즉시 실패 처리
        if not file_url:
            logger.warning(
                "[%s] Parser 스킵 — file_url 없음 (parse_retry=%d)",
                origin_id,
                state["parse_retry_count"],
            )
            return {"parse_retry_count": state["parse_retry_count"] + 1, "doc_result": {}}

        try:
            logger.debug(
                "[%s] Parser 시작 (시도 %d/3) — URL: %s",
                origin_id,
                state["parse_retry_count"] + 1,
                file_url[-60:],
            )

            # [STEP 1] 파일 다운로드
            content = await self._download_file(file_url)

            # [STEP 2] Magic Number 기반 파서 결정
            parser = DocumentParserFactory.from_content(
                content, filename_hint=state["filename_hint"]
            )
            logger.debug(
                "[%s] 파서 결정: %s (hint=%s)",
                origin_id,
                type(parser).__name__,
                state["filename_hint"] or "없음",
            )

            # [STEP 3] 텍스트/이미지 추출
            doc_result = await parser.parse(content)

            # 추출 결과 유효성 검사
            if doc_result["type"] == "text":
                extracted = doc_result["data"]
                if len(extracted.strip()) < 50:
                    raise ValueError(
                        f"추출 텍스트가 너무 짧음 ({len(extracted.strip())}자)"
                    )
            else:
                extracted = f"[이미지 {len(doc_result['data'])}장 → Vision AI 처리]"

            # debug_mode: 추출 텍스트 저장
            if state["debug_mode"]:
                self._write_debug_file("debug_2_extracted_text.txt", extracted)
                logger.info("[%s] [DEBUG] debug_2_extracted_text.txt 저장 완료", origin_id)

            logger.debug(
                "[%s] Parser 성공 — 타입: %s, 크기: %d",
                origin_id,
                doc_result["type"],
                len(extracted),
            )

            return {
                "doc_result": doc_result,
                "extracted_text": extracted,
            }

        except Exception as exc:
            new_retry = state["parse_retry_count"] + 1
            logger.warning(
                "[%s] Parser 실패 (시도 %d/3) — %s: %s",
                origin_id,
                new_retry,
                type(exc).__name__,
                exc,
            )
            return {
                "parse_retry_count": new_retry,
                "doc_result": {},
                "extracted_text": "",
            }

    # ─────────────────────────────────────────────────────────────────────
    # [노드: Extractor] GPT-4o AI 구조화
    # ─────────────────────────────────────────────────────────────────────

    async def _extractor_node(self, state: PolicySyncState) -> dict:
        """doc_result + original_summary를 GPT-4o에 전달하여 구조화된 JSON을 추출한다.

        API 오류나 JSON 파싱 실패 시 try-except로 포착하고
        analysis_retry_count를 증가시켜 재시도 흐름으로 전달한다.
        """
        origin_id = state["origin_id"]

        try:
            logger.debug(
                "[%s] Extractor 시작 (시도 %d/3) — doc_type: %s",
                origin_id,
                state["analysis_retry_count"] + 1,
                state["doc_result"].get("type", "unknown"),
            )

            structured = await self._call_openai(
                doc_result=state["doc_result"],
                original_summary=state["original_summary"],
            )

            # content_raw: doc_result 타입에 따라 결정
            if state["doc_result"].get("type") == "text":
                structured["content_raw"] = state["doc_result"]["data"]
            else:
                # Vision 모드: GPT가 읽어낸 extracted_text 를 원문으로 저장
                structured["content_raw"] = structured.get(
                    "extracted_text", state["original_summary"]
                )

            logger.debug(
                "[%s] Extractor 성공 — 필드 수: %d",
                origin_id,
                len(structured),
            )

            return {
                "structured_data": structured,
                "validation_errors": [],  # 이전 실패 흔적 초기화
            }

        except Exception as exc:
            new_retry = state["analysis_retry_count"] + 1
            logger.warning(
                "[%s] Extractor 실패 (시도 %d/3) — %s: %s",
                origin_id,
                new_retry,
                type(exc).__name__,
                exc,
            )
            return {
                "structured_data": {},
                "analysis_retry_count": new_retry,
                "validation_errors": [f"Extractor 예외: {exc}"],
            }

    # ─────────────────────────────────────────────────────────────────────
    # [노드: Validator] AI 출력 필드 검증
    # ─────────────────────────────────────────────────────────────────────

    async def _validator_node(self, state: PolicySyncState) -> dict:
        """structured_data에서 필수 필드 누락/null 여부를 검사한다.

        검증 통과 기준:
          - ai_summary   : 비어있지 않은 문자열
          - target_logic : None이 아닌 dict
          - content_raw  : 비어있지 않은 문자열
        """
        origin_id = state["origin_id"]
        data = state["structured_data"]
        errors: list[str] = []

        if not data.get("ai_summary"):
            errors.append("ai_summary 누락 또는 null")
        if not isinstance(data.get("target_logic"), dict):
            errors.append("target_logic 누락 또는 잘못된 형식")
        if not data.get("content_raw"):
            errors.append("content_raw 누락 또는 null")

        if errors:
            new_retry = state["analysis_retry_count"] + 1
            logger.warning(
                "[%s] Validator 실패 (시도 %d/3) — 누락 필드: %s",
                origin_id,
                new_retry,
                errors,
            )
            return {
                "validation_errors": errors,
                "analysis_retry_count": new_retry,
            }

        logger.debug("[%s] Validator 통과", origin_id)
        return {"validation_errors": []}

    # ─────────────────────────────────────────────────────────────────────
    # [내부 헬퍼]
    # ─────────────────────────────────────────────────────────────────────

    async def _download_file(self, url: str) -> bytes:
        """URL에서 파일 바이너리를 다운로드한다."""
        async with httpx.AsyncClient(
            follow_redirects=True, headers=_DEFAULT_HEADERS, timeout=30.0
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    def _build_system_prompt(self) -> str:
        return """
너는 대한민국 정부 정책 공고문을 분석하여 시스템 DB 저장용 JSON 데이터로 변환하는 'AI 데이터 엔지니어'야.

[준수 사항]
1. **정확한 타입 변환**:
   - 모든 금액은 '원' 단위의 숫자(Integer)로 변환해. (예: 50백만원 -> 50000000)
   - 날짜는 반드시 'YYYY-MM-DD' 형식을 지켜.
2. **데이터 결측치 처리**:
   - 정보가 없는 필드는 삭제하지 말고 반드시 `null`로 채워.
   - 불확실한 정보는 추측하지 말고 `null` 처리해.
3. **상시 접수 처리**:
   - 접수 마감일이 '상시', '예산 소진 시'인 경우 종료일(`end_date`)은 `9999-12-31`로 고정해.
4. **사용자 배려**:
   - `ai_summary`와 `ai_full_explanation`은 소상공인이나 비전공자가 이해하기 쉽게 풀어써줘.

{
  "title": "공고 제목 (핵심 키워드 포함)",
  "agency_name": "주관 기관 및 부처명",
  "category": "금융/기술/수출/인력/경영 중 택 1",
  "support_type": "보조금/융자/출연금/서비스지원 중 택 1",
  "region": "지원 지역 (전국/서울/경기 등)",
  "support_amount": {
    "min": 0,
    "max": 0,
    "description": "사용자에게 보여줄 금액 설명 (예: 업체당 최대 1억원)"
  },
  "dates": {
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD (상시접수면 9999-12-31)"
  },
  "target_logic": {
    "sectors": ["업종리스트"],
    "min_revenue": null,
    "max_debt_ratio": null,
    "target_age": null,
    "region_restricted": false
  },
  "bonus_logic": {
    "items": [{"name": "가점항목명", "point": 5}]
  },
  "required_documents": ["서류1", "서류2"],
  "ai_summary": "사장님이 이해하기 쉬운 3줄 요약",
  "ai_full_explanation": "공고 전체 내용을 이해하기 쉽게 풀어낸 설명",
  "extracted_text": "전체 문서 내용을 텍스트로 추출한 것 (RAG 검색용)"
}
        """

    async def _call_openai(
        self, doc_result: dict[str, Any], original_summary: str
    ) -> dict[str, Any]:
        """GPT-4o에 텍스트 또는 이미지를 전달하고 구조화된 JSON을 받는다."""
        messages: list[dict] = [
            {"role": "system", "content": self._build_system_prompt()}
        ]

        if doc_result.get("type") == "text":
            user_content = (
                f"원본 요약: {original_summary}\n\n"
                f"공고문 원문:\n{doc_result['data'][:10000]}"
            )
            messages.append({"role": "user", "content": user_content})
        else:
            content_parts: list[dict] = [
                {
                    "type": "text",
                    "text": (
                        f"원본 요약: {original_summary}\n\n"
                        "아래 첨부된 공고문 이미지를 읽고 분석해줘."
                    ),
                }
            ]
            for b64_img in doc_result.get("data", []):
                content_parts.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64_img}"},
                    }
                )
            messages.append({"role": "user", "content": content_parts})

        response = await self._client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)

    @staticmethod
    def _write_debug_file(filename: str, content: str) -> None:
        """디버그 파일을 로컬에 저장한다. 실패해도 에이전트 흐름을 중단하지 않는다."""
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError as exc:
            logger.warning("[DEBUG] 파일 저장 실패 (%s): %s", filename, exc)
