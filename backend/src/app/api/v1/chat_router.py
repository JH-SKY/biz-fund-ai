"""Chat API routes for BizMong."""

from __future__ import annotations

from datetime import datetime
import json
import uuid
import time
from typing import Any, AsyncGenerator, Optional
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel

from src.app.agents.biz_mong.nodes.chitchat_node import (
    PROMPT_VERSION_GENERAL,
    _GREETING_RESPONSES,
    _SYSTEM_PROMPT_GENERAL,
)
from src.app.agents.biz_mong.nodes.router_node import router_node
from src.app.agents.biz_mong.state import make_initial_state
from src.app.agents.biz_mong.telemetry import estimate_cost_usd
from src.app.api.deps.business_deps import ActiveBusiness
from src.app.api.deps.chat_deps import BizMongAgentDep, ChatServiceDep
from src.app.core.config import OPENAI_API_KEY
from src.app.core.response import api_json
from src.app.domains.chat.model import AgentNodeLog, AgentRunLog
from src.app.domains.chat.schema import CreateSessionRequest, SendMessageRequest

router = APIRouter(prefix="/chats", tags=["chats"])


class AgentMessageResponse(BaseModel):
    session_id: str
    message_id: str
    role: str
    content: str
    agent_type: str
    diagnosis_report: Optional[dict] = None
    simulation_report: Optional[dict] = None
    stats_insight: Optional[dict] = None
    rag_results: Optional[list] = None
    created_at: datetime


@router.post("/sessions")
async def create_chat_session(
    req: CreateSessionRequest,
    svc: ChatServiceDep,
    biz: ActiveBusiness,
):
    data = await svc.create_session(biz, req)
    return api_json(http_status=status.HTTP_201_CREATED, data=data.model_dump(), message="success")


@router.get("/sessions")
async def get_chat_sessions(
    svc: ChatServiceDep,
    biz: ActiveBusiness,
):
    data = await svc.get_sessions(biz)
    return api_json(http_status=status.HTTP_200_OK, data=[item.model_dump() for item in data], message="success")


@router.post("/sessions/{session_id}/messages")
async def send_chat_message(
    session_id: uuid.UUID,
    req: SendMessageRequest,
    svc: ChatServiceDep,
    biz: ActiveBusiness,
):
    data = await svc.send_message(biz, session_id, req)
    return api_json(http_status=status.HTTP_200_OK, data=data.model_dump(), message="success")


@router.get("/sessions/{session_id}/messages")
async def get_chat_messages(
    session_id: uuid.UUID,
    svc: ChatServiceDep,
    biz: ActiveBusiness,
):
    data = await svc.get_messages(biz, session_id)
    return api_json(http_status=status.HTTP_200_OK, data=[item.model_dump() for item in data], message="success")


@router.patch("/sessions/{session_id}/summary")
async def auto_summary_chat_session(
    session_id: uuid.UUID,
    svc: ChatServiceDep,
    biz: ActiveBusiness,
):
    data = await svc.auto_summary(biz, session_id)
    return api_json(http_status=status.HTTP_200_OK, data=data.model_dump(), message="success")


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_session(
    session_id: uuid.UUID,
    svc: ChatServiceDep,
    biz: ActiveBusiness,
):
    await svc.delete_session(biz, session_id)


