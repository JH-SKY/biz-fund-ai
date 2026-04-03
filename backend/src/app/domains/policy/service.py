# src/app/domains/policy/service.py
"""정책 도메인 비즈니스 로직 및 트랜잭션 경계.

설계 원칙:
  - [도메인 규칙 5.3] 인프라 우선 원칙: 매칭 엔진은 현재 Stub(Mock) 구현.
    실제 RAG 엔진 결합 전까지 고정 Mock 데이터를 반환하며 전체 플로우를 검증한다.
  - [도메인 규칙 5.3] Context Pass-through: 매칭 엔진 인터페이스는 항상
    business_id 등 컨텍스트를 인수로 받을 수 있는 서명을 유지한다.
  - 모든 DB 커밋은 Service에서만 발생한다 (Repository는 flush만).
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.app.domains.business.model import Business
from src.app.domains.policy.exception import policy_inactive, policy_not_found
from src.app.domains.policy.model import Policy
from src.app.domains.policy.repository import PolicyRepository
from src.app.domains.policy.schema import (
    ALWAYS_OPEN_DATE,
    BookmarkToggleResponse,
    MatchLevel,
    PolicyDetailResponse,
    PolicyListItem,
    PolicyListResponse,
    PolicyRecommendItem,
    PolicyRecommendResponse,
)


# ── 매칭 엔진 인터페이스 (Stub) ────────────────────────────────────────────


class MatchResult:
    """매칭 엔진 단건 결과 DTO."""

    def __init__(
        self,
        policy_id: uuid.UUID,
        match_level: MatchLevel,
        match_score: float,
        reason: str,
    ) -> None:
        self.policy_id = policy_id
        self.match_level = match_level
        self.match_score = match_score
        self.reason = reason


async def compute_match(
    policy: Policy,
    business: Business,
) -> MatchResult:
    """정책-사업장 매칭 계산 인터페이스.

    [도메인 규칙 5.3 Mocking Strategy]
    현재는 사업장 profile_score를 기반으로 신호등 등급을 결정하는
    단순 Mock 로직을 반환한다.

    실제 엔진 연결 시 이 함수 내부만 교체하면 된다.
    (Service 레이어, Router 레이어는 변경 불필요)

    TODO: RAG 엔진 / LangGraph 결합 시
      - policy.target_logic (JSONB) 기반 Hard Filter 적용 (도메인 규칙 4.1 Step 1)
      - policy.bonus_logic (JSONB) 기반 가산점 합산 (도메인 규칙 4.1 Step 2)
      - business.tax_arrears_yn → 체납 시 즉시 RED 판정
    """
    score = float(business.profile_score)

    if score >= 70:
        level = MatchLevel.GREEN
        reason = "사업장 정보 완성도가 높아 필수 요건을 충족합니다."
    elif score >= 40:
        level = MatchLevel.YELLOW
        reason = "일부 가점 요건 미충족 — 추가 정보 입력 시 GREEN 상향 가능합니다."
    else:
        level = MatchLevel.RED
        reason = "사업장 정보가 부족하여 자격 판단이 어렵습니다. 온보딩을 완료해 주세요."

    return MatchResult(
        policy_id=policy.id,
        match_level=level,
        match_score=round(score, 1),
        reason=reason,
    )


# ── 내부 유틸 ──────────────────────────────────────────────────────────────


def _to_list_item(policy: Policy, is_bookmarked: bool) -> PolicyListItem:
    return PolicyListItem(
        policy_id=policy.id,
        title=policy.title,
        category=policy.category,
        closed_at=policy.closed_at,
        is_bookmarked=is_bookmarked,
    )


def _to_detail_response(policy: Policy, is_bookmarked: bool) -> PolicyDetailResponse:
    required_docs: list[str] = []
    if isinstance(policy.required_documents, list):
        required_docs = policy.required_documents

    support_amount = policy.support_amount_desc
    if support_amount is None and policy.max_support is not None:
        support_amount = f"최대 {policy.max_support:,}원"

    return PolicyDetailResponse(
        policy_id=policy.id,
        title=policy.title,
        content=policy.content_raw,
        support_amount=support_amount,
        apply_url=policy.apply_url,
        required_documents=required_docs,
        category=policy.category,
        agency_name=policy.agency_name,
        closed_at=policy.closed_at,
        is_bookmarked=is_bookmarked,
    )


# ── Service ────────────────────────────────────────────────────────────────


class PolicyService:
    """정책 도메인 유스케이스."""

    def __init__(
        self,
        session: AsyncSession,
        repo: PolicyRepository,
    ) -> None:
        self._session = session
        self._repo = repo

    # ── 목록 조회 ─────────────────────────────────────────────────────────

    async def get_active_policies(
        self,
        *,
        page: int = 1,
        size: int = 10,
        business_id: Optional[uuid.UUID] = None,
    ) -> PolicyListResponse:
        """전체 활성 정책 목록 — 최신순 페이징.

        business_id가 주어지면 북마크 여부를 함께 반환한다.
        """
        policies, total_count, total_pages = await self._repo.get_active_policies(
            page=page, size=size
        )

        bookmarked_ids: set[uuid.UUID] = set()
        if business_id is not None and policies:
            policy_ids = [p.id for p in policies]
            bookmarked_ids = await self._repo.get_bookmarked_policy_ids(
                business_id=business_id, policy_ids=policy_ids
            )

        items = [_to_list_item(p, p.id in bookmarked_ids) for p in policies]
        return PolicyListResponse(
            items=items,
            total_count=total_count,
            total_pages=total_pages,
        )

    async def search_policies(
        self,
        *,
        keyword: Optional[str] = None,
        region: Optional[str] = None,
        category: Optional[str] = None,
        page: int = 1,
        size: int = 10,
        business_id: Optional[uuid.UUID] = None,
    ) -> PolicyListResponse:
        """키워드·지역·카테고리 복합 검색."""
        policies, total_count, total_pages = await self._repo.search_policies(
            keyword=keyword,
            region=region,
            category=category,
            page=page,
            size=size,
        )

        bookmarked_ids: set[uuid.UUID] = set()
        if business_id is not None and policies:
            bookmarked_ids = await self._repo.get_bookmarked_policy_ids(
                business_id=business_id, policy_ids=[p.id for p in policies]
            )

        items = [_to_list_item(p, p.id in bookmarked_ids) for p in policies]
        return PolicyListResponse(
            items=items,
            total_count=total_count,
            total_pages=total_pages,
        )

    # ── 상세 조회 ─────────────────────────────────────────────────────────

    async def get_policy_detail(
        self,
        policy_id: uuid.UUID,
        *,
        business_id: Optional[uuid.UUID] = None,
    ) -> PolicyDetailResponse:
        """정책 상세 + 북마크 여부 반환."""
        policy = await self._repo.get_policy_by_id(policy_id)
        if policy is None or not policy.is_active:
            raise policy_not_found()

        is_bookmarked = False
        if business_id is not None:
            bookmark = await self._repo.get_bookmark(
                business_id=business_id, policy_id=policy_id
            )
            is_bookmarked = bookmark is not None

        # 조회수 증가 (flush만 — 커밋은 여기서)
        policy.view_count += 1
        await self._session.flush()
        await self._session.commit()

        return _to_detail_response(policy, is_bookmarked)

    # ── 추천 (매칭 엔진 Stub) ─────────────────────────────────────────────

    async def get_recommended_policies(
        self,
        business: Business,
        *,
        page: int = 1,
        size: int = 10,
    ) -> PolicyRecommendResponse:
        """사업장 기반 맞춤 추천 — 신호등(RED/YELLOW/GREEN) 적용.

        [도메인 규칙 5.3] 현재는 Mock 데이터 반환.
        매칭 결과는 스냅샷 저장 대상(도메인 규칙 4.2)이나
        현재 단계에서는 실시간 계산 결과만 반환한다.
        """
        policies, _, _ = await self._repo.get_active_policies(page=page, size=size)

        bookmarked_ids = await self._repo.get_bookmarked_policy_ids(
            business_id=business.id,
            policy_ids=[p.id for p in policies],
        )

        items: list[PolicyRecommendItem] = []
        for policy in policies:
            result = await compute_match(policy=policy, business=business)
            items.append(
                PolicyRecommendItem(
                    policy_id=policy.id,
                    title=policy.title,
                    match_level=result.match_level,
                    match_score=result.match_score,
                    reason=result.reason,
                    is_bookmarked=policy.id in bookmarked_ids,
                )
            )

        # 신호등 우선순위 정렬: GREEN > YELLOW > RED
        level_order = {MatchLevel.GREEN: 0, MatchLevel.YELLOW: 1, MatchLevel.RED: 2}
        items.sort(key=lambda x: (level_order[x.match_level], -x.match_score))

        return PolicyRecommendResponse(items=items)

    # ── 북마크 ────────────────────────────────────────────────────────────

    async def toggle_bookmark(
        self,
        policy_id: uuid.UUID,
        business_id: uuid.UUID,
    ) -> BookmarkToggleResponse:
        """북마크 토글 — 존재하면 삭제, 없으면 생성.

        정책 존재 여부를 먼저 검증한 뒤 토글한다.
        """
        policy = await self._repo.get_policy_by_id(policy_id)
        if policy is None:
            raise policy_not_found()
        if not policy.is_active:
            raise policy_inactive()

        is_bookmarked = await self._repo.toggle_bookmark(
            business_id=business_id, policy_id=policy_id
        )
        await self._session.commit()

        return BookmarkToggleResponse(
            is_bookmarked=is_bookmarked,
            policy_id=policy_id,
        )

    async def get_bookmarked_policies(
        self,
        business_id: uuid.UUID,
        *,
        page: int = 1,
        size: int = 10,
    ) -> PolicyListResponse:
        """사업장 기준 북마크된 정책 목록."""
        policies, total_count, total_pages = await self._repo.get_bookmarked_policies(
            business_id=business_id, page=page, size=size
        )
        # 이 목록의 모든 정책은 is_bookmarked=True
        items = [_to_list_item(p, True) for p in policies]
        return PolicyListResponse(
            items=items,
            total_count=total_count,
            total_pages=total_pages,
        )
