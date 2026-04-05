"""비즈픽 도메인 FastAPI 의존성(Depends)."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.database.postgres.database import get_db
from src.app.domains.biz_pick.repository import BizPickRepository
from src.app.domains.biz_pick.service import BizPickService


async def get_biz_pick_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BizPickRepository:
    return BizPickRepository(db)


async def get_biz_pick_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    repo: Annotated[BizPickRepository, Depends(get_biz_pick_repo)],
) -> BizPickService:
    return BizPickService(
        session=db,
        repo=repo,
    )

BizPickServiceDep = Annotated[BizPickService, Depends(get_biz_pick_service)]