@router.post("/sessions/{session_id}/agent-message")
async def send_agent_message(
    session_id: uuid.UUID,
    req: SendMessageRequest,
    svc: ChatServiceDep,
    agent: BizMongAgentDep,
    biz: ActiveBusiness,
):
    room = await _verify_room_access(svc, biz, session_id)
    run_started_at = datetime.utcnow()

    user_log = await svc._repo.create_chat_log(
        user_id=biz.user_id,
        room_id=room.id,
        role="user",
        content=req.message,
    )
    await svc._session.commit()

    final_state = await agent.run(
        user_id=str(biz.user_id),
        business_id=str(biz.id),
        room_id=str(room.id),
        message=req.message,
    )

    agent_type = final_state.get("current_agent") or "general_qa"
    content = _build_response_content(agent_type, final_state)

    ai_log = await svc._repo.create_chat_log(
        user_id=biz.user_id,
        room_id=room.id,
        role="assistant",
        content=content,
    )
    await svc._session.commit()

    await _persist_agent_run(
        svc=svc,
        biz=biz,
        room_id=room.id,
        user_log_id=user_log.id,
        assistant_log_id=ai_log.id,
        question=req.message,
        route_intent=final_state.get("current_agent") or "general_qa",
        final_agent=agent_type,
        node_logs=_normalize_node_logs(final_state.get("node_logs")),
        started_at=run_started_at,
        completed_at=datetime.utcnow(),
        first_token_latency_ms=None,
        prompt_version=final_state.get("prompt_version") or PROMPT_VERSION_GENERAL,
        rag_hit_count=len(final_state.get("rag_results") or []),
        fallback_mode=final_state.get("fallback_mode"),
        fallback_reason=final_state.get("fallback_reason"),
    )

    response_data = AgentMessageResponse(
        session_id=str(session_id),
        message_id=str(ai_log.id),
        role="assistant",
        content=content,
        agent_type=agent_type,
        diagnosis_report=None,
        simulation_report=None,
        stats_insight=final_state.get("stats_insight") or None,
        rag_results=final_state.get("rag_results") or None,
        created_at=ai_log.created_at,
    )
    return api_json(http_status=status.HTTP_200_OK, data=response_data.model_dump(), message="success")


def _sse(event_type: str, payload: dict[str, Any]) -> str:
    return f"data: {json.dumps({'type': event_type, **payload}, ensure_ascii=False)}\n\n"


