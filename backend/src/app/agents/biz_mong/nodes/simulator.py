# src/app/agents/biz_mong/nodes/simulator.py
"""Node 3: Simulation Engine — 가상 변수 수정 시 진단 점수 변화 시뮬레이션.

[가드 로직]:
  diagnosis_report 가 비어 있으면 시뮬레이션 의미가 없으므로,
  hard_filter 노드로 선행 리다이렉트한다.
  - pending_intent = "simulator" 를 State 에 저장
  - LangGraph Command(goto="hard_filter") 반환
  - llm_evaluator 완료 후 pending_intent 감지 → 자동으로 이 노드로 복귀

시뮬레이션 대상 변수:
  employee_count, annual_revenue, is_ventured, has_patent

출력 형식:
  {
    "original_score": float,
    "virtual_score":  float,
    "diff": float,
    "virtual_state": {변경된 변수들},
    "benefit_amount": int | None,  # 이자 절감액 (대환 대출 시뮬레이션)
    "insights": [str, ...]         # 개선 인사이트 목록
  }
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langgraph.types import Command
from openai import AsyncOpenAI

from src.app.core.config import OPENAI_API_KEY
from src.app.agents.biz_mong.tools.finance_calc import calculate_finance_benefit

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# 노드 함수
# ═══════════════════════════════════════════════════════════════════════════════

async def simulator_node(
    state: dict,
    client: AsyncOpenAI | None = None,
) -> dict | Command:
    """가상 변수를 적용했을 때 진단 점수 변화를 분석한다.

    [가드 체크]:
        diagnosis_report 가 없으면 hard_filter → llm_evaluator 를 먼저 실행하도록
        Command(goto="hard_filter", update={"pending_intent": "simulator"}) 를 반환한다.
        이후 llm_evaluator 완료 시 pending_intent 를 감지해 이 노드로 자동 복귀한다.
    """
    # ── 가드 체크 ──────────────────────────────────────────────────────────
    diagnosis_report: dict = state.get("diagnosis_report") or {}
    if not diagnosis_report or not diagnosis_report.get("ranked_policies"):
        logger.info("[simulator] diagnosis_report 없음 → 진단 선행 실행")
        return Command(
            goto="hard_filter",
            update={"pending_intent": "simulator"},
        )

    # ── 시뮬레이션 실행 ────────────────────────────────────────────────────
    _client = client or AsyncOpenAI(api_key=OPENAI_API_KEY)

    biz_info: dict = state.get("biz_info") or {}
    financial_data: dict = state.get("financial_data") or {}
    messages: list = state.get("messages") or []

    # 사용자의 마지막 메시지에서 시뮬레이션 요청 파라미터 파싱
    last_user_msg = _get_last_user_message(messages)
    virtual_params = await _extract_virtual_params(_client, last_user_msg, biz_info, financial_data)

    # 원본 점수 (diagnosis_report 기반)
    original_score = diagnosis_report.get("score", 0)

    # 가상 상태에서 점수 재계산 (LLM 없이 룰 기반)
    virtual_biz_info = {**biz_info, **virtual_params.get("biz_overrides", {})}
    virtual_financial = {**financial_data, **virtual_params.get("financial_overrides", {})}
    virtual_score = _recalculate_score(virtual_biz_info, virtual_financial)

    diff = round(virtual_score - original_score, 1)

    # 대환 대출 이자 절감 계산 (loan 파라미터가 있을 경우)
    benefit_amount = None
    if virtual_params.get("loan_params"):
        lp = virtual_params["loan_params"]
        calc = calculate_finance_benefit(
            current_rate=lp.get("current_rate", 5.0),
            target_rate=lp.get("target_rate", 3.0),
            loan_amount=lp.get("loan_amount", 0),
            remaining_months=lp.get("remaining_months", 36),
        )
        benefit_amount = calc.get("interest_saving", 0)

    # 인사이트 생성 (LLM)
    insights = await _generate_insights(
        _client, biz_info, financial_data, virtual_params, original_score, virtual_score
    )

    simulation_report = {
        "original_score": original_score,
        "virtual_score": virtual_score,
        "diff": diff,
        "virtual_state": {
            **virtual_params.get("biz_overrides", {}),
            **virtual_params.get("financial_overrides", {}),
        },
        "benefit_amount": benefit_amount,
        "insights": insights,
        "changed_variables": list(virtual_params.get("biz_overrides", {}).keys())
            + list(virtual_params.get("financial_overrides", {}).keys()),
    }

    logger.info(
        "[simulator] 원본 점수: %.1f → 가상 점수: %.1f (차이: %+.1f)",
        original_score, virtual_score, diff,
    )

    return {"simulation_report": simulation_report}


# ═══════════════════════════════════════════════════════════════════════════════
# 내부 함수
# ═══════════════════════════════════════════════════════════════════════════════

async def _extract_virtual_params(
    client: AsyncOpenAI,
    user_message: str,
    biz_info: dict,
    financial_data: dict,
) -> dict[str, Any]:
    """사용자 메시지에서 시뮬레이션할 가상 변수를 LLM 으로 추출한다.

    예: "직원을 5명 더 뽑으면 어떻게 되나요?" → employee_count += 5
        "특허를 취득하면?" → has_patent = true
    """
    system_prompt = """사용자의 메시지에서 시뮬레이션할 변수 변경사항을 JSON 으로 추출하세요.

