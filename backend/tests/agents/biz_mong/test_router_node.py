from src.app.agents.biz_mong.nodes.router_node import _classify_by_keyword


def test_keyword_fallback_routes_greeting_messages():
    assert _classify_by_keyword("안녕 비즈몽") == "greeting"


def test_keyword_fallback_routes_policy_recommendation_questions_to_rag():
    assert _classify_by_keyword("내가 받을 수 있는 정책자금 뭐야?") == "rag"
    assert _classify_by_keyword("서울 초기창업 지원자금은 왜 추천돼?") == "rag"
    assert _classify_by_keyword("내 사업에 맞는 정책 추천해줘") == "rag"
    assert _classify_by_keyword("가스비랑 전기세가 너무 올라서 나라에서 보태주는 거 없나?") == "rag"
    assert _classify_by_keyword("직원 한 명 더 뽑으려고 하는데 고용지원금이 있나?") == "rag"


def test_keyword_fallback_routes_stats_questions_to_stats():
    assert _classify_by_keyword("동종업계 평균 매출과 비교해줘") == "stats"


def test_keyword_fallback_keeps_general_qa_for_non_search_questions():
    assert _classify_by_keyword("직원 1명 더 뽑으면 유리해져?") == "general_qa"
