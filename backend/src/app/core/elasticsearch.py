from __future__ import annotations

import logging
from typing import Any

from elasticsearch import AsyncElasticsearch

from src.app.core.config import (
    ELASTICSEARCH_ENABLED,
    ELASTICSEARCH_REQUEST_TIMEOUT,
    ELASTICSEARCH_URL,
)

logger = logging.getLogger(__name__)

_client: AsyncElasticsearch | None = None


def is_elasticsearch_enabled() -> bool:
    return ELASTICSEARCH_ENABLED and bool(ELASTICSEARCH_URL.strip())


def get_elasticsearch_client() -> AsyncElasticsearch:
    global _client
    if _client is None:
        _client = AsyncElasticsearch(
            hosts=[ELASTICSEARCH_URL],
            request_timeout=ELASTICSEARCH_REQUEST_TIMEOUT,
            retry_on_timeout=True,
            max_retries=2,
        )
    return _client


async def close_elasticsearch_client() -> None:
    global _client
    if _client is None:
        return
    try:
        await _client.close()
    finally:
        _client = None


async def ping_elasticsearch() -> bool:
    if not is_elasticsearch_enabled():
        return False
    try:
        return bool(await get_elasticsearch_client().ping())
    except Exception as exc:  # pragma: no cover - network failure path
        logger.warning("[elasticsearch] ping failed: %s", exc)
        return False


async def get_elasticsearch_info() -> dict[str, Any]:
    if not is_elasticsearch_enabled():
        return {"enabled": False}
    client = get_elasticsearch_client()
    info = await client.info()
    return {
        "enabled": True,
        "cluster_name": info.get("cluster_name"),
        "version": (info.get("version") or {}).get("number"),
        "tagline": info.get("tagline"),
    }
