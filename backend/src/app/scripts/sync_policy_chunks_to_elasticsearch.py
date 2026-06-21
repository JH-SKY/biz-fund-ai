from __future__ import annotations

import asyncio

import src.app.main  # noqa: F401

from src.app.core.elasticsearch import (
    close_elasticsearch_client,
    get_elasticsearch_client,
    get_elasticsearch_info,
    ping_elasticsearch,
)
from src.app.database.postgres.database import SessionLocal
from src.app.domains.policy.elasticsearch_index import (
    analyze_with_nori,
    count_index_documents,
    ensure_policy_chunk_index,
    extract_analyzed_tokens,
)
from src.app.domains.policy.elasticsearch_sync_service import (
    ElasticsearchPolicyChunkSyncService,
)


async def main() -> None:
    client = get_elasticsearch_client()
    healthy = await ping_elasticsearch()
    if not healthy:
        raise RuntimeError("Elasticsearch is not reachable.")

    info = await get_elasticsearch_info()
    print(f"[es] cluster={info.get('cluster_name')} version={info.get('version')}")

    await ensure_policy_chunk_index(client)
    analyze_result = await analyze_with_nori(client, "소상공인정책자금")
    print("[es] nori tokens:", extract_analyzed_tokens(analyze_result))

    async with SessionLocal() as session:
        sync_service = ElasticsearchPolicyChunkSyncService(session, client)
        sync_result = await sync_service.sync_all_policy_chunks()
        validation = await sync_service.count_or_validate_sync()

    es_count = await count_index_documents(client)
    print("[sync] result:", sync_result)
    print("[sync] validation:", validation)
    print("[sync] es_count:", es_count)

    await close_elasticsearch_client()


if __name__ == "__main__":
    asyncio.run(main())
