# src/app/models/business/financial_snapshot.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from src.app.models.business.business import Business

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, Numeric, String, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.models.base import Base


class BusinessFinancialSnapshot(Base):
    """재무 스냅샷(비즈몽 AI 재무 진단 근거). 설계서: business_financial_snapshots."""

    __tablename__ = "business_financial_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="재무 스냅샷 고유 식별자",
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id"),
        nullable=False,
        comment="대상 사업장 ID (businesses.id)",
    )
    snapshot_year: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="재무제표 기준 연도"
    )
    snapshot_period: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="기준 시기 (1Q, 2Q 등)"
    )
    term_type: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="공시 주기 (연간·분기 등)"
    )
    annual_revenue: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="연매출액"
    )
    net_income: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="당기순이익"
    )
    total_debt: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="총 부채액"
    )
    debt_ratio: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2), nullable=True, comment="부채 비율 (%)"
    )
    employee_count: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="직원 수"
    )
    tax_arrears_yn: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="세금 체납 여부"
    )
    ai_analysis_report: Mapped[Optional[Any]] = mapped_column(
        JSONB, nullable=True, comment="비즈몽 재무 진단 결과 (JSON)"
    )
    ocr_status: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="OCR·분석 진행 상태 (대기·완료 등)"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="스냅샷 생성 일시",
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="공식 서류 기반 검증 여부"
    )

    business: Mapped["Business"] = relationship("Business", back_populates="financial_snapshots")
