from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
import logging
import re
import unicodedata
import uuid
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import OPENAI_API_KEY
from src.app.core.elasticsearch import get_elasticsearch_client, is_elasticsearch_enabled
from src.app.domains.policy.elasticsearch_sparse_search import ElasticsearchSparseSearcher
from src.app.domains.policy.model import Policy, PolicyChunk, PolicyStatus
from src.app.domains.policy.target_logic import parse_target_logic

logger = logging.getLogger(__name__)

_EMBEDDING_MODEL = "text-embedding-3-small"
_RRF_K = 60
_VECTOR_LIMIT = 20
_FTS_LIMIT = 20
_FINAL_LIMIT = 5
_MAX_KEYWORDS = 8
_QUERY_REWRITE_MODEL = "gpt-4o-mini"

_STOPWORDS = {
    "이",
    "가",
    "은",
    "는",
    "을",
    "를",
    "좀",
    "조금",
    "관련",
    "문의",
    "있나",
    "있어",
    "있을까",
    "주세요",
    "알려줘",
    "알려주세요",
    "궁금해",
    "궁금합니다",
}

_DOMAIN_SYNONYMS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (
        ("운영비", "고정비", "월세", "전기료", "가스비", "관리비", "수도비", "재료비", "원자재", "공과금"),
        ("운영자금", "소상공인", "지원금", "경영안정", "긴급경영안정"),
    ),
    (
        ("직원", "채용", "급여", "인력", "고용", "월급", "알바", "아르바이트"),
        ("고용", "고용지원", "지원금", "일자리", "고용유지"),
    ),
    (("대출", "보증", "융자", "자금"), ("대출", "융자", "정책자금")),
    (("시설", "설비", "장비", "기계"), ("시설자금", "설비", "스마트공장")),
    (("창업", "초기", "스타트업"), ("창업", "초기창업")),
    (("수출", "해외", "판로"), ("수출", "해외진출", "판로")),
    (("특허", "지식재산"), ("특허", "지식재산")),
    (("벤처",), ("벤처",)),
    (("여성", "여성기업"), ("여성기업",)),
)

_REGION_HINTS = (
    "서울",
    "경기",
    "인천",
    "부산",
    "대구",
    "광주",
    "대전",
    "울산",
    "세종",
    "강원",
    "충북",
    "충남",
    "전북",
    "전남",
    "경북",
    "경남",
    "제주",
    "전국",
)

_REGION_HINT_ALIASES = {
    "강남": "서울",
    "강북": "서울",
    "서초": "서울",
    "송파": "서울",
    "마포": "서울",
    "영등포": "서울",
    "수원": "경기",
    "성남": "경기",
    "용인": "경기",
    "고양": "경기",
    "화성": "경기",
    "부천": "경기",
    "안산": "경기",
    "평택": "경기",
    "천안": "충남",
    "아산": "충남",
    "청주": "충북",
    "충주": "충북",
    "전주": "전북",
    "익산": "전북",
    "군산": "전북",
    "목포": "전남",
    "여수": "전남",
    "순천": "전남",
    "포항": "경북",
    "구미": "경북",
    "경주": "경북",
    "창원": "경남",
    "김해": "경남",
    "진주": "경남",
    "춘천": "강원",
    "원주": "강원",
    "강릉": "강원",
    "해운대": "부산",
    "달서": "대구",
    "유성": "대전",
    "서귀포": "제주",
    "제주시": "제주",
}

_QUERY_INTENT_RULES: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    (
        "operating_cost",
        (
            "월세",
            "전기료",
            "전기세",
            "가스비",
            "고정비",
            "운영비",
            "관리비",
            "수도비",
            "재료비",
            "원자재값",
            "공과금",
            "버티기",
            "빡빡",
            "부담",
            "벅거",
        ),
        ("소상공인", "운영자금", "경영안정", "긴급경영안정", "정책자금"),
    ),
    (
        "hiring",
        ("직원", "채용", "월급", "인건비", "고용", "급여", "알바", "아르바이트"),
        ("고용지원", "인건비", "일자리", "채용지원", "고용유지", "소상공인"),
    ),
    (
        "facility",
        ("설비", "장비", "기계", "공장", "교체", "자동화"),
        ("시설자금", "설비", "제조", "자동화", "스마트공장"),
    ),
    (
        "startup",
        ("창업", "초기", "입문", "스타트업", "예비창업"),
        ("초기창업", "창업자금", "창업지원", "사업화"),
    ),
    (
        "export",
        ("수출", "해외", "판로", "바이어"),
        ("수출", "해외진출", "판로", "마케팅"),
    ),
)

