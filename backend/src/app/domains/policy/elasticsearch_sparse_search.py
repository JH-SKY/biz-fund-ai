from __future__ import annotations

from typing import Any

from elasticsearch import AsyncElasticsearch

from src.app.domains.policy.elasticsearch_index import POLICY_CHUNK_INDEX_NAME

DEFAULT_FIELD_BOOSTS = {
    "title": 4,
    "agency_name": 3,
    "content": 1,
}


class ElasticsearchSparseSearcher:
    def __init__(
        self,
        client: AsyncElasticsearch,
        *,
        index_name: str = POLICY_CHUNK_INDEX_NAME,
        field_boosts: dict[str, int] | None = None,
    ) -> None:
        self._client = client
        self._index_name = index_name
        self._field_boosts = field_boosts or DEFAULT_FIELD_BOOSTS

    async def search(
        self,
        *,
        query_text: str,
        keywords: list[str],
        region_filter: str | None,
        biz_info: dict[str, Any] | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        if not query_text.strip() and not keywords:
            return []

        exists = await self._client.indices.exists(index=self._index_name)
        if not exists:
            return []

        query = self._build_query(
            query_text=query_text,
            keywords=keywords,
            region_filter=region_filter,
            biz_info=biz_info,
            limit=limit,
        )
        response = await self._client.search(index=self._index_name, **query)
        hits = (response.get("hits") or {}).get("hits") or []
        results: list[dict[str, Any]] = []
        for rank, hit in enumerate(hits):
            source = hit.get("_source") or {}
            results.append(
                {
                    "chunk_id": str(source.get("chunk_id") or hit.get("_id")),
                    "policy_id": str(source.get("policy_id")),
                    "rank": rank,
                    "score": float(hit.get("_score") or 0.0),
                    "backend": "elasticsearch_bm25",
                }
            )
        return results

    def _build_query(
        self,
        *,
        query_text: str,
        keywords: list[str],
        region_filter: str | None,
        biz_info: dict[str, Any] | None,
        limit: int,
    ) -> dict[str, Any]:
        fields = [f"{field}^{boost}" for field, boost in self._field_boosts.items()]
        clauses: list[dict[str, Any]] = []
        compact_query = query_text.strip()
        if compact_query:
            clauses.append(
                {
                    "multi_match": {
                        "query": compact_query,
                        "fields": fields,
                        "type": "best_fields",
                        "operator": "or",
                    }
                }
            )
        if keywords:
            clauses.append(
                {
                    "multi_match": {
                        "query": " ".join(keywords),
                        "fields": fields,
                        "type": "most_fields",
                        "operator": "or",
                    }
                }
            )

        should_clauses: list[dict[str, Any]] = []
        region_value = (region_filter or (biz_info or {}).get("region_sido") or "").strip()
        if region_value:
            should_clauses.append({"term": {"region": region_value}})
            should_clauses.append({"term": {"region": "전국"}})

        support_type = ((biz_info or {}).get("funding_purpose") or "").strip()
        if support_type:
            should_clauses.append({"term": {"support_type": support_type}})

        query: dict[str, Any] = {
            "size": limit,
            "_source": [
                "chunk_id",
                "policy_id",
                "title",
                "agency_name",
                "region",
                "support_type",
            ],
            "query": {
                "bool": {
                    "must": clauses,
                    "should": should_clauses,
                    "minimum_should_match": 0,
                }
            },
        }
        return query
