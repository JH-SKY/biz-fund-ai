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
    from src.app.domains.policy.model import Policy, PolicyBookmark
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
    UniqueConstraint,
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
    ksic_name: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="KSIC 세세분류 표시명 (예: 한식 일반 음식점업)"
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
    is_biz_no_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
        comment="국세청 API 진위 확인 완료 여부 (True 이면 재호출 불필요)",
    )
    biz_verified_status: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        comment="국세청 반환 사업자 상태 (계속사업자 | 휴업자 | 폐업자 등)",
    )
    tax_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="국세청 반환 과세 유형 (부가가치세 일반과세자 등)",
    )
    biz_verified_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="국세청 API 마지막 검증 시각 (UTC)",
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
    policy_bookmarks: Mapped[list["PolicyBookmark"]] = relationship(
        "PolicyBookmark", back_populates="business", cascade="all, delete-orphan"
    )


class BusinessFinancialSnapshot(Base):
    """business_financial_snapshots 테이블 — 연도별 재무 스냅샷.

    제약 조건:
      - (business_id, snapshot_year) UNIQUE: 동일 사업장의 연도 중복 등록 방지.
        Service 레이어 체크(finance_already_exists)와 DB 레이어 양쪽에서 무결성 보장.
    삭제 정책:
      - [도메인 규칙 0: Data Persistence] Soft Delete — is_active=False 처리.
        실수 입력 데이터도 감사(Audit) 목적으로 보존한다.
    """

    __tablename__ = "business_financial_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "business_id",
            "snapshot_year",
            name="uq_biz_financial_snapshot_year",
        ),
    )

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
        BigInteger, nullable=True, comment="연매출액 (원)"
    )
    operating_profit: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="영업이익 (원, 음수 가능) — API 명세서 #4·#5 대응"
    )
    net_income: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="당기순이익 (원, 음수 가능)"
    )
    total_debt: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="총 부채액 (원)"
    )
    capital: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="자본금 (원) — API 명세서 #4·#5 대응"
    )
    debt_ratio: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2), nullable=True, comment="부채 비율 (%) — 자동 계산"
    )
    employee_count: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="직원 수"
    )
    tax_arrears_yn: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
        comment="세금 체납 여부",
    )
    ai_analysis_report: Mapped[Optional[Any]] = mapped_column(
        JSONB, nullable=True, comment="비즈몽 재무 진단 결과 (JSON)"
    )
    ocr_status: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="OCR·분석 진행 상태 (대기·완료 등)"
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
        comment="공식 서류 기반 검증 여부",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        nullable=False,
        comment="[Soft Delete] 활성 여부 — False 이면 삭제 처리된 레코드",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="스냅샷 생성 일시",
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
    """documents 테이블 — 사업자등록증 등 서류 파일 관리.

    삭제 정책:
      - [도메인 규칙 0: Data Persistence] Soft Delete — is_active=False 처리.
        법적 보존 의무 및 재활용 가능성을 위해 파일 레코드를 유지한다.
    """

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
    ocr_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
        server_default=text("'PENDING'"),
        comment="OCR 분석 진행 상태 (PENDING | COMPLETED | FAILED)",
    )
    ocr_result: Mapped[Optional[Any]] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "OCR 추출 원본 데이터 (JSON). "
            "비동기 분석 완료 시 update_document_status()로 채워진다. "
            "API 명세서 #11 ocr_data 필드에 대응."
        ),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        nullable=False,
        comment="[Soft Delete] 활성 여부 — False 이면 삭제 처리된 레코드",
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