_INTENT_DISPLAY_NAMES = {
    "operating_cost": "운영자금",
    "hiring": "고용지원",
    "facility": "시설자금",
    "startup": "창업지원",
    "export": "수출지원",
    "general": "정책자금",
}

_PER_INTENT_QUOTA_MARKERS = (
    "각각",
    "각자",
    "하나씩",
    "한 개씩",
    "1개씩",
    "각 1개",
    "각각 하나",
    "두 가지",
)


@dataclass(slots=True)
class SearchTask:
    intent_name: str
    rewritten_queries: list[str]
    expected_support_types: list[str]
    explanation: str
    seed_query: str


async def policy_rag_search(
    query_text: str,
    session: AsyncSession,
    *,
    region_filter: str | None = None,
    biz_info: dict[str, Any] | None = None,
    top_k: int = _FINAL_LIMIT,
) -> dict[str, Any]:
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    search_plan = await _build_search_plan(query_text, biz_info=biz_info, client=client)
    per_task_limit = 3 if top_k >= 3 else max(2, top_k)
    intent_results: list[dict[str, Any]] = []

    for task in search_plan:
        task_results = await _search_for_task(
            task,
            session,
            region_filter=region_filter,
            biz_info=biz_info,
            client=client,
            limit=per_task_limit,
        )
        intent_results.append({
            "intent": task.intent_name,
            "intent_label": _INTENT_DISPLAY_NAMES.get(task.intent_name, task.intent_name),
            "queries": task.rewritten_queries,
            "expected_support_types": task.expected_support_types,
            "explanation": task.explanation,
            "results": task_results,
        })

    merged_results = _merge_intent_result_sets(intent_results, question=query_text, top_k=top_k)
    search_metadata = _build_search_metadata(search_plan, intent_results)

    logger.info(
        "[policy_rag] query='%s' intents=%s results=%d llm_rewrite=%s",
        query_text[:50],
        search_metadata["detected_intents"],
        len(merged_results),
        search_metadata["rewritten_by_llm"],
    )
    return {
        "results": merged_results,
        "intent_results": intent_results,
        "search_metadata": search_metadata,
    }


async def _build_search_plan(
    question: str,
    *,
    biz_info: dict[str, Any] | None = None,
    client: AsyncOpenAI | None = None,
) -> list[SearchTask]:
    detected_intents = _detect_query_intents(question)
    if not detected_intents:
        detected_intents = ["general"]

    tasks: list[SearchTask] = []
    for intent_name in detected_intents:
        expected_support_types = _get_intent_support_types(intent_name)
        seed_query = _build_task_seed_query(question, expected_support_types)
        rewritten_queries, rewrite_source = await _prepare_task_queries(
            seed_query,
            biz_info=biz_info,
            intent_name=intent_name,
            client=client,
        )
        explanation = _build_task_explanation(intent_name, rewrite_source, expected_support_types)
        tasks.append(
            SearchTask(
                intent_name=intent_name,
                rewritten_queries=rewritten_queries,
                expected_support_types=expected_support_types,
                explanation=explanation,
                seed_query=seed_query,
            )
        )
    return tasks


async def _prepare_task_queries(
    question: str,
    *,
    biz_info: dict[str, Any] | None,
    intent_name: str,
    client: AsyncOpenAI | None,
) -> tuple[list[str], str]:
    try:
        rewritten_queries = await _rewrite_query_with_llm(
            question,
            biz_info=biz_info,
            intent_name=intent_name,
            client=client,
        )
        return rewritten_queries, "llm"
    except Exception as exc:
        logger.warning("[policy_rag] llm rewrite fallback intent=%s reason=%s", intent_name, exc)
        return _rewrite_query_variants(question, biz_info=biz_info), "rule"


