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
from datetime import date
from typing import Any
import unicodedata

from openai import AsyncOpenAI
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import OPENAI_API_KEY
from src.app.domains.policy.model import Policy, PolicyChunk, PolicyStatus
from src.app.domains.policy.target_logic import parse_target_logic

logger = logging.getLogger(__name__)

_EMBEDDING_MODEL = "text-embedding-3-small"
_RRF_K = 60          # RRF 표준 상수
_VECTOR_LIMIT = 20   # 벡터 검색 후보 수
_FTS_LIMIT = 20      # FTS 후보 수
_FINAL_LIMIT = 5     # 최종 반환 개수
_MAX_KEYWORDS = 8

_STOPWORDS = {
    "이",
    "가",
    "을",
    "를",
    "은",
    "는",
    "에",
    "의",
    "도",
    "좀",
    "저",
    "제",
    "뭐",
    "문의",
    "관련",
    "있나",
    "있어요",
    "있을까",
    "주세요",
    "알려줘",
    "알려주세요",
    "궁금해",
    "궁금합니다",
}

_DOMAIN_SYNONYMS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (
        ("운영비", "고정비", "월세", "임대료", "인건비", "관리비", "유지비", "재료비", "식자재", "원자재", "공과금"),
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
    "제주도": "제주",
}

_QUERY_INTENT_RULES: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    (
        "operating_cost",
        (
            "월세",
            "임대료",
            "전기세",
            "가스비",
            "고정비",
            "운영비",
            "관리비",
            "유지비",
            "재료비",
            "식자재",
            "원자재값",
            "공과금",
            "버티기",
            "팍팍",
            "빠듯",
            "버거",
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
        ("시설자금", "설비", "제조업", "자동화", "스마트공장"),
    ),
    (
        "startup",
        ("창업", "초기", "업력", "스타트업", "예비창업"),
        ("초기창업", "창업자금", "창업지원", "사업화"),
    ),
    (
        "export",
        ("수출", "해외", "판로", "바이어"),
        ("수출", "해외진출", "판로", "마케팅"),
    ),
)


async def policy_rag_search(
    query_text: str,
    session: AsyncSession,
    *,
    region_filter: str | None = None,
    biz_info: dict[str, Any] | None = None,
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
    # 생활어 질문은 그대로 검색하면 후보가 너무 넓게 퍼지기 쉬워서
    # 검색용 질의를 몇 개로 다시 써 본 뒤 FTS 결과를 합친다.
    rewritten_queries = _rewrite_query_variants(query_text, biz_info=biz_info)
    fts_ids: list[str] = []
    seen_fts_ids: set[str] = set()
    for rewritten_query in rewritten_queries:
        keywords = _extract_keywords(rewritten_query)
        candidate_ids = await _fts_search(
            session,
            keywords,
            region_filter,
            biz_info=biz_info,
            limit=_FTS_LIMIT,
        )
        for candidate_id in candidate_ids:
            if candidate_id in seen_fts_ids:
                continue
            seen_fts_ids.add(candidate_id)
            fts_ids.append(candidate_id)

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

    top_ids = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)[: max(top_k * 3, top_k)]

    # ── Step 5: 정책 상세 조회 ────────────────────────────────────────────
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
        if len(results) >= top_k:
            break

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
    biz_info: dict[str, Any] | None = None,
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
    for kw in keywords[:8]:  # 재작성 질의에서 붙인 문맥 키워드까지 후보 필터에 반영한다.
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
    return [str(policy.id) for policy in ranked[:limit]]


def _extract_keywords(text: str) -> list[str]:
    """자연어 질문에서 검색 키워드를 추출한다.

    한국어 공백 분리 후 2글자 이상, 불용어 제거.
    """
    # 사용자가 "가게 보증금", "월급 지원"처럼 생활 언어로 묻더라도
    # 검색기는 정책 문서에 가까운 단어(운전자금, 고용지원 등)로 확장해서 찾는다.
    normalized_text = text.lower().strip()
    tokens = [
        token
        for token in re.split(r"[\s,?.!~]+", normalized_text)
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
        # 원문을 버리지 않고 확장 질의를 덧붙여야
        # 질문의 말투와 정책 문서 어휘를 둘 다 살릴 수 있다.
        rewritten_queries.append(f"{normalized_text} {' '.join(rewrite_terms)}")

    if biz_info and _is_broad_funding_query(normalized_text):
        context_terms = _build_business_context_terms(biz_info)
        if context_terms:
            rewritten_queries.append(f"{' '.join(context_terms)} {normalized_text}")

    ordered_queries: list[str] = []
    for query in rewritten_queries:
        compact = " ".join(query.split())
        if not compact or compact in ordered_queries:
            continue
        ordered_queries.append(compact)
    return ordered_queries


def _is_broad_funding_query(text: str) -> bool:
    normalized_text = text.lower()
    funding_markers = ("정책자금", "지원금", "운전자금", "대출", "융자", "보증금")
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
    """넓은 정책자금 질문에서는 자금 성격이 보이는 후보를 조금 더 앞세운다."""
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
        "OPERATING": ("운영", "경영", "고정비", "관리비", "유지비", "공과금"),
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
        "도매": "retail",
        "소매": "retail",
        "유통": "retail",
        "food": "food",
        "음식": "food",
        "카페": "food",
        "요식": "food",
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