[대상 변수]
- has_patent (bool): 특허 보유 여부
- is_ventured (bool): 벤처기업 인증 여부
- employee_count (int): 직원 수
- annual_revenue (int): 연매출 (원 단위)
- loan 파라미터 (대환 대출 시뮬레이션용):
  - current_rate (float): 현재 대출 금리 (%)
  - target_rate (float): 목표 대출 금리 (%)
  - loan_amount (int): 대출 원금 (원)
  - remaining_months (int): 잔여 기간 (개월)

[응답 형식]
{
  "biz_overrides": {"has_patent": true},
  "financial_overrides": {"employee_count": 10, "annual_revenue": 500000000},
  "loan_params": {"current_rate": 5.0, "target_rate": 3.0, "loan_amount": 100000000, "remaining_months": 36}
}

주의: 변경 사항이 없는 필드는 포함하지 마세요. loan_params 는 대출 관련 질문일 때만 포함하세요."""

    user_content = (
        f"현재 사업장 상태:\n{json.dumps({'biz_info': biz_info, 'financial': financial_data}, ensure_ascii=False)}\n\n"
        f"사용자 요청: {user_message}"
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        return json.loads(response.choices[0].message.content)
    except Exception as exc:
        logger.warning("[simulator] 가상 변수 추출 실패: %s", exc)
        return {"biz_overrides": {}, "financial_overrides": {}}


def _recalculate_score(biz_info: dict, financial_data: dict) -> float:
    """룰 기반으로 스코어카드 점수를 계산한다 (LLM 없음).

    llm_evaluator 와 동일한 기준을 Python 으로 구현한 버전.
    """
    score = 0.0

    # 기술력 (40점)
    if biz_info.get("has_patent"):
        score += 20
    if biz_info.get("is_ventured"):
        score += 20

    # 고용 (30점)
    emp = financial_data.get("employee_count") or 0
    if emp >= 10:
        score += 30
    elif emp >= 5:
        score += 20
    elif emp >= 1:
        score += 10

    # 안정성 (30점)
    revenue = financial_data.get("annual_revenue") or 0
    if revenue >= 10_0000_0000:    # 10억
        score += 30
    elif revenue >= 5_0000_0000:   # 5억
        score += 20
    elif revenue >= 1_0000_0000:   # 1억
        score += 10

    # 부채비율 패널티
    debt_ratio = financial_data.get("debt_ratio") or 0
    if debt_ratio > 200:
        score = max(0, score - 10)

    return round(min(100.0, score), 1)


async def _generate_insights(
    client: AsyncOpenAI,
    original_biz: dict,
    original_fin: dict,
    virtual_params: dict,
    original_score: float,
    virtual_score: float,
) -> list[str]:
    """변경 전후 점수를 비교하여 구체적인 개선 인사이트를 생성한다."""
    if not virtual_params.get("biz_overrides") and not virtual_params.get("financial_overrides"):
        return ["시뮬레이션할 변경 사항을 구체적으로 알려주세요. 예: '특허를 취득하면 어떻게 되나요?'"]

    changes = {
        **virtual_params.get("biz_overrides", {}),
        **virtual_params.get("financial_overrides", {}),
    }
    diff = virtual_score - original_score

    prompt = (
        f"현재 점수 {original_score:.1f}점에서 {changes} 로 변경하면 "
        f"{virtual_score:.1f}점 ({diff:+.1f}점) 이 됩니다.\n\n"
        "이 변화가 정책 자금 신청에 미치는 영향을 3가지 핵심 인사이트로 정리해 주세요. "
        "각 인사이트는 한 문장으로 작성하고, 소상공인이 이해하기 쉽게 설명하세요."
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        raw = response.choices[0].message.content.strip()
        # 번호 목록 파싱
        lines = [line.strip().lstrip("0123456789.-) ") for line in raw.split("\n") if line.strip()]
        return [line for line in lines if len(line) > 10][:3]
    except Exception as exc:
        logger.warning("[simulator] 인사이트 생성 실패: %s", exc)
        if diff > 0:
            return [f"변경 후 점수가 {diff:.1f}점 향상됩니다."]
        return [f"변경 후 점수가 {abs(diff):.1f}점 감소합니다."]


def _get_last_user_message(messages: list) -> str:
    """messages 목록에서 가장 최근 사용자 메시지 텍스트를 추출한다."""
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            return msg.get("content", "")
        if hasattr(msg, "content") and hasattr(msg, "type"):
            if msg.type == "human":
                return msg.content
    return ""