async def _rewrite_query_with_llm(
    question: str,
    biz_info: dict[str, Any] | None = None,
    *,
    intent_name: str | None = None,
    client: AsyncOpenAI | None = None,
) -> list[str]:
    openai_client = client or AsyncOpenAI(api_key=OPENAI_API_KEY)
    intent_label = _INTENT_DISPLAY_NAMES.get(intent_name or "general", "정책자금")
    business_context = ", ".join(_build_business_context_terms(biz_info or {})) or "없음"
    response = await openai_client.chat.completions.create(
        model=_QUERY_REWRITE_MODEL,
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "당신은 정책자금 검색어 재작성기다. "
                    "반드시 JSON 객체만 반환하고 key는 queries 하나만 사용한다. "
                    "queries는 1~3개의 한국어 검색 질의 배열이며 설명문은 넣지 않는다."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"원문 질문: {question}\n"
                    f"집중 의도: {intent_label}\n"
                    f"사업자 맥락: {business_context}\n"
                    "요구사항:\n"
                    "- 우회 표현은 정책 검색에 맞는 지원명/자금명으로 바꿀 것\n"
                    "- 원문 질문도 후보 중 하나로 포함할 것\n"
                    "- 너무 긴 문장은 피하고 검색 친화적으로 만들 것\n"
                    '- 예시 형태: {"queries":["원문","소상공인 운영자금","경영안정 정책자금"]}'
                ),
            },
        ],
    )
    content = (response.choices[0].message.content or "").strip()
    payload = json.loads(content)
    queries = payload.get("queries")
    if not isinstance(queries, list):
        raise ValueError("rewrite response missing queries")

    ordered: list[str] = []
    for raw_query in queries[:3]:
        if not isinstance(raw_query, str):
            continue
        compact = " ".join(raw_query.split())
        if compact and compact not in ordered:
            ordered.append(compact)
    original = " ".join(question.split())
    if original and original not in ordered:
        ordered.insert(0, original)
    if not ordered:
        raise ValueError("rewrite returned empty queries")
    return ordered[:3]


def _get_intent_support_types(intent_name: str) -> list[str]:
    for rule_intent, _, rewrite_terms in _QUERY_INTENT_RULES:
        if rule_intent == intent_name:
            return list(rewrite_terms)
    return ["정책자금", "소상공인", "지원사업"]


def _build_task_seed_query(question: str, expected_support_types: list[str]) -> str:
    if not expected_support_types:
        return question
    return f"{question} {' '.join(expected_support_types[:2])}"


def _build_task_explanation(
    intent_name: str,
    rewrite_source: str,
    expected_support_types: list[str],
) -> str:
    support_hint = ", ".join(expected_support_types[:3])
    rewrite_label = "LLM 재작성" if rewrite_source == "llm" else "규칙 기반 폴백"
    return f"{_INTENT_DISPLAY_NAMES.get(intent_name, intent_name)} 관점으로 분리했고 {rewrite_label}을 사용해 {support_hint} 중심으로 검색합니다."


