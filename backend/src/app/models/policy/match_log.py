# src/app/models/policy/match_log.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from src.app.models.business.business import Business
    from src.app.models.policy.policy import Policy

from sqlalchemy import ForeignKey, Integer, String, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.models.base import Base


class MatchLog(Base):
    """사업장·정책 매칭 결과. 설계서: match_logs."""

    __tablename__ = "match_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="매칭 결과 고유 식별자",
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id"),
        nullable=False,
        comment="매칭 대상 사업장 ID (businesses.id)",
    )
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("policies.id"),
        nullable=False,
        comment="매칭 대상 정책 ID (policies.id)",
    )
    match_score: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="매칭 점수 (0~100)"
    )
    match_status: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="신호등 상태 (G/Y/R 등)"
    )
    reason_json: Mapped[Optional[Any]] = mapped_column(
        JSONB, nullable=True, comment="점수 산정 근거 (JSON)"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="매칭 판정 일시",
    )

    business: Mapped["Business"] = relationship("Business", back_populates="match_logs")
    policy: Mapped["Policy"] = relationship("Policy", back_populates="match_logs")
