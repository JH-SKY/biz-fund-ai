# src/app/domains/admin/model.py
"""관리자 도메인 SQLAlchemy 모델 — admins."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    ForeignKey,
    String,
    Text,
    text,
)
from sqlalchemy import Enum as sqlalchemy_Enum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.database.postgres.base import Base


# 1. 관리자 권한 등급
class AdminRole(str, Enum):
    """관리자 권한 등급."""

    MASTER = "MASTER"
    OPERATOR = "OPERATOR"
    CS = "CS"


# 2. 관리자 메인 테이블
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

    # 같은 파일 내에 있는 클래스는 문자열 "AdminAuditLog"로 안전하게 연결됩니다.
    audit_logs: Mapped[list["AdminAuditLog"]] = relationship(
        "AdminAuditLog", back_populates="admin"
    )


# 3. 관리자 작업 로그 테이블
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


# 4. 피드백 정정 노트 테이블
class CorrectionNote(Base):
    """correction_notes 테이블 — 관리자가 피드백에 작성하는 정정 노트."""

    __tablename__ = "correction_notes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="정정 노트 고유 식별자",
    )
    feedback_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_logs.id", ondelete="CASCADE"),
        nullable=False,
        comment="대상 피드백 ChatLog ID",
    )
    created_by_admin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
        comment="작성 관리자 ID",
    )
    question_pattern: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="정정이 필요한 질문 패턴"
    )
    expected_answer: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="기대하는 정답/답변"
    )
    applies_to_agent: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="적용 대상 에이전트"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        server_default=text("true"),
        comment="활성 여부",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="작성 일시",
    )

    admin: Mapped[Optional["Admin"]] = relationship("Admin")
