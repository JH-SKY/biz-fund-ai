from __future__ import annotations

import asyncio

import src.app.main  # noqa: F401

from src.app.core.config import APP_ENV
from src.app.database.postgres.database import SessionLocal
from src.app.dev.test_seed import TEST_POLICY_IDS
from src.app.domains.policy.embedding_service import PolicyEmbeddingService
from src.app.domains.policy.repository import PolicyRepository


async def main() -> None:
    if APP_ENV == "production":
        raise RuntimeError("운영 환경에서는 테스트 공고 임베딩 스크립트를 실행할 수 없습니다.")

    async with SessionLocal() as session:
        repo = PolicyRepository(session)
        embedding_service = PolicyEmbeddingService(session=session, repo=repo)
        changed = 0
        skipped = 0

        for origin_id in TEST_POLICY_IDS:
            policy = await repo.get_policy_by_origin_id(origin_id)
            if policy is None:
                print(f"- {origin_id}: missing")
                continue

            re_embedded = await embedding_service.sync_policy_chunks(
                policy_id=policy.id,
                content_raw=policy.content_raw,
                policy_title=policy.title or "",
                agency_name=policy.agency_name or "",
                support_type=policy.support_type or "",
                force=True,
            )
            if re_embedded:
                changed += 1
            else:
                skipped += 1
            print(f"- {origin_id}: {'embedded' if re_embedded else 'skipped'}")

        await session.commit()

    print("테스트 공고 임베딩을 완료했습니다.")
    print(f"- changed: {changed}")
    print(f"- skipped: {skipped}")


if __name__ == "__main__":
    asyncio.run(main())
