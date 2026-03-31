# src/app/models/auth/admin_audit_log.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import ForeignKey, String, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.models.auth.admin import Admin
from src.app.models.base import Base


class AdminAuditLog(Base):
    """관리자 감사 로그. 설계서: admin_audit_logs."""

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

    admin: Mapped[Admin] = relationship("Admin", back_populates="audit_logs")
