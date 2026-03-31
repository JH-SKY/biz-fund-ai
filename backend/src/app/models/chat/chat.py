# src/app/models/chat/chat.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.app.models.chat.chat_log import ChatLog

from sqlalchemy import Boolean, ForeignKey, String, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.models.auth.user import User
from src.app.models.base import Base
from src.app.models.business.business import Business


class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="대화방(상담 세션) 고유 식별자",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        comment="상담을 시작한 사용자 ID (users.id)",
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id"),
        nullable=False,
        comment="상담 시 선택된 사업장 ID (businesses.id, 데이터 격리)",
    )
    title: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="대화방 제목 (AI 요약 등)"
    )
    user_feedback: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True, comment="사용자 만족도 (좋아요·싫어요 등)"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="상담 진행 상태 (진행·종료 등)"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="대화방 생성 일시",
    )

    user: Mapped[User] = relationship("User", back_populates="chat_rooms")
    business: Mapped[Business] = relationship("Business", back_populates="chat_rooms")
    chat_logs: Mapped[list["ChatLog"]] = relationship(
        "ChatLog", back_populates="room"
    )
