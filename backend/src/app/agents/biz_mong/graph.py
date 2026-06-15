# src/app/agents/biz_mong/graph.py
"""비즈몽 상담 에이전트 LangGraph 그래프 정의.

[에이전트 구조]
입력 메시지 → router_node(의도 분류)
              ├── greeting / general_qa → chitchat_node (일상 대화)
              ├── rag                  → _run_rag (정책 RAG 검색 + 답변 생성)
              └── stats                → stats_node (통계 조회)

[데이터 흐름]
- LangGraph StateGraph 가 thread_id(room_id) 기반으로 대화 상태를 유지한다.
- 각 노드 실행 결과는 _write_through 를 통해 chat_logs(system role)에 관측 로그로 저장된다.
- RAG 노드는 policy_rag_search 로 관련 정책 청크를 검색한 뒤 gpt-4o-mini 로 답변을 생성한다.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import time
import uuid
from typing import Any

from langgraph.graph import END, StateGraph
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.agents.biz_mong.checkpointer import get_langgraph_checkpointer
from src.app.agents.biz_mong.checkpointer import initialize_langgraph_checkpointer
from src.app.agents.biz_mong.nodes.chitchat_node import chitchat_node
from src.app.agents.biz_mong.nodes.router_node import router_node
from src.app.agents.biz_mong.nodes.stats_node import stats_node
from src.app.agents.biz_mong.state import make_initial_state
from src.app.agents.biz_mong.telemetry import build_node_log
from src.app.agents.biz_mong.tools.get_biz_info import get_biz_info
from src.app.agents.biz_mong.tools.policy_rag import policy_rag_search
from src.app.core.config import OPENAI_API_KEY
from src.app.domains.chat.model import ChatLog

logger = logging.getLogger(__name__)


class BizMongAgent:
    """비즈몽 상담 에이전트 (LangGraph 기반).

    사용자의 정책 자금 관련 질문에 답변하는 AI 상담사 에이전트.
    - router_node 가 의도를 분류하고, 의도에 따라 적절한 노드로 라우팅한다.
    - 세션(room_id)별로 대화 상태(메시지 히스토리)가 유지된다.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        # 그래프 구조는 인스턴스 생성 시 한 번만 빌드
        self._graph = self._build_graph()

    @classmethod
    async def create(cls, session: AsyncSession) -> "BizMongAgent":
        """비동기 초기화가 필요한 경우를 위한 팩토리 메서드.

        LangGraph 체크포인터(PostgreSQL 연결)를 초기화한 뒤 인스턴스를 반환한다.
        """
        await initialize_langgraph_checkpointer()
        return cls(session=session)

    async def run(
        self,
        *,
        user_id: str,
        business_id: str,
        room_id: str,
        message: str,
    ) -> dict[str, Any]:
        """사용자 메시지를 처리하고 에이전트 응답 상태를 반환한다.

        [로직]
        1. room_id 를 thread_id 로 사용하여 기존 대화 상태 조회
        2. 기존 상태가 있으면 메시지만 추가, 없으면 초기 상태 생성
        3. 그래프를 비동기 실행하여 최종 상태 반환
        """
        config = {"configurable": {"thread_id": room_id}}
        existing = self._graph.get_state(config)

        # 같은 room_id 로 이어지는 대화라면 이전 체크포인트를 이어받고,
        # 처음 시작하는 방이면 사업장 컨텍스트를 포함한 초기 상태를 만든다.
        if existing and existing.values:
            # 기존 대화가 있으면 새 메시지만 추가
            initial: dict[str, Any] = {
                "messages": [{"role": "user", "content": message}],
                # 체크포인트가 남아 있어도 신규 turn 입력에 식별자를 다시 넣어둔다.
                # 그래야 hydrate_context/write_through 같은 보조 노드가 항상 같은 기준으로 동작한다.
                "user_id": user_id,
                "business_id": business_id,
                "room_id": room_id,
            }
        else:
            # 처음 시작하는 대화 — 사용자·사업장 컨텍스트 포함 초기 상태 생성
            initial = make_initial_state(
                user_id=user_id,
                business_id=business_id,
                room_id=room_id,
                first_message=message,
            )

        return await self._graph.ainvoke(initial, config=config)

    async def run_from_route(
        self,
        *,
        state: dict[str, Any],
        route_intent: str,
    ) -> dict[str, Any]:
        """이미 라우팅된 의도(intent)에 맞는 노드를 직접 실행한다.

        [설계 의도]
        스트리밍 API 등에서 외부 라우터가 의도를 미리 결정했을 때,
        그래프 전체를 재실행하지 않고 특정 노드만 직접 호출하기 위한 메서드.
        """
        if route_intent in ("greeting", "general_qa"):
            return await chitchat_node(state, client=self._client)
        if route_intent == "rag":
            return await _run_rag(state, session=self._session, client=self._client)
        if route_intent == "stats":
            return await stats_node(state, session=self._session)
        # 알 수 없는 의도는 일반 QA 노드로 폴백
        return await chitchat_node(
            {**state, "current_agent": "general_qa"},
            client=self._client,
        )

    def _build_graph(self):
        """LangGraph StateGraph 를 빌드하고 컴파일한다.

        [그래프 구조]
        router → (의도에 따라) chitchat | rag | stats → END

        - router: 사용자 의도 분류 (greeting / general_qa / rag / stats)
        - chitchat: 일상 대화 및 일반 QA 처리
        - rag: 정책 RAG 검색 + GPT 답변 생성
        - stats: 사업장 통계 조회

        체크포인터(PostgreSQL)를 통해 thread_id(=room_id) 기반으로 대화 상태를 영속한다.
        """
        # 클로저로 session/client 를 잡아두면 각 노드가 같은 의존성을 재사용할 수 있다.
        session = self._session
        client = self._client

        async def _hydrate_context(state: dict) -> dict:
            return await _hydrate_business_context(state, session=session)

        async def _router(state: dict) -> dict:
            return await router_node(state, client=client)

        async def _chitchat(state: dict) -> dict:
            return await chitchat_node(state, client=client)

        async def _rag(state: dict) -> dict:
            result = await _run_rag(state, session=session, client=client)
            # RAG 실행 결과를 DB에도 기록 (토큰 사용량 포함)
            await _write_through(state, "rag", result)
            return result

        async def _stats(state: dict) -> dict:
            result = await stats_node(state, session=session)
            # 통계 조회 결과를 DB에 기록
            await _write_through(state, "stats", result)
            return result

        builder = StateGraph(dict)
        builder.add_node("hydrate_context", _hydrate_context)
        builder.add_node("router", _router)
        builder.add_node("chitchat", _chitchat)
        builder.add_node("rag", _rag)
        builder.add_node("stats", _stats)

        builder.set_entry_point("hydrate_context")
        # 상담 품질은 라우팅보다 컨텍스트가 먼저다.
        # 지역/업종/재무 정보가 채워진 뒤 라우터가 실행되어야 RAG 지역 필터와 통계 노드가 의미 있게 동작한다.
        builder.add_edge("hydrate_context", "router")
        # router 노드의 current_agent 값에 따라 다음 노드로 조건부 분기
        builder.add_conditional_edges(
            "router",
            lambda state: state.get("current_agent", "general_qa"),
            {
                "greeting": "chitchat",
                "general_qa": "chitchat",
                "rag": "rag",
                "stats": "stats",
            },
        )

        builder.add_edge("chitchat", END)
        builder.add_edge("rag", END)
        builder.add_edge("stats", END)

        return builder.compile(checkpointer=get_langgraph_checkpointer())


