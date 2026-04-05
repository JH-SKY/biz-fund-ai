"""비즈픽 도메인 DB 리포지토리."""

import uuid
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.domains.policy.model import BizPick


class BizPickRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_published_query(self):
        """
        사용자에게 노출될 '공개된 콘텐츠'의 기본 쿼리를 생성
        """
        return select(BizPick).where(BizPick.is_published.is_(True))

    async def get_published_contents(
        self,
        category: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> Tuple[List[BizPick], int, int]:
        """is_published=True인 콘텐츠 최신순/페이징 조회."""
        # 기본 쿼리 가져오기
        stmt = self._base_published_query()
        # 2. 카테고리 필터 적용 (있을 경우에만)
        if category:
            stmt = stmt.where(BizPick.category == category)

        # 3. 전체 개수 계산 (서브쿼리를 이용해 정확한 카운트)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_count = await self._session.scalar(count_stmt) or 0

        # 4. 페이징 및 정렬 적용
        offset = (page - 1) * size
        stmt = stmt.order_by(BizPick.created_at.desc()).offset(offset).limit(size)
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())

        total_pages = (total_count + size - 1) // size
        return items, total_count, total_pages

    async def get_content_by_id(self, content_id: uuid.UUID) -> Optional[BizPick]:
        """콘텐츠 상세 조회."""
        stmt = select(BizPick).where(
            BizPick.id == content_id,
            BizPick.is_published == True
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_todays_picks(self, limit: int = 3) -> List[BizPick]:
        """오늘의 추천 콘텐츠 (랜덤/최신순)."""
        stmt = (
            select(BizPick)
            .where(BizPick.is_published == True)
            .order_by(func.random())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ── Admin 전용 ────────────────────────────────────────────────────────

    async def get_biz_pick_by_id(self, content_id: uuid.UUID) -> Optional[BizPick]:
        """관리자용: 공개 여부 상관없이 ID로 조회"""
        stmt = select(BizPick).where(BizPick.id == content_id)
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()
    
    async def create_biz_pick_internal(
        self,
        *,
        title: str,
        category: str,
        content_html: str,
        thumbnail_url: str | None,
        is_published: bool,
    ) -> BizPick:
        """새로운 비즈픽 콘텐츠를 생성하고 DB에 임시 저장(flush)합니다."""
        row = BizPick(
            title=title,
            category=category,
            content_html=content_html,
            thumbnail_url=thumbnail_url,
            is_published=is_published,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def patch_biz_pick_internal(
        self,
        row: BizPick,
        *,
        title: str | None,
        body_html: str | None,
        thumbnail_url: str | None,
        is_published: bool | None,
    ) -> None:
        """기존 콘텐츠의 필드를 선택적으로 업데이트합니다."""
        if title is not None:
            row.title = title
        if body_html is not None:
            row.content_html = body_html
        if thumbnail_url is not None:
            row.thumbnail_url = thumbnail_url
        if is_published is not None:
            row.is_published = is_published
        await self._session.flush()
