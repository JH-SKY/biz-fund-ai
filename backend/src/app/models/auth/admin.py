# src/app/models/auth/admin.py
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.app.models.auth.admin_audit_log import AdminAuditLog

from sqlalchemy import Boolean, Enum as sqlalchemy_Enum, String, Text, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.models.base import Base


class AdminRole(str, Enum):
    """관리자 권한 등급. 설계서: admins.role."""

    MASTER = "MASTER"
    OPERATOR = "OPERATOR"
    CS = "CS"


class Admin(Base):
    """관리자 계정. 설계서: admins."""

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
    password: Mapped[str] = mapped_column(
        Text, nullable=False, comment="비밀번호 해시"
    )
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