async def _search_for_task(
    task: SearchTask,
    session: AsyncSession,
    *,
    region_filter: str | None,
    biz_info: dict[str, Any] | None,
    client: AsyncOpenAI,
    limit: int,
) -> list[dict[str, Any]]:
    rrf_scores: dict[str, float] = {}
    query_vectors: dict[str, list[float] | None] = {}
    dense_rank_map: dict[str, int] = {}
    sparse_rank_map: dict[str, int] = {}
    sparse_score_map: dict[str, float] = {}
    sparse_backend_labels: set[str] = set()
    sparse_fallback_used = False

    for rewritten_query in task.rewritten_queries:
        query_vector = await _create_query_embedding(client, rewritten_query)
        query_vectors[rewritten_query] = query_vector

        vector_ids: list[str] = []
        if query_vector:
            vector_ids = await _vector_search(
                session,
                query_vector,
                region_filter,
                limit=_VECTOR_LIMIT,
            )
            for rank, policy_id in enumerate(vector_ids):
                previous = dense_rank_map.get(policy_id)
                if previous is None or rank < previous:
                    dense_rank_map[policy_id] = rank

        keywords = _extract_keywords(rewritten_query)
        try:
            sparse_hits = await _sparse_search_elasticsearch(
                query_text=rewritten_query,
                keywords=keywords,
                region_filter=region_filter,
                biz_info=biz_info,
                limit=_FTS_LIMIT,
            )
        except Exception as exc:
            logger.warning(
                "[policy_rag] elasticsearch sparse fallback query='%s' reason=%s",
                rewritten_query[:40],
                exc,
            )
            sparse_fallback_used = True
            sparse_hits = await _keyword_search_postgres(
                session,
                keywords,
                region_filter,
                biz_info=biz_info,
                limit=_FTS_LIMIT,
            )

        for rank, policy_id in enumerate(vector_ids):
            rrf_scores[policy_id] = rrf_scores.get(policy_id, 0.0) + 1.0 / (_RRF_K + rank + 1)
        for sparse_hit in sparse_hits:
            policy_id = str(sparse_hit["policy_id"])
            rank = int(sparse_hit.get("rank", 0))
            score = float(sparse_hit.get("score") or 0.0)
            backend = str(sparse_hit.get("backend") or "postgres_fallback")
            sparse_backend_labels.add(backend)
            if backend != "elasticsearch_bm25":
                sparse_fallback_used = True
            rrf_scores[policy_id] = rrf_scores.get(policy_id, 0.0) + 1.0 / (_RRF_K + rank + 1)
            previous = sparse_rank_map.get(policy_id)
            if previous is None or rank < previous:
                sparse_rank_map[policy_id] = rank
            sparse_score_map[policy_id] = max(sparse_score_map.get(policy_id, 0.0), score)

    if not rrf_scores:
        return []

    top_ids = sorted(rrf_scores, key=lambda item: rrf_scores[item], reverse=True)[: max(limit * 3, limit)]
    primary_vector = next((vector for vector in query_vectors.values() if vector), None)
    results = await _materialize_policy_results(
        session,
        top_ids,
        rrf_scores=rrf_scores,
        query_vector=primary_vector,
        dense_rank_map=dense_rank_map,
        sparse_rank_map=sparse_rank_map,
        sparse_score_map=sparse_score_map,
        sparse_backend_labels=sparse_backend_labels,
        sparse_fallback_used=sparse_fallback_used,
        limit=limit,
    )
    for result in results:
        result["intent"] = task.intent_name
        result["intent_label"] = _INTENT_DISPLAY_NAMES.get(task.intent_name, task.intent_name)
    return results


async def _create_query_embedding(
    client: AsyncOpenAI,
    query_text: str,
) -> list[float] | None:
    try:
        emb_response = await client.embeddings.create(model=_EMBEDDING_MODEL, input=query_text)
        return emb_response.data[0].embedding
    except Exception as exc:
        logger.warning("[policy_rag] embedding fallback query='%s' reason=%s", query_text[:40], exc)
        return None


