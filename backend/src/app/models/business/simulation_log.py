# src/app/models/business/simulation_log.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.app.models.business.business import Business

from sqlalchemy import ForeignKey, String, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.models.base import Base


class SimulationLog(Base):
    """가산점·한도 등 시뮬레이션 이력. 설계서: simulation_logs."""

    __tablename__ = "simulation_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="시뮬레이션 로그 고유 식별자",
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id"),
        nullable=False,
        comment="기준 사업장 ID (businesses.id)",
    )
    sim_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="시뮬레이션 종류"
    )
    input_data: Mapped[Any] = mapped_column(
        JSONB, nullable=False, comment="사용자 입력 조건 (JSON)"
    )
    output_data: Mapped[Any] = mapped_column(
        JSONB, nullable=False, comment="계산·예측 결과 (JSON)"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="실행 일시",
    )

    business: Mapped["Business"] = relationship("Business", back_populates="simulation_logs")