async def _hydrate_business_context(
    state: dict,
    session: AsyncSession,
) -> dict[str, Any]:
    """그래프 실행 전에 사업장/재무 컨텍스트를 채워 상담 품질을 높인다.

    기존 체크포인트에 이미 값이 있으면 그대로 사용하고, 비어 있으면 DB에서 조회한다.
    조회 실패는 상담 흐름을 막지 않도록 빈 업데이트로 처리한다.
    """
    if state.get("biz_info") and state.get("financial_data"):
        return {}

    business_id = state.get("business_id")
    if not business_id:
        return {}

    try:
        # get_biz_info 는 DB 조회만 담당하는 도구다.
        # 정책 판단은 이후 RAG/Stats 노드가 맡고, 여기서는 상태에 필요한 원천 데이터만 채운다.
        biz_info, financial_data = await get_biz_info(str(business_id), session)
    except Exception as exc:
        logger.warning("[bizmong-context] business context hydration failed: %s", exc)
        return {}

    updates: dict[str, Any] = {}
    # LangGraph 상태 업데이트는 "변경할 필드만 반환"하는 방식이다.
    # 기존 체크포인트 값이 있으면 덮어쓰지 않아 대화 중 누적된 상태를 보존한다.
    if biz_info and not state.get("biz_info"):
        updates["biz_info"] = biz_info
    if financial_data and not state.get("financial_data"):
        updates["financial_data"] = financial_data
    return updates


