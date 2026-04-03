# src/app/domains/auth/model.py
"""인증 도메인 SQLAlchemy 모델 — users, user_tokens, admins, admin_audit_logs."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from src.app.domains.business.model import Business
    from src.app.domains.chat.model import ChatLog, ChatRoom
    from src.app.domains.notification.model import Notification
    from src.app.domains.system.model import LeadRequest

from sqlalchemy import (
    Boolean,
    Enum as sqlalchemy_Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    TIMESTAMP,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.database.postgres.base import Base


# ── 사용자 ──────────────────────────────────────────────────────────────────


class SocialProvider(str, Enum):
    KAKAO = "KAKAO"
    NAVER = "NAVER"


class User(Base):
    """
    users 테이블 — 소셜 로그인·프로필·관심분야.
    [도메인 설계 원칙]
    1. 탈퇴 시 실제 데이터를 삭제하지 않는 'Soft Delete' 방식을 사용합니다.
    2. 유저가 탈퇴(is_active=False)해도 연결된 'Business', 'ChatRoom' 데이터는 유지합니다.
    3. (주의) 타 도메인에서 데이터를 조회할 때, 반드시 유저의 is_active 상태를 확인해야 합니다.
    """

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
    # [도메인 규칙 1.2] ① 탈퇴 시각 — 비유: '폐기 예정일이 찍힌 보관 스티커'(5년 후 물리 삭제를 위한 타임스탬프 기록).
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP,
        nullable=True,
        default=None,
        comment="탈퇴 시각(UTC). 5년 후 물리 삭제를 위한 타임스탬프 기록",
    )
    marketing_agreed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP, nullable=True
    )
    interest_sectors: Mapped[Optional[Any]] = mapped_column(
        JSONB, nullable=True, comment="관심 업종/분야 리스트 (JSONB array)"
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
        JSONB, nullable=True, comment="기술 스택 리스트 (JSONB array)"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

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


class UserToken(Base):
    """user_tokens 테이블 — Refresh Token 저장·무효화."""

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


# ── 관리자 ──────────────────────────────────────────────────────────────────


class AdminRole(str, Enum):
    """관리자 권한 등급."""

    MASTER = "MASTER"
    OPERATOR = "OPERATOR"
    CS = "CS"


class Admin(Base):
    """admins 테이블 — 관리자 계정·권한 등급."""

    __tablename__ = "admins"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="관리자 고유 식별자",
    )
    login_id: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, comment="관리자 로그인 ID"
    )
    password: Mapped[str] = mapped_column(Text, nullable=False, comment="비밀번호 해시")
    role: Mapped[AdminRole] = mapped_column(
        sqlalchemy_Enum(AdminRole, name="adminrole"),
        nullable=False,
        comment="권한 등급 (MASTER·OPERATOR·CS)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        server_default=text("true"),
        comment="계정 활성 여부",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="계정 생성 일시",
    )

    audit_logs: Mapped[list["AdminAuditLog"]] = relationship(
        "AdminAuditLog", back_populates="admin"
    )


class AdminAuditLog(Base):
    """admin_audit_logs 테이블 — 관리자 작업 이력 감사 로그."""

    __tablename__ = "admin_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="감사 로그 고유 식별자",
    )
    admin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admins.id"),
        nullable=False,
        comment="작업 수행 관리자 ID (admins.id)",
    )
    action_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="작업 유형 (POLICY_UPDATE 등)"
    )
    target_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, comment="대상 엔티티 PK"
    )
    changes: Mapped[Optional[Any]] = mapped_column(
        JSONB, nullable=True, comment="변경 전·후 스냅샷 (JSON)"
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45), nullable=True, comment="요청 IP (IPv4/IPv6)"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="작업 발생 일시",
    )

    admin: Mapped["Admin"] = relationship("Admin", back_populates="audit_logs")
