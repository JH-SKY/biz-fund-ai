from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from elasticsearch import AsyncElasticsearch

from src.app.core.config import ELASTICSEARCH_INDEX_POLICY_CHUNKS

POLICY_CHUNK_INDEX_NAME = ELASTICSEARCH_INDEX_POLICY_CHUNKS


def build_policy_chunk_index_settings() -> dict[str, Any]:
    return {
        "settings": {
            "analysis": {
                "analyzer": {
                    "policy_nori_analyzer": {
                        "type": "custom",
                        "tokenizer": "nori_tokenizer",
                        "filter": ["lowercase", "nori_readingform"],
                    }
                },
                "tokenizer": {
                    "nori_tokenizer": {
                        "type": "nori_tokenizer",
                        "decompound_mode": "mixed",
                    }
                },
            }
        },
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "chunk_id": {"type": "keyword"},
                "policy_id": {"type": "keyword"},
                "chunk_index": {"type": "integer"},
                "title": {
                    "type": "text",
                    "analyzer": "policy_nori_analyzer",
                    "fields": {"keyword": {"type": "keyword"}},
                },
                "agency_name": {
                    "type": "text",
                    "analyzer": "policy_nori_analyzer",
                    "fields": {"keyword": {"type": "keyword"}},
                },
                "content": {
                    "type": "text",
                    "analyzer": "policy_nori_analyzer",
                },
                "region": {"type": "keyword"},
                "category": {"type": "keyword"},
                "support_type": {"type": "keyword"},
                "view_count": {"type": "integer"},
                "target_logic": {"type": "object", "enabled": False},
            },
        },
    }


async def ensure_policy_chunk_index(
    client: AsyncElasticsearch,
    index_name: str = POLICY_CHUNK_INDEX_NAME,
) -> dict[str, Any]:
    exists = await client.indices.exists(index=index_name)
    if exists:
        return {"index": index_name, "created": False}

    body = build_policy_chunk_index_settings()
    await client.indices.create(index=index_name, **body)
    return {"index": index_name, "created": True}


async def analyze_with_nori(
    client: AsyncElasticsearch,
    text: str,
    *,
    index_name: str = POLICY_CHUNK_INDEX_NAME,
) -> dict[str, Any]:
    await ensure_policy_chunk_index(client, index_name=index_name)
    return await client.indices.analyze(
        index=index_name,
        body={"analyzer": "policy_nori_analyzer", "text": text},
    )


async def count_index_documents(
    client: AsyncElasticsearch,
    index_name: str = POLICY_CHUNK_INDEX_NAME,
) -> int:
    exists = await client.indices.exists(index=index_name)
    if not exists:
        return 0
    result = await client.count(index=index_name)
    return int(result["count"])


def extract_analyzed_tokens(analyze_result: dict[str, Any]) -> list[str]:
    tokens = analyze_result.get("tokens") or []
    return [token["token"] for token in tokens if token.get("token")]


def normalize_keyword_values(values: Sequence[str | None]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        if value is None:
            continue
        compact = str(value).strip()
        if compact:
            normalized.append(compact)
    return normalized