async def _write_through(
    state: dict,
    node_name: str,
    result: dict,
) -> None:
    """노드 실행 결과를 chat_logs 테이블(system role)에 관측 로그로 저장한다.

    [목적]
    - 에이전트 내부 동작(RAG 검색 수, 통계 인사이트, 토큰 사용량 등)을 DB에 기록해
      나중에 모니터링·비용 분석·디버깅에 활용하기 위함.
    - 실패해도 메인 흐름에 영향을 주지 않도록 예외를 삼킨다.

    Args:
        state: 현재 그래프 상태 (room_id, user_id 추출용)
        node_name: 실행된 노드 이름 (rag | stats)
        result: 노드 반환 상태 딕셔너리
    """
    # 이 로그는 최종 사용자 답변이 아니라 "에이전트 내부에서 무슨 일이 있었는지"를 남긴다.
    # 장애 분석이나 품질 개선을 하려면 이런 내부 기록이 꼭 필요하다.
    room_id: str = state.get("room_id", "")
    user_id: str = state.get("user_id", "")
    if not room_id or not user_id:
        return

    try:
        room_uuid = uuid.UUID(room_id)
        user_uuid = uuid.UUID(user_id)
    except (ValueError, AttributeError):
        return

    summary = _summarize_result(node_name, result)

    try:
        from src.app.database.postgres.database import SessionLocal

        async with SessionLocal() as wt_session:
            # RAG 노드에서는 토큰 사용량도 함께 기록
            usage: dict = result.get("last_usage") or {} if node_name == "rag" else {}
            log = ChatLog(
                user_id=user_uuid,
                room_id=room_uuid,
                role="system",
                content=summary,
                context_type="agent",
                tokens_in=usage.get("tokens_in"),
                tokens_out=usage.get("tokens_out"),
                model_name=usage.get("model_name"),
                response_time_ms=usage.get("response_time_ms"),
            )
            wt_session.add(log)
            await wt_session.commit()
    except Exception as exc:
        logger.warning("[write_through] node=%s failed: %s", node_name, exc)


def _summarize_result(node_name: str, result: dict) -> str:
    """노드 실행 결과를 DB에 저장할 JSON 문자열로 요약한다.

    직렬화 실패 시 안전하게 오류 페이로드를 반환하며 예외를 외부로 전파하지 않는다.
    """
    try:
        if node_name == "rag":
            return json.dumps(
                {"node": "rag", "results_count": len(result.get("rag_results") or [])},
                ensure_ascii=False,
            )
        if node_name == "stats":
            insight = result.get("stats_insight") or {}
            return json.dumps(
                {
                    "node": "stats",
                    "peer_count": insight.get("peer_count"),
                    "avg_revenue": insight.get("avg_revenue"),
                },
                ensure_ascii=False,
            )
        return json.dumps({"node": node_name}, ensure_ascii=False)
    except Exception:
        return json.dumps({"node": node_name, "error": "serialize_failed"}, ensure_ascii=False)


