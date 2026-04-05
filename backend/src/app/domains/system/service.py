"""시스템(System) 도메인 서비스 계층."""

import uuid
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from src.app.domains.system.model import BatchLog
from src.app.domains.system.repository import SystemRepository


class SystemService:
    def __init__(self, session: AsyncSession, repo: SystemRepository) -> None:
        self._session = session
        self._repo = repo

    async def list_latest_batch_per_job(self) -> Sequence[BatchLog]:
        return await self._repo.list_latest_batch_per_job()

    async def get_batch_log_by_id(self, job_id: uuid.UUID) -> BatchLog | None:
        return await self._repo.get_batch_log_by_id(job_id)