@router.post("/sessions/{session_id}/stream")
async def stream_agent_message(
    session_id: uuid.UUID,
    req: SendMessageRequest,
    request: Request,
    svc: ChatServiceDep,
    agent: BizMongAgentDep,
    biz: ActiveBusiness,
):
    room = await _verify_room_access(svc, biz, session_id)
    user_log = await svc._repo.create_chat_log(
        user_id=biz.user_id,
        room_id=room.id,
        role="user",
        content=req.message,
    )
    await svc._session.commit()

    async def event_stream() -> AsyncGenerator[str, None]:
        run_started_at = datetime.utcnow()
        run_started_mono = time.monotonic()
        first_token_latency_ms: int | None = None
        openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        config = {"configurable": {"thread_id": str(room.id)}}
        existing = agent._graph.get_state(config)
        if existing and existing.values:
            init_state: dict[str, Any] = {"messages": [{"role": "user", "content": req.message}]}
        else:
            init_state = make_initial_state(
                user_id=str(biz.user_id),
                business_id=str(biz.id),
                room_id=str(room.id),
                first_message=req.message,
            )

        try:
            router_result = await router_node(init_state, client=openai_client)
            intent: str = router_result.get("current_agent", "general_qa")
            merged_state = {**init_state, **router_result}
            collected_content: list[str] = []
            node_logs = _normalize_node_logs(router_result.get("node_logs"))
            prompt_version = PROMPT_VERSION_GENERAL
            fallback_mode = router_result.get("fallback_mode")
            fallback_reason = router_result.get("fallback_reason")

            if intent in ("greeting", "general_qa"):
                qa_started_at = datetime.utcnow()
                qa_started_mono = time.monotonic()
                usage = None

                if intent == "greeting":
                    yield _sse("status", {"text": "안녕하세요. 비즈몽입니다."})
                    greeting_text = _GREETING_RESPONSES[0]
                    for char in greeting_text:
                        if first_token_latency_ms is None:
                            first_token_latency_ms = int((time.monotonic() - run_started_mono) * 1000)
                        collected_content.append(char)
                        yield _sse("token", {"content": char})
                    full_content = greeting_text
                else:
                    yield _sse("status", {"text": "질문을 이해하기 쉽게 정리해서 답변드리고 있어요..."})
                    history = [
                        message
                        for message in (merged_state.get("messages") or [])
                        if isinstance(message, dict) and message.get("role") in ("user", "assistant")
                    ][-12:]
                    gpt_messages = [{"role": "system", "content": _SYSTEM_PROMPT_GENERAL}] + history
                    stream = await openai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=gpt_messages,
                        temperature=0.25,
                        max_tokens=450,
                        stream=True,
                        stream_options={"include_usage": True},
                    )
                    async for chunk in stream:
                        if getattr(chunk, "usage", None) is not None:
                            usage = chunk.usage
                        delta = chunk.choices[0].delta.content if chunk.choices else None
                        if delta:
                            if first_token_latency_ms is None:
                                first_token_latency_ms = int((time.monotonic() - run_started_mono) * 1000)
                            collected_content.append(delta)
                            yield _sse("token", {"content": delta})
                    full_content = "".join(collected_content)

                node_logs.append(
                    {
                        "node_name": "general_qa",
                        "sequence": 2,
                        "status": "SUCCESS",
                        "latency_ms": int((time.monotonic() - qa_started_mono) * 1000),
                        "model_name": "gpt-4o-mini" if intent == "general_qa" else None,
                        "tokens_in": getattr(usage, "prompt_tokens", None),
                        "tokens_out": getattr(usage, "completion_tokens", None),
                        "cost_usd": estimate_cost_usd(
                            model_name="gpt-4o-mini" if intent == "general_qa" else None,
                            tokens_in=getattr(usage, "prompt_tokens", None),
                            tokens_out=getattr(usage, "completion_tokens", None),
                        ),
                        "started_at": qa_started_at,
                        "completed_at": datetime.utcnow(),
                        "error_code": None,
                        "error_message": None,
                        "metadata": {"mode": intent, "prompt_version": prompt_version},
                    }
                )
                agent_type = intent
                stats_insight = None
                rag_results = None
            else:
                status_map = {
                    "rag": "관련 공고와 정책 정보를 찾아보고 있어요...",
                    "stats": "비슷한 사업장 통계와 비교 정보를 정리하고 있어요...",
                }
                yield _sse("status", {"text": status_map.get(intent, "답변을 준비하고 있어요...")})
                final_state = await agent._graph.ainvoke(merged_state, config=config)
                agent_type = final_state.get("current_agent") or intent
                full_content = _build_response_content(agent_type, final_state)
                node_logs = _normalize_node_logs(final_state.get("node_logs"))
                prompt_version = final_state.get("prompt_version") or prompt_version
                stats_insight = final_state.get("stats_insight")
                rag_results = final_state.get("rag_results")

            ai_log = await svc._repo.create_chat_log(
                user_id=biz.user_id,
                room_id=room.id,
                role="assistant",
                content=full_content,
            )
            await svc._session.commit()

            await _persist_agent_run(
                svc=svc,
                biz=biz,
                room_id=room.id,
                user_log_id=user_log.id,
                assistant_log_id=ai_log.id,
                question=req.message,
                route_intent=intent,
                final_agent=agent_type,
                node_logs=node_logs,
                started_at=run_started_at,
                completed_at=datetime.utcnow(),
                first_token_latency_ms=first_token_latency_ms,
                prompt_version=prompt_version,
                rag_hit_count=len(rag_results or []),
                fallback_mode=fallback_mode,
                fallback_reason=fallback_reason,
            )

            yield _sse(
                "done",
                {
                    "agent_type": agent_type,
                    "message_id": str(ai_log.id),
                    "content": full_content,
                    "diagnosis_report": None,
                    "simulation_report": None,
                    "stats_insight": stats_insight,
                    "rag_results": rag_results,
                },
            )
        except Exception as exc:
            await _persist_agent_run(
                svc=svc,
                biz=biz,
                room_id=room.id,
                user_log_id=user_log.id,
                assistant_log_id=None,
                question=req.message,
                route_intent=None,
                final_agent=None,
                node_logs=[],
                started_at=run_started_at,
                completed_at=datetime.utcnow(),
                first_token_latency_ms=first_token_latency_ms,
                prompt_version=PROMPT_VERSION_GENERAL,
                rag_hit_count=0,
                status="ERROR",
                error_code=exc.__class__.__name__,
                error_message=str(exc),
            )
            raise

    origin = request.headers.get("origin", "")
    cors_headers: dict[str, str] = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }
    if origin:
        cors_headers["Access-Control-Allow-Origin"] = origin
        cors_headers["Access-Control-Allow-Credentials"] = "true"

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=cors_headers)


