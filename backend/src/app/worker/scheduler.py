# src/app/worker/scheduler.py
"""APScheduler 기반 백그라운드 작업 스케줄러 — PostgreSQL Advisory Lock 싱글턴 가드 포함.

[설계 원칙]
- 다중 서버 환경(수평 확장)에서 스케줄러가 중복 실행되는 것을 방지하기 위해
  PostgreSQL Advisory Lock (pg_try_advisory_lock) 을 사용한다.
- 락 획득에 성공한 인스턴스만 APScheduler 를 시작하고 배치 작업을 실행한다.
- 애플리케이션 종료 시 반드시 락을 해제해야 다른 인스턴스가 획득할 수 있다.

[등록된 작업]
- daily_policy_sync: 매일 새벽 3시, 정부 24 API에서 정책 공고를 수집하고
  AI 구조화 + 벡터 임베딩까지 처리하는 배치 작업.

[환경 변수]
- RUN_SCHEDULER=false  : 스케줄러를 아예 비활성화 (로컬 개발 환경용)
- SCHEDULER_LOCK_ID    : Advisory Lock ID (기본값: config.py 에서 설정)
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from src.app.core.config import RUN_SCHEDULER, SCHEDULER_LOCK_ID
from src.app.database.postgres.database import engine

logger = logging.getLogger(__name__)

# 프로세스 내 싱글턴 스케줄러 인스턴스
_scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
# Advisory Lock 을 보유한 DB 연결 (프로세스 생애 동안 유지)
_scheduler_lock_conn: AsyncConnection | None = None
_scheduler_started = False


async def _daily_policy_sync_job() -> None:
    """매일 새벽 3시에 실행되는 정책 공고 동기화 배치.

    [처리 순서]
    1. BizInfo API 에서 최신 정책 공고 수집
    2. PolicySyncAgent (AI) 로 JSON 구조화 및 요약 생성
    3. PolicyEmbeddingService 로 벡터 임베딩 생성 및 저장
    4. 성공/실패 카운트 로깅

    함수 내부 임포트 이유:
    스케줄러는 앱 초기화와 같은 시점에 등록되지만, 실제 실행은
    나중에 일어나므로 DATABASE_URL 등이 준비된 시점에 임포트해야 한다.
    """
    from src.app.agents.policy_sync_agent import PolicySyncAgent
    from src.app.database.postgres.database import SessionLocal
    from src.app.domains.policy.embedding_service import PolicyEmbeddingService
    from src.app.domains.policy.repository import PolicyRepository
    from src.app.domains.policy.sync_service import BizinfoSyncService

    logger.info("[SCHEDULER] daily policy sync started")

    async with SessionLocal() as session:
        try:
            repo = PolicyRepository(session)
            agent = PolicySyncAgent()
            emb_svc = PolicyEmbeddingService(session=session, repo=repo)
            svc = BizinfoSyncService(
                session=session,
                repo=repo,
                agent=agent,
                embedding_service=emb_svc,
                session_factory=SessionLocal,
            )

            result = await svc.sync_recent_policies()
            logger.info(
                "[SCHEDULER] daily policy sync finished | success=%d db_fail=%d",
                result.get("success", 0),
                result.get("db_fail", 0),
            )
        except Exception as exc:
            logger.error("[SCHEDULER] batch execution failed: %s", exc, exc_info=True)


async def _acquire_scheduler_lock() -> bool:
    """PostgreSQL Advisory Lock 을 획득하여 스케줄러 싱글턴을 보장한다.

    - pg_try_advisory_lock 은 락 획득에 실패해도 블로킹 없이 즉시 False 반환.
    - 획득 성공 시 해당 DB 연결을 _scheduler_lock_conn 에 보관.
      (연결이 끊기면 PostgreSQL 이 자동으로 락을 해제하기 때문에 연결 유지가 필수)
    - 획득 실패 = 다른 인스턴스가 이미 락을 보유 중 → 이 인스턴스는 스케줄러 미실행.
    """
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

    # 획득 실패 — 연결을 닫고 False 반환
    await conn.close()
    logger.warning(
        "[SCHEDULER] advisory lock is already held by another instance (lock_id=%s)",
        SCHEDULER_LOCK_ID,
    )
    return False


async def _release_scheduler_lock() -> None:
    """보유한 Advisory Lock 을 해제하고 DB 연결을 닫는다.

    애플리케이션 종료(shutdown_scheduler) 시 호출되어야 한다.
    락을 해제하지 않으면 PostgreSQL 세션이 살아있는 동안 다른 인스턴스가 락을 얻지 못한다.
    """
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
    """스케줄러에 주기적 작업을 등록한다.

    - daily_policy_sync: 매일 새벽 3시 0분 실행
    - misfire_grace_time=3600: 예정 시각을 1시간까지 놓쳐도 실행
    """
    _scheduler.add_job(
        _daily_policy_sync_job,
        trigger=CronTrigger(hour=3, minute=0),
        id="daily_policy_sync",
        name="daily_policy_sync",
        replace_existing=True,
        misfire_grace_time=3600,
    )


async def start_scheduler() -> bool:
    """Advisory Lock 을 획득한 인스턴스만 스케줄러를 시작한다.

    [로직]
    1. RUN_SCHEDULER=false 이면 즉시 종료 (로컬 개발용)
    2. 이미 실행 중이면 중복 시작 방지
    3. Advisory Lock 획득 시도 → 실패 시 종료
    4. 작업 등록 → APScheduler 시작

    Returns:
        True: 스케줄러 시작 성공
        False: 비활성화 or 락 획득 실패
    """
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
    """스케줄러를 중지하고 Advisory Lock 을 해제한다.

    FastAPI lifespan 종료 시점에 호출되어야 한다.
    """
    global _scheduler_started

    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[SCHEDULER] APScheduler stopped")

    _scheduler_started = False
    await _release_scheduler_lock()
