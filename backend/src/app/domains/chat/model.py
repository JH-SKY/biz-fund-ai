# src/app/domains/chat/model.py
"""채팅 도메인 SQLAlchemy 모델 — chat_rooms, chat_logs."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from src.app.domains.auth.model import User
    from src.app.domains.business.model import Business
    from src.app.domains.policy.model import Policy

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Numeric,
    String,
    Text,
    TIMESTAMP,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.database.postgres.base import Base


class ChatRoom(Base):
    """chat_rooms 테이블 — 비즈몽 상담 세션(대화방)."""

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

    user: Mapped["User"] = relationship("User", back_populates="chat_rooms")
    business: Mapped["Business"] = relationship("Business", back_populates="chat_rooms")
    chat_logs: Mapped[list["ChatLog"]] = relationship(
        "ChatLog", back_populates="room"
    )


class ChatLog(Base):
    """chat_logs 테이블 — 개별 메시지·RAG 참조·피드백."""

    __tablename__ = "chat_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="대화 메시지 고유 식별자",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        comment="대화 사용자 ID (users.id)",
    )
    ref_policy_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("policies.id"),
        nullable=True,
        comment="참조한 정책 ID (policies.id, 없으면 일반 상담)",
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_rooms.id"),
        nullable=False,
        comment="소속 대화방 ID (chat_rooms.id)",
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="화자 (user / assistant)"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="메시지 본문"
    )
    context_type: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="발생 위치 (위젯·페이지 등)"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="메시지 생성 일시",
    )
    trace_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="랭스미스 등 LLM 추적 ID"
    )
    total_cost: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 8), nullable=True, comment="해당 메시지 API 토큰 비용 (USD)"
    )
    referenced_chunks: Mapped[Optional[Any]] = mapped_column(
        JSONB, nullable=True, comment="RAG 참조 문단·청크 (JSON)"
    )
    is_disliked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        server_default=text("false"),
        comment="사용자 비추천(싫어요) 여부",
    )
    feedback_code: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="피드백 사유 코드"
    )
    feedback_text: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="피드백 상세 텍스트"
    )

    user: Mapped["User"] = relationship("User", back_populates="chat_logs")
    ref_policy: Mapped[Optional["Policy"]] = relationship(
        "Policy",
        back_populates="referenced_chat_logs",
        foreign_keys=[ref_policy_id],
    )
    room: Mapped["ChatRoom"] = relationship("ChatRoom", back_populates="chat_logs")
