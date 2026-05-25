from src.app.agents.biz_mong.tools.policy_rag import _extract_keywords


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
