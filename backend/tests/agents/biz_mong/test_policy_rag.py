from types import SimpleNamespace

from src.app.agents.biz_mong.tools.policy_rag import (
    _extract_keywords,
    _extract_region_hint,
    _score_fts_candidate,
)


def test_extract_keywords_expands_operating_cost_queries_into_policy_terms():
    keywords = _extract_keywords("요즘 월세랑 인건비가 너무 부담인데 운영비 도와주는 정책 있을까?")

    assert "운영자금" in keywords
    assert "소상공인" in keywords
    assert "지원금" in keywords
    assert "월세랑" in keywords
    assert "인건비가" in keywords


def test_extract_keywords_expands_hiring_and_loan_intents_without_duplicates():
    keywords = _extract_keywords("직원 채용 때문에 대출이나 보증 쪽도 같이 알아보고 싶어요")

    assert "고용" in keywords
    assert "고용지원" in keywords
    assert "정책자금" in keywords
    assert keywords.count("지원금") == 1


def test_extract_keywords_filters_noise_and_limits_result_size():
    keywords = _extract_keywords(
        "이거 관련해서 좀 알려주세요. 2026년에 서울에서 창업하고 수출도 하려는데 뭐가 있을까요?"
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
    )
    weak_match = SimpleNamespace(
        title="전국 혁신기업 오픈이노베이션 모집",
        ai_summary="전국 단위 사업화 프로그램",
        ai_full_explanation="창업이라는 표현은 있으나 자금 지원과 거리가 있습니다.",
        region="전국",
    )

    assert _score_fts_candidate(strong_match, keywords, "서울") > _score_fts_candidate(
        weak_match,
        keywords,
        "서울",
    )
