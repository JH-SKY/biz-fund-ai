# src/app/domains/business/model.py
"""비즈니스 도메인 SQLAlchemy 모델 — businesses, business_financial_snapshots, applications, documents."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from src.app.domains.auth.model import User
    from src.app.domains.chat.model import ChatRoom
    from src.app.domains.diagnosis.model import MatchLog, SimulationLog
    from src.app.domains.notification.model import Notification
    from src.app.domains.policy.model import Policy
    from src.app.domains.system.model import LeadRequest

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    TIMESTAMP,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.database.postgres.base import Base


class Business(Base):
    """businesses 테이블 — 사업장 기본정보·업종·지역·가점 요소."""

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
    biz_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="상호명")
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
    profile_score: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="사업장 정보 완성도 (0~100)"
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

    user: Mapped["User"] = relationship("User", back_populates="businesses")
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


class BusinessFinancialSnapshot(Base):
    """business_financial_snapshots 테이블 — 연도별 재무 스냅샷."""

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

    business: Mapped["Business"] = relationship(
        "Business", back_populates="financial_snapshots"
    )


class Application(Base):
    """applications 테이블 — 정책 신청·관심 이력 트래킹."""

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

    business: Mapped["Business"] = relationship(
        "Business", back_populates="applications"
    )
    policy: Mapped["Policy"] = relationship("Policy", back_populates="applications")


class Document(Base):
    """documents 테이블 — 사업자등록증 등 서류 파일 관리."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="서류 고유 식별자",
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id"),
        nullable=False,
        comment="소속 사업장 ID (businesses.id)",
    )
    doc_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="서류 종류 (사업자등록증 등)"
    )
    file_url: Mapped[str] = mapped_column(
        Text, nullable=False, comment="저장소(S3 등) 파일 경로"
    )
    issued_at: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="서류 발급 일자"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="업로드 일시",
    )

    business: Mapped["Business"] = relationship("Business", back_populates="documents")
