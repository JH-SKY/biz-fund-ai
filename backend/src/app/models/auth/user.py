# src/app/models/auth/user.py
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from src.app.models.auth.user_token import UserToken
    from src.app.models.business.business import Business
    from src.app.models.chat.chat import ChatRoom
    from src.app.models.chat.chat_log import ChatLog
    from src.app.models.system.lead_request import LeadRequest
    from src.app.models.system.notification import Notification

from sqlalchemy import Boolean, String, TIMESTAMP, Text, text, Enum as sqlalchemy_Enum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.app.models.base import Base


class SocialProvider(str, Enum):
    KAKAO = "KAKAO"
    NAVER = "NAVER"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="사용자 고유 식별자",
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    nickname: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    social_id: Mapped[str] = mapped_column(String(255), nullable=False)
    social_provider: Mapped[SocialProvider] = mapped_column(
        sqlalchemy_Enum(SocialProvider), nullable=False
    )
    profile_image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    marketing_agreed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP, nullable=True
    )

    # 추가 프로필 (auth.md #5, #6)
    interest_sectors: Mapped[Optional[Any]] = mapped_column(
        JSONB, nullable=True, comment="관심 업종/분야 리스트 (JSONB array)"
    )
    military_service: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True, comment="군필 여부 (COMPLETED/EXEMPTED/IN_PROGRESS/NA)"
    )
    is_non_major: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True, comment="비전공 창업자 여부"
    )
    tech_stack: Mapped[Optional[Any]] = mapped_column(
        JSONB, nullable=True, comment="기술 스택 리스트 (JSONB array)"
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    tokens: Mapped[list["UserToken"]] = relationship(
        "UserToken", back_populates="user"
    )
    businesses: Mapped[list["Business"]] = relationship(
        "Business", back_populates="user"
    )
    chat_rooms: Mapped[list["ChatRoom"]] = relationship(
        "ChatRoom", back_populates="user"
    )
    chat_logs: Mapped[list["ChatLog"]] = relationship("ChatLog", back_populates="user")
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="user"
    )
    lead_requests: Mapped[list["LeadRequest"]] = relationship(
        "LeadRequest", back_populates="user"
    )
