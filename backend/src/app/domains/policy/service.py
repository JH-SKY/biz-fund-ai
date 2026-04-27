from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.app.domains.business.exception import business_not_found
from src.app.domains.business.model import Business
from src.app.domains.business.repository import BusinessRepository
from src.app.domains.policy.exception import policy_not_found
from src.app.domains.policy.interfaces import IMatchEngine, IPolicySearcher, IVectorSearcher
from src.app.domains.policy.model import Policy
from src.app.domains.policy.repository import PolicyRepository
from src.app.domains.policy.schema import (
    BookmarkToggleResponse,
    CompletionTier,
    MatchLevel,
    PolicyDetailResponse,
    PolicyListItem,
    PolicyListResponse,
    PolicyRecommendItem,
    PolicyRecommendResponse,
)

RECOMMENDATION_CANDIDATE_LIMIT = 200


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
        content=policy.ai_full_explanation or policy.content_raw,
        support_amount=support_amount,
        apply_url=policy.apply_url,
        required_documents=required_docs,
        category=policy.category,
        agency_name=policy.agency_name,
        closed_at=policy.closed_at,
        view_count=policy.view_count,
        is_bookmarked=is_bookmarked,
    )


class PolicyService:
    def __init__(
        self,
        session: AsyncSession,
        repo: PolicyRepository,
        searcher: IPolicySearcher,
        match_engine: IMatchEngine,
        vector_searcher: IVectorSearcher | None = None,
        biz_repo: BusinessRepository | None = None,
    ) -> None:
        self._session = session
        self._repo = repo
        self._searcher = searcher
        self._match_engine = match_engine
        self._vector_searcher = vector_searcher
        self._biz_repo = biz_repo

    @staticmethod
    def _ensure_business_access(
        business: Business,
        requested_business_id: uuid.UUID,
    ) -> None:
        if business.id != requested_business_id:
            raise business_not_found()

    async def get_active_policies(
        self,
        *,
        page: int = 1,
        size: int = 10,
        business_id: Optional[uuid.UUID] = None,
    ) -> PolicyListResponse:
        policies, total_count, total_pages = await self._repo.get_active_policies(
            page=page,
            size=size,
        )

        bookmarked_ids: set[uuid.UUID] = set()
        if business_id and policies:
            bookmarked_ids = await self._repo.get_bookmarked_policy_ids(
                business_id=business_id,
                policy_ids=[policy.id for policy in policies],
            )

        items = [_to_list_item(policy, policy.id in bookmarked_ids) for policy in policies]
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
        policies, total_count, total_pages = await self._searcher.search(
            keyword=keyword,
            region=region,
            category=category,
            page=page,
            size=size,
        )

        bookmarked_ids: set[uuid.UUID] = set()
        if business_id and policies:
            bookmarked_ids = await self._repo.get_bookmarked_policy_ids(
                business_id=business_id,
                policy_ids=[policy.id for policy in policies],
            )

        items = [_to_list_item(policy, policy.id in bookmarked_ids) for policy in policies]
        return PolicyListResponse(
            items=items,
            total_count=total_count,
            total_pages=total_pages,
        )

    async def get_policy_detail(
        self,
        policy_id: uuid.UUID,
        *,
        business_id: Optional[uuid.UUID] = None,
    ) -> PolicyDetailResponse:
        policy = await self._repo.get_policy_by_id(policy_id)
        if policy is None or not policy.is_active:
            raise policy_not_found()

        is_bookmarked = False
        if business_id:
            bookmark = await self._repo.get_bookmark(
                business_id=business_id,
                policy_id=policy_id,
            )
            is_bookmarked = bookmark is not None
            await self._repo.increase_view_count(policy_id)

        response_dto = _to_detail_response(policy, is_bookmarked)
        await self._session.commit()
        return response_dto

    async def get_recommended_policies(
        self,
        business: Business,
        requested_business_id: uuid.UUID,
        *,
        page: int = 1,
        size: int = 10,
    ) -> PolicyRecommendResponse:
        self._ensure_business_access(business, requested_business_id)

        financial_snapshot = None
        if self._biz_repo is not None:
            financial_snapshot = await self._biz_repo.get_latest_financial_snapshot_internal(
                business.id
            )

        has_precise_finance = (
            financial_snapshot is not None
            and (
                financial_snapshot.annual_revenue is not None
                or financial_snapshot.total_debt is not None
                or financial_snapshot.debt_ratio is not None
            )
        )
        tier = CompletionTier.L2 if has_precise_finance else CompletionTier.L1
        policies = await self._repo.get_recommendation_candidates(
            limit=RECOMMENDATION_CANDIDATE_LIMIT
        )
        bookmarked_ids = await self._repo.get_bookmarked_policy_ids(
            business_id=business.id,
            policy_ids=[policy.id for policy in policies],
        )

        items: list[PolicyRecommendItem] = []
        for policy in policies:
            result = await self._match_engine.compute_match(
                policy=policy,
                business=business,
                financial_snapshot=financial_snapshot,
            )
            if result.match_level == MatchLevel.RED:
                continue

            items.append(
                PolicyRecommendItem(
                    policy_id=policy.id,
                    title=policy.title,
                    match_level=result.match_level,
                    match_score=result.match_score,
                    reason=result.reason,
                    estimated_probability=result.estimated_probability,
                    is_bookmarked=policy.id in bookmarked_ids,
                )
            )

        level_order = {MatchLevel.GREEN: 0, MatchLevel.YELLOW: 1, MatchLevel.RED: 2}
        items.sort(key=lambda item: (level_order[item.match_level], -item.match_score))
        start = max(0, (page - 1) * size)
        paged_items = items[start : start + size]

        upgrade_hint: str | None = None
        missing_fields: list[str] = []
        if tier == CompletionTier.L1:
            upgrade_hint = (
                "지금 추천은 1차 정보 기준 후보군입니다. "
                "매출, 부채, 체납 여부를 입력하면 실제 자격 조건까지 반영해 다시 추천합니다."
            )
            missing_fields = ["annual_revenue", "total_debt", "debt_ratio"]

        unverified_notice: str | None = None
        if not business.is_biz_no_verified:
            unverified_notice = "사업자번호 미검증 상태라 기본 사업 정보 기준으로만 추천합니다."

        return PolicyRecommendResponse(
            items=paged_items,
            completeness_tier=tier,
            upgrade_hint=upgrade_hint,
            missing_fields=missing_fields,
            unverified_notice=unverified_notice,
        )

    async def get_bookmarked_policies(
        self,
        *,
        business: Business,
        requested_business_id: uuid.UUID,
        page: int = 1,
        size: int = 10,
    ) -> PolicyListResponse:
        self._ensure_business_access(business, requested_business_id)

        policies, total_count, total_pages = await self._repo.get_bookmarked_policies(
            business_id=business.id,
            page=page,
            size=size,
        )

        items = [_to_list_item(policy, True) for policy in policies]
        return PolicyListResponse(
            items=items,
            total_count=total_count,
            total_pages=total_pages,
        )

    async def toggle_bookmark(
        self,
        policy_id: uuid.UUID,
        *,
        business: Business,
        requested_business_id: uuid.UUID,
    ) -> BookmarkToggleResponse:
        self._ensure_business_access(business, requested_business_id)

        policy = await self._repo.get_policy_by_id(policy_id)
        if not policy or not policy.is_active:
            raise policy_not_found()

        is_bookmarked = await self._repo.toggle_bookmark(
            business_id=business.id,
            policy_id=policy_id,
        )
        await self._session.commit()

        return BookmarkToggleResponse(is_bookmarked=is_bookmarked, policy_id=policy_id)

    async def list_top_policies_by_views(self, limit: int = 5) -> list[Policy]:
        return await self._repo.get_top_policies_by_views(limit=limit)

    async def create_policy_internal(self, **kwargs) -> Policy:
        origin_id = kwargs.get("origin_id")
        if origin_id:
            existing = await self._repo.get_policy_by_origin_id(origin_id)
            if existing:
                from src.app.domains.policy.exception import policy_already_exists

                raise policy_already_exists()

        new_policy = await self._repo.create_policy(
            origin_id=origin_id,
            title=kwargs.get("title", "제목 없음"),
            content_raw=kwargs.get("content_raw", ""),
            category=kwargs.get("category"),
            agency_name=kwargs.get("agency_name", "미정"),
            apply_url=kwargs.get("apply_url"),
            status=kwargs.get("status"),
            closed_at=kwargs.get("closed_at"),
        )

        await self._session.commit()
        return new_policy

    async def get_policy_by_id_internal(self, policy_id: uuid.UUID) -> Optional[Policy]:
        return await self._repo.get_policy_by_id(policy_id)

    async def patch_policy_internal(self, policy: Policy, **kwargs) -> None:
        await self._repo.patch_policy_internal(policy, **kwargs)

    async def vector_search_policies(
        self,
        query: str,
        *,
        region: Optional[str] = None,
        category: Optional[str] = None,
        status_filter: Optional[str] = "RECRUITING",
        limit: int = 10,
        offset: int = 0,
        business_id: Optional[uuid.UUID] = None,
    ) -> PolicyListResponse:
        from fastapi import HTTPException
        from openai import AsyncOpenAI

        from src.app.core.config import OPENAI_API_KEY

        if self._vector_searcher is None:
            raise HTTPException(
                status_code=503,
                detail="벡터 검색 기능이 활성화되지 않았습니다.",
            )

        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        embed_resp = await client.embeddings.create(
            model="text-embedding-3-small",
            input=[query],
        )
        query_vector: list[float] = embed_resp.data[0].embedding

        results = await self._vector_searcher.search(
            query_vector,
            region=region,
            category=category,
            status=status_filter,
            limit=limit,
            offset=offset,
        )

        policies = [row[0] for row in results]
        bookmarked_ids: set[uuid.UUID] = set()
        if business_id and policies:
            bookmarked_ids = await self._repo.get_bookmarked_policy_ids(
                business_id=business_id,
                policy_ids=[policy.id for policy in policies],
            )

        items = [_to_list_item(policy, policy.id in bookmarked_ids) for policy in policies]
        return PolicyListResponse(
            items=items,
            total_count=len(items),
            total_pages=1,
        )
