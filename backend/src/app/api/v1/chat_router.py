"""채팅 API 라우터."""

import uuid

from fastapi import APIRouter, status

from src.app.api.deps.business_deps import ActiveBusiness
from src.app.api.deps.chat_deps import ChatServiceDep
from src.app.core.response import api_json
from src.app.domains.chat.schema import (
    CreateSessionRequest,
    SendMessageRequest,
)

router = APIRouter(prefix="/chats", tags=["chats"])


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
