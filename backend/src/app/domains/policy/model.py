# src/app/domains/policy/model.py
"""정책 도메인 SQLAlchemy 모델 — policies, policy_bookmarks, biz_picks."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from src.app.domains.business.model import Application, Business
    from src.app.domains.chat.model import ChatLog
    from src.app.domains.diagnosis.model import MatchLog

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    Enum as sqlalchemy_Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    TIMESTAMP,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.database.postgres.base import Base


class PolicyStatus(str, Enum):
    """공고 진행 상태."""

    PREPARING = "PREPARING"
    RECRUITING = "RECRUITING"
    CLOSED = "CLOSED"
    END_OF_BUDGET = "END_OF_BUDGET"


class Policy(Base):
    """policies 테이블 — 정책 공고 마스터 데이터.

    closed_at 설계:
      - 상시접수 정책은 closed_at을 9999-12-31로 저장한다.
        → Service 레이어에서 9999-12-31 여부로 "상시접수" 여부를 판별.
      - server_default='9999-12-31'이므로 입력이 없으면 자동으로 상시접수 처리.
    """

    __tablename__ = "policies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="정책(공고) 고유 식별자",
    )
    title: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="공고 제목"
    )
    agency_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="공고 기관명"
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="정책 카테고리 (금융/바우처, R&D 등)"
    )
    support_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="지원 유형 (융자·출연금·보조금 등)"
    )
    region: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="지원 대상 지역 (검색·필터용)"
    )
    ai_summary: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="리스트용 3줄 요약 (AI 생성)"
    )
    ai_full_explanation: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="상세용 쉬운 풀이 (AI 생성)"
    )
    content_raw: Mapped[str] = mapped_column(
        Text, nullable=False, comment="공고 원문 전체 (RAG·분석용)"
    )
    max_support: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="최대 지원 금액 (원)"
    )
    support_amount_desc: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="지원 금액 표시 문자열 (예: 최대 400만원)"
    )
    required_documents: Mapped[Optional[Any]] = mapped_column(
        JSONB,
        nullable=True,
        comment="신청 필수 서류 목록 (문자열 배열 JSON, 예: ['사업자등록증', ...])",
    )
    start_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="접수 시작일"
    )
    end_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="접수 종료일 (레거시 — 신규 코드는 closed_at 사용)"
    )
    closed_at: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        default=date(9999, 12, 31),
        server_default=text("'9999-12-31'"),
        comment="접수 마감일. 상시접수는 9999-12-31 저장",
    )
    status: Mapped[PolicyStatus] = mapped_column(
        sqlalchemy_Enum(PolicyStatus, name="policystatus"),
        nullable=False,
        comment="공고 상태 (예정·접수중·마감·예산소진)",
    )
    apply_url: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="원문 신청 페이지 URL"
    )
    target_logic: Mapped[Optional[Any]] = mapped_column(
        JSONB, nullable=True, comment="사업장 대비 매칭 필터 규칙 (JSON)"
    )
    bonus_logic: Mapped[Optional[Any]] = mapped_column(
        JSONB, nullable=True, comment="가산점 계산 규칙 (JSON)"
    )
    scrap_source_url: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="크롤링·수집 원본 페이지 주소"
    )
    view_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="상세 조회 누적 건수",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        comment="[Soft Delete] 활성 여부 — False이면 서비스에서 노출 안 됨",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="등록 일시",
    )

    match_logs: Mapped[list["MatchLog"]] = relationship(
        "MatchLog", back_populates="policy"
    )
    applications: Mapped[list["Application"]] = relationship(
        "Application", back_populates="policy"
    )
    referenced_chat_logs: Mapped[list["ChatLog"]] = relationship(
        "ChatLog",
        back_populates="ref_policy",
        foreign_keys="ChatLog.ref_policy_id",
    )
    bookmarks: Mapped[list["PolicyBookmark"]] = relationship(
        "PolicyBookmark", back_populates="policy", cascade="all, delete-orphan"
    )


class PolicyBookmark(Base):
    """policy_bookmarks 테이블 — 사업장(Business)×정책(Policy) N:M 관심 등록.

    [도메인 규칙 2.2] Business-Centric: 북마크는 User가 아닌 Business 기준으로 관리한다.
    동일 사업장이 동일 정책에 중복 북마크할 수 없도록 UniqueConstraint 적용.
    """

    __tablename__ = "policy_bookmarks"
    __table_args__ = (
        UniqueConstraint(
            "business_id",
            "policy_id",
            name="uq_policy_bookmark_biz_policy",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="북마크 고유 식별자",
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id"),
        nullable=False,
        comment="북마크한 사업장 ID (businesses.id)",
    )
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("policies.id"),
        nullable=False,
        comment="북마크 대상 정책 ID (policies.id)",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="북마크 등록 일시",
    )

    business: Mapped["Business"] = relationship(
        "Business", back_populates="policy_bookmarks"
    )
    policy: Mapped["Policy"] = relationship("Policy", back_populates="bookmarks")


class BizPick(Base):
    """biz_picks 테이블 — 비즈픽 콘텐츠(카드뉴스·꿀팁)."""

    __tablename__ = "biz_picks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="콘텐츠 고유 식별자",
    )
    title: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="콘텐츠 제목"
    )
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="카테고리 (세무·정책자금 등)"
    )
    content_html: Mapped[str] = mapped_column(
        Text, nullable=False, comment="HTML 본문 (관리자 API에서 그대로 저장·조회)"
    )
    thumbnail_url: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="썸네일 이미지 URL"
    )
    is_published: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        comment="발행(공개) 여부",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="작성·발행 일시",
    )
