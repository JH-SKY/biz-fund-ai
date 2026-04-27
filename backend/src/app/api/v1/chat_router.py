"""채팅 API 라우터."""

import json
import uuid
from datetime import datetime
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.app.api.deps.business_deps import ActiveBusiness
from src.app.api.deps.chat_deps import BizMongAgentDep, ChatServiceDep
from src.app.core.response import api_json
from src.app.domains.chat.schema import (
    CreateSessionRequest,
    SendMessageRequest,
)

router = APIRouter(prefix="/chats", tags=["chats"])


# ── 에이전트 전용 응답 스키마 ───────────────────────────────────────────────────

class AgentMessageResponse(BaseModel):
    """BizMong 멀티 에이전트 응답 스키마."""

    session_id: str
    message_id: str
    role: str
    content: str                              # 사용자에게 보여줄 요약 텍스트
    agent_type: str                           # "diagnosis" | "simulator" | "rag" | "stats"
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
    """새로운 AI 상담 세션 생성."""
    data = await svc.create_session(biz, req)
    return api_json(
        http_status=status.HTTP_201_CREATED,
        data=data.model_dump(),
        message="success",
    )


@router.get("/sessions")
async def get_chat_sessions(
    svc: ChatServiceDep,
    biz: ActiveBusiness,
):
    """사업장 소유의 상담 세션 목록 조회."""
    data = await svc.get_sessions(biz)
    return api_json(
        http_status=status.HTTP_200_OK,
        data=[d.model_dump() for d in data],
        message="success",
    )


@router.post("/sessions/{session_id}/messages")
async def send_chat_message(
    session_id: uuid.UUID,
    req: SendMessageRequest,
    svc: ChatServiceDep,
    biz: ActiveBusiness,
):
    """기존 세션에 질문 보내기 및 AI 답변 수신."""
    data = await svc.send_message(biz, session_id, req)
    return api_json(
        http_status=status.HTTP_200_OK,
        data=data.model_dump(),
        message="success",
    )


@router.get("/sessions/{session_id}/messages")
async def get_chat_messages(
    session_id: uuid.UUID,
    svc: ChatServiceDep,
    biz: ActiveBusiness,
):
    """특정 상담 세션의 대화 내역 전체 조회."""
    data = await svc.get_messages(biz, session_id)
    return api_json(
        http_status=status.HTTP_200_OK,
        data=[d.model_dump() for d in data],
        message="success",
    )


@router.patch("/sessions/{session_id}/summary")
async def auto_summary_chat_session(
    session_id: uuid.UUID,
    svc: ChatServiceDep,
    biz: ActiveBusiness,
):
    """대화 내용을 바탕으로 제목 자동 요약."""
    data = await svc.auto_summary(biz, session_id)
    return api_json(
        http_status=status.HTTP_200_OK,
        data=data.model_dump(),
        message="success",
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_session(
    session_id: uuid.UUID,
    svc: ChatServiceDep,
    biz: ActiveBusiness,
):
    """상담 세션 삭제 (Soft Delete)."""
    await svc.delete_session(biz, session_id)


# ── BizMong 멀티 에이전트 엔드포인트 ───────────────────────────────────────────

@router.post(
    "/sessions/{session_id}/agent-message",
    summary="BizMong 멀티 에이전트 메시지 전송",
    description=(
        "사용자 메시지를 LangGraph 기반 멀티 에이전트로 처리한다.\n\n"
        "- **diagnosis**: 정책 자금 진단 (하드필터 → Batch LLM 채점)\n"
        "- **simulator**: 조건 변경 시 점수 시뮬레이션\n"
        "- **rag**: 특정 정책 질의응답 (Hybrid RAG)\n"
        "- **stats**: 동종업계 통계 비교\n\n"
        "대화 맥락은 session_id 기준으로 MemorySaver 에 유지되며, "
        "각 노드 완료마다 chat_logs 에 Write-through 기록된다."
    ),
)
async def send_agent_message(
    session_id: uuid.UUID,
    req: SendMessageRequest,
    svc: ChatServiceDep,
    agent: BizMongAgentDep,
    biz: ActiveBusiness,
):
    """BizMong 멀티 에이전트에 메시지를 전달하고 결과를 반환한다."""

    # 1. 세션 소유권 검증 (기존 ChatService 활용)
    room = await svc._repo.get_chat_room_by_id(session_id)
    if not room or room.business_id != biz.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="세션에 접근 권한이 없습니다.")

    # 2. 사용자 메시지 ChatLog 저장
    await svc._repo.create_chat_log(
        user_id=biz.user_id,
        room_id=room.id,
        role="user",
        content=req.message,
    )
    await svc._session.commit()

    # 3. BizMong 에이전트 실행
    final_state = await agent.run(
        user_id=str(biz.user_id),
        business_id=str(biz.id),
        room_id=str(room.id),
        message=req.message,
    )

    # 4. 에이전트 타입 및 사용자 응답 텍스트 결정
    agent_type = final_state.get("current_agent") or "diagnosis"
    content = _build_response_content(agent_type, final_state)

    # 5. 최종 AI 응답을 ChatLog 에 저장
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
        diagnosis_report=final_state.get("diagnosis_report") or None,
        simulation_report=final_state.get("simulation_report") or None,
        stats_insight=final_state.get("stats_insight") or None,
        rag_results=final_state.get("rag_results") or None,
        created_at=ai_log.created_at,
    )

    return api_json(
        http_status=status.HTTP_200_OK,
        data=response_data.model_dump(),
        message="success",
    )


