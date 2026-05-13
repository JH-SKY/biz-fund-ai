from __future__ import annotations

import asyncio

from src.app.database.postgres.database import SessionLocal
from src.app.dev.test_seed import seed_test_scenarios


async def main() -> None:
    async with SessionLocal() as session:
        summary = await seed_test_scenarios(session)
        await session.commit()

    print("BizMong 개발용 테스트 데이터 시드를 완료했습니다.")
    for key, value in summary.items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
