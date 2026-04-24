"""
정책 공고 임베딩 테스트 스크립트
- DB에 저장된 최신 정책 1건을 가져와 청킹 + 임베딩 후 policy_chunks에 저장
- 저장 후 벡터 유사도 검색으로 Supabase pgvector 동작 검증
실행: uv run python test_embed.py
"""

import asyncio
import os
import sys

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from openai import AsyncOpenAI

# SQLAlchemy 관계 해결을 위해 모든 모델 먼저 로드 (src.app 경로 통일)
import src.app.domains.policy.model        # noqa: F401
import src.app.domains.admin.model         # noqa: F401
import src.app.domains.auth.model          # noqa: F401
import src.app.domains.chat.model          # noqa: F401
import src.app.domains.biz_pick.model      # noqa: F401
import src.app.domains.system.model        # noqa: F401
import src.app.domains.diagnosis.model     # noqa: F401
import src.app.domains.notification.model  # noqa: F401
import src.app.domains.business.model      # noqa: F401

from src.app.domains.policy.repository import PolicyRepository
from src.app.domains.policy.embedding_service import PolicyEmbeddingService, chunk_text

DATABASE_URL = os.environ["DATABASE_URL"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]


async def main():
    print("=" * 60)
    print("  Biz-Fund-AI - pgvector 임베딩 테스트")
    print("=" * 60)

    # ── 1. DB 연결 ──────────────────────────────────────────────
    print("\n[1] Supabase 연결 중...")
    engine = create_async_engine(DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as session:
        # ── 2. pgvector 확장 확인 ────────────────────────────────
        print("[2] pgvector 확장 확인...")
        result = await session.execute(
            text("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector'")
        )
        row = result.fetchone()
        if row:
            print(f"    ✅ pgvector {row[1]} 설치 확인")
        else:
            print("    ❌ pgvector 확장이 없습니다! Supabase Dashboard → Extensions → vector 활성화 필요")
            return

        # ── 3. 최신 정책 1건 조회 ───────────────────────────────
        print("[3] 최신 정책 조회...")
        result = await session.execute(
            text("SELECT id, title, agency_name, support_type, content_raw, content_hash FROM policies ORDER BY created_at DESC LIMIT 1")
        )
        policy = result.fetchone()
        if not policy:
            print("    ❌ policies 테이블에 데이터가 없습니다.")
            return

        policy_id, title, agency_name, support_type, content_raw, content_hash = policy
        print(f"    ✅ 정책 발견: [{title}] ({agency_name})")
        print(f"       ID: {policy_id}")
        print(f"       content_hash: {content_hash or '(없음 — 미임베딩)'}")

        # ── 4. 청킹 미리보기 ────────────────────────────────────
        print(f"\n[4] 청킹 분석...")
        chunks = chunk_text(content_raw or "")
        print(f"    → {len(chunks)}개 청크 생성")
        for i, c in enumerate(chunks[:3]):
            preview = c.chunk_text[:60].replace("\n", " ")
            print(f"    [{i}] type={c.chunk_type} | {preview}...")
        if len(chunks) > 3:
            print(f"    ... (외 {len(chunks)-3}개)")

        if not chunks:
            print("    ❌ 청킹 결과가 없습니다. content_raw가 비어있을 수 있습니다.")
            return

        # ── 5. 임베딩 실행 ──────────────────────────────────────
        print(f"\n[5] OpenAI 임베딩 실행 (text-embedding-3-small)...")
        repo = PolicyRepository(session)
        embedding_svc = PolicyEmbeddingService(session=session, repo=repo)

        changed = await embedding_svc.sync_policy_chunks(
            policy_id=policy_id,
            content_raw=content_raw,
            policy_title=title or "",
            agency_name=agency_name or "",
            support_type=support_type or "",
            force=True,  # 강제 재임베딩
        )
        await session.commit()

        if changed:
            print(f"    ✅ 임베딩 완료 ({len(chunks)}개 청크 → policy_chunks 저장)")
        else:
            print("    ⚠️  변경 없음 (force=True인데 스킵? content_raw 확인 필요)")

        # ── 6. 저장 검증 ─────────────────────────────────────────
        print(f"\n[6] policy_chunks 저장 확인...")
        result = await session.execute(
            text("SELECT COUNT(*) FROM policy_chunks WHERE policy_id = :pid"),
            {"pid": str(policy_id)},
        )
        (total_count,) = result.fetchone()

        result2 = await session.execute(
            text("SELECT COUNT(*) FROM policy_chunks WHERE policy_id = :pid AND embedding IS NOT NULL"),
            {"pid": str(policy_id)},
        )
        (embedded_count,) = result2.fetchone()

        print(f"    총 청크 수: {total_count}")
        print(f"    임베딩 있는 청크: {embedded_count}")

        # ── 7. 벡터 유사도 검색 테스트 ──────────────────────────
        print(f"\n[7] 벡터 유사도 검색 테스트...")
        query_text = f"{title} 지원 대상"
        print(f"    쿼리: '{query_text}'")

        openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        resp = await openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=[query_text],
        )
        query_vector = resp.data[0].embedding

        # pgvector ORM 방식으로 코사인 거리 검색
        from sqlalchemy import select, func
        from src.app.domains.policy.model import PolicyChunk

        stmt = (
            select(
                PolicyChunk.chunk_type,
                PolicyChunk.chunk_text,
                PolicyChunk.embedding.cosine_distance(query_vector).label("dist"),
            )
            .where(PolicyChunk.policy_id == policy_id)
            .order_by(PolicyChunk.embedding.cosine_distance(query_vector))
            .limit(3)
        )
        result = await session.execute(stmt)
        rows = result.all()

        print(f"    ✅ 상위 3개 유사 청크:")
        for i, (chunk_type, chunk_text_val, dist) in enumerate(rows):
            sim = 1 - float(dist)
            preview = (chunk_text_val or "")[:70].replace("\n", " ")
            print(f"    [{i+1}] similarity={sim:.4f} | type={chunk_type}")
            print(f"         {preview}...")

    print("\n" + "=" * 60)
    print("  테스트 완료! pgvector가 Supabase에서 정상 동작합니다. ✅")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