async def _materialize_policy_results(
    session: AsyncSession,
    top_ids: list[str],
    *,
    rrf_scores: dict[str, float],
    query_vector: list[float] | None,
    dense_rank_map: dict[str, int],
    sparse_rank_map: dict[str, int],
    sparse_score_map: dict[str, float],
    sparse_backend_labels: set[str],
    sparse_fallback_used: bool,
    limit: int,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen_policy_keys: set[str] = set()

    for policy_id in top_ids:
        policy = await _get_policy(session, policy_id)
        if policy is None:
            continue
        dedupe_key = _build_policy_dedupe_key(policy.title, policy.agency_name)
        if dedupe_key in seen_policy_keys:
            continue
        seen_policy_keys.add(dedupe_key)
        chunk_text = await _get_relevant_chunk(session, policy.id, query_vector)
        results.append({
            "policy_id": str(policy.id),
            "title": policy.title,
            "agency_name": policy.agency_name,
            "ai_summary": policy.ai_summary or "",
            "support_amount_desc": policy.support_amount_desc or "",
            "support_type": policy.support_type or "",
            "category": policy.category or "",
            "max_support": policy.max_support,
            "region": policy.region or "전국",
            "end_date": policy.closed_at.isoformat() if policy.closed_at else "",
            "apply_url": policy.apply_url or "",
            "rrf_score": rrf_scores[policy_id],
            "dense_rank": dense_rank_map.get(policy_id),
            "sparse_rank": sparse_rank_map.get(policy_id),
            "sparse_score": sparse_score_map.get(policy_id),
            "retrieval_backend": _build_retrieval_backend_label(
                dense_rank_map.get(policy_id),
                sparse_rank_map.get(policy_id),
            ),
            "sparse_backend": _collapse_sparse_backend_labels(sparse_backend_labels),
            "sparse_fallback_used": sparse_fallback_used,
            "relevant_chunk": chunk_text,
            "_dedupe_key": dedupe_key,
        })
        if len(results) >= limit:
            break
    return results


def _merge_intent_result_sets(
    intent_results: list[dict[str, Any]],
    *,
    question: str,
    top_k: int,
) -> list[dict[str, Any]]:
    if not intent_results:
        return []

    if len(intent_results) == 1:
        return [_strip_internal_fields(item) for item in intent_results[0].get("results", [])[:top_k]]

    merged: list[dict[str, Any]] = []
    seen_policy_keys: set[str] = set()
    require_per_intent_minimum = _requires_per_intent_minimum(question) or len(intent_results) > 1

    if require_per_intent_minimum:
        for group in intent_results:
            for candidate in group.get("results", []):
                dedupe_key = candidate.get("_dedupe_key")
                if dedupe_key in seen_policy_keys:
                    continue
                seen_policy_keys.add(dedupe_key)
                merged.append(_strip_internal_fields(candidate))
                break

    result_pointers = {group["intent"]: 0 for group in intent_results}
    while len(merged) < top_k:
        best_candidate: dict[str, Any] | None = None
        best_group_intent: str | None = None
        best_score = -1.0

        for group in intent_results:
            group_results = group.get("results", [])
            cursor = result_pointers[group["intent"]]
            while cursor < len(group_results):
                candidate = group_results[cursor]
                if candidate.get("_dedupe_key") in seen_policy_keys:
                    cursor += 1
                    result_pointers[group["intent"]] = cursor
                    continue
                score = float(candidate.get("rrf_score") or 0.0)
                if score > best_score:
                    best_candidate = candidate
                    best_group_intent = group["intent"]
                    best_score = score
                break

        if best_candidate is None or best_group_intent is None:
            break

        seen_policy_keys.add(best_candidate.get("_dedupe_key"))
        merged.append(_strip_internal_fields(best_candidate))
        result_pointers[best_group_intent] += 1

    return merged[:top_k]


def _strip_internal_fields(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if not key.startswith("_")}


def _build_retrieval_backend_label(
    dense_rank: int | None,
    sparse_rank: int | None,
) -> str:
    if dense_rank is not None and sparse_rank is not None:
        return "dense+sparse"
    if dense_rank is not None:
        return "dense_only"
    if sparse_rank is not None:
        return "sparse_only"
    return "none"


def _collapse_sparse_backend_labels(sparse_backend_labels: set[str]) -> str | None:
    if not sparse_backend_labels:
        return None
    if len(sparse_backend_labels) == 1:
        return next(iter(sparse_backend_labels))
    return "mixed"


def _build_search_metadata(
    search_plan: list[SearchTask],
    intent_results: list[dict[str, Any]],
) -> dict[str, Any]:
    detected_intents = [task.intent_name for task in search_plan]
    rewritten_by_llm = any("LLM 재작성" in task.explanation for task in search_plan)
    return {
        "rewritten_by_llm": rewritten_by_llm,
        "detected_intents": detected_intents,
        "search_plan_count": len(search_plan),
        "multi_intent_mode": len(detected_intents) > 1,
        "intent_result_count": len(intent_results),
    }


def _requires_per_intent_minimum(question: str) -> bool:
    normalized_question = question.replace(" ", "")
    return any(marker.replace(" ", "") in normalized_question for marker in _PER_INTENT_QUOTA_MARKERS)


async def _vector_search(
    session: AsyncSession,
    query_vector: list[float],
    region_filter: str | None,
    *,
    limit: int,
) -> list[str]:
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

    min_dist = func.min(PolicyChunk.embedding.cosine_distance(query_vector)).label("min_dist")
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


async def _keyword_search_postgres(
    session: AsyncSession,
    keywords: list[str],
    region_filter: str | None,
    *,
    biz_info: dict[str, Any] | None = None,
    limit: int,
) -> list[dict[str, Any]]:
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

    keyword_clauses = []
    for kw in keywords[:8]:
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
        select(Policy)
        .where(*base_conditions, or_(*keyword_clauses))
        .order_by(Policy.view_count.desc())
        .limit(limit * 4)
    )
    result = await session.execute(stmt)
    policies = list(result.scalars().all())
    region_hint = _extract_region_hint(" ".join(keywords)) or region_filter
    broad_funding_query = _is_broad_funding_query(" ".join(keywords))
    ranked = sorted(
        policies,
        key=lambda policy: (
            _score_fts_candidate(
                policy,
                keywords,
                region_hint,
                biz_info=biz_info,
                broad_funding_query=broad_funding_query,
            ),
            policy.view_count,
        ),
        reverse=True,
    )
    return [
        {
            "policy_id": str(policy.id),
            "rank": rank,
            "score": float(policy.view_count or 0),
            "backend": "postgres_fallback",
        }
        for rank, policy in enumerate(ranked[:limit])
    ]


