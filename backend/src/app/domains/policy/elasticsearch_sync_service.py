from __future__ import annotations

import json
from typing import Any

from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.app.domains.policy.elasticsearch_index import (
    POLICY_CHUNK_INDEX_NAME,
    ensure_policy_chunk_index,
)
from src.app.domains.policy.model import Policy, PolicyChunk


class ElasticsearchPolicyChunkSyncService:
    def __init__(
        self,
        session: AsyncSession,
        client: AsyncElasticsearch,
        *,
        index_name: str = POLICY_CHUNK_INDEX_NAME,
    ) -> None:
        self._session = session
        self._client = client
        self._index_name = index_name

    async def sync_all_policy_chunks(self) -> dict[str, int]:
        await ensure_policy_chunk_index(self._client, self._index_name)
        stmt = (
            select(PolicyChunk, Policy)
            .join(Policy, Policy.id == PolicyChunk.policy_id)
            .where(Policy.is_active.is_(True))
        )
        result = await self._session.execute(stmt)
        rows = result.all()
        actions = [self._build_index_action(chunk, policy) for chunk, policy in rows]
        success, errors = await async_bulk(
            self._client,
            actions,
            raise_on_error=False,
            raise_on_exception=False,
        )
        return {"indexed": int(success), "failed": len(errors), "total": len(actions)}

    async def sync_policy(self, policy_id: Any) -> dict[str, int]:
        await ensure_policy_chunk_index(self._client, self._index_name)
        stmt = (
            select(Policy)
            .options(selectinload(Policy.chunks))
            .where(Policy.id == policy_id)
        )
        policy = (await self._session.execute(stmt)).scalars().first()
        if policy is None:
            return {"indexed": 0, "failed": 0, "total": 0}

        actions = [self._build_index_action(chunk, policy) for chunk in policy.chunks]
        success, errors = await async_bulk(
            self._client,
            actions,
            raise_on_error=False,
            raise_on_exception=False,
        )
        return {"indexed": int(success), "failed": len(errors), "total": len(actions)}

    async def delete_policy(self, policy_id: Any) -> dict[str, int]:
        exists = await self._client.indices.exists(index=self._index_name)
        if not exists:
            return {"deleted": 0}
        result = await self._client.delete_by_query(
            index=self._index_name,
            query={"term": {"policy_id": str(policy_id)}},
            conflicts="proceed",
            refresh=True,
        )
        return {"deleted": int(result.get("deleted", 0))}

    async def delete_chunk(self, chunk_id: Any) -> dict[str, int]:
        exists = await self._client.indices.exists(index=self._index_name)
        if not exists:
            return {"deleted": 0}
        result = await self._client.delete(
            index=self._index_name,
            id=str(chunk_id),
            ignore=[404],
            refresh=True,
        )
        return {"deleted": 0 if result.get("result") == "not_found" else 1}

    async def count_or_validate_sync(self) -> dict[str, int]:
        exists = await self._client.indices.exists(index=self._index_name)
        es_count = 0
        if exists:
            es_count = int((await self._client.count(index=self._index_name))["count"])

        db_count_stmt = select(PolicyChunk).join(Policy, Policy.id == PolicyChunk.policy_id).where(
            Policy.is_active.is_(True)
        )
        db_count = len((await self._session.execute(db_count_stmt)).scalars().all())
        return {"db_count": db_count, "es_count": es_count, "missing": max(db_count - es_count, 0)}

    def serialize_chunk_document(self, chunk: PolicyChunk, policy: Policy) -> dict[str, Any]:
        target_logic = policy.target_logic
        if not isinstance(target_logic, dict):
            target_logic = {"raw": target_logic} if target_logic is not None else {}

        return {
            "chunk_id": str(chunk.id),
            "policy_id": str(policy.id),
            "chunk_index": int(chunk.chunk_index),
            "title": policy.title or "",
            "agency_name": policy.agency_name or "",
            "content": chunk.chunk_text or "",
            "region": policy.region or "",
            "category": policy.category or "",
            "support_type": policy.support_type or "",
            "view_count": int(policy.view_count or 0),
            "target_logic": json.loads(json.dumps(target_logic, default=str)),
        }

    def _build_index_action(self, chunk: PolicyChunk, policy: Policy) -> dict[str, Any]:
        return {
            "_op_type": "index",
            "_index": self._index_name,
            "_id": str(chunk.id),
            "_source": self.serialize_chunk_document(chunk, policy),
        }
