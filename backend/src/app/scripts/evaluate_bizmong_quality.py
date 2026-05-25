"""비즈몽 질문셋을 자동 실행해 라우팅/정책/답변 키워드를 검증한다.

감으로 "잘 되는 것 같다"를 판단하지 않기 위해
시나리오 계정으로 실제 API 흐름을 따라가며 pass/fail 을 집계한다.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time

import httpx

from src.app.dev.bizmong_eval_cases import EVAL_CASES
from src.app.main import app


async def _run_case(client: httpx.AsyncClient, scenario_key: str, question: str) -> dict:
    """평가 케이스 1건을 실제 로그인/세션 생성/API 호출 순서대로 실행한다."""
    login = await client.post("/api/v1/auth/dev-login", json={"scenario_key": scenario_key})
    token = login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = await client.get("/api/v1/businesses/me", headers=headers)
    biz = me.json()["data"]
    headers["X-Business-Id"] = biz["biz_id"]

    session = await client.post(
        "/api/v1/chats/sessions",
        headers=headers,
        json={"initial_message": "quality eval"},
    )
    session_id = session.json()["data"]["session_id"]

    started_at = time.perf_counter()
    response = await client.post(
        f"/api/v1/chats/sessions/{session_id}/agent-message",
        headers=headers,
        json={"message": question},
    )
    elapsed_ms = round((time.perf_counter() - started_at) * 1000, 1)
    data = response.json()["data"]
    return {
        "scenario_key": scenario_key,
        "business_name": biz["biz_name"],
        "question": question,
        "agent_type": data.get("agent_type"),
        "content": data.get("content") or "",
        "rag_titles": [item.get("title") for item in (data.get("rag_results") or [])],
        "stats_insight": data.get("stats_insight") or {},
        "response_ms": elapsed_ms,
    }


def _evaluate(result: dict, expected_route: str, expected_policies: tuple[str, ...], expected_keywords: tuple[str, ...]) -> dict:
    """실행 결과가 기대 라우팅/정책/핵심 키워드를 만족하는지 판정한다."""
    route_ok = result["agent_type"] == expected_route
    policy_ok = True
    missing_policies: list[str] = []
    if expected_policies:
        joined_titles = " ".join(result["rag_titles"])
        missing_policies = [
            expected_policy
            for expected_policy in expected_policies
            if expected_policy not in joined_titles
        ]
        policy_ok = len(missing_policies) < len(expected_policies)
    missing_keywords = [
        keyword for keyword in expected_keywords if keyword not in result["content"]
    ]
    keyword_ok = not missing_keywords if expected_keywords else True
    failure_reasons: list[str] = []
    if not route_ok:
        failure_reasons.append("route_mismatch")
    if not policy_ok:
        failure_reasons.append("policy_mismatch")
    if not keyword_ok:
        failure_reasons.append("keyword_mismatch")
    return {
        "route_ok": route_ok,
        "policy_ok": policy_ok,
        "keyword_ok": keyword_ok,
        "passed": route_ok and policy_ok and keyword_ok,
        "missing_policies": missing_policies,
        "missing_keywords": missing_keywords,
        "failure_reasons": failure_reasons,
    }


def _summarize(rows: list[dict]) -> dict:
    total = len(rows)
    passed = sum(1 for row in rows if row["passed"])
    route_ok = sum(1 for row in rows if row["route_ok"])
    policy_ok = sum(1 for row in rows if row["policy_ok"])
    keyword_ok = sum(1 for row in rows if row["keyword_ok"])
    latencies = [row["response_ms"] for row in rows]
    failed_cases = [
        {
            "question": row["question"],
            "failure_reasons": row["failure_reasons"],
            "actual_route": row["actual_route"],
        }
        for row in rows
        if not row["passed"]
    ]

    latency_avg = round(statistics.mean(latencies), 1) if latencies else 0.0
    latency_p95 = (
        round(sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)], 1)
        if latencies
        else 0.0
    )
    return {
        "passed": passed,
        "total": total,
        "pass_rate": round((passed / total) * 100, 1) if total else 0.0,
        "route_accuracy": round((route_ok / total) * 100, 1) if total else 0.0,
        "policy_accuracy": round((policy_ok / total) * 100, 1) if total else 0.0,
        "keyword_accuracy": round((keyword_ok / total) * 100, 1) if total else 0.0,
        "latency_avg_ms": latency_avg,
        "latency_p95_ms": latency_p95,
        "failed_cases": failed_cases,
    }


def _select_cases(
    *,
    scenario_key: str | None,
    contains: str | None,
    limit: int | None,
) -> list:
    cases = list(EVAL_CASES)
    if scenario_key:
        cases = [case for case in cases if case.scenario_key == scenario_key]
    if contains:
        cases = [case for case in cases if contains in case.question]
    if limit is not None:
        cases = cases[:limit]
    return cases


async def main(
    *,
    scenario_key: str | None = None,
    contains: str | None = None,
    limit: int | None = None,
) -> None:
    """전체 질문셋을 돌며 JSON 라인 로그와 최종 통계를 출력한다."""
    transport = httpx.ASGITransport(app=app)
    summary: list[dict] = []
    cases = _select_cases(
        scenario_key=scenario_key,
        contains=contains,
        limit=limit,
    )

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", timeout=120.0) as client:
        for case in cases:
            result = await _run_case(client, case.scenario_key, case.question)
            evaluation = _evaluate(
                result,
                case.expected_route,
                case.expected_policies,
                case.expected_answer_keywords,
            )
            row = {
                "scenario_key": case.scenario_key,
                "business_name": result["business_name"],
                "question": case.question,
                "expected_route": case.expected_route,
                "actual_route": result["agent_type"],
                "expected_policies": list(case.expected_policies),
                "actual_policies": result["rag_titles"],
                "passed": evaluation["passed"],
                "route_ok": evaluation["route_ok"],
                "policy_ok": evaluation["policy_ok"],
                "keyword_ok": evaluation["keyword_ok"],
                "missing_policies": evaluation["missing_policies"],
                "missing_keywords": evaluation["missing_keywords"],
                "failure_reasons": evaluation["failure_reasons"],
                "note": case.note,
                "content_preview": result["content"][:240],
                "response_ms": result["response_ms"],
                "rag_result_count": len(result["rag_titles"]),
            }
            summary.append(row)
            print(json.dumps(row, ensure_ascii=False))

    summary_row = _summarize(summary)
    print()
    print(json.dumps(summary_row, ensure_ascii=False))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="BizMong quality evaluation runner")
    parser.add_argument("--scenario", dest="scenario_key")
    parser.add_argument("--contains")
    parser.add_argument("--limit", type=int)
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(
        main(
            scenario_key=args.scenario_key,
            contains=args.contains,
            limit=args.limit,
        )
    )
