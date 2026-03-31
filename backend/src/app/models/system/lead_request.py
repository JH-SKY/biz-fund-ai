# src/app/models/system/lead_request.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.app.models.auth.user import User
    from src.app.models.business.business import Business

from sqlalchemy import ForeignKey, String, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.models.base import Base


class LeadRequest(Base):
    """파트너 상담 리드. 설계서: lead_requests."""

    __tablename__ = "lead_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="리드 요청 고유 식별자",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        comment="신청 사용자 ID (users.id)",
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id"),
        nullable=False,
        comment="상담 대상 사업장 ID (businesses.id)",
    )
    lead_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="상담 종류 (로봇·세무 등)"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="처리 상태 (신청·검토·연결완료 등)"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="신청 일시",
    )

    user: Mapped["User"] = relationship("User", back_populates="lead_requests")
    business: Mapped["Business"] = relationship("Business", back_populates="lead_requests")
