# src/app/models/business/business.py
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.app.models.business.application import Application
    from src.app.models.business.document import Document
    from src.app.models.business.financial_snapshot import BusinessFinancialSnapshot
    from src.app.models.business.simulation_log import SimulationLog
    from src.app.models.chat.chat import ChatRoom
    from src.app.models.policy.match_log import MatchLog
    from src.app.models.system.lead_request import LeadRequest
    from src.app.models.system.notification import Notification

from sqlalchemy import Boolean, Date, ForeignKey, String, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.models.auth.user import User
from src.app.models.base import Base


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="사업장 고유 식별자",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        comment="이 사업장을 소유한 사용자 ID (users.id)",
    )
    biz_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="상호명"
    )
    representative_name: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="대표자명"
    )
    biz_no: Mapped[Optional[str]] = mapped_column(
        String(12), nullable=True, comment="사업자등록번호"
    )
    ksic_code: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="표준산업분류코드"
    )
    sector_code: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="세부 업종 코드"
    )
    region_sido: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="시·도 (표시·매칭용)"
    )
    region_sigungu: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="시·군·구 (표시·매칭용)"
    )
    region_code: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True, comment="법정동 코드 (시스템 지역 필터용)"
    )
    establishment_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="설립 일자 (업력 등 자격 판단)"
    )
    has_patent: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="특허 보유 여부"
    )
    is_female_ent: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="여성 기업 여부"
    )
    is_ventured: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="벤처 기업 여부"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="업장 활성 여부 (폐업·삭제 등)"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="사업장 정보 최초 등록 일시",
    )

    user: Mapped[User] = relationship("User", back_populates="businesses")
    financial_snapshots: Mapped[list["BusinessFinancialSnapshot"]] = relationship(
        "BusinessFinancialSnapshot", back_populates="business"
    )
    match_logs: Mapped[list["MatchLog"]] = relationship(
        "MatchLog", back_populates="business"
    )
    applications: Mapped[list["Application"]] = relationship(
        "Application", back_populates="business"
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="business"
    )
    lead_requests: Mapped[list["LeadRequest"]] = relationship(
        "LeadRequest", back_populates="business"
    )
    simulation_logs: Mapped[list["SimulationLog"]] = relationship(
        "SimulationLog", back_populates="business"
    )
    chat_rooms: Mapped[list["ChatRoom"]] = relationship(
        "ChatRoom", back_populates="business"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="business"
    )