# ── SSE 스트리밍 엔드포인트 ─────────────────────────────────────────────────

def _sse(event_type: str, payload: dict) -> str:
    """SSE 이벤트 한 줄 생성."""
    return f"data: {json.dumps({'type': event_type, **payload}, ensure_ascii=False)}\n\n"


@router.post(
    "/sessions/{session_id}/stream",
    summary="BizMong 스트리밍 메시지 전송 (SSE)",
    description=(
        "greeting/general_qa 는 GPT 토큰 스트리밍, "
        "diagnosis·simulator·rag·stats 는 진행 상태 이벤트 + 완료 이벤트를 반환한다.\n\n"
        "SSE 이벤트 형식:\n"
        "- `{type:'status', text:'...'}` — 처리 중 안내\n"
        "- `{type:'token', content:'...'}` — 텍스트 토큰 (chitchat 전용)\n"
        "- `{type:'done', agent_type, message_id, content, diagnosis_report, ...}`"
    ),
)
async def stream_agent_message(
    session_id: uuid.UUID,
    req: SendMessageRequest,
    svc: ChatServiceDep,
    agent: BizMongAgentDep,
    biz: ActiveBusiness,
):
    """SSE 기반 스트리밍 응답."""

    # 세션 소유권 검증
    room = await svc._repo.get_chat_room_by_id(session_id)
    if not room or room.business_id != biz.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="세션에 접근 권한이 없습니다.")

    # 사용자 메시지 저장
    await svc._repo.create_chat_log(
        user_id=biz.user_id,
        room_id=room.id,
        role="user",
        content=req.message,
    )
    await svc._session.commit()

    async def event_stream() -> AsyncGenerator[str, None]:
        from src.app.agents.biz_mong.nodes.router_node import router_node
        from src.app.agents.biz_mong.state import make_initial_state
        from openai import AsyncOpenAI
        from src.app.core.config import OPENAI_API_KEY

        openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

        # 1. 라우터로 intent 먼저 파악
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
        intent: str = router_result.get("current_agent", "diagnosis")
        merged_state = {**init_state, **router_result}

        collected_content: list[str] = []

        # 2. chitchat (greeting/general_qa) → 토큰 스트리밍
        if intent in ("greeting", "general_qa"):
            async def on_token(token: str) -> None:
                collected_content.append(token)
                # greeting 은 한 번에 전체 전달, general_qa 는 토큰 단위
                pass  # 아래 루프에서 처리

            if intent == "greeting":
                yield _sse("status", {"text": "안녕하세요!"})
                # greeting 메시지를 단어 단위로 스트리밍
                from src.app.agents.biz_mong.nodes.chitchat_node import _GREETING_RESPONSES
                greeting_text = _GREETING_RESPONSES[0]
                biz_info: dict = merged_state.get("biz_info") or {}
                biz_name: str = biz_info.get("biz_name", "")
                if biz_name:
                    greeting_text = greeting_text.replace("사장님!", f"{biz_name} 사장님!")

                # 문자 단위로 스트리밍 (자연스러운 타이핑 느낌)
                for char in greeting_text:
                    collected_content.append(char)
                    yield _sse("token", {"content": char})
                full_content = greeting_text

            else:
                # general_qa: GPT 토큰 스트리밍
                yield _sse("status", {"text": "답변을 생성하고 있어요..."})

                async def token_cb(token: str) -> None:
                    collected_content.append(token)

                from src.app.agents.biz_mong.nodes.chitchat_node import (
                    _SYSTEM_PROMPT_GENERAL,
                )
                messages_hist: list = merged_state.get("messages") or []
                history = [
                    m for m in messages_hist
                    if isinstance(m, dict) and m.get("role") in ("user", "assistant")
                ][-12:]
                gpt_msgs = [{"role": "system", "content": _SYSTEM_PROMPT_GENERAL}] + history

                stream = await openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=gpt_msgs,
                    temperature=0.3,
                    max_tokens=400,
                    stream=True,
                )
                async for chunk in stream:
                    delta = chunk.choices[0].delta.content if chunk.choices else None
                    if delta:
                        collected_content.append(delta)
                        yield _sse("token", {"content": delta})

                full_content = "".join(collected_content)

        else:
            # 3. 도구 필요 에이전트 (diagnosis/simulator/rag/stats) — 상태 이벤트
            _STATUS_MAP = {
                "diagnosis": "🔍 정책 자금 적합도를 분석하고 있어요...",
                "simulator": "⚙️ 시나리오 시뮬레이션을 계산하고 있어요...",
                "rag": "📚 관련 정책을 검색하고 있어요...",
                "stats": "📊 동종업계 통계를 집계하고 있어요...",
            }
            yield _sse("status", {"text": _STATUS_MAP.get(intent, "분석 중...")})

            # LangGraph 풀 파이프라인 실행
            final_state = await agent._graph.ainvoke(merged_state, config=config)
            agent_type = final_state.get("current_agent") or intent
            full_content = _build_response_content(agent_type, final_state)

            # AI 로그 저장 후 done 이벤트 발행
            ai_log = await svc._repo.create_chat_log(
                user_id=biz.user_id,
                room_id=room.id,
                role="assistant",
                content=full_content,
            )
            await svc._session.commit()

            yield _sse("done", {
                "agent_type": agent_type,
                "message_id": str(ai_log.id),
                "content": full_content,
                "diagnosis_report": final_state.get("diagnosis_report"),
                "simulation_report": final_state.get("simulation_report"),
                "stats_insight": final_state.get("stats_insight"),
                "rag_results": final_state.get("rag_results"),
            })
            return

        # chitchat done 이벤트
        ai_log = await svc._repo.create_chat_log(
            user_id=biz.user_id,
            room_id=room.id,
            role="assistant",
            content=full_content,
        )
        await svc._session.commit()

        yield _sse("done", {
            "agent_type": intent,
            "message_id": str(ai_log.id),
            "content": full_content,
            "diagnosis_report": None,
            "simulation_report": None,
            "stats_insight": None,
            "rag_results": None,
        })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


