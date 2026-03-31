# src/app/models/business/application.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.app.models.business.business import Business
    from src.app.models.policy.policy import Policy

from sqlalchemy import ForeignKey, String, Text, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.models.base import Base


class Application(Base):
    """정책 신청·관심 트래킹. 설계서: applications."""

    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="신청(관심) 기록 고유 식별자",
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id"),
        nullable=False,
        comment="신청 사업장 ID (businesses.id)",
    )
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("policies.id"),
        nullable=False,
        comment="대상 정책 ID (policies.id)",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="신청 단계 (관심·제출·승인 등)"
    )
    applied_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP, nullable=True, comment="실제 신청(제출) 일시"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="상태 마지막 변경 일시",
    )
    memo: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="사용자 메모"
    )

    business: Mapped["Business"] = relationship("Business", back_populates="applications")
    policy: Mapped["Policy"] = relationship("Policy", back_populates="applications")
