# src/app/domains/policy/model.py
"""정책 도메인 SQLAlchemy 모델 — policies, policy_bookmarks, biz_picks.

이 파일은 시스템의 '그릇' 역할을 합니다. 
1. 정책 데이터(Policy)를 담고, 
2. 사용자의 관심(Bookmark)을 연결하며, 
3. 서비스 콘텐츠(BizPick)를 저장합니다.
"""

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
    Index,
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
    """공고 진행 상태를 정의하는 '상태 표지판'입니다."""

    PREPARING = "PREPARING"      # 준비 중
    RECRUITING = "RECRUITING"    # 접수 중 (가장 활발히 노출됨)
    CLOSED = "CLOSED"            # 마감됨
    END_OF_BUDGET = "END_OF_BUDGET" # 예산 소진 (조기 마감)


class Policy(Base):
    """policies 테이블 — 정책 공고 마스터 데이터.

    설계 의도:
      - '상시접수' 정책은 물리적인 마감일이 없으므로, 시스템 정렬 로직의 통일성을 위해
        9999-12-31(먼 미래)을 기본 마감일로 설정합니다. (비유: 무기한 출입증)
      - AI 기반 추천 및 요약을 위해 ai_ 관련 필드를 별도로 관리하여 원본(content_raw)을 보존합니다.
    """

    __tablename__ = "policies"

    # 1. 고유 식별자 및 기본 정보
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="정책(공고) 고유 식별자",
    )
    title: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="공고 제목 (검색 최적화 인덱스 적용)"
    )
    agency_name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="공고 기관명 (주관 부처 검색용)"
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True, comment="정책 카테고리 (금융/바우처, R&D 등)"
    )
    support_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="지원 유형 (융자·출연금·보조금 등)"
    )
    region: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True, comment="지원 대상 지역 (전국/서울 등)"
    )

    # 2. AI 데이터 계층 (추적성 및 가공 데이터)
    ai_summary: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="리스트용 3줄 요약 (AI가 읽기 쉽게 가공한 데이터)"
    )
    ai_full_explanation: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="상세용 쉬운 풀이 (비전공자 사용자를 위한 AI 해설)"
    )
    ai_metadata: Mapped[Optional[dict]] = mapped_column(
        JSONB, 
        nullable=True, 
        comment="AI 추천 엔진용 메타데이터 (가중치, 벡터 DB 참조 ID 등 임시 저장소)"
    )
    content_raw: Mapped[str] = mapped_column(
        Text, nullable=False, comment="공고 원문 전체 (RAG 엔진이 학습하고 분석할 실제 원천 데이터)"
    )

    # 3. 지원 조건 및 금액
    max_support: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="최대 지원 금액 (원 단위, 통계 및 정렬용)"
    )
    support_amount_desc: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="지원 금액 표시 문자열 (사용자에게 직접 보여줄 텍스트)"
    )
    required_documents: Mapped[Optional[Any]] = mapped_column(
        JSONB,
        nullable=True,
        comment="신청 필수 서류 목록 (JSON 배열: AI가 원문에서 추출하여 저장)",
    )

    # 4. 기간 및 상태 (도메인 규칙 준수)
    start_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="접수 시작일"
    )
    end_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="접수 종료일 (하위 호환성 유지용)"
    )
    closed_at: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        default=date(9999, 12, 31),
        server_default=text("'9999-12-31'"),
        comment="최종 마감일. 상시접수는 9999-12-31 저장 (정렬 및 필터링 핵심 필드)",
    )
    status: Mapped[PolicyStatus] = mapped_column(
        sqlalchemy_Enum(PolicyStatus, name="policystatus", native_enum=False),
        nullable=False,
        comment="공고 상태 (예예정·접수중·마감 등)",
    )

    # 5. 부가 정보 및 시스템 필드
    apply_url: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="원문 신청 페이지 URL (외부 링크)"
    )
    target_logic: Mapped[Optional[Any]] = mapped_column(
        JSONB, nullable=True, comment="사업장 매칭 필터 규칙 (AI가 판단할 기준점)"
    )
    bonus_logic: Mapped[Optional[Any]] = mapped_column(
        JSONB, nullable=True, comment="가산점 계산 규칙 (우대 사항 점수화)"
    )
    view_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="상세 조회 누적 건수 (인기 정책 산출 근거)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        comment="[Soft Delete] 실제 삭제 대신 숨김 처리하여 데이터 무결성 유지",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="데이터 생성 시점",
    )

    # 6. 연관 관계 (관계형 데이터베이스의 '연결 고리')
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
    """policy_bookmarks 테이블 — 사업장(Business)과 정책(Policy) 사이의 '관심' 연결 다리.

    [도메인 규칙 2.2] 사용자 개인이 아닌 '사업장'이 주인공입니다.
    사업장 하나가 동일 정책을 여러 번 찜할 수 없도록 'UniqueConstraint'라는 잠금 장치를 걸었습니다.
    """

    __tablename__ = "policy_bookmarks"
    __table_args__ = (
        UniqueConstraint(
            "business_id",
            "policy_id",
            name="uq_policy_bookmark_biz_policy",
        ),
        Index("ix_policy_bookmark_business_id", "business_id"), # 특정 사업장의 찜 목록 조회 최적화
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="북마크 식별자",
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id"),
        nullable=False,
        comment="북마크 주인 (어느 사업장인가?)",
    )
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("policies.id"),
        nullable=False,
        comment="북마크 대상 (어떤 정책인가?)",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="북마크 클릭 시점",
    )

    business: Mapped["Business"] = relationship(
        "Business", back_populates="policy_bookmarks"
    )
    policy: Mapped["Policy"] = relationship("Policy", back_populates="bookmarks")


class BizPick(Base):
    """biz_picks 테이블 — 사용자에게 도움을 주는 '꿀팁' 콘텐츠 보관소입니다.
    
    이 코드는 현재 정책 도메인에 머물러 있으나, 추후 관리자 도메인으로 이사가 예정되어 있습니다.
    """

    __tablename__ = "biz_picks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="콘텐츠 고유 ID",
    )
    title: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="콘텐츠 제목"
    )
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="카테고리 (세무·정책자금 등 분류)"
    )
    content_html: Mapped[str] = mapped_column(
        Text, nullable=False, comment="HTML 본문 (관리자 도구에서 작성된 원본)"
    )
    thumbnail_url: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="썸네일 이미지 주소"
    )
    is_published: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        comment="공개 여부 (준비 중인 글은 숨김)",
    )
    view_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="조회수",
    )
    like_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="좋아요 수 (인기 콘텐츠 정렬 기준)",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="발행 시점",
    )