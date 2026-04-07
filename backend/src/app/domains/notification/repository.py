"""알림 도메인 DB 리포지토리."""

import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.domains.notification.model import Notification


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_notifications(
        self,
        user_id: uuid.UUID,
        business_id: Optional[uuid.UUID] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[Notification], int]:
        """
        내 알림 목록 페이징 조회.

        1. 사용자 식별: 로그인한 유저의 ID로 알림을 필터링합니다.
        2. 사업장 컨텍스트: business_id가 주어지면 해당 사업장 전용 알림 또는 전체 공통 알림을 가져옵니다.
        3. 정렬 및 페이징: 최신순으로 정렬하여 요청된 페이지의 데이터만 끊어서 반환합니다.
        """
        stmt = select(Notification).where(Notification.user_id == user_id)

        if business_id is not None:
            # 사업장 전용 필터링: 해당 사업장 알림이거나 전체 유저 공통 알림(business_id가 None인 경우)
            stmt = stmt.where(
                (Notification.business_id == business_id)
                | (Notification.business_id.is_(None))
            )

        # 전체 개수 파악: 페이징 처리를 위해 조건에 맞는 전체 데이터 숫자를 확인하는 '계산서'입니다.
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_count = await self._session.scalar(count_stmt) or 0

        # 페이징 적용 및 최신순 정렬
        offset = (page - 1) * size
        stmt = stmt.order_by(Notification.created_at.desc()).offset(offset).limit(size)

        result = await self._session.execute(stmt)
        items = list(result.scalars().all())

        return items, total_count

    async def mark_all_as_read(self, user_id: uuid.UUID) -> None:
        """유저의 모든 미확인 알림을 읽음 처리."""
        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
            .values(is_read=True)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def get_unread_count(self, user_id: uuid.UUID) -> int:
        """유저의 미확인 알림 총개수 반환 (GNB 종 모양 아이콘 표시용)."""
        stmt = select(func.count()).where(
            Notification.user_id == user_id, Notification.is_read == False
        )
        count = await self._session.scalar(stmt)
        return count or 0

    async def get_notification_by_id(
        self, noti_id: uuid.UUID
    ) -> Optional[Notification]:
        """알림 단건 조회."""
        stmt = select(Notification).where(Notification.id == noti_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_notification_read_status(
        self, noti: Notification, is_read: bool
    ) -> None:
        """개별 알림 읽음 상태 업데이트."""
        noti.is_read = is_read
        await self._session.flush()

    async def create_notification(
        self,
        user_id: uuid.UUID,
        noti_type: str,
        title: str,
        message: str,
        business_id: Optional[uuid.UUID] = None,
        link_url: Optional[str] = None,
    ) -> Notification:
        """
        신규 알림 생성. (타 도메인에서 호출 가능)

        이 함수는 다른 서비스(정책, 채팅 등)에서 알림이라는 '우편물'을 만들어 보내는 역할을 합니다.
        title 인자를 추가하여 명세서의 요구사항을 반영했습니다.
        """
        noti = Notification(
            user_id=user_id,
            business_id=business_id,
            type=noti_type,
            title=title,
            message=message,
            link_url=link_url,
            is_read=False,
        )
        self._session.add(noti)
        await self._session.flush()
        return noti

    async def bulk_create_system_notification(
        self,
        user_ids: list[uuid.UUID],
        noti_type: str,
        title: str,
        message: str,
        link_url: Optional[str] = None,
    ) -> int:
        """
        [Admin 전용] 전 서버 유저 대상 대량 알림 발송.
        (User 테이블을 직접 쿼리하지 않고, 전달받은 ID 리스트를 활용해 Bulk Insert)
        """
        if not user_ids:
            return 0

        mappings = [
            {
                "user_id": uid,
                "business_id": None,
                "type": noti_type,
                "title": title,
                "message": message,
                "is_read": False,
                "link_url": link_url,
            }
            for uid in user_ids
        ]

        stmt = insert(Notification).values(mappings)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount

    async def delete_old_notifications(self, cutoff_date: datetime) -> int:
        """
        기준일 이전의 오래된 알림 일괄 물리 삭제 (배치용).

        [도메인 규칙 6.3] 알림 데이터가 무한정 쌓여 DB 성능이 떨어지는 것을 방지하는 '청소 도구'입니다.
        """
        stmt = delete(Notification).where(Notification.created_at < cutoff_date)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount
