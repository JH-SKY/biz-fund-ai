"""알림(Notification) 도메인 서비스 계층."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.app.domains.auth.model import User
from src.app.domains.business.model import Business
from src.app.domains.notification.exception import (
    notification_forbidden,
    notification_not_found,
)
from src.app.domains.auth.service import AuthService
from src.app.domains.notification.model import Notification
from src.app.domains.notification.repository import NotificationRepository
from src.app.domains.notification.schema import (
    NotificationItem,
    NotificationListResponseData,
    NotificationSettingsResponseData,
    ReadNotificationResponseData,
    UnreadCountResponseData,
    UpdateNotificationSettingsRequest,
)


class NotificationService:
    def __init__(
        self,
        session: AsyncSession,
        repo: NotificationRepository,
        auth_service: AuthService, 
    ) -> None:
        self._session = session
        self._repo = repo
        self._auth_service = auth_service

    async def get_my_notifications(
        self,
        user: User,
        business: Optional[Business] = None,
        page: int = 1,
        size: int = 20,
    ) -> NotificationListResponseData:
        """
        내 알림 내역 조회.
        
        [도메인 실무 포인트]
        - X-Business-Id 헤더가 존재해 `business` 객체가 주입된 경우,
          해당 사업장과 연관된 알림(또는 전체 공통 알림)만 필터링하여 보여준다.
        """
        biz_id = business.id if business else None
        
        items, total_count = await self._repo.get_notifications(
            user_id=user.id,
            business_id=biz_id,
            page=page,
            size=size,
        )

        noti_items = []
        for noti in items:
            noti_items.append(
                NotificationItem(
                    noti_id=str(noti.id),
                    type=noti.type,
                    title=noti.title,  # 고정 문자열에서 DB 저장 값으로 수정
                    content=noti.message,
                    is_read=noti.is_read,
                    deep_link=noti.link_url,
                    created_at=noti.created_at,
                )
            )

        return NotificationListResponseData(
            items=noti_items,
            total_count=total_count,
        )

    async def mark_all_as_read(self, user: User) -> None:
        """모든 미확인 알림 읽음 처리."""
        await self._repo.mark_all_as_read(user.id)
        await self._session.commit()

    async def get_unread_count(self, user: User) -> UnreadCountResponseData:
        """읽지 않은 알림 총 개수 반환."""
        count = await self._repo.get_unread_count(user.id)
        return UnreadCountResponseData(unread_count=count)

    async def read_notification(
        self,
        user: User,
        noti_id: uuid.UUID,
    ) -> ReadNotificationResponseData:
        """
        개별 알림 읽음 처리.
        
        [도메인 실무 포인트]
        1. 존재 확인: 요청한 알림이 실제 존재하는지 먼저 확인합니다.
        2. 권한 검증: 본인 소유의 알림인지 엄격히 검증하여 타인의 접근을 원천 차단합니다.
        """
        noti = await self._repo.get_notification_by_id(noti_id)
        
        if not noti:
            raise notification_not_found()
            
        if noti.user_id != user.id:
            raise notification_forbidden()

        await self._repo.update_notification_read_status(noti, is_read=True)
        await self._session.commit()

        return ReadNotificationResponseData(
            noti_id=str(noti.id),
            is_read=noti.is_read,
        )

    async def get_notification_settings(self, user: User) -> NotificationSettingsResponseData:
            """
            알림 설정 조회.
            라우터에서 넘겨받은 user 객체(인증됨)에서 직접 설정값을 읽어옵니다.
            """
            return NotificationSettingsResponseData(
                # 모델에 새 컬럼이 추가되었으므로 바로 가져올 수 있습니다.
                # getattr를 쓴 이유는 마이그레이션 타이밍 이슈로 인한 속성 에러 방어 목적입니다.
                push_enabled=getattr(user, 'push_enabled', True),
                marketing_enabled=getattr(user, 'marketing_enabled', False),
                policy_update_enabled=getattr(user, 'policy_update_enabled', True),
                chat_answer_enabled=getattr(user, 'chat_answer_enabled', True),
            )

    async def update_notification_settings(
        self,
        user: User,
        req: UpdateNotificationSettingsRequest,
    ) -> None:
        """
        알림 설정 변경.
        AuthService의 브릿지 함수를 호출하여 User 테이블을 업데이트합니다 (도메인 격리 준수).
        """
        await self._auth_service.update_notification_settings_internal(
            user=user,
            push_enabled=req.push_enabled,
            marketing_enabled=req.marketing_enabled,
            policy_update_enabled=req.policy_update_enabled,
            chat_answer_enabled=req.chat_answer_enabled,
        )
        
        # 업데이트 내역 확정
        await self._session.commit()

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
        공통 알림 생성 메서드.
        
        타 도메인(Policy, Chat 등)에서 '우편물'을 접수하는 창구 역할을 합니다. [cite: 2026-03-05]
        서비스 레이어의 commit을 통해 데이터의 최종 저장을 확정합니다.
        """
        noti = await self._repo.create_notification(
            user_id=user_id,
            noti_type=noti_type,
            title=title,
            message=message,
            business_id=business_id,
            link_url=link_url,
        )
        await self._session.commit()
        return noti

    async def create_system_bulk_notification(
        self,
        noti_type: str,
        title: str,
        message: str,
        link_url: Optional[str] = None,
    ) -> int:
        """
        [Admin 전용] 전 유저 대상 시스템 대량 공지 발송.
        도메인 격리를 위해 Auth 서비스에서 ID를 먼저 받아온 뒤 Insert를 수행합니다.
        """
        user_ids = await self._auth_service.get_all_active_user_ids_internal()
        if not user_ids:
            return 0
            
        count = await self._repo.bulk_create_system_notification(
            user_ids=user_ids,
            noti_type=noti_type,
            title=title,
            message=message,
            link_url=link_url,
        )
        if count > 0:
            await self._session.commit()
        return count

    async def delete_old_notifications_batch(self, retention_days: int = 90) -> int:
        """
        오래된 알림 일괄 삭제 (배치 시스템 연동용).
        
        알림 데이터가 무한정 쌓이지 않도록 주기적 파기.
        지정된 retention_days(기본 90일)가 지난 알림을 물리 삭제하여 DB를 쾌적하게 유지합니다. [cite: 2026-03-05]
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        deleted_count = await self._repo.delete_old_notifications(cutoff_date)
        
        if deleted_count > 0:
            await self._session.commit()
            
        return deleted_count