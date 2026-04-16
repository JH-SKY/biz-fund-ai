# src/app/worker/scheduler.py
"""APScheduler 기반 배치 작업 스케줄러.

설계 의도:
  - FastAPI lifespan 이벤트에서 시작/종료한다 (main.py 참고).
  - 스케줄러는 FastAPI 요청 사이클 밖에서 실행되므로,
    요청 스코프 세션(get_db)을 사용할 수 없다.
    → SessionLocal(database.py) 로 독립 세션을 직접 생성한다.

  - 배치 작업의 비즈니스 로직(BizinfoSyncService)을 직접 조립하여 호출한다.
    이를 통해 AdminService 를 거치지 않고 도메인 서비스를 직접 호출하는
    '내부 배치 경로'와 관리자 API 경로를 분리한다.

스케줄 (기본 설정):
  - daily_policy_sync : 매일 03:00 (한국 시각 = UTC+9 기준 지정 필요)
    → KST 03:00 = UTC 18:00 (전날)
    → 서버가 KST 로 운영되는 경우 hour=3 그대로 사용 가능.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# 모듈 레벨 스케줄러 인스턴스 — main.py 에서 start()/shutdown() 호출
_scheduler = AsyncIOScheduler(timezone="Asia/Seoul")


async def _daily_policy_sync_job() -> None:
    """[배치] 매일 새벽 3시 기업마당 정책 공고 자동 동기화.

    처리 흐름:
      1. SessionLocal 로 독립 DB 세션 생성 (요청 사이클과 분리)
      2. BizinfoSyncService 직접 조립 (DI 컨테이너 없이)
      3. sync_recent_policies() 호출 (2페이지 × 100건 = 최대 200건)
      4. 세션은 finally 블록에서 반드시 닫힘
    """
    # 지연 임포트: 순환 참조 방지 및 앱 초기화 이후에만 임포트
    from src.app.agents.policy_sync_agent import PolicySyncAgent
    from src.app.database.postgres.database import SessionLocal
    from src.app.domains.policy.repository import PolicyRepository
    from src.app.domains.policy.sync_service import BizinfoSyncService

    logger.info("[SCHEDULER] 일일 정책 동기화 배치 시작")

    async with SessionLocal() as session:
        try:
            repo = PolicyRepository(session)
            agent = PolicySyncAgent()
            svc = BizinfoSyncService(session=session, repo=repo, agent=agent)

            result = await svc.sync_recent_policies()

            logger.info(
                "[SCHEDULER] 완료 | 성공: %d | DB 실패: %d",
                result.get("success", 0),
                result.get("db_fail", 0),
            )
        except Exception as exc:
            logger.error("[SCHEDULER] 배치 실행 중 예외 발생: %s", exc, exc_info=True)


def start_scheduler() -> None:
    """스케줄러를 시작하고 크론 잡을 등록한다. main.py 의 lifespan startup 에서 호출."""
    _scheduler.add_job(
        _daily_policy_sync_job,
        trigger=CronTrigger(hour=3, minute=0),  # 매일 03:00 (KST)
        id="daily_policy_sync",
        name="일일 기업마당 정책 동기화",
        replace_existing=True,  # 중복 등록 방지
        misfire_grace_time=3600,  # 서버 재시작으로 놓친 실행 허용 시간: 1시간
    )
    _scheduler.start()
    logger.info("[SCHEDULER] 🟢 APScheduler 시작 — daily_policy_sync @ 매일 03:00 (KST)")


def shutdown_scheduler() -> None:
    """스케줄러를 정상 종료한다. main.py 의 lifespan shutdown 에서 호출."""
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[SCHEDULER] 🔴 APScheduler 종료")
