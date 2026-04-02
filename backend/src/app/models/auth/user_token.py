# src/app/models/auth/user_token.py
"""Refresh Token 저장 모델. 로그아웃 시 is_revoked=True 처리로 무효화한다."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.app.models.auth.user import User

from sqlalchemy import Boolean, ForeignKey, Text, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.models.base import Base


class UserToken(Base):
    """Refresh Token 레코드. .cursorrules: Refresh Token은 DB에 저장."""

    __tablename__ = "user_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="토큰 레코드 식별자",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        comment="소유 사용자 ID (users.id)",
    )
    token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
        comment="opaque Refresh Token 원본값 저장",
    )
    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, comment="토큰 만료 일시"
    )
    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        server_default=text("false"),
        comment="로그아웃·탈퇴로 무효화 여부",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="발급 일시",
    )

    user: Mapped["User"] = relationship("User", back_populates="tokens")