def _build_response_content(agent_type: str, state: dict[str, Any]) -> str:
    if agent_type in ("greeting", "general_qa", "rag"):
        messages = state.get("messages") or []
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "assistant":
                return msg.get("content", "")
            if hasattr(msg, "type") and msg.type == "ai":
                return msg.content
        return "궁금한 점을 편하게 물어보세요."

    if agent_type == "stats":
        insight = state.get("stats_insight") or {}
        comparison = insight.get("peer_comparison", "")
        trend = insight.get("market_trend", "")
        if trend and comparison:
            return f"{trend}\n\n{comparison}"
        return trend or comparison or "통계 비교 정보를 정리했습니다."

    return "답변을 정리했습니다."


async def _verify_room_access(
    svc: ChatServiceDep,
    biz: ActiveBusiness,
    session_id: uuid.UUID,
):
    room = await svc._repo.get_chat_room_by_id(session_id)
    if not room or room.business_id != biz.id:
        raise HTTPException(status_code=403, detail="세션 접근 권한이 없습니다.")
    return room


def _normalize_node_logs(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    logs: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            logs.append(item)
    return logs


async def _persist_agent_run(
    *,
    svc: ChatServiceDep,
    biz: ActiveBusiness,
    room_id: uuid.UUID,
    user_log_id: uuid.UUID,
    assistant_log_id: uuid.UUID | None,
    question: str,
    route_intent: str | None,
    final_agent: str | None,
    node_logs: list[dict[str, Any]],
    started_at: datetime,
    completed_at: datetime,
    first_token_latency_ms: int | None,
    prompt_version: str | None,
    rag_hit_count: int,
    fallback_mode: str | None = None,
    fallback_reason: str | None = None,
    status: str = "SUCCESS",
    error_code: str | None = None,
    error_message: str | None = None,
) -> None:
    total_tokens_in = sum((log.get("tokens_in") or 0) for log in node_logs) or None
    total_tokens_out = sum((log.get("tokens_out") or 0) for log in node_logs) or None
    total_cost: Decimal | None = None
    raw_cost = sum(float(log.get("cost_usd") or 0) for log in node_logs)
    if raw_cost > 0:
        total_cost = Decimal(str(raw_cost))
    model_name = next((log.get("model_name") for log in reversed(node_logs) if log.get("model_name")), None)

    run = AgentRunLog(
        room_id=room_id,
        user_id=biz.user_id,
        business_id=biz.id,
        user_message_log_id=user_log_id,
        assistant_message_log_id=assistant_log_id,
        route_intent=route_intent,
        final_agent=final_agent,
        prompt_version=prompt_version,
        graph_version="bizmong-graph-v1",
        rag_strategy_version="policy-rag-v1",
        model_name=model_name,
        status=status,
        fallback_mode=fallback_mode,
        fallback_reason=fallback_reason,
        question_preview=question[:300],
        started_at=started_at,
        completed_at=completed_at,
        total_latency_ms=max(0, int((completed_at - started_at).total_seconds() * 1000)),
        first_token_latency_ms=first_token_latency_ms,
        tokens_in=total_tokens_in,
        tokens_out=total_tokens_out,
        total_cost_usd=total_cost,
        rag_hit_count=rag_hit_count,
        error_code=error_code,
        error_message=error_message,
    )
    svc._session.add(run)
    await svc._session.flush()

    for idx, node in enumerate(node_logs, start=1):
        svc._session.add(
            AgentNodeLog(
                run_id=run.id,
                node_name=node.get("node_name") or f"node_{idx}",
                sequence=int(node.get("sequence") or idx),
                status=node.get("status") or "SUCCESS",
                model_name=node.get("model_name"),
                started_at=node.get("started_at"),
                completed_at=node.get("completed_at"),
                latency_ms=node.get("latency_ms"),
                tokens_in=node.get("tokens_in"),
                tokens_out=node.get("tokens_out"),
                cost_usd=node.get("cost_usd"),
                error_code=node.get("error_code"),
                error_message=node.get("error_message"),
                metadata=node.get("metadata"),
            )
        )

    await svc._session.commit()
