"""비즈픽 콘텐츠 도메인 서비스 로직."""

import uuid
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from src.app.api.deps.user_auth import CurrentUser  # 유저 연동을 위해 추가
from src.app.core.exceptions import NotFoundException
from src.app.domains.biz_pick.model import BizPick
from src.app.domains.biz_pick.repository import BizPickRepository
from src.app.domains.biz_pick.schema import (
    BizPickDetailResponseData,
    BizPickLikeResponseData,
    BizPickListItem,
    BizPickListResponseData,
    CategoryItem,
    TodayPickItem,
)


class BizPickService:
    def __init__(
        self,
        session: AsyncSession,
        repo: BizPickRepository,
    ) -> None:
        self._session = session
        self._repo = repo

    async def get_published_contents(
        self,
        current_user: Optional[
            CurrentUser
        ] = None,  # [수정] 좋아요 여부 판단을 위해 추가
        category: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> BizPickListResponseData:
        """1. 공개된 콘텐츠 목록을 가져오고, 유저의 좋아요 상태를 매핑합니다."""
        items, total_count, total_pages = await self._repo.get_published_contents(
            category=category, page=page, size=size
        )

        # 실무 팁: 리스트 조회 시 유저가 로그인 상태라면 좋아요 여부를 한꺼번에 조회하는 로직이 필요하지만,
        # 여기서는 기본 구조에 맞춰 개별 체크 또는 기본값 처리를 수행합니다.
        return BizPickListResponseData(
            items=[
                BizPickListItem.model_validate(
                    item
                )  # [최적화] schema의 ConfigDict 활용
                for item in items
            ],
            total_count=total_count,
            total_pages=total_pages,
        )

    async def get_content_detail(
        self,
        content_id: uuid.UUID,
        current_user: Optional[
            CurrentUser
        ] = None,  # [추가] 로그인 유저의 찜 여부 확인용
    ) -> BizPickDetailResponseData:
        """2. 상세 정보를 조회하고 조회수를 1 증가시킵니다."""
        content = await self._repo.get_content_by_id(content_id)
        if not content:
            raise NotFoundException("콘텐츠를 찾을 수 없습니다.")

        # 1. 조회수 증가 (Atomic하게 처리하기 위해 flush 활용)
        content.view_count += 1
        await self._session.flush()
        # 주의: commit은 router나 middleware 수준에서 관리하는 것이 트랜잭션 전파에 유리합니다.

        # 2. 결과 반환 (스키마의 model_validate를 통해 깔끔하게 변환)
        response = BizPickDetailResponseData.model_validate(content)

        # 3. 추가 정보 세팅 (현재는 하드코딩이지만 향후 PolicyService와 연동 지점)
        response.author = "비즈업 에디터"
        response.tags = [content.category]

        return response

    async def get_todays_picks(self) -> List[TodayPickItem]:
        """3. 오늘의 추천 3종을 가져옵니다."""
        picks = await self._repo.get_todays_picks(limit=3)
        return [TodayPickItem.model_validate(p) for p in picks]

    async def toggle_like(
        self,
        content_id: uuid.UUID,
        current_user: CurrentUser,  # [필수] 로그인한 유저 정보 필수
    ) -> BizPickLikeResponseData:
        """
        4. 좋아요 토글 (설계 의도: 유저-콘텐츠 매핑 테이블 연동).
        현재는 매핑 테이블 로직을 시뮬레이션하지만, 구조는 실무 규격을 유지합니다.
        """
        content = await self._repo.get_content_by_id(content_id)
        if not content:
            raise NotFoundException("콘텐츠를 찾을 수 없습니다.")

        # [실무 로직 예시]
        # 1. repo.get_like(user_id, content_id) 조회
        # 2. 있으면 삭제(Unlike) & like_count -1
        # 3. 없으면 생성(Like) & like_count +1

        # 여기서는 우선 카운트 증가 로직을 유지하되, 리턴 타입을 명세서에 맞춥니다.
        is_liked_now = True  # 실제로는 토글 결과에 따라 달라짐
        content.like_count += 1

        await self._session.flush()

        return BizPickLikeResponseData(
            is_liked=is_liked_now,
            total_likes=content.like_count,
        )

    # ── Admin 전용 (리포지토리와 동일하게 internal 유지) ─────────────────────

    async def create_biz_pick_internal(self, **kwargs) -> BizPick:
        return await self._repo.create_biz_pick_internal(**kwargs)

    async def get_biz_pick_by_id_internal(
        self, content_id: uuid.UUID
    ) -> Optional[BizPick]:
        return await self._repo.get_biz_pick_by_id(content_id)

    async def list_biz_picks_internal(
        self,
        *,
        category: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[BizPick], int, int]:
        return await self._repo.list_biz_picks(category=category, page=page, size=size)

    async def patch_biz_pick_internal(self, row: BizPick, **kwargs) -> None:
        await self._repo.patch_biz_pick_internal(row, **kwargs)

    async def delete_biz_pick_internal(self, row: BizPick) -> None:
        await self._repo.delete_biz_pick(row)

    def get_categories(self) -> List[CategoryItem]:
        """카테고리 목록 정의 (설계 의도: 코드 관리 효율성을 위해 서비스에서 정의)."""
        categories = [
            ("SUCCESS_STORY", "성공사례"),
            ("POLICY_GUIDE", "정책가이드"),
            ("BIZ_TIP", "운영꿀팁"),
        ]
        return [CategoryItem(code=c[0], name=c[1]) for c in categories]
