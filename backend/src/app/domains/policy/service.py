# src/app/domains/policy/service.py
"""정책 도메인 비즈니스 로직 및 트랜잭션 경계.

설계 원칙:
  - [도메인 규칙 5.3] 인프라 우선 원칙: 매칭 엔진은 현재 Stub(Mock) 구현.
  - 모든 DB 트랜잭션 커밋(Commit)은 Service 계층에서 책임집니다.
  - 외부 의존성(Searcher, Engine)은 인터페이스를 통해 결합도를 낮춥니다.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.app.domains.business.model import Business
from src.app.domains.policy.exception import (
    policy_inactive,
    policy_not_found,
)
from src.app.domains.policy.interfaces import (
    IMatchEngine,
    IPolicySearcher,
)
from src.app.domains.policy.model import Policy
from src.app.domains.policy.repository import PolicyRepository
from src.app.domains.policy.schema import (
    BookmarkToggleResponse,
    MatchLevel,
    PolicyDetailResponse,
    PolicyListItem,
    PolicyListResponse,
    PolicyRecommendItem,
    PolicyRecommendResponse,
)

# ── 내부 유틸 (Private Utilities) ──────────────────────────────────────────


def _to_list_item(policy: Policy, is_bookmarked: bool) -> PolicyListItem:
    """1. DB 모델을 목록용 응답 스키마로 변환합니다."""
    return PolicyListItem(
        policy_id=policy.id,
        title=policy.title,
        category=policy.category,
        closed_at=policy.closed_at,
        is_bookmarked=is_bookmarked,
    )


def _to_detail_response(policy: Policy, is_bookmarked: bool) -> PolicyDetailResponse:
    """2. DB 모델을 상세 페이지용 응답 스키마로 변환합니다. (조회수 포함)"""
    required_docs: list[str] = []
    if isinstance(policy.required_documents, list):
        required_docs = policy.required_documents

    # 지원 금액 표시 로직: 설명 문구가 없으면 숫자 기반으로 생성
    support_amount = policy.support_amount_desc
    if support_amount is None and policy.max_support is not None:
        support_amount = f"최대 {policy.max_support:,}원"

    return PolicyDetailResponse(
        policy_id=policy.id,
        title=policy.title,
        content=policy.ai_full_explanation or policy.content_raw,
        support_amount=support_amount,
        apply_url=policy.apply_url,
        required_documents=required_docs,
        category=policy.category,
        agency_name=policy.agency_name,
        closed_at=policy.closed_at,
        view_count=policy.view_count, # [추가] 실시간 조회수 반영
        is_bookmarked=is_bookmarked,
    )


# ── Service ────────────────────────────────────────────────────────────────


class PolicyService:
    """정책 도메인의 유스케이스(Use Case)를 실행하는 서비스 클래스."""

    def __init__(
        self,
        session: AsyncSession,
        repo: PolicyRepository,
        searcher: IPolicySearcher,
        match_engine: IMatchEngine,
    ) -> None:
        self._session = session
        self._repo = repo
        self._searcher = searcher
        self._match_engine = match_engine

    # ── 목록 및 검색 ──────────────────────────────────────────────────────

    async def get_active_policies(
        self,
        *,
        page: int = 1,
        size: int = 10,
        business_id: Optional[uuid.UUID] = None,
    ) -> PolicyListResponse:
        """최신순으로 활성화된 정책 목록을 가져옵니다."""
        policies, total_count, total_pages = await self._repo.get_active_policies(
            page=page, size=size
        )

        bookmarked_ids: set[uuid.UUID] = set()
        if business_id and policies:
            bookmarked_ids = await self._repo.get_bookmarked_policy_ids(
                business_id=business_id, policy_ids=[p.id for p in policies]
            )

        items = [_to_list_item(p, p.id in bookmarked_ids) for p in policies]
        return PolicyListResponse(items=items, total_count=total_count, total_pages=total_pages)

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
        """복합 검색 엔진(IPolicySearcher)을 사용하여 정책을 검색합니다."""
        policies, total_count, total_pages = await self._searcher.search(
            keyword=keyword, region=region, category=category, page=page, size=size
        )

        bookmarked_ids: set[uuid.UUID] = set()
        if business_id and policies:
            bookmarked_ids = await self._repo.get_bookmarked_policy_ids(
                business_id=business_id, policy_ids=[p.id for p in policies]
            )

        items = [_to_list_item(p, p.id in bookmarked_ids) for p in policies]
        return PolicyListResponse(items=items, total_count=total_count, total_pages=total_pages)

    # ── 상세 조회 및 조회수 로직 ────────────────────────────────────────────

    async def get_policy_detail(
        self,
        policy_id: uuid.UUID,
        *,
        business_id: Optional[uuid.UUID] = None,
    ) -> PolicyDetailResponse:
        """정책 상세 정보를 조회하고 비즈니스 규칙에 따라 조회수를 올립니다.
        
        조회수 증가 규칙 (도메인 규칙 3.3):
          - 로그인한 사용자(business_id 존재)가 조회할 때만 카운팅.
          - [사고과정] 현재는 단순 증가이나, 추후 Redis 도입 시 24시간 제한 로직 추가 예정.
        """
        # 1. 정책 존재 여부 검증
        policy = await self._repo.get_policy_by_id(policy_id)
        if policy is None or not policy.is_active:
            raise policy_not_found()

        # 2. 개인화 정보(북마크) 및 조회수 처리
        is_bookmarked = False
        if business_id:
            # 북마크 여부 확인
            bookmark = await self._repo.get_bookmark(business_id=business_id, policy_id=policy_id)
            is_bookmarked = bookmark is not None
            
            # 조회수 원자적 증가 (Repository 위임)
            await self._repo.increase_view_count(policy_id)

        # 3. 트랜잭션 확정 (조회수 반영)
        response_dto = _to_detail_response(policy, is_bookmarked)
        await self._session.commit()
        
        return response_dto

    # ── AI 맞춤 추천 ──────────────────────────────────────────────────────

    async def get_recommended_policies(
        self,
        business: Business,
        requested_business_id: uuid.UUID,  # [추가] 라우터에서 넘겨받은 ID
        *,
        page: int = 1,
        size: int = 10,
    ) -> PolicyRecommendResponse:
        """매칭 엔진(IMatchEngine)을 활용하여 사업장 맞춤형 정책을 추천합니다.
        
        설계 의도:
          - [A5 권한 격리] 헤더로 들어온 ID와 DB에서 조회된 실제 사업장 객체가 일치하는지 검증합니다.
          - 일치하지 않을 경우, 권한 없는 데이터 접근으로 간주하여 에러를 발생시킵니다.
        """
        # 1. 권한 검증 (라우터에서 이관된 로직)
        if business.id != requested_business_id:
            from src.app.domains.business.exception import business_not_found
            raise business_not_found()

        # 2. 정책 데이터 로드
        policies, _, _ = await self._repo.get_active_policies(page=page, size=size)
        
        # ... (이하 로직은 기존 원본과 동일)
        bookmarked_ids = await self._repo.get_bookmarked_policy_ids(
            business_id=business.id, policy_ids=[p.id for p in policies]
        )

        items: list[PolicyRecommendItem] = []
        for policy in policies:
            # 인터페이스를 통한 매칭 계산 (현재는 Mock)
            result = await self._match_engine.compute_match(policy=policy, business=business)
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

        # 신호등 등급순(GREEN -> YELLOW -> RED) 및 점수 내림차순 정렬
        level_order = {MatchLevel.GREEN: 0, MatchLevel.YELLOW: 1, MatchLevel.RED: 2}
        items.sort(key=lambda x: (level_order[x.match_level], -x.match_score))

        return PolicyRecommendResponse(items=items)

    # ── 북마크 토글 ──────────────────────────────────────────────────────

    async def toggle_bookmark(
        self,
        policy_id: uuid.UUID,
        business_id: uuid.UUID,
    ) -> BookmarkToggleResponse:
        """북마크 상태를 변경합니다. (도메인 규칙: 존재 시 삭제, 미존재 시 생성)"""
        policy = await self._repo.get_policy_by_id(policy_id)
        if not policy or not policy.is_active:
            raise policy_not_found()

        is_bookmarked = await self._repo.toggle_bookmark(
            business_id=business_id, policy_id=policy_id
        )
        await self._session.commit()

        return BookmarkToggleResponse(is_bookmarked=is_bookmarked, policy_id=policy_id)