async def _sparse_search_elasticsearch(
    *,
    query_text: str,
    keywords: list[str],
    region_filter: str | None,
    biz_info: dict[str, Any] | None,
    limit: int,
) -> list[dict[str, Any]]:
    if not is_elasticsearch_enabled():
        raise RuntimeError("elasticsearch disabled")

    client = get_elasticsearch_client()
    searcher = ElasticsearchSparseSearcher(client)
    return await searcher.search(
        query_text=query_text,
        keywords=keywords,
        region_filter=region_filter,
        biz_info=biz_info,
        limit=limit,
    )


def _extract_keywords(text: str) -> list[str]:
    normalized_text = text.lower().strip()
    tokens = [
        token
        for token in re.split(r"[\s,?.!~+/]+", normalized_text)
        if _is_meaningful_token(token)
    ]

    expanded: list[str] = []
    for triggers, synonyms in _DOMAIN_SYNONYMS:
        if any(trigger in normalized_text for trigger in triggers):
            expanded.extend(synonyms)

    return _merge_keywords(expanded, tokens)[:_MAX_KEYWORDS]


def _detect_query_intents(text: str) -> list[str]:
    normalized_text = text.lower()
    detected: list[str] = []
    for intent_name, triggers, _ in _QUERY_INTENT_RULES:
        if any(trigger in normalized_text for trigger in triggers):
            detected.append(intent_name)
    return detected


def _rewrite_query_variants(
    text: str,
    *,
    biz_info: dict[str, Any] | None = None,
) -> list[str]:
    normalized_text = text.strip()
    intents = _detect_query_intents(normalized_text)
    rewritten_queries = [normalized_text]
    for intent_name, _, rewrite_terms in _QUERY_INTENT_RULES:
        if intent_name not in intents:
            continue
        rewritten_queries.append(f"{normalized_text} {' '.join(rewrite_terms)}")

    if biz_info and _is_broad_funding_query(normalized_text):
        context_terms = _build_business_context_terms(biz_info)
        if context_terms:
            rewritten_queries.append(f"{' '.join(context_terms)} {normalized_text}")

    ordered_queries: list[str] = []
    for query in rewritten_queries:
        compact = " ".join(query.split())
        if compact and compact not in ordered_queries:
            ordered_queries.append(compact)
    return ordered_queries


def _is_broad_funding_query(text: str) -> bool:
    normalized_text = text.lower()
    funding_markers = ("정책자금", "지원자금", "운전자금", "대출", "융자", "보증금")
    broad_markers = ("뭐", "뭐야", "있어", "있을까", "추천", "받을 수", "가능", "알려")
    return any(marker in normalized_text for marker in funding_markers) and any(
        marker in normalized_text for marker in broad_markers
    )


