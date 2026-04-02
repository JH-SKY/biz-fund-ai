# src/app/domains/system/model.py
"""시스템 도메인 SQLAlchemy 모델 — lead_requests, batch_logs."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from src.app.domains.auth.model import User
    from src.app.domains.business.model import Business

from sqlalchemy import ForeignKey, Integer, String, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.database.postgres.base import Base


class LeadRequest(Base):
    """lead_requests 테이블 — 파트너(세무사·로봇) 상담 연결 요청."""

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
    business: Mapped["Business"] = relationship(
        "Business", back_populates="lead_requests"
    )


class BatchLog(Base):
    """batch_logs 테이블 — 크롤링·동기화 배치 작업 실행 이력."""

    __tablename__ = "batch_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="배치 실행 로그 고유 식별자",
    )
    job_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="작업 명칭 (예: POLICY_CRAWLING)"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="실행 상태 (SUCCESS·FAILED·RUNNING 등)"
    )
    total_count: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="처리 대상 전체 건수"
    )
    success_count: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="성공 반영 건수"
    )
    fail_count: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="실패 건수"
    )
    error_details: Mapped[Optional[Any]] = mapped_column(
        JSONB, nullable=True, comment="오류 상세 (JSON)"
    )
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="작업 시작 일시",
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP, nullable=True, comment="작업 종료 일시"
    )
