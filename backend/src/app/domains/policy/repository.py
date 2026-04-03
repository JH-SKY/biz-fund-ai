# src/app/domains/policy/repository.py
"""정책 도메인 DB 접근 계층.

원칙:
  - 비즈니스 판단(예외 발생, 조건 분기)은 Service에서, I/O만 여기에.
  - [도메인 규칙 0] is_active=True 필터를 모든 공개 조회에 적용(Soft Delete).
  - [도메인 규칙 2.2] 북마크 조회는 business_id 기준으로 격리.
"""

from __future__ import annotations

import math
import uuid
from typing import Optional

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.domains.policy.model import Policy, PolicyBookmark


class PolicyRepository:
    """정책 도메인 Repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Policy 목록 ────────────────────────────────────────────────────────

    async def get_active_policies(
        self,
        *,
        page: int = 1,
        size: int = 10,
    ) -> tuple[list[Policy], int, int]:
        """is_active=True 정책 전체 — 최신순 페이징.

        Returns:
            (items, total_count, total_pages)
        """
        base = select(Policy).where(Policy.is_active.is_(True))

        count_stmt = select(func.count()).select_from(
            base.subquery()
        )
        total_count_result = await self._session.execute(count_stmt)
        total_count: int = total_count_result.scalar_one()

        total_pages = max(1, math.ceil(total_count / size))

        stmt = (
            base.order_by(Policy.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())

        return items, total_count, total_pages

    async def get_policy_by_id(self, policy_id: uuid.UUID) -> Policy | None:
        """단건 조회 — is_active 무관(Service에서 판단)."""
        stmt = select(Policy).where(Policy.id == policy_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def search_policies(
        self,
        *,
        keyword: Optional[str] = None,
        region: Optional[str] = None,
        category: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> tuple[list[Policy], int, int]:
        """키워드·지역·카테고리 복합 검색 (is_active=True 전제).

        - keyword: title 또는 content_raw ILIKE 검색
        - region: Policy.region ILIKE 검색
        - category: 정확 일치
        """
        conditions = [Policy.is_active.is_(True)]

        if keyword:
            pattern = f"%{keyword}%"
            conditions.append(
                or_(
                    Policy.title.ilike(pattern),
                    Policy.content_raw.ilike(pattern),
                )
            )
        if region:
            conditions.append(Policy.region.ilike(f"%{region}%"))
        if category:
            conditions.append(Policy.category == category)

        base = select(Policy).where(*conditions)

        count_stmt = select(func.count()).select_from(base.subquery())
        total_count: int = (await self._session.execute(count_stmt)).scalar_one()
        total_pages = max(1, math.ceil(total_count / size))

        stmt = (
            base.order_by(Policy.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total_count, total_pages

    # ── PolicyBookmark ──────────────────────────────────────────────────────

    async def get_bookmark(
        self,
        *,
        business_id: uuid.UUID,
        policy_id: uuid.UUID,
    ) -> PolicyBookmark | None:
        """단건 북마크 조회."""
        stmt = select(PolicyBookmark).where(
            PolicyBookmark.business_id == business_id,
            PolicyBookmark.policy_id == policy_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_bookmarked_policy_ids(
        self,
        *,
        business_id: uuid.UUID,
        policy_ids: list[uuid.UUID],
    ) -> set[uuid.UUID]:
        """주어진 policy_ids 중 해당 사업장이 북마크한 ID 집합 반환.

        목록 조회 시 is_bookmarked 여부를 O(1) 판별용으로 사용.
        """
        if not policy_ids:
            return set()
        stmt = select(PolicyBookmark.policy_id).where(
            PolicyBookmark.business_id == business_id,
            PolicyBookmark.policy_id.in_(policy_ids),
        )
        result = await self._session.execute(stmt)
        return set(result.scalars().all())

    async def get_bookmarked_policies(
        self,
        *,
        business_id: uuid.UUID,
        page: int = 1,
        size: int = 10,
    ) -> tuple[list[Policy], int, int]:
        """해당 사업장이 북마크한 활성 정책 목록 — 최신 북마크 순."""
        base = (
            select(Policy)
            .join(
                PolicyBookmark,
                (PolicyBookmark.policy_id == Policy.id)
                & (PolicyBookmark.business_id == business_id),
            )
            .where(Policy.is_active.is_(True))
        )

        count_stmt = select(func.count()).select_from(base.subquery())
        total_count: int = (await self._session.execute(count_stmt)).scalar_one()
        total_pages = max(1, math.ceil(total_count / size))

        stmt = (
            base.order_by(PolicyBookmark.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total_count, total_pages

    async def create_bookmark(
        self,
        *,
        business_id: uuid.UUID,
        policy_id: uuid.UUID,
    ) -> PolicyBookmark:
        """북마크 생성."""
        bookmark = PolicyBookmark(
            business_id=business_id,
            policy_id=policy_id,
        )
        self._session.add(bookmark)
        await self._session.flush()
        await self._session.refresh(bookmark)
        return bookmark

    async def delete_bookmark(self, bookmark: PolicyBookmark) -> None:
        """북마크 물리 삭제 (북마크는 Soft Delete 불필요 — 이력 가치 없음)."""
        stmt = delete(PolicyBookmark).where(PolicyBookmark.id == bookmark.id)
        await self._session.execute(stmt)
        await self._session.flush()

    async def toggle_bookmark(
        self,
        *,
        business_id: uuid.UUID,
        policy_id: uuid.UUID,
    ) -> bool:
        """북마크 토글 — 있으면 삭제, 없으면 생성.

        Returns:
            True: 북마크 추가됨, False: 북마크 취소됨
        """
        existing = await self.get_bookmark(
            business_id=business_id, policy_id=policy_id
        )
        if existing is not None:
            await self.delete_bookmark(existing)
            return False
        await self.create_bookmark(
            business_id=business_id, policy_id=policy_id
        )
        return True