async def _run_rag(
    state: dict,
    session: AsyncSession,
    client: AsyncOpenAI,
) -> dict:
    """정책 RAG 검색 후 GPT 로 최종 답변을 생성하는 함수.

    [로직 순서]
    1. 마지막 사용자 메시지 추출 (없으면 빈 문자열)
    2. policy_rag_search 로 관련 정책 청크 검색 (지역 필터 적용)
       - 결과 없으면 "정보를 찾지 못했다"는 fallback 응답 반환
    3. 검색 결과 상위 3개를 컨텍스트로 구성
    4. GPT (gpt-4o-mini) 에 컨텍스트 + 질문을 넘겨 최종 답변 생성
    5. 각 단계의 지연 시간(latency_ms)을 node_logs 에 기록
    """
    # RAG 노드는 "질문 -> 정책 검색 -> 검색 근거로 답변 생성" 전체를 맡는다.
    messages: list = state.get("messages") or []
    last_msg = _get_last_user_message(messages)
    biz_info: dict = state.get("biz_info") or {}
    region = biz_info.get("region_sido")  # 사용자 사업장 지역 (정책 필터링에 사용)
    node_logs: list[dict[str, Any]] = []

    # [1] 정책 청크 검색
    retrieval_started_at = datetime.now(timezone.utc)
    retrieval_started = time.monotonic()
    # 지역 필터가 있으면 "내 사업장 지역 + 전국 공고" 중심으로 검색해 추천 품질을 높인다.
    # 지역 정보가 없으면 전체 공고에서 검색되므로 상담은 계속 가능하다.
    search_payload = await policy_rag_search(
        last_msg,
        session,
        region_filter=region,
        biz_info=biz_info,
    )
    rag_results = search_payload.get("results") or []
    rag_intent_results = search_payload.get("intent_results") or []
    search_metadata = search_payload.get("search_metadata") or {}
    retrieval_elapsed_ms = int((time.monotonic() - retrieval_started) * 1000)
    node_logs.append(
        build_node_log(
            node_name="rag_retrieval",
            sequence=2,
            status="SUCCESS",
            latency_ms=retrieval_elapsed_ms,
            started_at=retrieval_started_at,
            completed_at=datetime.now(timezone.utc),
            metadata={
                "region_filter": region,
                "result_count": len(rag_results),
                "detected_intents": search_metadata.get("detected_intents") or [],
                "multi_intent_mode": search_metadata.get("multi_intent_mode", False),
            },
        )
    )

    # [2] 검색 결과가 없으면 안내 메시지 반환
    if not rag_results:
        return {
            "rag_results": [],
            "rag_intent_results": [],
            "messages": [
                {
                    "role": "assistant",
                    "content": "관련 정책 정보를 바로 찾지 못했습니다. 정책명이나 기관명, 지역, 분야를 조금 더 구체적으로 알려주시면 다시 찾아볼게요.",
                }
            ],
            "fallback_mode": "rag",
            "fallback_reason": "no_rag_results",
            "response_metadata": {
                "is_fallback": True,
                "response_source": "rag_empty_result",
                **search_metadata,
            },
            "node_logs": node_logs,
        }

    # [3] 상위 3개 청크를 컨텍스트 문자열로 조합
    # 상위 몇 개 근거만 문맥에 넣어 토큰 사용량을 줄이고,
    # 너무 많은 문서를 넣어서 답변 초점이 흐려지는 것도 막는다.
    context = _build_rag_context(rag_intent_results, rag_results)

    # [4] GPT 답변 생성
    generation_started_at = datetime.now(timezone.utc)
    generation_started = time.monotonic()
    # 검색된 정책 문서만 넘기면 답변이 일반적이기 쉽다.
    # 사업장 컨텍스트를 함께 넣어 "왜 이 사용자에게 맞는지"까지 설명하게 만든다.
    answer, usage = await _generate_rag_answer(
        client,
        last_msg,
        context,
        biz_info=biz_info,
        financial_data=state.get("financial_data") or {},
        multi_intent_mode=search_metadata.get("multi_intent_mode", False),
        detected_intents=search_metadata.get("detected_intents") or [],
    )
    fallback_mode: str | None = None
    fallback_reason: str | None = None
    response_metadata = {
        "is_fallback": False,
        "response_source": "rag_generated",
        **search_metadata,
    }
    if not usage:
        answer = _build_rag_fallback_answer(last_msg, rag_intent_results, rag_results)
        fallback_mode = "rag"
        fallback_reason = "generation_error"
        response_metadata = {
            "is_fallback": True,
            "response_source": "rag_fallback",
            **search_metadata,
        }
    generation_elapsed_ms = int((time.monotonic() - generation_started) * 1000)
    node_logs.append(
        build_node_log(
            node_name="rag_generation",
            sequence=3,
            status="SUCCESS" if answer else "ERROR",
            latency_ms=generation_elapsed_ms,
            model_name="gpt-4o-mini",
            tokens_in=getattr(usage, "prompt_tokens", None),
            tokens_out=getattr(usage, "completion_tokens", None),
            started_at=generation_started_at,
            completed_at=datetime.now(timezone.utc),
            metadata={
                "result_count": len(rag_results),
                "intent_group_count": len(rag_intent_results),
            },
        )
    )

    return {
        "rag_results": rag_results,
        "rag_intent_results": rag_intent_results,
        "messages": [{"role": "assistant", "content": answer}],
        "node_logs": node_logs,
        "fallback_mode": fallback_mode,
        "fallback_reason": fallback_reason,
        "response_metadata": response_metadata,
        "last_usage": {
            "tokens_in": getattr(usage, "prompt_tokens", None),
            "tokens_out": getattr(usage, "completion_tokens", None),
            "model_name": "gpt-4o-mini",
            "response_time_ms": generation_elapsed_ms,
        },
    }


