"""채팅 API 라우터."""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, status
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
    import json
    from datetime import datetime, timezone

    # 1. 세션 소유권 검증 (기존 ChatService 활용)
    room = await svc._repo.get_chat_room_by_id(session_id)
    if not room or room.business_id != biz.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="세션에 접근 권한이 없습니다.")

    # 2. 사용자 메시지 ChatLog 저장
    user_log = await svc._repo.create_chat_log(
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


def _build_response_content(agent_type: str, state: dict) -> str:
    """에이전트 결과에서 사용자에게 보여줄 한국어 요약 텍스트를 생성한다."""
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
