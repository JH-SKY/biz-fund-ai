# src/app/worker/scheduler.py
"""APScheduler bootstrap with a Postgres advisory lock guard."""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from src.app.core.config import RUN_SCHEDULER, SCHEDULER_LOCK_ID
from src.app.database.postgres.database import engine

logger = logging.getLogger(__name__)

_scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
_scheduler_lock_conn: AsyncConnection | None = None
_scheduler_started = False


async def _daily_policy_sync_job() -> None:
    """Run the daily policy sync batch."""
    from src.app.agents.policy_sync_agent import PolicySyncAgent
    from src.app.database.postgres.database import SessionLocal
    from src.app.domains.policy.repository import PolicyRepository
    from src.app.domains.policy.sync_service import BizinfoSyncService

    logger.info("[SCHEDULER] daily policy sync started")

    async with SessionLocal() as session:
        try:
            repo = PolicyRepository(session)
            agent = PolicySyncAgent()
            svc = BizinfoSyncService(session=session, repo=repo, agent=agent)

            result = await svc.sync_recent_policies()
            logger.info(
                "[SCHEDULER] daily policy sync finished | success=%d db_fail=%d",
                result.get("success", 0),
                result.get("db_fail", 0),
            )
        except Exception as exc:
            logger.error("[SCHEDULER] batch execution failed: %s", exc, exc_info=True)


async def _acquire_scheduler_lock() -> bool:
    global _scheduler_lock_conn

    if _scheduler_lock_conn is not None:
        return True

    conn = await engine.connect()
    acquired = bool(
        await conn.scalar(text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": SCHEDULER_LOCK_ID})
    )
    if acquired:
        _scheduler_lock_conn = conn
        logger.info("[SCHEDULER] advisory lock acquired (lock_id=%s)", SCHEDULER_LOCK_ID)
        return True

    await conn.close()
    logger.warning(
        "[SCHEDULER] advisory lock is already held by another instance (lock_id=%s)",
        SCHEDULER_LOCK_ID,
    )
    return False


async def _release_scheduler_lock() -> None:
    global _scheduler_lock_conn

    if _scheduler_lock_conn is None:
        return

    try:
        await _scheduler_lock_conn.execute(
            text("SELECT pg_advisory_unlock(:lock_id)"),
            {"lock_id": SCHEDULER_LOCK_ID},
        )
    except Exception as exc:
        logger.warning("[SCHEDULER] advisory lock release failed: %s", exc, exc_info=True)
    finally:
        await _scheduler_lock_conn.close()
        _scheduler_lock_conn = None


def _register_jobs() -> None:
    _scheduler.add_job(
        _daily_policy_sync_job,
        trigger=CronTrigger(hour=3, minute=0),
        id="daily_policy_sync",
        name="daily_policy_sync",
        replace_existing=True,
        misfire_grace_time=3600,
    )


async def start_scheduler() -> bool:
    """Start the scheduler only when this instance owns the advisory lock."""
    global _scheduler_started

    if not RUN_SCHEDULER:
        logger.info("[SCHEDULER] skipped because RUN_SCHEDULER is disabled")
        return False

    if _scheduler_started and _scheduler.running:
        return True

    if not await _acquire_scheduler_lock():
        return False

    _register_jobs()
    _scheduler.start()
    _scheduler_started = True
    logger.info("[SCHEDULER] APScheduler started with singleton guard")
    return True


async def shutdown_scheduler() -> None:
    """Stop the scheduler and release the advisory lock if held."""
    global _scheduler_started

    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[SCHEDULER] APScheduler stopped")

    _scheduler_started = False
    await _release_scheduler_lock()