def _build_business_context_terms(biz_info: dict[str, Any]) -> list[str]:
    terms: list[str] = []

    region_sido = biz_info.get("region_sido")
    if region_sido:
        terms.append(str(region_sido))

    terms.append("소상공인")

    funding_purpose = str(biz_info.get("funding_purpose") or "").upper()
    if funding_purpose in {"OPERATING", "WORKING", "MIXED"}:
        terms.append("운영자금")

    if _is_early_stage_business(biz_info.get("establishment_date")):
        terms.extend(["초기창업", "창업자금"])

    return _merge_keywords(terms)


def _is_early_stage_business(
    establishment_date: str | date | None,
    *,
    today: date | None = None,
) -> bool:
    opened_at = _parse_establishment_date(establishment_date)
    if opened_at is None:
        return False

    base_date = today or date.today()
    elapsed_months = (base_date.year - opened_at.year) * 12 + (base_date.month - opened_at.month)
    if base_date.day < opened_at.day:
        elapsed_months -= 1
    return elapsed_months <= 36


def _parse_establishment_date(value: str | date | None) -> date | None:
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _extract_region_hint(text: str) -> str | None:
    for region in _REGION_HINTS:
        if region in text:
            return region
    for alias, region in _REGION_HINT_ALIASES.items():
        if alias in text:
            return region
    return None


def _score_text_match(text: str, keywords: list[str]) -> int:
    normalized = text.lower()
    score = 0
    for keyword in keywords:
        lowered = keyword.lower()
        if lowered in normalized:
            score += 1
    return score


def _score_fts_candidate(
    policy: Policy,
    keywords: list[str],
    region_hint: str | None,
    *,
    biz_info: dict[str, Any] | None = None,
    broad_funding_query: bool = False,
) -> int:
    title = policy.title or ""
    summary = policy.ai_summary or ""
    explanation = policy.ai_full_explanation or ""
    region = policy.region or ""

    score = 0
    score += _score_text_match(title, keywords) * 5
    score += _score_text_match(summary, keywords) * 3
    score += _score_text_match(explanation, keywords)

    if region_hint:
        if region_hint in region:
            score += 6
        elif "전국" in region:
            score += 2

    joined_title = f"{title} {summary}".lower()
    if any(keyword.lower() in joined_title for keyword in keywords[:2]):
        score += 2

    score += _score_business_context_match(policy, biz_info)
    if broad_funding_query:
        score += _score_broad_funding_match(policy)
    return score


def _score_broad_funding_match(policy: Policy) -> int:
    haystack = " ".join(
        filter(
            None,
            [
                policy.title,
                policy.category,
                policy.support_type,
                policy.ai_summary,
            ],
        )
    ).lower()

    score = 0
    if any(keyword in haystack for keyword in ("운전자금", "운영자금", "정책자금")):
        score += 4
    if "소상공인" in haystack:
        score += 2
    return score


def _score_business_context_match(
    policy: Policy,
    biz_info: dict[str, Any] | None,
) -> int:
    if not biz_info:
        return 0

    score = 0
    logic = parse_target_logic(getattr(policy, "target_logic", None))
    haystack = " ".join(
        filter(
            None,
            [
                policy.title,
                policy.category,
                policy.support_type,
                policy.region,
                policy.ai_summary,
                policy.ai_full_explanation,
            ],
        )
    ).lower()

    region_sido = str(biz_info.get("region_sido") or "")
    if logic is not None and logic.region_restricted and logic.allowed_regions:
        if _biz_region_matches(region_sido, logic.allowed_regions):
            score += 6
        else:
            score -= 8
    elif region_sido:
        if region_sido.lower() in haystack:
            score += 3
        elif "전국" in haystack:
            score += 1

    if logic is not None and logic.sectors:
        if _biz_sector_matches(biz_info, logic.sectors):
            score += 5
        else:
            score -= 6

    if _biz_funding_purpose_matches(biz_info, haystack):
        score += 4

    if _is_early_stage_business(biz_info.get("establishment_date")):
        if "초기창업" in haystack or "창업" in haystack:
            score += 3

    if logic is not None and logic.require_ventured and not bool(biz_info.get("is_ventured")):
        score -= 6
    if logic is not None and logic.require_patent and not bool(biz_info.get("has_patent")):
        score -= 6

    return score


