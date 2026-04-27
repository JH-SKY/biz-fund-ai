# src/app/agents/biz_mong/graph.py
"""BizMong 멀티 에이전트 메인 그래프.

아키텍처:
  START → router_node
  router_node → (conditional: current_agent) → {hard_filter, simulator, rag, stats}
  hard_filter → llm_evaluator
  llm_evaluator → (conditional: pending_intent) → {simulator, END}
  simulator → (conditional: guard) → {hard_filter, END}
  rag → END
  stats → END

[MemorySaver]:
  - 모듈 레벨 싱글톤으로 선언하여 동일 thread_id(= room_id) 에 대해
    여러 요청 간 대화 맥락이 유지된다.
  - 서버 재시작 시 소멸 → Write-through ChatLog 가 장기 영속성을 담당한다.

[Write-through]:
  - 각 terminal 노드(llm_evaluator, simulator, rag, stats) 완료 후
    중간 결과를 ChatLog 에 즉시 기록(별도 DB 세션)한다.
  - 서버 장애 또는 타임아웃 발생 시에도 진행된 노드의 결과가 보존된다.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from langgraph.graph import END, StateGraph
from langgraph.types import Command
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.agents.biz_mong.checkpointer import get_langgraph_checkpointer
from src.app.agents.biz_mong.checkpointer import initialize_langgraph_checkpointer
from src.app.agents.biz_mong.nodes.chitchat_node import chitchat_node
from src.app.agents.biz_mong.nodes.hard_filter import hard_filter_node
from src.app.agents.biz_mong.nodes.llm_evaluator import llm_evaluator_node
from src.app.agents.biz_mong.nodes.router_node import router_node
from src.app.agents.biz_mong.nodes.simulator import simulator_node
from src.app.agents.biz_mong.nodes.stats_node import stats_node
from src.app.agents.biz_mong.state import make_initial_state
from src.app.core.config import OPENAI_API_KEY
from src.app.domains.chat.model import ChatLog
from src.app.agents.biz_mong.tools.policy_rag import policy_rag_search

# SessionLocal 은 _write_through 에서만 사용하므로 지연 임포트로 처리한다.
# (모듈 로드 시 DATABASE_URL 미설정 환경에서 엔진 생성 오류 방지)

logger = logging.getLogger(__name__)

# ── MemorySaver 싱글톤 (프로세스 생애 동안 유지) ──────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
# BizMongAgent
# ═══════════════════════════════════════════════════════════════════════════════

class BizMongAgent:
    """LangGraph 기반 BizMong 멀티 에이전트.

    FastAPI 엔드포인트에서 요청마다 새 인스턴스를 생성한다.
    (session 은 요청마다 다르지만, _MEMORY_SAVER 는 공유된다.)

    사용 예:
        agent = BizMongAgent(session=db)
        result = await agent.run(
            user_id=str(user.id),
            business_id=str(biz.id),
            room_id=str(room.id),
            message="어떤 정책 자금을 받을 수 있나요?",
        )
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self._graph = self._build_graph()

    @classmethod
    async def create(cls, session: AsyncSession) -> "BizMongAgent":
        await initialize_langgraph_checkpointer()
        return cls(session=session)

    # ── 공개 API ──────────────────────────────────────────────────────────

    async def run(
        self,
        *,
        user_id: str,
        business_id: str,
        room_id: str,
        message: str,
    ) -> dict[str, Any]:
        """에이전트를 실행하고 최종 State 를 반환한다.

        Args:
            user_id:      현재 로그인 사용자 UUID 문자열
            business_id:  조회 사업장 UUID 문자열
            room_id:      ChatRoom.id (= LangGraph thread_id)
            message:      사용자 입력 메시지

        Returns:
            최종 State dict.
            caller 는 state["diagnosis_report"], state["simulation_report"] 등을 사용한다.
        """
        # thread_id = room_id 로 대화 맥락 유지
        config = {"configurable": {"thread_id": room_id}}

        # 현재 체크포인트가 있으면 메시지만 추가, 없으면 초기 상태 생성
        existing = self._graph.get_state(config)
        if existing and existing.values:
            # 기존 대화 재개: messages 에 새 메시지만 추가
            initial = {"messages": [{"role": "user", "content": message}]}
        else:
            initial = make_initial_state(
                user_id=user_id,
                business_id=business_id,
                room_id=room_id,
                first_message=message,
            )

        final_state = await self._graph.ainvoke(initial, config=config)
        return final_state

    # ── 그래프 빌드 ────────────────────────────────────────────────────────

    def _build_graph(self):
        """StateGraph 를 조립하고 컴파일한다."""
        session = self._session
        client = self._client

        # ── 노드 래퍼 (session/client 를 클로저로 주입) ──────────────────

        async def _router(state: dict) -> dict:
            return await router_node(state, client=client)

        async def _chitchat(state: dict) -> dict:
            return await chitchat_node(state, client=client)

        async def _hard_filter(state: dict) -> dict:
            result = await hard_filter_node(state, session=session)
            await _write_through(state, "diagnosis_filter", result)
            return result

        async def _llm_evaluator(state: dict) -> dict | Command:
            result = await llm_evaluator_node(state, client=client)
            # Command 이면 write-through 후 그대로 반환
            if isinstance(result, Command):
                await _write_through(state, "llm_evaluator", result.update or {})
                return result
            await _write_through(state, "llm_evaluator", result)
            return result

        async def _simulator(state: dict) -> dict | Command:
            result = await simulator_node(state, client=client)
            if isinstance(result, Command):
                # guard redirect — write-through 생략 (아직 실행 안 함)
                return result
            await _write_through(state, "simulator", result)
            return result

        async def _rag(state: dict) -> dict:
            result = await _run_rag(state, session=session, client=client)
            await _write_through(state, "rag", result)
            return result

        async def _stats(state: dict) -> dict:
            result = await stats_node(state, session=session)
            await _write_through(state, "stats", result)
            return result

        # ── 그래프 조립 ──────────────────────────────────────────────────
        builder = StateGraph(dict)

        builder.add_node("router", _router)
        builder.add_node("chitchat", _chitchat)
        builder.add_node("hard_filter", _hard_filter)
        builder.add_node("llm_evaluator", _llm_evaluator)
        builder.add_node("simulator", _simulator)
        builder.add_node("rag", _rag)
        builder.add_node("stats", _stats)

        builder.set_entry_point("router")

        # router → conditional (current_agent 기반)
        builder.add_conditional_edges(
            "router",
            lambda s: s.get("current_agent", "diagnosis"),
            {
                "greeting":   "chitchat",
                "general_qa": "chitchat",
                "diagnosis":  "hard_filter",
                "simulator":  "simulator",
                "rag":        "rag",
                "stats":      "stats",
            },
        )

        # chitchat → END (도구 없이 즉시 종료)
        builder.add_edge("chitchat", END)

        # diagnosis 서브 플로우 (순차)
        builder.add_edge("hard_filter", "llm_evaluator")

        # llm_evaluator 이후: pending_intent 가 있으면 simulator 로, 없으면 END
        # (Command 반환 시 LangGraph 가 자동 처리)
        builder.add_conditional_edges(
            "llm_evaluator",
            _route_after_evaluator,
            {"simulator": "simulator", "__end__": END},
        )

        # simulator 이후: guard 가 발동하면 hard_filter, 아니면 END
        # (simulator_node 가 Command(goto="hard_filter") 반환 → LangGraph 처리)
        builder.add_conditional_edges(
            "simulator",
            _route_after_simulator,
            {"hard_filter": "hard_filter", "__end__": END},
        )

        builder.add_edge("rag", END)
        builder.add_edge("stats", END)

        return builder.compile(checkpointer=get_langgraph_checkpointer())

    # ── Write-through 내부 함수는 클로저로 노드에서 호출 ─────────────────

