# src/app/domains/policy/schema.py
"""정책 도메인 Pydantic 요청/응답 스키마.

검증 규칙 (도메인 규칙서 3.3 준수):
  - title: min_length=1, max_length=255
  - keyword (검색): min_length=1 이상 필수
  - match_level: MatchLevel Enum (GREEN / YELLOW / RED)
  - page: ge=1, size: ge=1 le=100
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# 9999-12-31 상수 — 상시접수 여부 판별 기준
ALWAYS_OPEN_DATE = date(9999, 12, 31)


class MatchLevel(str, Enum):
    """신호등 매칭 등급 (도메인 규칙 4.1)."""

    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class CompletionTier(str, Enum):
    """맞춤 추천 완성도 단계.

    L1 — 사업자 기본정보만 입력된 상태 (업종·지역·인원·용도).
    L2 — 재무 스냅샷까지 입력 완료 → 확률·시뮬레이션 활성.
    """

    L1 = "L1"
    L2 = "L2"


# ── 목록 조회 ──────────────────────────────────────────────────────────────


class PolicyListItem(BaseModel):
    """정책 목록 아이템 (명세서 §1 / §4 / §6 공통 규격)."""

    policy_id: UUID
    title: str
    category: Optional[str] = None
    closed_at: date
    is_bookmarked: bool = False

    model_config = ConfigDict(from_attributes=True)


class PolicyListResponse(BaseModel):
    """페이징이 적용된 정책 목록 응답."""

    items: list[PolicyListItem]
    total_count: int
    total_pages: int


# ── 추천 목록 ──────────────────────────────────────────────────────────────


class PolicyRecommendItem(BaseModel):
    """매칭 추천 아이템 — 신호등 등급 포함 (명세서 §2)."""

    policy_id: UUID
    title: str
    match_level: MatchLevel
    match_score: float = Field(..., ge=0.0, le=100.0, description="매칭 점수 (0~100)")
    reason: str = Field(..., min_length=1, description="매칭 판정 근거 문구")
    estimated_probability: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="추정 수혜 확률 (0~100). L2(재무) 입력 시에만 제공되는 참고 수치.",
    )
    is_bookmarked: bool = False

    model_config = ConfigDict(from_attributes=True)


class PolicyRecommendResponse(BaseModel):
    items: list[PolicyRecommendItem]
    completeness_tier: CompletionTier = Field(
        CompletionTier.L1,
        description="현재 추천 완성도 단계. L2 이면 확률·시뮬 기능 활성.",
    )
    upgrade_hint: Optional[str] = Field(
        None,
        description="L1 단계 사용자에게 보여줄 L2 유도 안내 문구",
    )
    missing_fields: list[str] = Field(
        default_factory=list,
        description="L2 전환에 필요한 누락 항목 목록",
    )
    unverified_notice: Optional[str] = Field(
        None,
        description="사업자번호 국세청 미검증 시 맞춤 추천 상단 안내 문구",
    )


# ── 상세 조회 ──────────────────────────────────────────────────────────────


class PolicyDetailResponse(BaseModel):
    """정책 상세 응답 (명세서 §3).

    기존 필드에 실시간 조회수(view_count)를 추가하여 사용자에게 정책의 인기도를 전달합니다.
    """

    policy_id: UUID
    title: str
    content: str = Field(..., description="공고 원문 전체 또는 AI 요약")
    support_amount: Optional[str] = Field(None, description="지원 금액 표시 문자열")
    apply_url: Optional[str] = None
    required_documents: list[str] = Field(
        default_factory=list, description="신청 필수 서류 목록"
    )
    category: Optional[str] = None
    agency_name: str
    closed_at: date
    view_count: int = Field(
        0, description="정책 상세 조회수"
    )  # [추가] 실시간 조회수 지표
    is_bookmarked: bool = False

    model_config = ConfigDict(from_attributes=True)


# ── 북마크 ─────────────────────────────────────────────────────────────────


class BookmarkToggleResponse(BaseModel):
    """북마크 토글 결과 (명세서 §5)."""

    is_bookmarked: bool
    policy_id: UUID


# ── 검색 쿼리 파라미터 ─────────────────────────────────────────────────────


class PolicySearchParams(BaseModel):
    """정책 키워드 검색 파라미터 (명세서 §4)."""

    keyword: Optional[str] = Field(None, min_length=1, description="검색 키워드")
    region: Optional[str] = Field(None, description="지역 필터 (예: 서울)")
    category: Optional[str] = Field(None, description="카테고리 필터 (예: R&D)")
    page: int = Field(1, ge=1)
    size: int = Field(10, ge=1, le=100)
