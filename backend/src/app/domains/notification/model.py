# src/app/domains/notification/model.py
"""알림 도메인 SQLAlchemy 모델 — notifications."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.app.domains.auth.model import User
    from src.app.domains.business.model import Business

from sqlalchemy import Boolean, ForeignKey, String, Text, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.database.postgres.base import Base


class Notification(Base):
    """notifications 테이블 — 사용자 알림 발송 이력."""

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="알림 고유 식별자",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        comment="수신 사용자 ID (users.id)",
    )
    business_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id"),
        nullable=True,
        comment="연관 사업장 ID (businesses.id, 가게별 필터용)",
    )
    type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="알림 유형 (매칭·공지 등)"
    )
    message: Mapped[str] = mapped_column(
        Text, nullable=False, comment="알림 본문"
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        server_default=text("false"),
        comment="읽음 여부",
    )
    link_url: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="이동 URL"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="알림 생성 일시",
    )

    user: Mapped["User"] = relationship("User", back_populates="notifications")
    business: Mapped[Optional["Business"]] = relationship(
        "Business", back_populates="notifications"
    )
