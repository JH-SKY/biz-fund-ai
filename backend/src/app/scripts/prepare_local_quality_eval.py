"""로컬 품질평가용 데이터를 한 번에 준비하는 실행 스크립트."""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
import sys

from dotenv import load_dotenv

if __package__ in {None, ""}:
    backend_root = Path(__file__).resolve().parents[3]
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))
else:
    backend_root = Path(__file__).resolve().parents[3]

load_dotenv(backend_root / ".env")

from sqlalchemy import update

from src.app.core.config import APP_ENV, OPENAI_API_KEY
from src.app.database.postgres.database import SessionLocal
from src.app.dev.test_seed import TEST_POLICY_IDS, seed_test_scenarios
from src.app.domains.policy.embedding_service import PolicyEmbeddingService
from src.app.domains.policy.model import Policy
from src.app.domains.policy.repository import PolicyRepository
from src.app.scripts.evaluate_bizmong_quality import main as run_quality_eval
from src.app.scripts.evaluate_bizmong_quality import _preflight_database_connection


async def _seed_and_freeze(*, freeze_non_test: bool) -> dict[str, int]:
    async with SessionLocal() as session:
        summary = await seed_test_scenarios(session)
        if freeze_non_test:
            result = await session.execute(
                update(Policy)
                .where(Policy.origin_id.not_in(TEST_POLICY_IDS))
                .values(is_active=False)
            )
            summary["non_test_policies_disabled"] = result.rowcount or 0
        else:
            summary["non_test_policies_disabled"] = 0
        await session.commit()
    return summary


async def _embed_test_policies() -> dict[str, int]:
    async with SessionLocal() as session:
        repo = PolicyRepository(session)
        embedding_service = PolicyEmbeddingService(session=session, repo=repo)
        changed = 0
        skipped = 0
        missing = 0

        for origin_id in TEST_POLICY_IDS:
            policy = await repo.get_policy_by_origin_id(origin_id)
            if policy is None:
                missing += 1
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

        await session.commit()

    return {
        "embedded_changed": changed,
        "embedded_skipped": skipped,
        "embedded_missing": missing,
    }


async def main(
    *,
    database_url: str | None = None,
    freeze_non_test: bool = True,
    run_embedding: bool = True,
    run_eval: bool = False,
    eval_limit: int | None = None,
) -> None:
    if APP_ENV == "production":
        raise RuntimeError("운영 환경에서는 로컬 품질평가 준비 스크립트를 실행할 수 없습니다.")

    if database_url:
        os.environ["DATABASE_URL"] = database_url

    resolved_database_url = database_url or os.getenv("DATABASE_URL")
    preflight_error = await _preflight_database_connection(resolved_database_url)
    if preflight_error is not None:
        raise RuntimeError(f"DB preflight failed: {preflight_error}")

    summary = await _seed_and_freeze(freeze_non_test=freeze_non_test)
    if run_embedding:
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY 없이 테스트 공고 임베딩을 실행할 수 없습니다.")
        summary.update(await _embed_test_policies())
    else:
        summary.update(
            {
                "embedded_changed": 0,
                "embedded_skipped": 0,
                "embedded_missing": 0,
            }
        )

    print("BizMong 로컬 품질평가 준비를 완료했습니다.")
    print(f"- freeze_non_test: {freeze_non_test}")
    print(f"- run_embedding: {run_embedding}")
    for key, value in summary.items():
        print(f"- {key}: {value}")

    if run_eval:
        print()
        print("이어서 BizMong 품질평가를 실행합니다.")
        await run_quality_eval(
            limit=eval_limit,
            database_url=resolved_database_url,
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare local data for BizMong quality evaluation")
    parser.add_argument("--database-url")
    parser.add_argument("--skip-freeze", action="store_true")
    parser.add_argument("--skip-embedding", action="store_true")
    parser.add_argument("--run-eval", action="store_true")
    parser.add_argument("--eval-limit", type=int)
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(
        main(
            database_url=args.database_url,
            freeze_non_test=not args.skip_freeze,
            run_embedding=not args.skip_embedding,
            run_eval=args.run_eval,
            eval_limit=args.eval_limit,
        )
    )