async def _generate_rag_answer(
    client: AsyncOpenAI,
    question: str,
    context: str,
    *,
    biz_info: dict[str, Any] | None = None,
    financial_data: dict[str, Any] | None = None,
    multi_intent_mode: bool = False,
    detected_intents: list[str] | None = None,
) -> tuple[str, object | None]:
    """GPT 에 정책 컨텍스트와 질문을 전달하여 최종 답변을 생성한다.

    - 시스템 프롬프트에서 "근거 없는 내용 추측 금지"를 명시하여 환각(hallucination)을 방지한다.
    - temperature=0.2 로 낮게 설정해 일관된 형식의 답변을 유도한다.
    - API 호출 실패 시 안내 메시지와 None usage 를 반환한다.

    Returns:
        (answer_text, usage) — usage 는 토큰 사용량 집계용
    """
    needs_sections = multi_intent_mode or _requires_sectioned_rag_answer(question)
    detected_intent_text = ", ".join(detected_intents or []) or "없음"
    system_prompt = (
        "당신은 정책자금 전문 비서 비즈몽이다. 아래 정책 정보만 근거로 설명하고, "
        "사용자의 사업장 상황을 반영해 우선순위를 정리하세요. "
        "답변은 1) 핵심 판단, 2) 추천 정책/근거, 3) 확인해야 할 조건, 4) 다음 행동 순서로 작성하세요. "
        "근거가 없는 내용은 추측하지 말고 공고 원문 확인이 필요하다고 말하세요."
    )
    user_content = (
        # LLM이 DB를 직접 조회할 수 없으므로 필요한 사업장 정보를 프롬프트에 명시적으로 주입한다.
        # 이 값이 빠지면 지역 필터는 되어도 답변 근거가 사용자 상황과 분리될 수 있다.
        f"[사업장 정보]\n{_format_business_context(biz_info or {}, financial_data or {})}\n\n"
        f"[정책 정보]\n{context}\n\n"
        f"[질문]\n{question}"
    )

    # 생성이 실패해도 호출부에서 fallback 답변으로 복구할 수 있게
    # 빈 문자열과 None usage 를 반환한다.
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
        )
        return (response.choices[0].message.content or "").strip(), response.usage
    except Exception as exc:
        logger.warning("[rag] answer generation failed: %s", exc)
        return "", None


