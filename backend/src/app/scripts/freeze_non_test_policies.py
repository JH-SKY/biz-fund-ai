from __future__ import annotations

import asyncio

import src.app.main  # noqa: F401
from sqlalchemy import update

from src.app.core.config import APP_ENV
from src.app.database.postgres.database import SessionLocal
from src.app.dev.test_seed import TEST_POLICY_IDS, seed_test_scenarios
from src.app.domains.policy.model import Policy


async def main() -> None:
    if APP_ENV == "production":
        raise RuntimeError("운영 환경에서는 테스트용 비활성화 스크립트를 실행할 수 없습니다.")

    async with SessionLocal() as session:
        await seed_test_scenarios(session)
        result = await session.execute(
            update(Policy)
            .where(Policy.origin_id.not_in(TEST_POLICY_IDS))
            .values(is_active=False)
        )
        await session.commit()

    print("테스트 공고를 제외한 기존 공고를 로컬 DB에서 비활성화했습니다.")
    print(f"- kept_test_policy_ids: {', '.join(TEST_POLICY_IDS)}")
    print(f"- affected_rows: {result.rowcount}")


if __name__ == "__main__":
    asyncio.run(main())
