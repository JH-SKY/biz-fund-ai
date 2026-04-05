"""알림 API 라우터."""

import uuid

from fastapi import APIRouter, Query, status

from src.app.api.deps.business_deps import OptionalBusiness
from src.app.api.deps.notification_deps import NotificationServiceDep
from src.app.api.deps.user_auth import CurrentUser
from src.app.core.response import api_json
from src.app.domains.notification.schema import UpdateNotificationSettingsRequest

# 'notifications' 태그를 통해 Swagger UI에서 알림 관련 API를 그룹화하여 보여줍니다.
router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def get_my_notifications(
    _current_user: CurrentUser,
    svc: NotificationServiceDep,
    biz: OptionalBusiness,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """
    내 알림 내역 조회.
    
    [실무 포인트]
    1. 필터링 메커니즘: X-Business-Id 헤더 유무에 따라 '특정 가게 알림'만 볼지, '전체 알림'을 볼지 결정합니다.
    2. 페이징 처리: 데이터가 많아질 것에 대비해 한 번에 20개씩 끊어서 가져오는 '책갈피' 기능을 제공합니다.
    """
    data = await svc.get_my_notifications(
        user=_current_user,
        business=biz,
        page=page,
        size=size,
    )
    return api_json(
        http_status=status.HTTP_200_OK,
        data=data.model_dump(),
        message="success",
    )


@router.post("/read-all")
async def mark_all_as_read(
    _current_user: CurrentUser,
    svc: NotificationServiceDep,
):
    """
    모든 알림 한꺼번에 읽음 처리.
    
    사용자가 '모두 읽음' 버튼을 눌렀을 때, 쌓여있는 모든 미확인 우편물을 '확인 완료' 상태로 바꿉니다.
    """
    await svc.mark_all_as_read(user=_current_user)
    return api_json(
        http_status=status.HTTP_200_OK,
        data={},
        message="모든 알림이 읽음 처리되었습니다.",
    )


@router.get("/unread-count")
async def get_unread_count(
    _current_user: CurrentUser,
    svc: NotificationServiceDep,
):
    """
    읽지 않은 알림 총개수 반환 (종 모양 아이콘 뱃지용).
    
    앱 상단 GNB(Global Navigation Bar)의 종 모양 아이콘 옆에 '3'과 같이 숫자를 띄우기 위한 용도입니다.
    """
    data = await svc.get_unread_count(user=_current_user)
    return api_json(
        http_status=status.HTTP_200_OK,
        data=data.model_dump(),
        message="success",
    )


@router.patch("/{noti_id}/read")
async def read_notification(
    noti_id: uuid.UUID,
    _current_user: CurrentUser,
    svc: NotificationServiceDep,
):
    """
    특정 개별 알림 클릭 시 읽음 상태로 업데이트.
    
    특정 우편물을 '클릭'해서 내용을 확인했을 때, 그 우편물만 '읽음' 도장을 찍는 과정입니다.
    """
    data = await svc.read_notification(
        user=_current_user,
        noti_id=noti_id,
    )
    return api_json(
        http_status=status.HTTP_200_OK,
        data=data.model_dump(),
        message="success",
    )


@router.get("/settings")
async def get_notification_settings(
    _current_user: CurrentUser,
    svc: NotificationServiceDep,
):
    """
    푸시 알림 수신 동의 현황(설정) 조회.
    
    마케팅 정보나 채팅 답변 알림 등을 켜두었는지 확인하는 설정 창 정보를 가져옵니다.
    """
    data = await svc.get_notification_settings(user=_current_user)
    return api_json(
        http_status=status.HTTP_200_OK,
        data=data.model_dump(),
        message="success",
    )


@router.patch("/settings")
async def update_notification_settings(
    req: UpdateNotificationSettingsRequest,
    _current_user: CurrentUser,
    svc: NotificationServiceDep,
):
    """
    특정 카테고리의 알림 수신 여부 설정 변경.
    
    사용자가 알림 설정 페이지에서 스위치를 끄거나 켤 때 동작하는 '스위치 조작' 로직입니다.
    """
    await svc.update_notification_settings(user=_current_user, req=req)
    return api_json(
        http_status=status.HTTP_200_OK,
        data={},
        message="알림 설정이 변경되었습니다.",
    )