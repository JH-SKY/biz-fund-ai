# src/app/domains/policy/service.py
"""정책 도메인 비즈니스 로직 및 트랜잭션 경계.

설계 원칙:
  - [도메인 규칙 5.3] 인프라 우선 원칙: 매칭 엔진은 현재 Stub(Mock) 구현.
  - 모든 DB 트랜잭션 커밋(Commit)은 Service 계층에서 책임집니다.
  - 외부 의존성(Searcher, Engine)은 인터페이스를 통해 결합도를 낮춥니다.
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from src.app.domains.business.model import Business
from src.app.domains.business.exception import business_not_found
from src.app.domains.policy.exception import (
    policy_not_found,
)
from src.app.domains.policy.interfaces import (
    IMatchEngine,
    IPolicySearcher,
    IVectorSearcher,
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
        view_count=policy.view_count,  # [추가] 실시간 조회수 반영
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
        vector_searcher: IVectorSearcher | None = None,
    ) -> None:
        self._session = session
        self._repo = repo
        self._searcher = searcher
        self._match_engine = match_engine
        self._vector_searcher = vector_searcher

    @staticmethod
    def _ensure_business_access(
        business: Business,
        requested_business_id: uuid.UUID,
    ) -> None:
        """헤더 X-Business-Id와 실제 활성 사업장 객체의 정합성을 검증한다."""
        if business.id != requested_business_id:
            raise business_not_found()

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
        return PolicyListResponse(
            items=items, total_count=total_count, total_pages=total_pages
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
        return PolicyListResponse(
            items=items, total_count=total_count, total_pages=total_pages
        )

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
            bookmark = await self._repo.get_bookmark(
                business_id=business_id, policy_id=policy_id
            )
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
        self._ensure_business_access(business, requested_business_id)

        # 2. 정책 데이터 로드
        policies, _, _ = await self._repo.get_active_policies(page=page, size=size)

        # ... (이하 로직은 기존 원본과 동일)
        bookmarked_ids = await self._repo.get_bookmarked_policy_ids(
            business_id=business.id, policy_ids=[p.id for p in policies]
        )

        items: list[PolicyRecommendItem] = []
        for policy in policies:
            # 인터페이스를 통한 매칭 계산 (현재는 Mock)
            result = await self._match_engine.compute_match(
                policy=policy, business=business
            )
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

        unverified_notice: str | None = None
        if not business.is_biz_no_verified:
            unverified_notice = "미검증 사업자 정보 기반 추천입니다"

        return PolicyRecommendResponse(
            items=items,
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
        """특정 사업장 기준 북마크 정책 목록을 반환한다."""
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

    # ── 북마크 토글 ──────────────────────────────────────────────────────

    async def toggle_bookmark(
        self,
        policy_id: uuid.UUID,
        *,
        business: Business,
        requested_business_id: uuid.UUID,
    ) -> BookmarkToggleResponse:
        """북마크 상태를 변경합니다. (도메인 규칙: 존재 시 삭제, 미존재 시 생성)"""
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
        """Admin Dashboard를 위한 인기 정책 TOP N 조회"""
        return await self._repo.get_top_policies_by_views(limit=limit)

    # ── 정책 생성 (Internal) ──────────────────────────────────────────────────

    async def create_policy_internal(self, **kwargs) -> Policy:
        """
        [도메인 규칙] 정책 저장 전 중복 여부를 확인하고, 없으면 저장합니다.
        """
        # 1. 준비물: 중복 확인에 필요한 데이터 꺼내기
        origin_id = kwargs.get("origin_id")

        # 1. origin_id가 넘어온 경우에만 중복 체크 (관리자가 완전 수동 등록 시엔 없을 수 있음)
        if origin_id:
            existing = await self._repo.get_policy_by_origin_id(origin_id)
            if existing:
                from src.app.domains.policy.exception import policy_already_exists
                raise policy_already_exists()

         # 2. 중복이 아니면 DB에 저장
        new_policy = await self._repo.create_policy(
            origin_id=origin_id,  # [추가] 고유 식별자 저장
            title=kwargs.get("title", "제목 없음"),
            content_raw=kwargs.get("content_raw", ""),
            category=kwargs.get("category"),
            agency_name=kwargs.get("agency_name", "미정"),
            apply_url=kwargs.get("apply_url"),
            status=kwargs.get("status"), # 상태
            closed_at=kwargs.get("closed_at") # 마감일
        )

        await self._session.commit()
        return new_policy
    
    async def get_policy_by_id_internal(self, policy_id: uuid.UUID) -> Optional[Policy]:
        """
        [Internal] 관리자 정보 수정 등을 위해 정책 원본 모델을 조회합니다.
        비즈니스 규칙 검증 없이 순수하게 DB의 데이터를 가져옵니다.
        """
        return await self._repo.get_policy_by_id(policy_id)

    async def patch_policy_internal(self, policy: Policy, **kwargs) -> None:
        """
        [Internal] 정책 정보를 부분 수정합니다.
        트랜잭션 커밋(commit)은 호출한 상위 서비스(AdminService)에 위임하기 위해
        이곳에서는 flush 로직까지만 호출합니다.
        """
        await self._repo.patch_policy_internal(policy, **kwargs)

    # ── 3. 중복 검증용 조회 ──────────────────────────────────────────────────

    # ── 벡터(하이브리드) 검색 ────────────────────────────────────────────────

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
        """
        [하이브리드 검색] 쿼리를 임베딩하고 SQL 필터 + 벡터 코사인 유사도 검색을 수행합니다.

        처리 흐름:
          [1] 쿼리 텍스트를 OpenAI API로 임베딩합니다.
          [2] VectorPolicySearcher를 통해 SQL 필터(지역·카테고리·상태) 후 벡터 검색합니다.
          [3] 결과에 북마크 여부를 포함하여 PolicyListResponse로 반환합니다.

        vector_searcher가 주입되지 않은 경우 HTTPException(503)을 발생시킵니다.
        """
        from openai import AsyncOpenAI
        from fastapi import HTTPException
        from src.app.core.config import OPENAI_API_KEY

        if self._vector_searcher is None:
            raise HTTPException(
                status_code=503,
                detail="벡터 검색 기능이 활성화되지 않았습니다. (pgvector 미설정)",
            )

        # [1] 쿼리 임베딩 생성
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        embed_resp = await client.embeddings.create(
            model="text-embedding-3-small",
            input=[query],
        )
        query_vector: list[float] = embed_resp.data[0].embedding

        # [2] 하이브리드 검색 실행
        results = await self._vector_searcher.search(
            query_vector,
            region=region,
            category=category,
            status=status_filter,
            limit=limit,
            offset=offset,
        )

        # [3] 북마크 여부 포함
        policies = [row[0] for row in results]
        bookmarked_ids: set[uuid.UUID] = set()
        if business_id and policies:
            bookmarked_ids = await self._repo.get_bookmarked_policy_ids(
                business_id=business_id, policy_ids=[p.id for p in policies]
            )

        items = [_to_list_item(p, p.id in bookmarked_ids) for p in policies]
        return PolicyListResponse(
            items=items,
            total_count=len(items),
            total_pages=1,
        )
