# src/app/agents/biz_mong/tools/policy_rag.py
"""Tool: Hybrid RAG — 벡터 검색 + FTS(키워드) 검색 + RRF 결합.

설계 원칙:
  [Hybrid Search Strategy]
  1. Vector Search  — OpenAI text-embedding-3-small 으로 쿼리를 임베딩하고 pgvector cosine distance 검색.
  2. FTS Search     — Policy.title, ai_summary, ai_full_explanation 에 대해 ilike 키워드 검색.
                      (PostgreSQL pg_trgm 미설치 환경을 고려하여 표준 ilike 를 사용한다.)
  3. RRF Fusion     — Reciprocal Rank Fusion(k=60) 으로 두 결과를 결합, 상위 N 개를 반환한다.

  RRF 공식: score(d) = Σ 1 / (k + rank_i(d))
  - k=60 은 Cormack et al.(2009) 논문에서 권장하는 표준값입니다.
  - 두 검색 결과 중 하나에만 있는 문서는 해당 항목만 더해집니다.
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import OPENAI_API_KEY
from src.app.domains.policy.model import Policy, PolicyChunk, PolicyStatus

logger = logging.getLogger(__name__)

_EMBEDDING_MODEL = "text-embedding-3-small"
_RRF_K = 60          # RRF 표준 상수
_VECTOR_LIMIT = 20   # 벡터 검색 후보 수
_FTS_LIMIT = 20      # FTS 후보 수
_FINAL_LIMIT = 5     # 최종 반환 개수


async def policy_rag_search(
    query_text: str,
    session: AsyncSession,
    *,
    region_filter: str | None = None,
    top_k: int = _FINAL_LIMIT,
) -> list[dict[str, Any]]:
    """사용자 질문에 맞는 정책 공고를 Hybrid Search 로 검색한다.

    Args:
        query_text:    사용자 자연어 질문
        session:       AsyncSession
        region_filter: 지역 필터 (선택). 예: "서울", "전국"
        top_k:         반환할 최대 정책 수 (기본 5)

    Returns:
        [{
            "policy_id": str,
            "title": str,
            "agency_name": str,
            "ai_summary": str,
            "support_amount_desc": str,
            "region": str,
            "end_date": str,
            "apply_url": str,
            "rrf_score": float,
            "relevant_chunk": str,  # 검색에 매칭된 청크 텍스트
        }, ...]
    """
    # 검색기는 "질문을 임베딩으로 찾는 방식"과 "키워드로 찾는 방식"을 함께 쓴다.
    # 한쪽만 쓰면 의미 검색은 되는데 정책명을 놓치거나, 반대로 정확한 명칭만 찾고 문맥을 놓칠 수 있다.
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    # ── Step 1: 쿼리 임베딩 ──────────────────────────────────────────────
    try:
        emb_response = await client.embeddings.create(
            model=_EMBEDDING_MODEL,
            input=query_text,
        )
        query_vector = emb_response.data[0].embedding
    except Exception as exc:
        logger.warning("[policy_rag] 임베딩 실패, FTS 단독 검색으로 폴백: %s", exc)
        query_vector = None

    # ── Step 2: 벡터 검색 ──────────────────────────────────────────────
    vector_ids: list[str] = []
    if query_vector:
        vector_ids = await _vector_search(session, query_vector, region_filter, limit=_VECTOR_LIMIT)

    # ── Step 3: FTS (키워드) 검색 ────────────────────────────────────────
    keywords = _extract_keywords(query_text)
    fts_ids: list[str] = await _fts_search(session, keywords, region_filter, limit=_FTS_LIMIT)

    # ── Step 4: RRF 결합 ─────────────────────────────────────────────────
    # RRF 는 두 검색 결과를 한 점수표로 합치는 단계다.
    # 벡터 검색 상위권이면서 키워드 검색 상위권인 문서일수록 더 앞으로 오르게 된다.
    rrf_scores: dict[str, float] = {}
    for rank, pid in enumerate(vector_ids):
        rrf_scores[pid] = rrf_scores.get(pid, 0.0) + 1.0 / (_RRF_K + rank + 1)
    for rank, pid in enumerate(fts_ids):
        rrf_scores[pid] = rrf_scores.get(pid, 0.0) + 1.0 / (_RRF_K + rank + 1)

    if not rrf_scores:
        logger.info("[policy_rag] 검색 결과 없음 (query=%s)", query_text[:50])
        return []

    top_ids = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)[:top_k]

    # ── Step 5: 정책 상세 조회 ────────────────────────────────────────────
    results: list[dict[str, Any]] = []
    for policy_id in top_ids:
        policy = await _get_policy(session, policy_id)
        if policy is None:
            continue

        # 가장 관련 있는 청크 텍스트 추출 (벡터 검색 결과 우선)
        chunk_text = await _get_relevant_chunk(session, policy.id, query_vector)

        results.append({
            "policy_id": str(policy.id),
            "title": policy.title,
            "agency_name": policy.agency_name,
            "ai_summary": policy.ai_summary or "",
            "support_amount_desc": policy.support_amount_desc or "",
            "max_support": policy.max_support,
            "region": policy.region or "전국",
            "end_date": policy.closed_at.isoformat() if policy.closed_at else "",
            "apply_url": policy.apply_url or "",
            "rrf_score": rrf_scores[policy_id],
            "relevant_chunk": chunk_text,
        })

    logger.info("[policy_rag] query='%s' → %d 개 결과", query_text[:50], len(results))
    return results


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

async def _vector_search(
    session: AsyncSession,
    query_vector: list[float],
    region_filter: str | None,
    *,
    limit: int,
) -> list[str]:
    """pgvector cosine distance 기반 정책 ID 목록 반환 (거리 오름차순)."""
    policy_conditions = [
        Policy.is_active.is_(True),
        Policy.status == PolicyStatus.RECRUITING,
    ]
    if region_filter:
        policy_conditions.append(
            or_(
                Policy.region.ilike(f"%{region_filter}%"),
                Policy.region.ilike("%전국%"),
            )
        )

    min_dist = func.min(
        PolicyChunk.embedding.cosine_distance(query_vector)
    ).label("min_dist")

    stmt = (
        select(Policy.id, min_dist)
        .join(PolicyChunk, PolicyChunk.policy_id == Policy.id)
        .where(*policy_conditions)
        .group_by(Policy.id)
        .order_by(min_dist)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [str(row[0]) for row in result.all()]


async def _fts_search(
    session: AsyncSession,
    keywords: list[str],
    region_filter: str | None,
    *,
    limit: int,
) -> list[str]:
    """키워드 기반 ilike 검색으로 정책 ID 목록 반환."""
    if not keywords:
        return []

    base_conditions = [
        Policy.is_active.is_(True),
        Policy.status == PolicyStatus.RECRUITING,
    ]
    if region_filter:
        base_conditions.append(
            or_(
                Policy.region.ilike(f"%{region_filter}%"),
                Policy.region.ilike("%전국%"),
            )
        )

    # 각 키워드를 title, ai_summary 에서 OR 검색
    keyword_clauses = []
    for kw in keywords[:5]:  # 최대 5개 키워드만 사용
        pattern = f"%{kw}%"
        keyword_clauses.append(
            or_(
                Policy.title.ilike(pattern),
                Policy.ai_summary.ilike(pattern),
                Policy.ai_full_explanation.ilike(pattern),
            )
        )

    if not keyword_clauses:
        return []

    stmt = (
        select(Policy.id)
        .where(*base_conditions, or_(*keyword_clauses))
        .order_by(Policy.view_count.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [str(row[0]) for row in result.all()]


def _extract_keywords(text: str) -> list[str]:
    """자연어 질문에서 검색 키워드를 추출한다.

    한국어 공백 분리 후 2글자 이상, 불용어 제거.
    """
    # 사용자가 "가게 보증금", "월급 지원"처럼 생활 언어로 묻더라도
    # 검색기는 정책 문서에 가까운 단어(운전자금, 고용지원 등)로 확장해서 찾는다.
    stopwords = {
        "이", "가", "은", "는", "을", "를", "에", "서", "의", "와", "과",
        "그", "이것", "저것", "무엇", "어디", "어떻게", "왜", "언제",
        "있나요", "있어요", "주세요", "알려", "해줘", "해주세요",
        "너무", "요즘", "하나씩만", "각각", "좀", "이라도",
    }
    tokens = [t for t in re.split(r"[\s,?.!]+", text) if len(t) >= 2 and t not in stopwords]

    expanded: list[str] = []
    lowered = text.lower()
    if any(keyword in lowered for keyword in ("가스비", "전기세", "월세", "임대료", "고정비", "운영비")):
        expanded.extend(["운영자금", "소상공인", "지원금"])
    if any(keyword in lowered for keyword in ("직원", "월급", "인건비", "고용")):
        expanded.extend(["고용", "고용지원", "지원금"])
    if any(keyword in lowered for keyword in ("보증금", "대출", "융자")):
        expanded.extend(["대출", "운전자금", "정책자금"])
    if any(keyword in lowered for keyword in ("창업", "업력", "몇 년", "연차")):
        expanded.extend(["창업", "업력"])
    if any(keyword in lowered for keyword in ("여성기업", "여성")):
        expanded.append("여성기업")

    ordered: list[str] = []
    for keyword in expanded + tokens:
        normalized = keyword.strip()
        if not normalized or normalized in ordered:
            continue
        ordered.append(normalized)
    return ordered


async def _get_policy(session: AsyncSession, policy_id: str) -> Policy | None:
    stmt = select(Policy).where(Policy.id == uuid.UUID(policy_id))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _get_relevant_chunk(
    session: AsyncSession,
    policy_id: uuid.UUID,
    query_vector: list[float] | None,
) -> str:
    """정책에서 가장 관련 있는 청크 텍스트를 반환한다."""
    # 임베딩이 있으면 질문과 가장 가까운 청크를 고르고,
    # 없으면 최소한 첫 번째 청크라도 보여 주도록 안전하게 폴백한다.
    if query_vector:
        stmt = (
            select(PolicyChunk.chunk_text)
            .where(PolicyChunk.policy_id == policy_id)
            .order_by(PolicyChunk.embedding.cosine_distance(query_vector))
            .limit(1)
        )
    else:
        stmt = (
            select(PolicyChunk.chunk_text)
            .where(PolicyChunk.policy_id == policy_id)
            .order_by(PolicyChunk.chunk_index)
            .limit(1)
        )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    return row or ""