def _build_response_content(agent_type: str, state: dict) -> str:
    """에이전트 결과에서 사용자에게 보여줄 한국어 요약 텍스트를 생성한다."""
    # chitchat (greeting / general_qa): messages 에 이미 assistant 응답이 들어있음
    if agent_type in ("greeting", "general_qa"):
        messages = state.get("messages") or []
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "assistant":
                return msg.get("content", "")
            if hasattr(msg, "type") and msg.type == "ai":
                return msg.content
        return "안녕하세요! 무엇이든 편하게 물어보세요."

    if agent_type == "diagnosis":
        report = state.get("diagnosis_report") or {}
        if not report:
            return "진단을 완료했습니다. 조건에 맞는 정책을 찾지 못했습니다."
        score = report.get("score", 0)
        top = report.get("top_policy", "")
        advice = report.get("advice", "")
        total = report.get("total_candidates", 0)
        return (
            f"진단 완료! 현재 프로필 적합도 점수: {score:.1f}점\n"
            f"추천 정책: {top} (총 {total}개 매칭)\n"
            f"{advice}"
        )

    elif agent_type == "simulator":
        sim = state.get("simulation_report") or {}
        if not sim:
            return "시뮬레이션을 완료했습니다."
        orig = sim.get("original_score", 0)
        virt = sim.get("virtual_score", 0)
        diff = sim.get("diff", 0)
        sign = "+" if diff >= 0 else ""
        insights = sim.get("insights") or []
        insight_text = "\n".join(f"• {i}" for i in insights[:3])
        return (
            f"시뮬레이션 결과: {orig:.1f}점 → {virt:.1f}점 ({sign}{diff:.1f}점)\n\n"
            f"{insight_text}"
        )

    elif agent_type == "rag":
        # RAG 는 이미 messages 에 assistant 답변이 추가됨
        messages = state.get("messages") or []
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "assistant":
                return msg.get("content", "")
            if hasattr(msg, "type") and msg.type == "ai":
                return msg.content
        return "관련 정책 정보를 검색했습니다."

    elif agent_type == "stats":
        insight = state.get("stats_insight") or {}
        comparison = insight.get("peer_comparison", "")
        trend = insight.get("market_trend", "")
        return f"{trend}\n\n{comparison}" if trend else "동종업계 통계 분석을 완료했습니다."

    return "에이전트 처리를 완료했습니다."