def _build_rag_fallback_answer(
    question: str,
    rag_intent_results: list[dict[str, Any]],
    rag_results: list[dict[str, Any]],
) -> str:
    """OpenAI 생성이 실패해도 검색 결과 기반 요약 답변을 만든다."""
    top_results = _prioritize_fallback_results(question, rag_results)[:3]
    if not top_results:
        return (
            "관련 정책 정보를 바로 찾지 못했습니다. 정책명이나 기관명, 지역, 분야를 조금 더 "
            "구체적으로 알려주시면 다시 찾아볼게요."
        )

    lines = ["지금 확인되는 관련 정책은 아래와 같습니다."]
    for idx, result in enumerate(top_results, start=1):
        title = result.get("title") or "정책명 미상"
        region = result.get("region") or "전국"
        support_type = result.get("support_type") or ""
        support_amount = result.get("support_amount_desc") or "지원 내용은 공고문 확인이 필요합니다."
        summary = result.get("ai_summary") or ""
        end_date = result.get("end_date") or "상시/공고문 확인"

        detail_parts = [region]
        if support_type:
            detail_parts.append(support_type)
        detail_parts.extend([support_amount, f"마감 {end_date}"])
        if summary:
            detail_parts.append(summary)
        lines.append(f"{idx}. {title}: " + " / ".join(detail_parts))

    if any(keyword in question for keyword in ("벤처", "특허", "기술창업", "it", "IT")):
        lines.append("질문에 벤처·특허·기술창업 조건이 들어 있어서 기술창업 성격의 정책을 우선 확인했습니다.")
    if any(keyword in question for keyword in ("고용", "월급", "인건비")):
        lines.append("질문에서 고용지원금 성격을 함께 찾고 있어 인건비·고용확대와 연결되는 정책을 우선 포함했습니다.")
    if any(keyword in question for keyword in ("보증금", "대출", "융자")):
        lines.append("보증금이나 대출 성격 질문은 운전자금·정책자금 계열 공고를 우선 확인하는 방식으로 정리했습니다.")
    if any(keyword in question for keyword in ("정책자금", "추천", "뭐")) and (
        _rag_results_contain_keyword(top_results, "운전자금")
        or _rag_results_contain_keyword(top_results, "운영자금")
    ):
        lines.append("목록 안에 운전자금 계열 공고가 포함되어 있어 운영비나 고정비 질문이면 해당 항목을 먼저 확인해 보셔도 됩니다.")
    if any(keyword in question for keyword in ("왜", "추천", "맞")):
        lines.append("추천 사유는 지역, 지원대상, 업종 또는 성장단계 키워드가 질문과 겹친 정책이 우선 검색됐기 때문입니다.")

    lines.append("세부 자격과 제외 조건은 실제 공고문 본문에서 마지막으로 한 번 더 확인하는 것이 안전합니다.")
    return "\n".join(lines)


def _rag_results_contain_keyword(
    rag_results: list[dict[str, Any]],
    keyword: str,
) -> bool:
    """상위 후보에 특정 키워드가 포함돼 있는지 확인한다."""
    fields = ("title", "support_type", "support_amount_desc", "ai_summary")
    for result in rag_results:
        for field in fields:
            value = result.get(field)
            if isinstance(value, str) and keyword in value:
                return True
    return False


