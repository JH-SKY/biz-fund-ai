from types import SimpleNamespace

from src.app.scripts.evaluate_bizmong_quality import (
    _build_error_row,
    _classify_runner_error,
    _normalize_database_url_for_asyncpg,
    _evaluate,
    _parse_args,
    _select_cases,
    _summarize,
)


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
                "response_metadata": {"is_fallback": False},
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
                "response_metadata": {"is_fallback": True},
            },
        ],
        planned_total=3,
        aborted_reason="database offline",
    )

    assert summary["passed"] == 1
    assert summary["total"] == 2
    assert summary["pass_rate"] == 50.0
    assert summary["route_accuracy"] == 100.0
    assert summary["policy_accuracy"] == 50.0
    assert summary["keyword_accuracy"] == 50.0
    assert summary["fallback_count"] == 1
    assert summary["fallback_rate"] == 50.0
    assert summary["latency_avg_ms"] == 200.0
    assert summary["latency_p95_ms"] == 100.0
    assert summary["planned_total"] == 3
    assert summary["aborted"] is True
    assert summary["aborted_reason"] == "database offline"
    assert summary["failed_cases"][0]["failure_reasons"] == [
        "policy_mismatch",
        "keyword_mismatch",
    ]


def test_select_cases_filters_by_scenario_and_limit():
    cases = _select_cases(scenario_key="BIZ-01", contains=None, limit=2)

    assert len(cases) == 2
    assert all(case.scenario_key == "BIZ-01" for case in cases)


def test_parse_args_reads_database_url_option(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            "evaluate_bizmong_quality.py",
            "--scenario",
            "BIZ-01",
            "--database-url",
            "postgresql+asyncpg://biz_user:biz_password@localhost:5432/biz_fund_ai",
        ],
    )

    args = _parse_args()

    assert args.scenario_key == "BIZ-01"
    assert args.database_url == "postgresql+asyncpg://biz_user:biz_password@localhost:5432/biz_fund_ai"


def test_build_error_row_marks_runner_error_case():
    case = SimpleNamespace(
        scenario_key="BIZ-01",
        question="내가 받을 수 있는 정책자금 뭐야?",
        expected_route="rag",
        expected_policies=("전국 소상공인 운전자금",),
        expected_answer_keywords=("운전자금", "정책"),
        note="환경 오류 테스트",
    )

    row = _build_error_row(case, RuntimeError("database offline"))

    assert row["actual_route"] == "runner_error"
    assert row["passed"] is False
    assert row["failure_reasons"] == ["runner_error"]
    assert row["missing_policies"] == ["전국 소상공인 운전자금"]
    assert row["missing_keywords"] == ["운전자금", "정책"]
    assert row["content_preview"] == "database offline"


def test_classify_runner_error_marks_infra_unavailable():
    assert _classify_runner_error("(ENOTFOUND) postgres host not found") == "infra_unavailable"
    assert _classify_runner_error("connection was closed in the middle of operation") == "infra_unavailable"
    assert _classify_runner_error("database offline") == "runner_error"


def test_normalize_database_url_for_asyncpg_strips_driver_name():
    assert (
        _normalize_database_url_for_asyncpg(
            "postgresql+asyncpg://biz_user:biz_password@localhost:5432/biz_fund_ai"
        )
        == "postgresql://biz_user:biz_password@localhost:5432/biz_fund_ai"
    )
