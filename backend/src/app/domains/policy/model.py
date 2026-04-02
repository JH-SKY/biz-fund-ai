# src/app/domains/policy/model.py
"""정책 도메인 SQLAlchemy 모델 — policies, biz_picks."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from src.app.domains.business.model import Application
    from src.app.domains.chat.model import ChatLog
    from src.app.domains.diagnosis.model import MatchLog

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    Enum as sqlalchemy_Enum,
    Integer,
    String,
    Text,
    TIMESTAMP,
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
    """policies 테이블 — 정책 공고 마스터 데이터."""

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
    support_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="지원 유형 (융자·출연금·보조금 등)"
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
        BigInteger, nullable=True, comment="최대 지원 금액"
    )
    start_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="접수 시작일"
    )
    end_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="접수 종료일"
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
