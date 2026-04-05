"""채팅(비즈몽) 도메인 Pydantic 스키마."""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    initial_message: str = Field(..., description="상담을 시작할 첫 메시지")


class CreateSessionResponseData(BaseModel):
    session_id: str
    title: str
    created_at: datetime


class ChatSessionItem(BaseModel):
    session_id: str
    title: str
    last_message: Optional[str] = None
    updated_at: datetime


class SendMessageRequest(BaseModel):
    message: str = Field(..., description="사용자가 보내는 질문 메시지")


class ReferencedPolicy(BaseModel):
    id: str
    title: str


class SendMessageResponseData(BaseModel):
    message_id: str
    role: str
    content: str
    referenced_policies: List[ReferencedPolicy] = Field(default_factory=list)
    created_at: datetime


class ChatMessageItem(BaseModel):
    role: str
    content: str


class AutoSummaryResponseData(BaseModel):
    new_title: str
