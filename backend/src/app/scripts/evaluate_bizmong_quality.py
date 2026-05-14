from __future__ import annotations

import asyncio
import json

import httpx

from src.app.dev.bizmong_eval_cases import EVAL_CASES
from src.app.main import app


async def _run_case(client: httpx.AsyncClient, scenario_key: str, question: str) -> dict:
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

    response = await client.post(
        f"/api/v1/chats/sessions/{session_id}/agent-message",
        headers=headers,
        json={"message": question},
    )
    data = response.json()["data"]
    return {
        "scenario_key": scenario_key,
        "business_name": biz["biz_name"],
        "question": question,
        "agent_type": data.get("agent_type"),
        "content": data.get("content") or "",
        "rag_titles": [item.get("title") for item in (data.get("rag_results") or [])],
        "stats_insight": data.get("stats_insight") or {},
    }


def _evaluate(result: dict, expected_route: str, expected_policies: tuple[str, ...], expected_keywords: tuple[str, ...]) -> dict:
    route_ok = result["agent_type"] == expected_route
    policy_ok = True
    if expected_policies:
        policy_ok = any(
            expected_policy in " ".join(result["rag_titles"])
            for expected_policy in expected_policies
        )
    keyword_ok = all(keyword in result["content"] for keyword in expected_keywords) if expected_keywords else True
    return {
        "route_ok": route_ok,
        "policy_ok": policy_ok,
        "keyword_ok": keyword_ok,
        "passed": route_ok and policy_ok and keyword_ok,
    }


async def main() -> None:
    transport = httpx.ASGITransport(app=app)
    summary: list[dict] = []

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", timeout=120.0) as client:
        for case in EVAL_CASES:
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
                "note": case.note,
                "content_preview": result["content"][:240],
            }
            summary.append(row)
            print(json.dumps(row, ensure_ascii=False))

    passed = sum(1 for row in summary if row["passed"])
    total = len(summary)
    print()
    print(json.dumps({"passed": passed, "total": total, "pass_rate": round((passed / total) * 100, 1)}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
