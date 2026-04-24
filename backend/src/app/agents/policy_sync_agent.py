# src/app/agents/policy_sync_agent.py
"""LangGraph 기반 정책 공고 AI 분석 Self-Correction 에이전트.

계층 원칙:
  Router → Service → Agent → Service → Repository

  이 Agent는 '분석' 전용 계층입니다. DB에 직접 접근하지 않으며,
  파싱·AI 구조화·검증 결과를 담은 최종 State를 Service에 반환합니다.

Self-Correction 전략:
  - Parser 단계: 다운로드·파싱 실패 시 최대 2회 재시도 (parse_retry_count)
  - Extractor/Validator 단계: AI 출력 필수 필드 누락 시 재시도 (analysis_retry_count)
  - [핵심] 두 단계의 카운터를 완전히 분리하여 서로 간섭하지 않도록 설계했습니다.

최적화 전략 (2026.04 적용):
  - 파일 URL 부재 시 불필요한 루프를 타지 않고 즉시 Fail-Fast 처리합니다.
  - GPT에게 원문을 다시 생성하게 하는(extracted_text) 프롬프트를 제거하여 출력 토큰 비용을 절감했습니다.
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

# 공통 HTTP 헤더 (정부 사이트 다운로드 차단 방지용)
_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# State (그래프 전역 상태)
# ─────────────────────────────────────────────────────────────────────────────

class PolicySyncState(TypedDict):
    """LangGraph 그래프에서 노드 간 데이터를 주고받는 '택배 상자' 역할입니다."""

    raw_api_data: dict          # API 원본 응답
    file_url: str               # 첨부파일 다운로드 URL
    filename_hint: str          # 파일명 힌트 (파서 결정용)
    original_summary: str       # 기업마당이 제공한 원본 요약 (Fallback 용도)
    doc_result: dict            # 파서 결과물 {"type": "text"/"images", "data": ...}
    extracted_text: str         # 파서 추출 텍스트 (로그 기록용, AI가 생성하지 않음)
    structured_data: dict       # GPT-4o가 구조화한 최종 JSON 데이터
    validation_errors: list[str]# Validator 노드에서 발견된 결함 목록
    parse_retry_count: int      # Parser 단계 재시도 횟수
    analysis_retry_count: int   # AI 추출/검증 단계 재시도 횟수
    origin_id: str              # 추적용 로그 ID
    status: str                 # 최종 상태 (SUCCESS / PARSE_ERROR / ANALYSIS_ERROR)
    debug_mode: bool


# ─────────────────────────────────────────────────────────────────────────────
# Agent (메인 클래스)
# ─────────────────────────────────────────────────────────────────────────────

class PolicySyncAgent:
    """정책 공고 파일을 파싱하고 GPT-4o로 구조화하는 Self-Correction 에이전트."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self._graph = self._build_graph()

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
        """초기 상태를 세팅하고 LangGraph 사이클을 시작합니다."""
        initial_state: PolicySyncState = {
            "raw_api_data": raw_api_data,
            "file_url": file_url,
            "filename_hint": filename_hint,
            "original_summary": original_summary,
            "doc_result": {},
            "extracted_text": "",
            "structured_data": {},
            "validation_errors":[],
            "parse_retry_count": 0,
            "analysis_retry_count": 0,
            "origin_id": origin_id,
            "status": "",
            "debug_mode": debug_mode,
        }
        # ainvoke를 호출하면 _build_graph에서 설정한 순서대로 노드를 타고 흐릅니다.
        return await self._graph.ainvoke(initial_state)

    def _build_graph(self) -> Any:
        """노드(작업)와 엣지(흐름 조건)를 연결하여 그래프를 완성합니다."""
        builder = StateGraph(PolicySyncState)

        # 1. 노드 등록 (각각의 작업 단위)
        builder.add_node("parser", self._parser_node)
        builder.add_node("extractor", self._extractor_node)
        builder.add_node("validator", self._validator_node)
        builder.add_node("set_parse_error", self._set_parse_error_node)
        builder.add_node("set_analysis_error", self._set_analysis_error_node)
        builder.add_node("set_success", self._set_success_node)

        # 2. 진입점 설정
        builder.set_entry_point("parser")

        # 3. 라우팅 엣지 설정 (조건에 따라 어디로 갈지 결정)
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

        # 4. 종료점 설정
        builder.add_edge("set_parse_error", END)
        builder.add_edge("set_analysis_error", END)
        builder.add_edge("set_success", END)

        return builder.compile()

    # ─────────────────────────────────────────────────────────────────────
    # [터미널 상태 노드] 최종 status 확정 및 로그 출력
    # ─────────────────────────────────────────────────────────────────────

    async def _set_parse_error_node(self, state: PolicySyncState) -> dict:
        logger.warning(
            "[%s] PARSE_ERROR — 텍스트 추출 실패 또는 파일 없음 (시도: %d회)",
            state["origin_id"],
            state["parse_retry_count"],
        )
        return {"status": "PARSE_ERROR"}

    async def _set_analysis_error_node(self, state: PolicySyncState) -> dict:
        logger.warning(
            "[%s] ANALYSIS_ERROR — AI 검증 실패 초과 (%d회) | 사유: %s",
            state["origin_id"],
            state["analysis_retry_count"],
            state["validation_errors"],
        )
        return {"status": "ANALYSIS_ERROR"}

    async def _set_success_node(self, state: PolicySyncState) -> dict:
        if state["debug_mode"]:
            self._write_debug_file("3_ai_result.json", json.dumps(state["structured_data"], ensure_ascii=False, indent=4), origin_id=state["origin_id"])
        logger.info("[%s] SUCCESS — AI 구조화 및 검증 완료", state["origin_id"])
        return {"status": "SUCCESS"}

    # ─────────────────────────────────────────────────────────────────────
    # [라우팅 함수] 현재 상태를 보고 다음 목적지를 문자열로 반환
    # ─────────────────────────────────────────────────────────────────────

    def _route_after_parser(self, state: PolicySyncState) -> str:
        if state["doc_result"]:
            return "extractor"
        if state["parse_retry_count"] < 2:
            return "retry_parser"
        return "parse_error"

    def _route_after_validator(self, state: PolicySyncState) -> str:
        if not state["validation_errors"]:
            return "success"
        if state["analysis_retry_count"] < 2:
            return "retry_extractor"
        return "analysis_error"

    # ─────────────────────────────────────────────────────────────────────
    # [핵심 노드 로직] Parser -> Extractor -> Validator
    # ─────────────────────────────────────────────────────────────────────

    async def _parser_node(self, state: PolicySyncState) -> dict:
        origin_id = state["origin_id"]
        file_url = state["file_url"]

        if state["debug_mode"] and state["parse_retry_count"] == 0:
            self._write_debug_file("1_api_raw.json", json.dumps(state["raw_api_data"], ensure_ascii=False, indent=4), origin_id=origin_id)

        # [버그 수정 & 최적화] 파일 URL이 없으면 재시도 없이 즉시 실패 처리 (Fail-Fast)
        # 3번이나 빈 URL을 다운로드하려 시도하는 무의미한 루프를 방지합니다.
        if not file_url:
            logger.warning("[%s] Parser 스킵 — 다운로드할 파일 URL이 없습니다.", origin_id)
            return {
                "parse_retry_count": 3,  # 최대치로 설정하여 라우터가 parse_error로 즉시 보내게 함
                "doc_result": {}
            }

        try:
            logger.debug("[%s] Parser 시작 (시도 %d/3)", origin_id, state["parse_retry_count"] + 1)
            content = await self._download_file(file_url)
            parser = DocumentParserFactory.from_content(content, filename_hint=state["filename_hint"])
            doc_result = await parser.parse(content)

            if doc_result["type"] == "text":
                extracted = doc_result["data"]
                if len(extracted.strip()) < 50:
                    raise ValueError(f"추출 텍스트가 너무 짧음 ({len(extracted.strip())}자)")
            else:
                extracted = f"[이미지 {len(doc_result['data'])}장 → Vision AI 처리]"

            if state["debug_mode"]:
                self._write_debug_file("2_extracted_text.txt", extracted, origin_id=origin_id)

            return {
                "doc_result": doc_result,
                "extracted_text": extracted,
            }

        except Exception as exc:
            new_retry = state["parse_retry_count"] + 1
            logger.warning("[%s] Parser 실패 (%d/3) — %s: %s", origin_id, new_retry, type(exc).__name__, exc)
            return {"parse_retry_count": new_retry, "doc_result": {}, "extracted_text": ""}

    async def _extractor_node(self, state: PolicySyncState) -> dict:
        origin_id = state["origin_id"]

        try:
            logger.debug("[%s] Extractor 시작 (%d/3)", origin_id, state["analysis_retry_count"] + 1)
            structured = await self._call_openai(
                doc_result=state["doc_result"],
                original_summary=state["original_summary"],
            )

            #[비용 절감 핵심] GPT가 `extracted_text`를 다시 쓰지 않게 했으므로 서버에서 직접 꽂아줍니다.
            if state["doc_result"].get("type") == "text":
                structured["content_raw"] = state["doc_result"]["data"]
            else:
                # Vision 모드(이미지)인 경우, 원문이 없으므로 API 요약과 GPT 풀이를 합쳐서 저장합니다.
                structured["content_raw"] = (
                    f"[이미지 공고]\n{state['original_summary']}\n\n"
                    f"[상세설명]\n{structured.get('ai_full_explanation', '')}"
                )

            return {"structured_data": structured, "validation_errors": []}

        except Exception as exc:
            new_retry = state["analysis_retry_count"] + 1
            logger.warning("[%s] Extractor 실패 (%d/3) — %s", origin_id, new_retry, exc)
            return {
                "structured_data": {},
                "analysis_retry_count": new_retry,
                "validation_errors": [f"Extractor 예외: {exc}"],
            }

    async def _validator_node(self, state: PolicySyncState) -> dict:
        """
        [품질 강화] 비즈니스 로직에 필요한 핵심 필드들이 GPT 응답에 잘 포함되었는지 검사합니다.
        누락된 필드가 있으면 analysis_retry_count를 올리고 다시 Extractor로 보냅니다.
        """
        _ = state["origin_id"]
        data = state["structured_data"]
        errors: list[str] =[]

        # 1. 요약문 검증
        if not data.get("ai_summary"):
            errors.append("ai_summary(3줄 요약) 누락")
        
        # 2. 지원 조건 로직 검증 (비즈니스 핵심)
        if not isinstance(data.get("target_logic"), dict):
            errors.append("target_logic(지원조건) 누락 또는 잘못된 형식(dict 아님)")
            
        # 3. 지원 금액 검증 (비즈니스 핵심)
        if not isinstance(data.get("support_amount"), dict):
            errors.append("support_amount(지원금액) 누락 또는 잘못된 형식(dict 아님)")
            
        # 4. 기간 검증
        if not isinstance(data.get("dates"), dict):
            errors.append("dates(기간) 누락 또는 잘못된 형식(dict 아님)")

        if errors:
            new_retry = state["analysis_retry_count"] + 1
            return {"validation_errors": errors, "analysis_retry_count": new_retry}

        return {"validation_errors":[]}

    # ─────────────────────────────────────────────────────────────────────
    # [내부 헬퍼] 외부 API 통신 및 프롬프트
    # ─────────────────────────────────────────────────────────────────────

    async def _download_file(self, url: str) -> bytes:
        async with httpx.AsyncClient(follow_redirects=True, headers=_DEFAULT_HEADERS, timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    def _build_system_prompt(self) -> str:
        """
        [프롬프트 최적화]
        - extracted_text 필드를 삭제하여 출력 토큰(비용)을 절반 이하로 줄였습니다.
        - 불확실한 데이터는 null 처리를 명확히 지시했습니다.
        """
        return """
너는 대한민국 정부 정책 공고문을 분석하여 시스템 DB 저장용 JSON 데이터로 변환하는 'AI 데이터 엔지니어'야.

[준수 사항]
1. 정확한 타입 변환: 모든 금액은 '원' 단위의 숫자(Integer)로 변환해. (예: 50백만원 -> 50000000)
2. 날짜 형식: 날짜는 반드시 'YYYY-MM-DD' 형식을 지켜.
3. 결측치 처리: 정보가 없는 필드는 삭제하지 말고 반드시 `null`로 채워. 불확실하면 억지로 만들지 마.
4. 상시 접수: 접수 마감일이 '상시', '예산 소진 시'인 경우 종료일(`end_date`)은 `9999-12-31`로 고정해.
5. 사용자 배려: `ai_summary`와 `ai_full_explanation`은 소상공인이 직관적으로 이해하기 쉽게 풀어써줘.

[출력 JSON 구조]
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
    "items":[{"name": "가점항목명", "point": 5}]
  },
  "required_documents":["서류1", "서류2"],
  "ai_summary": "사장님이 이해하기 쉬운 3줄 요약",
  "ai_full_explanation": "공고 전체 내용을 이해하기 쉽게 풀어낸 설명"
}
        """

    async def _call_openai(self, doc_result: dict[str, Any], original_summary: str) -> dict[str, Any]:
        messages: list[dict] =[{"role": "system", "content": self._build_system_prompt()}]

        if doc_result.get("type") == "text":
            # 긴 공고문(주로 HWP)의 경우 컨텍스트 윈도우 초과를 막고 비용을 방어하기 위해 15,000자로 자릅니다.
            # 중요한 내용은 보통 앞부분(개요, 지원조건)에 집중되어 있습니다.
            safe_text = doc_result['data'][:15000]
            user_content = f"원본 요약: {original_summary}\n\n공고문 원문:\n{safe_text}"
            messages.append({"role": "user", "content": user_content})
        else:
            # Vision 모드: 이미지를 직접 분석합니다.
            content_parts: list[dict] =[
                {"type": "text", "text": f"원본 요약: {original_summary}\n\n아래 첨부된 공고문 이미지를 읽고 분석해줘."}
            ]
            for b64_img in doc_result.get("data",[]):
                content_parts.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}})
            messages.append({"role": "user", "content": content_parts})

        response = await self._client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)

    @staticmethod
    def _write_debug_file(filename: str, content: str, origin_id: str = "") -> None:
        import os
        try:
            debug_dir = os.path.join("debug_output", origin_id) if origin_id else "debug_output"
            os.makedirs(debug_dir, exist_ok=True)
            filepath = os.path.join(debug_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            logger.debug("[DEBUG] 파일 저장 완료: %s", filepath)
        except OSError as exc:
            logger.warning("[DEBUG] 파일 저장 실패 (%s): %s", filename, exc)