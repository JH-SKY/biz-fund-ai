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
        """PostgreSQL DISTINCT ON(job_name) — 최신 started_at 기준.

        processed_count가 아직 DB에 없어도 동작하도록 fallback 쿼리를 포함합니다.
        """
        stmt = (
            select(BatchLog)
            .distinct(BatchLog.job_name)
            .order_by(BatchLog.job_name, desc(BatchLog.started_at))
        )
        try:
            res = await self._session.execute(stmt)
            return res.scalars().all()
        except Exception:
            # processed_count 등 신규 컬럼이 아직 없을 때: 컬럼을 명시적으로 지정해 재시도
            await self._session.rollback()
            from sqlalchemy import text
            sql = text(
                """
                SELECT DISTINCT ON (job_name)
                    id, job_name, status,
                    total_count, success_count, fail_count,
                    api_error_count, parse_error_count, analysis_error_count, db_fail_count,
                    error_details, started_at, finished_at,
                    NULL::int AS processed_count
                FROM batch_logs
                ORDER BY job_name, started_at DESC
                """
            )
            try:
                res2 = await self._session.execute(sql)
                rows = res2.mappings().all()
                result: list[BatchLog] = []
                for row in rows:
                    obj = BatchLog(
                        job_name=row["job_name"],
                        status=row["status"],
                        total_count=row["total_count"],
                        success_count=row["success_count"],
                        fail_count=row["fail_count"],
                        api_error_count=row["api_error_count"] or 0,
                        parse_error_count=row["parse_error_count"] or 0,
                        analysis_error_count=row["analysis_error_count"] or 0,
                        db_fail_count=row["db_fail_count"] or 0,
                        error_details=row["error_details"],
                        started_at=row["started_at"],
                        finished_at=row["finished_at"],
                    )
                    obj.id = row["id"]
                    result.append(obj)
                return result
            except Exception:
                return []

    async def get_batch_log_by_id(self, job_id: uuid.UUID) -> BatchLog | None:
        stmt = select(BatchLog).where(BatchLog.id == job_id)
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()
