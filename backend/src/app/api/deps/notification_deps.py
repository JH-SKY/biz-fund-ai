"""알림 도메인 FastAPI 의존성 주입(Depends)."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.database.postgres.database import get_db
from src.app.domains.notification.repository import NotificationRepository
from src.app.domains.notification.service import NotificationService
from src.app.api.deps.user_auth import get_auth_service
from src.app.domains.auth.service import AuthService

async def get_notification_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationRepository:
    return NotificationRepository(db)

async def get_notification_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    repo: Annotated[NotificationRepository, Depends(get_notification_repo)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> NotificationService:
    return NotificationService(
        session=db,
        repo=repo,
        auth_service=auth_service,
    )

NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]