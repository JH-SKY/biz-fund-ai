from src.app.scripts.evaluate_bizmong_quality import _evaluate, _select_cases, _summarize


def test_evaluate_reports_missing_policy_and_keyword_reasons():
    result = {
        "agent_type": "general_qa",
        "rag_titles": ["서울 초기창업 지원자금"],
        "content": "정책 설명만 있습니다.",
    }

    evaluation = _evaluate(
        result,
        expected_route="rag",
        expected_policies=("경기 소상공인 운영자금",),
        expected_keywords=("대출", "정책"),
    )

    assert evaluation["passed"] is False
    assert evaluation["route_ok"] is False
    assert evaluation["policy_ok"] is False
    assert evaluation["keyword_ok"] is False
    assert evaluation["missing_policies"] == ["경기 소상공인 운영자금"]
    assert evaluation["missing_keywords"] == ["대출"]
    assert evaluation["failure_reasons"] == [
        "route_mismatch",
        "policy_mismatch",
        "keyword_mismatch",
    ]


def test_summarize_returns_accuracy_and_latency_breakdown():
    summary = _summarize(
        [
            {
                "question": "q1",
                "passed": True,
                "route_ok": True,
                "policy_ok": True,
                "keyword_ok": True,
                "response_ms": 100.0,
                "failure_reasons": [],
                "actual_route": "rag",
            },
            {
                "question": "q2",
                "passed": False,
                "route_ok": True,
                "policy_ok": False,
                "keyword_ok": False,
                "response_ms": 300.0,
                "failure_reasons": ["policy_mismatch", "keyword_mismatch"],
                "actual_route": "rag",
            },
        ]
    )

    assert summary["passed"] == 1
    assert summary["total"] == 2
    assert summary["pass_rate"] == 50.0
    assert summary["route_accuracy"] == 100.0
    assert summary["policy_accuracy"] == 50.0
    assert summary["keyword_accuracy"] == 50.0
    assert summary["latency_avg_ms"] == 200.0
    assert summary["latency_p95_ms"] == 100.0
    assert summary["failed_cases"][0]["failure_reasons"] == [
        "policy_mismatch",
        "keyword_mismatch",
    ]


def test_select_cases_filters_by_scenario_and_limit():
    cases = _select_cases(scenario_key="BIZ-01", contains=None, limit=2)

    assert len(cases) == 2
    assert all(case.scenario_key == "BIZ-01" for case in cases)
