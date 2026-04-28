"""BizMong counselor graph."""

from __future__ import annotations

import json
import logging
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
from src.app.agents.biz_mong.tools.policy_rag import policy_rag_search
from src.app.core.config import OPENAI_API_KEY
from src.app.domains.chat.model import ChatLog

logger = logging.getLogger(__name__)


class BizMongAgent:
    """Counselor-style BizMong agent.

    The chat agent is intentionally lightweight:
    - `greeting` and `general_qa` answer like a policy-funding secretary
    - `rag` searches policy documents and explains them
    - `stats` compares with industry statistics

    Detailed diagnosis and simulation are handled on their own pages, not here.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self._graph = self._build_graph()

    @classmethod
    async def create(cls, session: AsyncSession) -> "BizMongAgent":
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
        config = {"configurable": {"thread_id": room_id}}
        existing = self._graph.get_state(config)

        if existing and existing.values:
            initial: dict[str, Any] = {"messages": [{"role": "user", "content": message}]}
        else:
            initial = make_initial_state(
                user_id=user_id,
                business_id=business_id,
                room_id=room_id,
                first_message=message,
            )

        return await self._graph.ainvoke(initial, config=config)

    def _build_graph(self):
        session = self._session
        client = self._client

        async def _router(state: dict) -> dict:
            return await router_node(state, client=client)

        async def _chitchat(state: dict) -> dict:
            return await chitchat_node(state, client=client)

        async def _rag(state: dict) -> dict:
            result = await _run_rag(state, session=session, client=client)
            await _write_through(state, "rag", result)
            return result

        async def _stats(state: dict) -> dict:
            result = await stats_node(state, session=session)
            await _write_through(state, "stats", result)
            return result

        builder = StateGraph(dict)
        builder.add_node("router", _router)
        builder.add_node("chitchat", _chitchat)
        builder.add_node("rag", _rag)
        builder.add_node("stats", _stats)

        builder.set_entry_point("router")
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
    import time as _time

    messages: list = state.get("messages") or []
    last_msg = _get_last_user_message(messages)
    biz_info: dict = state.get("biz_info") or {}
    region = biz_info.get("region_sido")

    rag_results = await policy_rag_search(last_msg, session, region_filter=region)

    if not rag_results:
        return {
            "rag_results": [],
            "messages": [
                {
                    "role": "assistant",
                    "content": "관련 정책 정보를 바로 찾지 못했습니다. 정책명, 기관명, 지역, 지원 분야를 조금 더 구체적으로 알려주시면 다시 찾아볼게요.",
                }
            ],
        }

    context = "\n\n".join(
        f"[{result['title']}]\n{result['relevant_chunk']}"
        for result in rag_results[:3]
    )

    started = _time.monotonic()
    answer, usage = await _generate_rag_answer(client, last_msg, context)
    elapsed_ms = int((_time.monotonic() - started) * 1000)

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
    system_prompt = (
        "너는 정책자금 전문 비서 비즈몽이다. 아래 검색된 정책 정보만 근거로 답하라. "
        "대표가 이해하기 쉽게 풀어서 설명하고, 핵심은 신청 자격, 지원 내용, 주의할 조건 순서로 정리하라. "
        "근거에 없는 내용은 추측하지 말고 공고 원문 확인이 필요하다고 말하라."
    )
    user_content = f"[정책 정보]\n{context}\n\n[질문]\n{question}"

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
        return "답변을 정리하는 중 오류가 생겼습니다. 같은 질문을 한 번 더 보내주시면 다시 확인해볼게요.", None


def _get_last_user_message(messages: list) -> str:
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            return msg.get("content", "")
        if hasattr(msg, "content") and getattr(msg, "type", "") == "human":
            return msg.content
    return ""
