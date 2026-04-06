# src/app/domains/policy/repository.py
"""정책 도메인 DB 접근 계층.

원칙:
  - 비즈니스 판단(예외 발생, 조건 분기)은 Service에서, I/O(쿼리 실행)만 여기에 담습니다.
  - [도메인 규칙 0] 모든 일반 사용자용 조회에는 is_active=True 필터를 강제합니다. (Soft Delete 대응)
  - [도메인 규칙 2.2] 북마크 조회는 반드시 business_id를 기준으로 격리하여 보안을 유지합니다.
"""

from __future__ import annotations

import math
import uuid
from datetime import date
from typing import Optional

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.app.domains.policy.model import Policy, PolicyBookmark, PolicyStatus


class PolicyRepository:
    """정책 도메인의 '창고 관리자'입니다.

    데이터를 넣고(C), 찾고(R), 고치고(U), 치우는(D) 일만 수행합니다.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── 1. Policy 조회 (사용자용) ──────────────────────────────────────────────

    async def get_active_policies(
        self,
        *,
        page: int = 1,
        size: int = 10,
    ) -> tuple[list[Policy], int, int]:
        """활성 상태인 정책 목록을 '최신 등록순'으로 가져옵니다. (배달 전 포장 작업)"""
        # 1. 기본 필터링 (활성 상태만)
        base = select(Policy).where(Policy.is_active.is_(True))

        # 2. 전체 개수 파악 (전체 페이지 계산용)
        count_stmt = select(func.count()).select_from(base.subquery())
        total_count: int = (await self._session.execute(count_stmt)).scalar_one()

        total_pages = max(1, math.ceil(total_count / size))

        # 3. 데이터 페이징 조회
        stmt = (
            base.order_by(Policy.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())

        return items, total_count, total_pages

    async def get_policy_by_id(self, policy_id: uuid.UUID) -> Policy | None:
        """아이디로 정책 하나를 찾습니다. (비유: 특정 학번 학생 찾기)"""
        stmt = select(Policy).where(Policy.id == policy_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def increase_view_count(self, policy_id: uuid.UUID) -> None:
        """조회수를 안전하게 1 올립니다.

        설계 의도:
          - 여러 명의 사용자가 동시에 조회할 때 데이터가 씹히지 않도록
            DB가 직접 '+ 1'을 수행하게 합니다. (Atomic Update)
        """
        stmt = (
            update(Policy)
            .where(Policy.id == policy_id)
            .values(view_count=Policy.view_count + 1)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def search_policies(
        self,
        *,
        keyword: Optional[str] = None,
        region: Optional[str] = None,
        category: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> tuple[list[Policy], int, int]:
        """제목, 지역, 카테고리 등 여러 조건으로 정책을 검색합니다."""
        conditions = [Policy.is_active.is_(True)]

        # 1. 키워드 검색 (제목 또는 원문 포함 여부)
        if keyword:
            pattern = f"%{keyword}%"
            conditions.append(
                or_(
                    Policy.title.ilike(pattern),
                    Policy.content_raw.ilike(pattern),
                )
            )

        # 2. 필터링 조건 추가 (지역, 카테고리)
        if region:
            conditions.append(Policy.region.ilike(f"%{region}%"))
        if category:
            conditions.append(Policy.category == category)

        base = select(Policy).where(*conditions)

        # 3. 페이징 및 결과 반환
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

    # ── 2. PolicyBookmark (찜하기 로직) ──────────────────────────────────────────

    async def get_bookmark(
        self,
        *,
        business_id: uuid.UUID,
        policy_id: uuid.UUID,
    ) -> PolicyBookmark | None:
        """특정 사업장이 이 정책을 찜했는지 확인합니다."""
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
        """주어진 정책들 중 찜한 것들만 골라냅니다. (목록에서 '빨간 하트' 표시용)"""
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
        """해당 사업장의 북마크 목록을 가져옵니다.

        설계 의도:
          - 정책 데이터(Policy)와 북마크(PolicyBookmark)를 합쳐서(Join) 조회하며,
            사용자가 '최근에 찜한 순서'대로 정렬합니다.
        """
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
        """북마크 정보를 창고에 새로 등록합니다."""
        bookmark = PolicyBookmark(
            business_id=business_id,
            policy_id=policy_id,
        )
        self._session.add(bookmark)
        await self._session.flush()  # ID를 즉시 생성하기 위해 flush
        await self._session.refresh(bookmark)
        return bookmark

    async def delete_bookmark(self, bookmark: PolicyBookmark) -> None:
        """북마크를 영구히 삭제합니다. (도메인 규칙 A4: 하드 딜리트)"""
        stmt = delete(PolicyBookmark).where(PolicyBookmark.id == bookmark.id)
        await self._session.execute(stmt)
        await self._session.flush()

    async def toggle_bookmark(
        self,
        *,
        business_id: uuid.UUID,
        policy_id: uuid.UUID,
    ) -> bool:
        """찜하기 스위치를 끄거나 켭니다. (이미 있으면 삭제, 없으면 추가)"""
        bookmark = await self.get_bookmark(business_id=business_id, policy_id=policy_id)
        if bookmark:
            await self.delete_bookmark(bookmark)
            return False

        await self.create_bookmark(business_id=business_id, policy_id=policy_id)
        return True

    async def get_top_policies_by_views(self, limit: int = 5) -> list[Policy]:
        """조회수 상위 정책 리스트 조회 (실무 랭킹 로직)"""
        stmt = (
            select(Policy)
            .where(Policy.is_active == True)  # 활성화된 정책만!
            .order_by(Policy.view_count.desc())  # 조회수 높은 순서대로
            .limit(limit)  # 딱 5개만
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create_policy(
        self,
        *,
        title: str,
        content_raw: str,
        category: str,
        agency_name: str = "미정",
        apply_url: str | None = None,
        status: PolicyStatus = PolicyStatus.RECRUITING,  # [추가] 상태값 받기
        closed_at: date | None = None,  # [추가] 마감일 받기
        **kwargs,  # [꿀팁] 그 외 예상치 못한 데이터 방어
    ) -> Policy:
        """새로운 정책 데이터를 DB 모델로 변환하여 세션에 추가합니다."""

        new_policy = Policy(
            title=title,
            content_raw=content_raw,
            category=category,
            agency_name=agency_name,
            apply_url=apply_url,
            status=status,  # 받은 상태값 적용
            closed_at=closed_at or date(9999, 12, 31),  # 마감일 없으면 무기한
            is_active=True,
            view_count=0,
        )

        self._session.add(new_policy)
        await self._session.flush()
        return new_policy

    # ── 3. 중복 검증용 조회 ──────────────────────────────────────────────────

    async def get_policy_by_title_and_agency(
        self, *, title: str, agency_name: str
    ) -> Optional[Policy]:
        """
        [설계 의도] 제목과 기관명이 완전히 일치하는 정책이 있는지 확인합니다.
        비유: 도서관에 이미 똑같은 책(제목+출판사)이 있는지 검색해보는 과정입니다.
        """
        # 1. 준비물: 정책 테이블에서 데이터를 뽑을 쿼리 작성
        stmt = select(Policy).where(
            Policy.title == title,
            Policy.agency_name == agency_name,
            Policy.is_active == True,  # 활성화된 정책 중에서만 중복 체크
        )

        # 2. 버튼 찾기: 쿼리 실행
        result = await self._session.execute(stmt)

        # 3. 일 시키기: 결과가 있으면 객체를 반환하고, 없으면 None을 반환
        return result.scalar_one_or_none()