# ═══════════════════════════════════════════════════════════════════════════════
# Write-through: 별도 세션으로 ChatLog 즉시 기록
# ═══════════════════════════════════════════════════════════════════════════════

async def _write_through(
    state: dict,
    node_name: str,
    result: dict,
) -> None:
    """노드 완료 시마다 ChatLog 에 중간 결과를 즉시 기록한다.

    [설계 의도]:
      - SessionLocal() 로 별도 세션을 사용하여 메인 트랜잭션과 격리한다.
      - 커밋 실패 시 로그만 남기고 에이전트 실행은 계속한다 (Write-through 는 보조 수단).
    """
    room_id: str = state.get("room_id", "")
    user_id: str = state.get("user_id", "")

    if not room_id or not user_id:
        return

    try:
        room_uuid = uuid.UUID(room_id)
        user_uuid = uuid.UUID(user_id)
    except (ValueError, AttributeError):
        return

    # result 에서 직렬화 가능한 요약만 추출
    summary = _summarize_result(node_name, result)

    try:
        from src.app.database.postgres.database import SessionLocal
        async with SessionLocal() as wt_session:
            # rag 노드의 경우 usage 메트릭을 함께 저장
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
            logger.debug("[write_through] node=%s room=%s 기록 완료", node_name, room_id[:8])
    except Exception as exc:
        logger.warning("[write_through] node=%s 기록 실패 (무시): %s", node_name, exc)


