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
            initial: dict[str, Any] = {"messages": [{"role": "user", "content": message}]}
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
        builder.add_node("router", _router)
        builder.add_node("chitchat", _chitchat)
        builder.add_node("rag", _rag)
        builder.add_node("stats", _stats)

        builder.set_entry_point("router")
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
    rag_results = await policy_rag_search(last_msg, session, region_filter=region)
    retrieval_elapsed_ms = int((time.monotonic() - retrieval_started) * 1000)
    node_logs.append(
        build_node_log(
            node_name="rag_retrieval",
            sequence=2,
            status="SUCCESS",
            latency_ms=retrieval_elapsed_ms,
            started_at=retrieval_started_at,
            completed_at=datetime.now(timezone.utc),
            metadata={"region_filter": region, "result_count": len(rag_results)},
        )
    )

    # [2] 검색 결과가 없으면 안내 메시지 반환
    if not rag_results:
        return {
            "rag_results": [],
            "messages": [
                {
                    "role": "assistant",
                    "content": "관련 정책 정보를 바로 찾지 못했습니다. 정책명이나 기관명, 지역, 분야를 조금 더 구체적으로 알려주시면 다시 찾아볼게요.",
                }
            ],
            "node_logs": node_logs,
        }

    # [3] 상위 3개 청크를 컨텍스트 문자열로 조합
    # 상위 몇 개 근거만 문맥에 넣어 토큰 사용량을 줄이고,
    # 너무 많은 문서를 넣어서 답변 초점이 흐려지는 것도 막는다.
    context = "\n\n".join(
        f"[{result['title']}]\n{result['relevant_chunk']}"
        for result in rag_results[:3]
    )

    # [4] GPT 답변 생성
    generation_started_at = datetime.now(timezone.utc)
    generation_started = time.monotonic()
    answer, usage = await _generate_rag_answer(client, last_msg, context)
    if not usage:
        answer = _build_rag_fallback_answer(last_msg, rag_results)
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
            metadata={"result_count": len(rag_results)},
        )
    )

    return {
        "rag_results": rag_results,
        "messages": [{"role": "assistant", "content": answer}],
        "node_logs": node_logs,
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
) -> tuple[str, object | None]:
    """GPT 에 정책 컨텍스트와 질문을 전달하여 최종 답변을 생성한다.

    - 시스템 프롬프트에서 "근거 없는 내용 추측 금지"를 명시하여 환각(hallucination)을 방지한다.
    - temperature=0.2 로 낮게 설정해 일관된 형식의 답변을 유도한다.
    - API 호출 실패 시 안내 메시지와 None usage 를 반환한다.

    Returns:
        (answer_text, usage) — usage 는 토큰 사용량 집계용
    """
    system_prompt = (
        "당신은 정책자금 전문 비서 비즈몽이다. 아래 정책 정보만 근거로 설명하고, "
        "지원 대상, 신청 자격, 지원 내용, 주의할 조건 순서로 간단히 정리하라. "
        "근거가 없는 내용은 추측하지 말고 공고 원문 확인이 필요하다고 말하라."
    )
    user_content = f"[정책 정보]\n{context}\n\n[질문]\n{question}"

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
    rag_results: list[dict[str, Any]],
) -> str:
    """OpenAI 생성이 실패해도 검색 결과 기반 요약 답변을 만든다."""
    top_results = rag_results[:3]
    if not top_results:
        return (
            "관련 정책 정보를 바로 찾지 못했습니다. 정책명이나 기관명, 지역, 분야를 조금 더 "
            "구체적으로 알려주시면 다시 찾아볼게요."
        )

    lines = ["지금 확인되는 관련 정책은 아래와 같습니다."]
    for idx, result in enumerate(top_results, start=1):
        title = result.get("title") or "정책명 미상"
        region = result.get("region") or "전국"
        support_amount = result.get("support_amount_desc") or "지원 내용은 공고문 확인이 필요합니다."
        summary = result.get("ai_summary") or ""
        end_date = result.get("end_date") or "상시/공고문 확인"

        detail_parts = [region, support_amount, f"마감 {end_date}"]
        if summary:
            detail_parts.append(summary)
        lines.append(f"{idx}. {title}: " + " / ".join(detail_parts))

    if any(keyword in question for keyword in ("벤처", "특허", "기술창업", "it", "IT")):
        lines.append("질문에 벤처·특허·기술창업 조건이 들어 있어서 기술창업 성격의 정책을 우선 확인했습니다.")
    if any(keyword in question for keyword in ("고용", "월급", "인건비")):
        lines.append("질문에서 고용지원금 성격을 함께 찾고 있어 인건비·고용확대와 연결되는 정책을 우선 포함했습니다.")
    if any(keyword in question for keyword in ("보증금", "대출", "융자")):
        lines.append("보증금이나 대출 성격 질문은 운전자금·정책자금 계열 공고를 우선 확인하는 방식으로 정리했습니다.")
    if any(keyword in question for keyword in ("왜", "추천", "맞")):
        lines.append("추천 사유는 지역, 지원대상, 업종 또는 성장단계 키워드가 질문과 겹친 정책이 우선 검색됐기 때문입니다.")

    lines.append("세부 자격과 제외 조건은 실제 공고문 본문에서 마지막으로 한 번 더 확인하는 것이 안전합니다.")
    return "\n".join(lines)


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