def _biz_region_matches(region_sido: str, allowed_regions: list[str]) -> bool:
    normalized_region = region_sido.lower().strip()
    if not normalized_region:
        return False
    return any(normalized_region in str(item).lower() for item in allowed_regions)


def _biz_sector_matches(biz_info: dict[str, Any], sectors: list[str]) -> bool:
    raw_tokens = [
        str(biz_info.get("ksic_code") or ""),
        str(biz_info.get("ksic_name") or ""),
        str(biz_info.get("sector_code") or ""),
    ]
    haystack = " ".join(token.lower() for token in raw_tokens if token)
    normalized_biz_tokens = {_normalize_sector_token(token) for token in raw_tokens if token}

    for sector in sectors:
        lowered = str(sector).lower()
        if lowered and lowered in haystack:
            return True
        if _normalize_sector_token(str(sector)) in normalized_biz_tokens:
            return True
    return False


def _biz_funding_purpose_matches(biz_info: dict[str, Any], haystack: str) -> bool:
    purpose_keywords = {
        "FACILITY": ("시설", "설비", "장비"),
        "OPERATING": ("운영", "경영", "고정비", "관리비", "수도비", "공과금"),
        "WORKING": ("운전자금", "자재", "원자재", "재료비", "인건비"),
        "MIXED": ("자금", "운영", "시설"),
    }
    funding_purpose = str(biz_info.get("funding_purpose") or "").upper()
    keywords = purpose_keywords.get(funding_purpose, ())
    return any(keyword in haystack for keyword in keywords)


def _normalize_sector_token(value: str) -> str:
    text = value.strip().lower()
    alias_map = {
        "service": "service",
        "서비스": "service",
        "컨설팅": "service",
        "제조": "manufacturing",
        "manufacturing": "manufacturing",
        "금속": "manufacturing",
        "기계": "manufacturing",
        "it": "it",
        "기술": "it",
        "프로그램": "it",
        "소프트웨어": "it",
        "관광": "tourism",
        "숙박": "tourism",
        "호텔": "tourism",
        "retail": "retail",
        "판매": "retail",
        "도매": "retail",
        "유통": "retail",
        "food": "food",
        "외식": "food",
        "카페": "food",
        "급식": "food",
    }
    for keyword, normalized in alias_map.items():
        if keyword in text:
            return normalized
    return text


def _is_meaningful_token(token: str) -> bool:
    stripped = re.sub(r"[^\w가-힣]", "", token).strip()
    if len(stripped) < 2:
        return False
    if stripped in _STOPWORDS:
        return False
    if stripped.isdigit():
        return False
    return True


def _merge_keywords(*keyword_groups: list[str]) -> list[str]:
    ordered: list[str] = []
    for group in keyword_groups:
        for keyword in group:
            normalized = re.sub(r"[^\w가-힣]", "", keyword).strip()
            if not normalized or normalized in ordered:
                continue
            ordered.append(normalized)
    return ordered


def _build_policy_dedupe_key(title: str | None, agency_name: str | None) -> str:
    normalized_title = _normalize_dedupe_text(title)
    normalized_agency = _normalize_dedupe_text(agency_name)
    return f"{normalized_title}::{normalized_agency}"


def _normalize_dedupe_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKC", value).lower().strip()
    normalized = re.sub(r"\s+", "", normalized)
    normalized = re.sub(r"[^\w가-힣]", "", normalized)
    return normalized


async def _get_policy(session: AsyncSession, policy_id: str) -> Policy | None:
    stmt = select(Policy).where(Policy.id == uuid.UUID(policy_id))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _get_relevant_chunk(
    session: AsyncSession,
    policy_id: uuid.UUID,
    query_vector: list[float] | None,
) -> str:
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
