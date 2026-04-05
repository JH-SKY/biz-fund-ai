"""시스템(System) 도메인 리포지토리."""

import uuid
from typing import Sequence

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.domains.system.model import BatchLog


class SystemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_latest_batch_per_job(self) -> Sequence[BatchLog]:
        """PostgreSQL DISTINCT ON(job_name) — 최신 started_at 기준."""
        sub = (
            select(BatchLog)
            .distinct(BatchLog.job_name)
            .order_by(BatchLog.job_name, desc(BatchLog.started_at))
        )
        res = await self._session.execute(sub)
        return res.scalars().all()

    async def get_batch_log_by_id(self, job_id: uuid.UUID) -> BatchLog | None:
        stmt = select(BatchLog).where(BatchLog.id == job_id)
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()
