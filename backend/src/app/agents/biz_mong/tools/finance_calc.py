# src/app/agents/biz_mong/tools/finance_calc.py
"""Tool: 대환 대출 이자 절감액 및 ROI 계산기.

설계 원칙:
  - 순수 파이썬 계산 함수입니다. LLM 호출 없음, DB 접근 없음.
  - 모든 금액 단위는 '원(KRW)' 입니다.
  - 음수 이자 절감액은 0 으로 클램프합니다 (대환이 불리한 경우).
"""

from __future__ import annotations

from typing import Any


def calculate_finance_benefit(
    *,
    current_rate: float,
    target_rate: float,
    loan_amount: int,
    remaining_months: int,
) -> dict[str, Any]:
    """대환 대출로 예상되는 이자 절감액을 계산한다.

    Args:
        current_rate:      현재 대출 연이율 (%) — 예: 5.5
        target_rate:       대환 목표 연이율 (%) — 예: 3.0
        loan_amount:       원금 (원) — 예: 100_000_000
        remaining_months:  잔여 상환 기간 (개월) — 예: 36

    Returns:
        {
            "current_total_interest": int,   # 현재 금리 기준 잔여 이자 (원)
            "target_total_interest":  int,   # 목표 금리 기준 잔여 이자 (원)
            "interest_saving":        int,   # 절감 이자 (원)
            "monthly_saving":         int,   # 월 절감액 (원)
            "annual_saving":          int,   # 연 절감액 (원)
            "saving_ratio":           float, # 절감 비율 (%)
            "summary":                str,   # 사용자에게 보여줄 한국어 요약
        }
    """
    if remaining_months <= 0 or loan_amount <= 0:
        return _zero_result("잔여 기간 또는 대출금이 0 입니다.")

    rate_diff = current_rate - target_rate
    if rate_diff <= 0:
        return _zero_result("목표 금리가 현재 금리보다 높거나 같습니다.")

    # 원리금균등상환 방식으로 총 이자 계산
    current_total = _total_interest(loan_amount, current_rate, remaining_months)
    target_total = _total_interest(loan_amount, target_rate, remaining_months)

    saving = max(0, current_total - target_total)
    monthly_saving = saving // remaining_months if remaining_months > 0 else 0
    annual_saving = monthly_saving * 12
    saving_ratio = (saving / current_total * 100) if current_total > 0 else 0.0

    summary = (
        f"현재 연{current_rate:.1f}% → 대환 연{target_rate:.1f}% 기준, "
        f"{remaining_months}개월 동안 약 {_fmt(saving)}원 이자 절감이 가능합니다. "
        f"(월 약 {_fmt(monthly_saving)}원, 연 약 {_fmt(annual_saving)}원)"
    )

    return {
        "current_total_interest": current_total,
        "target_total_interest": target_total,
        "interest_saving": saving,
        "monthly_saving": monthly_saving,
        "annual_saving": annual_saving,
        "saving_ratio": round(saving_ratio, 2),
        "summary": summary,
    }


def calculate_grant_roi(
    *,
    grant_amount: int,
    preparation_cost: int,
    success_probability: float,
) -> dict[str, Any]:
    """정책 자금(보조금/출연금) 신청 ROI 계산.

    Args:
        grant_amount:         지원금 상한 (원)
        preparation_cost:     신청 준비 예상 비용 (원, 인건비 포함)
        success_probability:  예상 선정 확률 (0.0~1.0)

    Returns:
        {
            "expected_value": int,   # 기대값 = grant * probability (원)
            "net_roi":        float, # (기대값 - 준비비용) / 준비비용 * 100 (%)
            "break_even_prob": float, # ROI ≥ 0 이 되는 최소 확률 (%)
            "summary":        str,
        }
    """
    expected = int(grant_amount * max(0.0, min(1.0, success_probability)))
    net_roi = ((expected - preparation_cost) / preparation_cost * 100) if preparation_cost > 0 else 0.0
    break_even = (preparation_cost / grant_amount * 100) if grant_amount > 0 else 100.0

    if net_roi >= 0:
        verdict = "신청 투자 가치 있음"
    else:
        verdict = "준비 비용 대비 기대 수익이 낮음"

    summary = (
        f"지원금 {_fmt(grant_amount)}원, 선정 확률 {success_probability*100:.0f}% 가정 시 "
        f"기대 수익 {_fmt(expected)}원 (ROI {net_roi:.1f}%). {verdict}."
    )

    return {
        "expected_value": expected,
        "net_roi": round(net_roi, 2),
        "break_even_prob": round(break_even, 2),
        "summary": summary,
    }


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

def _total_interest(principal: int, annual_rate_pct: float, months: int) -> int:
    """원리금균등상환(PMT) 방식으로 총 납부 이자를 계산한다."""
    r = annual_rate_pct / 100 / 12  # 월 이율
    if r == 0:
        return 0
    pmt = principal * r * (1 + r) ** months / ((1 + r) ** months - 1)
    total_payment = pmt * months
    return max(0, int(total_payment - principal))


def _fmt(amount: int) -> str:
    """금액을 한국식 단위(억/만)로 포맷한다."""
    if amount >= 1_0000_0000:
        return f"{amount / 1_0000_0000:.1f}억"
    if amount >= 1_0000:
        return f"{amount // 1_0000}만"
    return str(amount)


def _zero_result(reason: str) -> dict[str, Any]:
    return {
        "current_total_interest": 0,
        "target_total_interest": 0,
        "interest_saving": 0,
        "monthly_saving": 0,
        "annual_saving": 0,
        "saving_ratio": 0.0,
        "summary": reason,
    }
