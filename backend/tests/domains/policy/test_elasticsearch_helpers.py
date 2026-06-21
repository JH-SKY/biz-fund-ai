from types import SimpleNamespace
import uuid

import pytest

from src.app.agents.biz_mong.tools.policy_rag import (
    _build_retrieval_backend_label,
    _collapse_sparse_backend_labels,
)
from src.app.domains.policy.elasticsearch_index import (
    build_policy_chunk_index_settings,
    extract_analyzed_tokens,
)
from src.app.domains.policy.elasticsearch_sparse_search import (
    ElasticsearchSparseSearcher,
)
from src.app.domains.policy.elasticsearch_sync_service import (
    ElasticsearchPolicyChunkSyncService,
)


def test_policy_chunk_index_uses_nori_analyzer():
    settings = build_policy_chunk_index_settings()

    analyzer = settings["settings"]["analysis"]["analyzer"]["policy_nori_analyzer"]
    assert analyzer["tokenizer"] == "nori_tokenizer"
    assert "lowercase" in analyzer["filter"]


def test_extract_analyzed_tokens_returns_compact_token_list():
    result = {"tokens": [{"token": "소상공인"}, {"token": "정책"}, {"token": "자금"}]}

    assert extract_analyzed_tokens(result) == ["소상공인", "정책", "자금"]


def test_serialize_chunk_document_uses_chunk_id_as_primary_document_key():
    chunk_id = uuid.uuid4()
    policy_id = uuid.uuid4()
    chunk = SimpleNamespace(
        id=chunk_id,
        policy_id=policy_id,
        chunk_index=2,
        chunk_text="정책 본문 청크",
    )
    policy = SimpleNamespace(
        id=policy_id,
        title="재도전특별자금",
        agency_name="중소벤처기업진흥공단",
        region="전국",
        category="정책자금",
        support_type="운전자금",
        view_count=42,
        target_logic={"region_restricted": False},
    )

    service = ElasticsearchPolicyChunkSyncService(
        session=SimpleNamespace(),
        client=SimpleNamespace(),
    )
    doc = service.serialize_chunk_document(chunk, policy)

    assert doc["chunk_id"] == str(chunk_id)
    assert doc["policy_id"] == str(policy_id)
    assert doc["title"] == "재도전특별자금"
    assert doc["agency_name"] == "중소벤처기업진흥공단"
    assert doc["content"] == "정책 본문 청크"


class _FakeIndices:
    async def exists(self, *, index: str) -> bool:
        return index == "policy_chunks_sparse"


class _FakeClient:
    def __init__(self) -> None:
        self.indices = _FakeIndices()

    async def search(self, *, index: str, **kwargs):
        assert index == "policy_chunks_sparse"
        self.last_query = kwargs
        return {
            "hits": {
                "hits": [
                    {
                        "_id": "chunk-1",
                        "_score": 3.2,
                        "_source": {"chunk_id": "chunk-1", "policy_id": "policy-1"},
                    },
                    {
                        "_id": "chunk-2",
                        "_score": 2.8,
                        "_source": {"chunk_id": "chunk-2", "policy_id": "policy-2"},
                    },
                ]
            }
        }


@pytest.mark.asyncio
async def test_sparse_search_returns_ranked_hits():
    client = _FakeClient()
    searcher = ElasticsearchSparseSearcher(client)

    results = await searcher.search(
        query_text="재도전특별자금 받을 수 있나요",
        keywords=["재도전특별자금", "정책자금"],
        region_filter="전국",
        biz_info={"funding_purpose": "운전자금"},
        limit=2,
    )

    assert results[0]["policy_id"] == "policy-1"
    assert results[0]["rank"] == 0
    assert results[0]["backend"] == "elasticsearch_bm25"
    assert results[1]["policy_id"] == "policy-2"


def test_retrieval_backend_label_reflects_dense_and_sparse_presence():
    assert _build_retrieval_backend_label(0, 1) == "dense+sparse"
    assert _build_retrieval_backend_label(0, None) == "dense_only"
    assert _build_retrieval_backend_label(None, 0) == "sparse_only"
    assert _build_retrieval_backend_label(None, None) == "none"


def test_sparse_backend_label_collapse_handles_mixed_and_single_backends():
    assert _collapse_sparse_backend_labels({"elasticsearch_bm25"}) == "elasticsearch_bm25"
    assert _collapse_sparse_backend_labels({"postgres_fallback"}) == "postgres_fallback"
    assert _collapse_sparse_backend_labels({"elasticsearch_bm25", "postgres_fallback"}) == "mixed"
