"""Chat API routes for BizMong."""

import json
import uuid
from datetime import datetime
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.app.api.deps.business_deps import ActiveBusiness
from src.app.api.deps.chat_deps import BizMongAgentDep, ChatServiceDep
from src.app.core.response import api_json
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
    return api_json(status.HTTP_201_CREATED, data=data.model_dump(), message="success")


@router.get("/sessions")
async def get_chat_sessions(
    svc: ChatServiceDep,
    biz: ActiveBusiness,
):
    data = await svc.get_sessions(biz)
    return api_json(
        status.HTTP_200_OK,
        data=[item.model_dump() for item in data],
        message="success",
    )


@router.post("/sessions/{session_id}/messages")
async def send_chat_message(
    session_id: uuid.UUID,
    req: SendMessageRequest,
    svc: ChatServiceDep,
    biz: ActiveBusiness,
):
    data = await svc.send_message(biz, session_id, req)
    return api_json(status.HTTP_200_OK, data=data.model_dump(), message="success")


@router.get("/sessions/{session_id}/messages")
async def get_chat_messages(
    session_id: uuid.UUID,
    svc: ChatServiceDep,
    biz: ActiveBusiness,
):
    data = await svc.get_messages(biz, session_id)
    return api_json(
        status.HTTP_200_OK,
        data=[item.model_dump() for item in data],
        message="success",
    )


@router.patch("/sessions/{session_id}/summary")
async def auto_summary_chat_session(
    session_id: uuid.UUID,
    svc: ChatServiceDep,
    biz: ActiveBusiness,
):
    data = await svc.auto_summary(biz, session_id)
    return api_json(status.HTTP_200_OK, data=data.model_dump(), message="success")


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_session(
    session_id: uuid.UUID,
    svc: ChatServiceDep,
    biz: ActiveBusiness,
):
    await svc.delete_session(biz, session_id)


