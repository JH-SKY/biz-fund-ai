from datetime import date
from types import SimpleNamespace

from src.app.agents.biz_mong.tools.policy_rag import (
    _build_business_context_terms,
    _detect_query_intents,
    _extract_keywords,
    _extract_region_hint,
    _is_early_stage_business,
    _rewrite_query_variants,
    _score_fts_candidate,
)


def test_extract_keywords_expands_operating_cost_queries_into_policy_terms():
    keywords = _extract_keywords("요즘 월세랑 인건비가 너무 부담인데 운영비 지원해 주는 정책 있을까")

    assert "운영자금" in keywords
    assert "소상공인" in keywords
    assert "지원금" in keywords
    assert any(token.startswith("월세") for token in keywords)
    assert any(token.startswith("인건비") for token in keywords)


def test_extract_keywords_expands_hiring_and_loan_intents_without_duplicates():
    keywords = _extract_keywords("직원 채용 때문에 대출이나 보증 쪽도 같이 알아보고 싶어요")

    assert "고용" in keywords
    assert "고용지원" in keywords
    assert "정책자금" in keywords
    assert keywords.count("지원금") == 1


def test_extract_keywords_filters_noise_and_limits_result_size():
    keywords = _extract_keywords(
        "이거 관련해서 좀 알려주세요 2026년에 서울에서 창업하고 수출도 해보려는데 뭐가 있을까요?"
    )

    assert "관련해서" in keywords
    assert "알려주세요" not in keywords
    assert "창업" in keywords
    assert "수출" in keywords
    assert len(keywords) <= 8


def test_extract_region_hint_finds_explicit_region_name():
    assert _extract_region_hint("서울에서 받을 수 있는 창업 지원이 있을까요?") == "서울"
    assert _extract_region_hint("지역 언급 없이 물어보는 질문") is None


def test_score_fts_candidate_prefers_region_and_title_keyword_overlap():
    keywords = ["서울", "창업", "지원자금"]
    strong_match = SimpleNamespace(
        title="서울 초기창업 지원자금",
        ai_summary="서울 창업 기업 대상 정책자금 지원",
        ai_full_explanation="서울 소재 초기창업 기업이 신청할 수 있는 자금입니다.",
        region="서울",
        category="창업지원",
        support_type="운영자금",
        target_logic=None,
    )
    weak_match = SimpleNamespace(
        title="전국 혁신기업 스케일업 모집",
        ai_summary="전국 사업장 대상 프로그램",
        ai_full_explanation="창업이라는 표현은 있으나 자금 지원과 거리가 있습니다.",
        region="전국",
        category="사업화",
        support_type="프로그램",
        target_logic=None,
    )

    assert _score_fts_candidate(strong_match, keywords, "서울") > _score_fts_candidate(
        weak_match,
        keywords,
        "서울",
    )


def test_detect_query_intents_handles_mixed_operating_and_hiring_signals():
    intents = _detect_query_intents("월세랑 직원 월급이 같이 부담돼서 버티기 힘들어요")

    assert "operating_cost" in intents
    assert "hiring" in intents


def test_rewrite_query_variants_adds_search_friendly_expansions():
    variants = _rewrite_query_variants("요즘 전기세랑 월세가 너무 올라서 버티기 힘들어요")

    assert variants[0] == "요즘 전기세랑 월세가 너무 올라서 버티기 힘들어요"
    assert any("운영자금" in variant for variant in variants)
    assert any("정책자금" in variant for variant in variants)


def test_build_business_context_terms_collects_region_stage_and_funding_hints():
    terms = _build_business_context_terms(
        {
            "region_sido": "서울",
            "funding_purpose": "OPERATING",
            "establishment_date": "2025-03-15",
        }
    )

    assert "서울" in terms
    assert "소상공인" in terms
    assert "운영자금" in terms
    assert "초기창업" in terms


def test_is_early_stage_business_uses_36_month_cutoff():
    assert _is_early_stage_business("2025-03-15", today=date(2026, 5, 28)) is True
    assert _is_early_stage_business("2021-03-15", today=date(2026, 5, 28)) is False


def test_rewrite_query_variants_adds_business_context_for_broad_funding_question():
    variants = _rewrite_query_variants(
        "내가 받을 수 있는 정책자금 뭐야?",
        biz_info={
            "region_sido": "서울",
            "funding_purpose": "OPERATING",
            "establishment_date": "2025-03-15",
        },
    )

    assert any("서울" in variant for variant in variants[1:])
    assert any("운영자금" in variant for variant in variants[1:])
    assert any("초기창업" in variant for variant in variants[1:])


def test_score_fts_candidate_prefers_business_context_matched_policy():
    keywords = ["정책자금", "서울", "운영자금"]
    biz_info = {
        "region_sido": "서울",
        "ksic_name": "카페",
        "sector_code": "FOOD",
        "funding_purpose": "OPERATING",
        "establishment_date": "2025-03-15",
        "is_ventured": False,
        "has_patent": False,
    }
    matched_policy = SimpleNamespace(
        title="서울 초기창업 지원자금",
        ai_summary="서울 소상공인 창업 안정화용 정책자금",
        ai_full_explanation="운영자금과 소상공인, 초기창업 설명을 포함합니다.",
        region="서울",
        category="창업지원",
        support_type="운영자금",
        target_logic={"allowed_regions": ["서울"], "region_restricted": True, "sectors": ["food"]},
    )
    mismatched_policy = SimpleNamespace(
        title="2026 예술산업 금융지원 시범사업",
        ai_summary="예술시설 설비를 기반으로 한 사업장을 대상으로 하는 융자",
        ai_full_explanation="예술 업종과 초기창업이 아닌 경우가 많습니다.",
        region="전국",
        category="예술지원",
        support_type="시설자금",
        target_logic={"allowed_regions": ["부산"], "region_restricted": True, "sectors": ["예술"], "require_patent": True},
    )

    assert _score_fts_candidate(
        matched_policy,
        keywords,
        "서울",
        biz_info=biz_info,
    ) > _score_fts_candidate(
        mismatched_policy,
        keywords,
        "서울",
        biz_info=biz_info,
    )
