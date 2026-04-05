"""알림 도메인 예외 처리."""

from src.app.core.exceptions import ForbiddenException, NotFoundException

def notification_not_found() -> NotFoundException:
    return NotFoundException("해당 알림을 찾을 수 없어요. 이미 삭제된 알림일 수 있습니다.")

def notification_forbidden() -> ForbiddenException:
    return ForbiddenException("사장님 본인의 알림이 아닙니다. 접근 권한이 없어요.")