@router.post(
    "/sessions/{session_id}/agent-message",
    summary="BizMong 상담 메시지 전송",
    description=(
        "비즈몽은 정책자금 전문 비서형 상담 에이전트입니다.\n\n"
        "- general_qa: 정책 용어 설명, 사업장 고민 상담, 진단 결과 해석\n"
        "- rag: 특정 공고나 정책 문서 검색 기반 설명\n"
        "- stats: 동종업계 비교 통계 설명\n\n"
        "정밀진단과 시뮬레이션은 전용 페이지 기능이며, 채팅 안에서 직접 실행하지 않습니다."
    ),
)
async def send_agent_message(
    session_id: uuid.UUID,
    req: SendMessageRequest,
    svc: ChatServiceDep,
    agent: BizMongAgentDep,
    biz: ActiveBusiness,
):
    room = await svc._repo.get_chat_room_by_id(session_id)
    if not room or room.business_id != biz.id:
        raise HTTPException(status_code=403, detail="세션 접근 권한이 없습니다.")

    await svc._repo.create_chat_log(
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

    return api_json(status.HTTP_200_OK, data=response_data.model_dump(), message="success")


def _sse(event_type: str, payload: dict) -> str:
    return f"data: {json.dumps({'type': event_type, **payload}, ensure_ascii=False)}\n\n"


@router.post(
    "/sessions/{session_id}/stream",
    summary="BizMong 상담 스트리밍 메시지 전송",
    description=(
        "비즈몽은 정책자금 전문 비서처럼 답합니다.\n"
        "용어 설명, 공고 해석, 사업장 고민 상담, 통계 설명을 처리하며 "
        "정밀진단/시뮬레이션은 전용 페이지에서 진행하도록 안내합니다."
    ),
)
async def stream_agent_message(
    session_id: uuid.UUID,
    req: SendMessageRequest,
    request: Request,
    svc: ChatServiceDep,
    agent: BizMongAgentDep,
    biz: ActiveBusiness,
):
    room = await svc._repo.get_chat_room_by_id(session_id)
    if not room or room.business_id != biz.id:
        raise HTTPException(status_code=403, detail="세션 접근 권한이 없습니다.")

    await svc._repo.create_chat_log(
        user_id=biz.user_id,
        room_id=room.id,
        role="user",
        content=req.message,
    )
    await svc._session.commit()

    async def event_stream() -> AsyncGenerator[str, None]:
        from openai import AsyncOpenAI

        from src.app.agents.biz_mong.nodes.chitchat_node import (
            _GREETING_RESPONSES,
            _SYSTEM_PROMPT_GENERAL,
        )
        from src.app.agents.biz_mong.nodes.router_node import router_node
        from src.app.agents.biz_mong.state import make_initial_state
        from src.app.core.config import OPENAI_API_KEY

        openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        config = {"configurable": {"thread_id": str(room.id)}}
        existing = agent._graph.get_state(config)
        if existing and existing.values:
            init_state: dict = {"messages": [{"role": "user", "content": req.message}]}
        else:
            init_state = make_initial_state(
                user_id=str(biz.user_id),
                business_id=str(biz.id),
                room_id=str(room.id),
                first_message=req.message,
            )

        router_result = await router_node(init_state, client=openai_client)
        intent: str = router_result.get("current_agent", "general_qa")
        merged_state = {**init_state, **router_result}
        collected_content: list[str] = []

        if intent in ("greeting", "general_qa"):
            if intent == "greeting":
                yield _sse("status", {"text": "안녕하세요. 비즈몽입니다."})
                greeting_text = _GREETING_RESPONSES[0]
                for char in greeting_text:
                    collected_content.append(char)
                    yield _sse("token", {"content": char})
                full_content = greeting_text
            else:
                yield _sse("status", {"text": "대표님 질문에 맞게 쉽게 정리하고 있습니다..."})

                messages_hist: list = merged_state.get("messages") or []
                history = [
                    message
                    for message in messages_hist
                    if isinstance(message, dict)
                    and message.get("role") in ("user", "assistant")
                ][-12:]
                gpt_messages = [{"role": "system", "content": _SYSTEM_PROMPT_GENERAL}] + history

                stream = await openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=gpt_messages,
                    temperature=0.25,
                    max_tokens=450,
                    stream=True,
                )
                async for chunk in stream:
                    delta = chunk.choices[0].delta.content if chunk.choices else None
                    if delta:
                        collected_content.append(delta)
                        yield _sse("token", {"content": delta})

                full_content = "".join(collected_content)
        else:
            status_map = {
                "rag": "관련 공고와 정책 정보를 찾아보고 있습니다...",
                "stats": "동종업계 비교 정보를 정리하고 있습니다...",
            }
            yield _sse("status", {"text": status_map.get(intent, "답변을 준비하고 있습니다...")})

            final_state = await agent._graph.ainvoke(merged_state, config=config)
            agent_type = final_state.get("current_agent") or intent
            full_content = _build_response_content(agent_type, final_state)

            ai_log = await svc._repo.create_chat_log(
                user_id=biz.user_id,
                room_id=room.id,
                role="assistant",
                content=full_content,
            )
            await svc._session.commit()

            yield _sse(
                "done",
                {
                    "agent_type": agent_type,
                    "message_id": str(ai_log.id),
                    "content": full_content,
                    "diagnosis_report": None,
                    "simulation_report": None,
                    "stats_insight": final_state.get("stats_insight"),
                    "rag_results": final_state.get("rag_results"),
                },
            )
            return

        ai_log = await svc._repo.create_chat_log(
            user_id=biz.user_id,
            room_id=room.id,
            role="assistant",
            content=full_content,
        )
        await svc._session.commit()

        yield _sse(
            "done",
            {
                "agent_type": intent,
                "message_id": str(ai_log.id),
                "content": full_content,
                "diagnosis_report": None,
                "simulation_report": None,
                "stats_insight": None,
                "rag_results": None,
            },
        )

    origin = request.headers.get("origin", "")
    cors_headers: dict[str, str] = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }
    if origin:
        cors_headers["Access-Control-Allow-Origin"] = origin
        cors_headers["Access-Control-Allow-Credentials"] = "true"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers=cors_headers,
    )


def _build_response_content(agent_type: str, state: dict) -> str:
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
        return trend or comparison or "동종업계 비교 정보를 정리했습니다."

    return "답변을 정리했습니다."