def _prioritize_fallback_results(
    question: str,
    rag_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """넓은 정책자금 질문에서는 자금 성격이 드러나는 후보를 먼저 보여준다."""
    if not _is_broad_funding_question(question):
        return rag_results

    scored_results: list[tuple[int, int, dict[str, Any]]] = []
    for index, result in enumerate(rag_results):
        score = 0
        haystack = " ".join(
            str(result.get(field) or "")
            for field in ("title", "support_type", "support_amount_desc", "ai_summary")
        )
        if any(keyword in haystack for keyword in ("운전자금", "운영자금", "정책자금")):
            score += 3
        if "소상공인" in haystack:
            score += 1
        scored_results.append((score, -index, result))

    return [result for _, _, result in sorted(scored_results, reverse=True)]


def _is_broad_funding_question(question: str) -> bool:
    funding_markers = ("정책자금", "지원금", "운전자금", "대출", "융자", "보증금")
    broad_markers = ("뭐", "뭐야", "있어", "추천", "받을 수", "알려")
    return any(marker in question for marker in funding_markers) and any(
        marker in question for marker in broad_markers
    )


async def _generate_rag_answer(
    client: AsyncOpenAI,
    question: str,
    context: str,
    *,
    biz_info: dict[str, Any] | None = None,
    financial_data: dict[str, Any] | None = None,
    multi_intent_mode: bool = False,
    detected_intents: list[str] | None = None,
) -> tuple[str, object | None]:
    needs_sections = multi_intent_mode or _requires_sectioned_rag_answer(question)
    detected_intent_text = ", ".join(detected_intents or []) or "없음"
    system_prompt = (
        "당신은 정책자금 분석 도우미 BizMong이다. "
        "아래 정책 정보만 근거로 설명하고 근거 없는 추측은 하지 않는다. "
        "답변은 1) 판단 요약, 2) 추천 정책과 근거, 3) 확인할 조건, 4) 다음 행동 순서로 작성한다. "
        "복합 질문이면 의도별로 섹션을 분리해 답변하고, 각각/하나씩/두 가지 같은 표현이 있으면 섹션 분리를 반드시 지킨다."
    )
    user_content = (
        f"[사업자 정보]\n{_format_business_context(biz_info or {}, financial_data or {})}\n\n"
        f"[감지된 의도]\n{detected_intent_text}\n\n"
        f"[복합 의도 모드]\n{needs_sections}\n\n"
        f"[정책 정보]\n{context}\n\n"
        f"[질문]\n{question}"
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
        )
        return (response.choices[0].message.content or "").strip(), response.usage
    except Exception as exc:
        logger.warning("[rag] answer generation failed: %s", exc)
        return "", None


def _build_rag_fallback_answer(
    question: str,
    rag_intent_results: list[dict[str, Any]],
    rag_results: list[dict[str, Any]],
) -> str:
    if not rag_results:
        return "관련 정책 정보를 바로 찾지 못했어요. 정책명이나 기간, 지역, 지원 분야를 조금 더 구체적으로 알려주시면 다시 찾아볼게요."

    if len(rag_intent_results) > 1:
        lines = ["질문을 의도별로 나눠서 우선 확인된 정책을 정리했어요."]
        for group in rag_intent_results:
            grouped_results = _prioritize_fallback_results(question, group.get("results") or [])[:2]
            if not grouped_results:
                continue
            lines.append(f"[{group.get('intent_label') or group.get('intent')}]")
            lines.extend(_build_fallback_lines_for_results(grouped_results))
        lines.append("각 의도별 자격조건과 제외조건은 실제 공고문에서 마지막으로 다시 확인하는 것이 안전합니다.")
        return "\n".join(lines)

    top_results = _prioritize_fallback_results(question, rag_results)[:3]
    lines = ["지금 확인되는 관련 정책은 아래와 같습니다."]
    lines.extend(_build_fallback_lines_for_results(top_results))
    lines.append("자격조건과 제외조건은 실제 공고문에서 마지막으로 다시 확인하는 것이 안전합니다.")
    return "\n".join(lines)


def _prioritize_fallback_results(
    question: str,
    rag_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not _is_broad_funding_question(question):
        return rag_results

    scored_results: list[tuple[int, int, dict[str, Any]]] = []
    for index, result in enumerate(rag_results):
        score = 0
        haystack = " ".join(
            str(result.get(field) or "")
            for field in ("title", "support_type", "support_amount_desc", "ai_summary")
        )
        if any(keyword in haystack for keyword in ("운전자금", "운영자금", "정책자금")):
            score += 3
        if "소상공인" in haystack:
            score += 1
        scored_results.append((score, -index, result))

    return [result for _, _, result in sorted(scored_results, reverse=True)]


def _is_broad_funding_question(question: str) -> bool:
    funding_markers = ("정책자금", "지원자금", "운전자금", "대출", "융자", "보증금")
    broad_markers = ("뭐", "뭐야", "있어", "추천", "받을 수", "알려")
    return any(marker in question for marker in funding_markers) and any(
        marker in question for marker in broad_markers
    )


def _build_rag_context(
    rag_intent_results: list[dict[str, Any]],
    rag_results: list[dict[str, Any]],
) -> str:
    if len(rag_intent_results) > 1:
        sections: list[str] = []
        for group in rag_intent_results:
            top_results = group.get("results") or []
            if not top_results:
                continue
            body = "\n\n".join(
                f"[{result['title']}]\n{result['relevant_chunk']}"
                for result in top_results[:2]
            )
            sections.append(f"[의도: {group.get('intent_label') or group.get('intent')}]\n{body}")
        return "\n\n".join(sections)

    return "\n\n".join(
        f"[{result['title']}]\n{result['relevant_chunk']}"
        for result in rag_results[:3]
    )


def _requires_sectioned_rag_answer(question: str) -> bool:
    markers = ("각각", "각자", "하나씩", "한 개씩", "1개씩", "두 가지")
    return any(marker in question for marker in markers)


def _build_fallback_lines_for_results(results: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for idx, result in enumerate(results, start=1):
        title = result.get("title") or "정책명 미상"
        region = result.get("region") or "전국"
        support_type = result.get("support_type") or ""
        support_amount = result.get("support_amount_desc") or "지원 내용은 공고문 확인이 필요합니다."
        summary = result.get("ai_summary") or ""
        end_date = result.get("end_date") or "상시/공고문 확인"

        detail_parts = [region]
        if support_type:
            detail_parts.append(support_type)
        detail_parts.extend([support_amount, f"마감 {end_date}"])
        if summary:
            detail_parts.append(summary)
        lines.append(f"{idx}. {title}: " + " / ".join(detail_parts))
    return lines


def _format_business_context(
    biz_info: dict[str, Any],
    financial_data: dict[str, Any],
) -> str:
    """RAG 답변 프롬프트에 넣을 사업장 컨텍스트를 짧게 직렬화한다."""
    parts: list[str] = []
    mapping = {
        "biz_name": "상호",
        "region_sido": "지역",
        "region_sigungu": "시군구",
        "ksic_code": "업종코드",
        "sector_code": "업종분야",
        "establishment_date": "개업일",
        "is_ventured": "벤처기업",
        "has_patent": "특허보유",
        "is_female_ent": "여성기업",
    }
    for key, label in mapping.items():
        value = biz_info.get(key)
        if value not in (None, "", []):
            parts.append(f"{label}={value}")

    # 재무 정보는 숫자가 그대로 들어가도 LLM이 비교/주의사항을 설명하는 데 충분하다.
    # 화면 표시용 포맷팅은 프론트나 응답 생성 단계에서 별도로 처리한다.
    finance_mapping = {
        "snapshot_year": "재무연도",
        "annual_revenue": "연매출",
        "employee_count": "직원수",
        "debt_ratio": "부채비율",
        "tax_arrears_yn": "세금체납",
    }
    for key, label in finance_mapping.items():
        value = financial_data.get(key)
        if value not in (None, "", []):
            parts.append(f"{label}={value}")

    return ", ".join(parts) if parts else "등록된 사업장/재무 정보 없음"


def _get_last_user_message(messages: list) -> str:
    """메시지 목록에서 가장 최근 사용자 메시지의 텍스트를 추출한다.

    LangGraph 메시지는 dict 형태 또는 HumanMessage 객체 두 가지 형식이 혼재할 수 있어
    두 경우를 모두 처리한다.
    """
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            return msg.get("content", "")
        if hasattr(msg, "content") and getattr(msg, "type", "") == "human":
            return msg.content
    return ""