def _summarize_result(node_name: str, result: dict) -> str:
    """노드 결과에서 ChatLog 에 저장할 요약 텍스트를 생성한다."""
    try:
        if node_name == "diagnosis_filter":
            count = len(result.get("candidate_policies") or [])
            return json.dumps(
                {"node": "hard_filter", "passed_count": count},
                ensure_ascii=False,
            )
        elif node_name == "llm_evaluator":
            report = result.get("diagnosis_report") or {}
            return json.dumps(
                {
                    "node": "llm_evaluator",
                    "score": report.get("score"),
                    "top_policy": report.get("top_policy"),
                    "total_candidates": report.get("total_candidates"),
                },
                ensure_ascii=False,
            )
        elif node_name == "simulator":
            sim = result.get("simulation_report") or {}
            return json.dumps(
                {
                    "node": "simulator",
                    "original_score": sim.get("original_score"),
                    "virtual_score": sim.get("virtual_score"),
                    "diff": sim.get("diff"),
                },
                ensure_ascii=False,
            )
        elif node_name == "rag":
            return json.dumps(
                {"node": "rag", "results_count": len(result.get("rag_results") or [])},
                ensure_ascii=False,
            )
        elif node_name == "stats":
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
        return json.dumps({"node": node_name, "error": "직렬화 실패"}, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════════════════════
# RAG 노드 실행 함수
# ═══════════════════════════════════════════════════════════════════════════════

async def _run_rag(
    state: dict,
    session: AsyncSession,
    client: AsyncOpenAI,
) -> dict:
    """RAG 검색 + GPT-4o-mini 답변 생성."""
    import time as _time

    messages: list = state.get("messages") or []
    last_msg = _get_last_user_message(messages)
    biz_info: dict = state.get("biz_info") or {}
    region = biz_info.get("region_sido")

    # Hybrid RAG 검색
    rag_results = await policy_rag_search(last_msg, session, region_filter=region)

    if not rag_results:
        return {
            "rag_results": [],
            "messages": [{"role": "assistant", "content": "관련 정책 자금 정보를 찾지 못했습니다. 더 구체적인 키워드로 질문해 주세요."}],
        }

    # 검색된 청크로 답변 생성
    context = "\n\n".join(
        f"[{r['title']}]\n{r['relevant_chunk']}" for r in rag_results[:3]
    )

    t0 = _time.monotonic()
    answer, usage = await _generate_rag_answer(client, last_msg, context)
    elapsed_ms = int((_time.monotonic() - t0) * 1000)

    return {
        "rag_results": rag_results,
        "messages": [{"role": "assistant", "content": answer}],
        "last_usage": {
            "tokens_in": usage.prompt_tokens if usage else None,
            "tokens_out": usage.completion_tokens if usage else None,
            "model_name": "gpt-4o-mini",
            "response_time_ms": elapsed_ms,
        },
    }


async def _generate_rag_answer(
    client: AsyncOpenAI,
    question: str,
    context: str,
) -> tuple[str, object | None]:
    """RAG 검색 결과를 기반으로 답변을 생성한다. (content, usage) 튜플 반환"""
    system_prompt = (
        "당신은 대한민국 중소기업·소상공인 정책 자금 전문 상담사입니다. "
        "아래 제공된 정책 정보만을 근거로 질문에 답하세요. "
        "정보에 없는 내용은 '해당 정보가 공고에 명시되어 있지 않습니다'라고 답하세요."
    )
    user_content = f"[관련 정책 정보]\n{context}\n\n[질문]\n{question}"

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip(), response.usage
    except Exception as exc:
        logger.warning("[rag] 답변 생성 실패: %s", exc)
        return "답변 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.", None


# ═══════════════════════════════════════════════════════════════════════════════
# 라우팅 함수 (conditional_edges 용)
# ═══════════════════════════════════════════════════════════════════════════════

def _route_after_evaluator(state: dict) -> str:
    """llm_evaluator 완료 후 다음 노드 결정.

    pending_intent == "simulator" 이면 simulator 로, 아니면 END.
    """
    if state.get("pending_intent") == "simulator":
        return "simulator"
    return "__end__"


def _route_after_simulator(state: dict) -> str:
    """simulator 완료 후 다음 노드 결정.

    diagnosis_report 가 없고 pending_intent == "simulator" 이면 hard_filter 로 리다이렉트.
    """
    if (
        not (state.get("diagnosis_report") or {}).get("ranked_policies")
        and state.get("pending_intent") == "simulator"
    ):
        return "hard_filter"
    return "__end__"


def _get_last_user_message(messages: list) -> str:
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            return msg.get("content", "")
        if hasattr(msg, "content") and getattr(msg, "type", "") == "human":
            return msg.content
    return ""
