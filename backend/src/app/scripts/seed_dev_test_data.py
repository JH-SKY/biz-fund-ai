"""비즈몽 개발/평가용 시나리오 데이터를 DB 에 적재하는 실행 스크립트."""

from __future__ import annotations

import asyncio

from src.app.database.postgres.database import SessionLocal
from src.app.dev.test_seed import seed_test_scenarios


async def main() -> None:
    """가상 사업자/정책 데이터를 시드하고 요약 결과를 출력한다."""
    async with SessionLocal() as session:
        summary = await seed_test_scenarios(session)
        await session.commit()

    print("BizMong 개발용 테스트 데이터 시드를 완료했습니다.")
    for key, value in summary.items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
