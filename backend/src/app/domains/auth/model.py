"""인증 도메인 SQLAlchemy 모델 — users, user_tokens."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

# [비유] TYPE_CHECKING은 '나중에 할 일 메모'와 같습니다. 
# 순환 참조(서로를 무한히 불러오는 현상)를 방지하기 위해 설계되었습니다.
if TYPE_CHECKING:
    from src.app.domains.business.model import Business
    from src.app.domains.chat.model import ChatLog, ChatRoom
    from src.app.domains.notification.model import Notification
    from src.app.domains.system.model import LeadRequest

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    ForeignKey,
    String,
    Text,
    text,
)
from sqlalchemy import (
    Enum as sqlalchemy_Enum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.database.postgres.base import Base

# ── 1. 사용자 관련 정의 ─────────────────────────────────────────────────────────

class SocialProvider(str, Enum):
    """소셜 로그인 제공자."""
    KAKAO = "KAKAO"
    NAVER = "NAVER"


class User(Base):
    """
    users 테이블 — 소셜 로그인 프로필 및 사용자 상태 관리.
    
    [설계 의도]
    1. Soft Delete: 'deleted_at'에 날짜가 찍히면 '폐기 예정 스티커'가 붙은 것으로 간주합니다.
    2. 관계 유지: 유저가 떠나도 그 유저가 남긴 비즈니스 정보나 채팅 로그는 데이터 분석을 위해 보존합니다.
    """

    __tablename__ = "users"

    # 식별자 및 기본 정보
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
    
    # 소셜 로그인 정보
    social_id: Mapped[str] = mapped_column(String(255), nullable=False)
    social_provider: Mapped[SocialProvider] = mapped_column(
        sqlalchemy_Enum(SocialProvider), nullable=False
    )
    profile_image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 계정 상태 제어
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP,
        nullable=True,
        default=None,
        comment="탈퇴 시각(UTC). 5년 후 물리 삭제를 위한 기록",
    )
    marketing_agreed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP, nullable=True
    )

    # 관심 분야 및 역량 정보 (JSONB 활용)
    interest_sectors: Mapped[Optional[Any]] = mapped_column(
        JSONB, nullable=True, comment="관심 업종 리스트"
    )
    military_service: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        comment="군필 여부 (COMPLETED/EXEMPTED/IN_PROGRESS/NA)",
    )
    is_non_major: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True, comment="비전공 창업자 여부"
    )
    tech_stack: Mapped[Optional[Any]] = mapped_column(
        JSONB, nullable=True, comment="기술 스택 리스트"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    # ── 알림 설정 (Notification Settings) ────────────────────────────────────────
    # [설계 의도] 마스터 스위치: push_enabled가 꺼지면 모든 알림이 차단됩니다.
    push_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        comment="전체 푸시 알림 마스터 스위치",
    )
    marketing_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        comment="마케팅 정보 수신 동의 여부",
    )
    policy_update_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        comment="약관 및 정책 변경 알림 수신 여부",
    )
    chat_answer_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        comment="AI 채팅 답변 완료 알림 수신 여부",
    )

    # ── 타 도메인과의 관계 (Relationships) ─────────────────────────────────────────
    tokens: Mapped[list["UserToken"]] = relationship("UserToken", back_populates="user")
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


# ── 2. 인증 토큰 관련 정의 ───────────────────────────────────────────────────────

class UserToken(Base):
    """user_tokens 테이블 — Refresh Token 저장소."""

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
        comment="소유 사용자 ID",
    )
    token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
        comment="Refresh Token 값",
    )
    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, comment="만료 일시"
    )
    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        server_default=text("false"),
        comment="로그아웃 등으로 인한 무효화 여부",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="tokens")