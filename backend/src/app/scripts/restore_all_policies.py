"""로컬 개발 DB 의 모든 정책을 다시 활성화하는 복구 스크립트."""

from __future__ import annotations

import asyncio

import src.app.main  # noqa: F401
from sqlalchemy import update

from src.app.core.config import APP_ENV
from src.app.database.postgres.database import SessionLocal
from src.app.domains.policy.model import Policy


async def main() -> None:
    """비활성화된 정책까지 모두 다시 보이게 되돌린다."""
    if APP_ENV == "production":
        raise RuntimeError("운영 환경에서는 전체 공고 복구 스크립트를 실행할 수 없습니다.")

    async with SessionLocal() as session:
        result = await session.execute(update(Policy).values(is_active=True))
        await session.commit()

    print("로컬 DB의 전체 공고를 다시 활성화했습니다.")
    print(f"- affected_rows: {result.rowcount}")


if __name__ == "__main__":
    asyncio.run(main())
