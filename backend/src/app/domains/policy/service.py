# src/app/domains/policy/service.py
"""정책(Policy) 도메인 비즈니스 로직 및 트랜잭션 경계.

설계 원칙:
  - 정책 목록/검색/상세/북마크/추천 유스케이스를 담당한다.
  - IPolicySearcher(키워드 검색), IMatchEngine(매칭 점수 계산),
    IVectorSearcher(벡터 검색)는 인터페이스로 주입받아 구현 교체가 쉽다.
  - 추천 알고리즘은 [L1: 기본 정보] / [L2: 재무 정보 포함] 두 단계로 나뉘며,
    재무 정보가 있을수록 더 정밀한 추천이 가능하다.
  - 모든 DB 커밋은 이 Service에서만 발생한다 (Repository는 flush만 수행).
"""

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

# 추천 후보 정책 최대 수: 이 수만큼 정책을 불러온 뒤 매칭 엔진으로 필터링한다
RECOMMENDATION_CANDIDATE_LIMIT = 200


def _to_list_item(policy: Policy, is_bookmarked: bool) -> PolicyListItem:
    """Policy 모델 → 목록 아이템 DTO 변환 헬퍼."""
    return PolicyListItem(
        policy_id=policy.id,
        title=policy.title,
        category=policy.category,
        closed_at=policy.closed_at,
        is_bookmarked=is_bookmarked,
    )


def _to_detail_response(policy: Policy, is_bookmarked: bool) -> PolicyDetailResponse:
    """Policy 모델 → 상세 응답 DTO 변환 헬퍼.

    [처리 내용]
    - required_documents 가 list 타입인 경우만 사용 (데이터 정합성 방어)
    - support_amount_desc 가 없으면 max_support 를 '최대 N원' 형식으로 조합
    - AI가 정리한 ai_full_explanation 이 있으면 우선 사용, 없으면 원문(content_raw) 노출
    """
    required_docs: list[str] = []
    if isinstance(policy.required_documents, list):
        required_docs = policy.required_documents

    # 지원금액 문구: AI 요약이 있으면 우선, 없으면 최대 지원액으로 조합
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
    """정책 도메인 유스케이스.

    외부 서비스는 생성자 주입으로 받는다 — 테스트·교체 시 이 클래스만 변경.
      - searcher       : 키워드/지역/카테고리 기반 검색
      - match_engine   : 사업장 프로필과 정책 조건 매칭 점수 계산
      - vector_searcher: pgvector 기반 의미 검색 (선택 기능)
      - biz_repo       : 재무 스냅샷 조회용 (정밀 추천에 필요)
    """

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
        """[내부 헬퍼] 요청된 사업장 ID가 현재 인증된 사업장과 일치하는지 검증한다.

        불일치 시 404 반환 (보안상 403 대신 404로 리소스 존재 여부도 숨김).
        """
        if business.id != requested_business_id:
            raise business_not_found()

    async def get_active_policies(
        self,
        *,
        page: int = 1,
        size: int = 10,
        business_id: Optional[uuid.UUID] = None,
    ) -> PolicyListResponse:
        """활성 정책 목록을 페이징 조회한다.

        business_id 가 제공되면 해당 사업장의 북마크 여부도 함께 반환한다.
        """
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
        """키워드·지역·카테고리 조건으로 정책을 검색한다.

        IPolicySearcher 구현체에 검색 로직을 위임하며,
        결과에 북마크 여부를 포함하여 반환한다.
        """
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
        """정책 상세 정보를 조회한다.

        [로직]
        1. 정책이 없거나 비활성 상태면 404 반환
        2. business_id 가 있으면 북마크 여부 확인 + 조회수 1 증가
        3. AI 요약 본문이 있으면 우선 반환, 없으면 원문 반환
        """
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
        """사업장 프로필 기반 맞춤 정책 추천 목록을 반환한다.

        [추천 단계]
        - L1 (기본): 사업장 기본 정보(업종·지역·가점 항목)만으로 후보 필터링
        - L2 (정밀): 재무 스냅샷(매출·부채 등)이 있으면 자격 조건까지 반영한 정밀 매칭

        [로직 순서]
        1. 소유권 검증
        2. 최신 재무 스냅샷 조회 → 단계(tier) 결정
        3. 후보 정책(최대 RECOMMENDATION_CANDIDATE_LIMIT개) 로드
        4. 매칭 엔진으로 각 정책의 매칭 점수 계산, RED(부적합)는 제외
        5. GREEN → YELLOW 순으로 정렬 후 페이징
        6. L1 단계이면 재무 정보 입력 유도 힌트 추가
        """
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
        """사업장이 북마크한 정책 목록을 페이징 조회한다."""
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
        """정책 북마크를 토글한다 (없으면 추가, 있으면 제거).

        [로직]
        1. 소유권 검증
        2. 정책이 활성 상태인지 확인
        3. 북마크 토글 후 현재 북마크 상태 반환
        """
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
        """[Admin] 조회수 기준 상위 정책 목록 반환 (대시보드 인기 정책 위젯용)."""
        return await self._repo.get_top_policies_by_views(limit=limit)

    async def create_policy_internal(self, **kwargs) -> Policy:
        """[Internal] 관리자 또는 동기화 배치에서 새 정책을 생성한다.

        origin_id 가 있으면 외부 공공 API 데이터 중복 등록을 방지하기 위해
        먼저 동일 origin_id 존재 여부를 확인한다.
        """
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
        """[Internal] 정책 ID로 단건 조회 (활성 여부 미필터, 도메인 내부 연동용)."""
        return await self._repo.get_policy_by_id(policy_id)

    async def patch_policy_internal(self, policy: Policy, **kwargs) -> None:
        """[Internal] 정책 일부 필드를 수정한다 (관리자·동기화 배치용)."""
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
        """자연어 쿼리로 의미 기반(벡터) 정책 검색을 수행한다.

        [로직]
        1. OPENAI_API_KEY로 쿼리 문자열을 임베딩 벡터로 변환
        2. pgvector 기반 IVectorSearcher로 유사 정책 청크 검색
        3. 결과에 북마크 여부 포함하여 반환

        [주의]
        vector_searcher 가 None 이면 기능이 비활성 상태이므로 503을 반환한다.
        """
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
