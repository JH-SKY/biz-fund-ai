"""시스템 도메인 의존성 주입(Depends)."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.database.postgres.database import get_db
from src.app.domains.system.repository import SystemRepository
from src.app.domains.system.service import SystemService


async def get_system_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SystemRepository:
    return SystemRepository(db)


async def get_system_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    repo: Annotated[SystemRepository, Depends(get_system_repo)],
) -> SystemService:
    return SystemService(session=db, repo=repo)


SystemServiceDep = Annotated[SystemService, Depends(get_system_service)]
