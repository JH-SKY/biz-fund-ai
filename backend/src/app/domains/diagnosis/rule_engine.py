# src/app/domains/diagnosis/rule_engine.py
"""규칙 기반 사업 건강도 진단 엔진.

[설계 원칙]
- IDiagnosisEngine 인터페이스를 구현하며, AI 없이 순수 수식·임계값으로 진단한다.
- 진단 결과는 4개 축 점수의 가중 합산으로 계산된다:
    재무건전성(40%) + 성장잠재력(20%) + 운영안정성(25%) + 리스크관리(15%)
- 체납 또는 과도한 부채 상태이면 총점에 상한선(ceiling)을 적용한다.

[부채비율 임계값]
  _DEBT_WARN     (100%): 주의 구간
  _DEBT_HIGH     (200%): 위험 구간
  _DEBT_CRITICAL (300%): 심각 구간 — 이 이상이면 총점 42점 이하로 제한
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.app.domains.business.model import Business
from src.app.domains.diagnosis.interfaces import DiagnosisResult, IDiagnosisEngine
from src.app.domains.diagnosis.schema import DiagnosisFinalInputs
from src.app.domains.policy.model import Policy

# 부채비율 임계값 (단위: %)
_DEBT_CRITICAL = 300.0  # 심각: 총점 상한 42점 적용
_DEBT_HIGH = 200.0      # 위험: 각 축 점수 대폭 감점
_DEBT_WARN = 100.0      # 주의: 각 축 점수 소폭 감점


@dataclass(slots=True)
class DiagnosisEvaluation:
    """진단 계산 중간 결과를 담는 내부 데이터 클래스."""

    total_score: float
    grade: str
    traffic_light: str
    scores: dict[str, float]
    summary: str
    strengths: list[str]
    risk_signals: list[str]
    action_items: list[str]


class RuleBasedDiagnosisEngine(IDiagnosisEngine):
    """규칙 기반 사업 건강도 진단 엔진.

    정책 적합성이 아닌 사업 자체의 재무·운영 건강도를 진단한다.
    AI 없이 수식과 임계값만으로 동작하므로 비용이 들지 않고 결과가 일정하다.
    """

    async def execute_diagnosis(
        self,
        business: Business,
        year: int,
        inputs: DiagnosisFinalInputs,
        use_ai: bool = True,
    ) -> DiagnosisResult:
        """진단을 실행하고 DiagnosisResult DTO를 반환한다."""
        _ = year, use_ai
        evaluation = _evaluate_business_health(business, inputs)
        return DiagnosisResult(
            total_score=evaluation.total_score,
            grade=evaluation.grade,
            scores=evaluation.scores,
            summary=evaluation.summary,
            strengths=evaluation.strengths,
            risk_signals=evaluation.risk_signals,
            action_items=evaluation.action_items,
            traffic_light=evaluation.traffic_light,
        )

    async def execute_simulation(
        self,
        business: Business,
        policy: Policy | None,
        conditions: dict,
    ):
        """가상 조건 시뮬레이션을 실행한다.

        [로직]
        1. base_inputs(현재 상태)로 기준 점수 계산
        2. base_inputs + virtual_conditions 를 합산하여 가상 점수 계산
        3. 두 점수 차이와 변화 요인(gain_factors)을 반환
        """
        from src.app.domains.diagnosis.interfaces import SimulationResult

        _ = policy  # 현재 규칙 엔진에서는 개별 정책 조건을 별도로 적용하지 않음
        base_inputs = conditions.get("base_inputs", {})
        base_eval = _evaluate_from_mapping(base_inputs, business)

        # 가상 조건을 현재 입력값에 덮어써서 시뮬레이션 평가 수행
        virtual_inputs = {**base_inputs, **conditions.get("virtual_conditions", {})}
        simulated_eval = _evaluate_from_mapping(virtual_inputs, business)

        return SimulationResult(
            base_rate=base_eval.total_score,
            simulated_rate=simulated_eval.total_score,
            gain_factors=_build_gain_factors(base_eval, simulated_eval, base_inputs, virtual_inputs),
        )


def _evaluate_from_mapping(raw: dict, business: Business) -> DiagnosisEvaluation:
    """딕셔너리 형태의 입력값을 DiagnosisFinalInputs 로 변환 후 진단을 수행한다.

    시뮬레이션에서 base_inputs / virtual_inputs 모두 이 함수를 통해 평가한다.
    """
    inputs = DiagnosisFinalInputs(
        has_tax_arrears=bool(raw.get("has_tax_arrears")),
        annual_revenue=raw.get("annual_revenue"),
        total_debt=raw.get("total_debt"),
        debt_ratio=raw.get("debt_ratio"),
        employee_count=int(raw.get("employee_count") or 0),
        has_patent=bool(raw.get("has_patent")),
        is_female_ent=bool(raw.get("is_female_ent")),
        is_ventured=bool(raw.get("is_ventured")),
    )
    return _evaluate_business_health(business, inputs)


def _evaluate_business_health(
    business: Business,
    inputs: DiagnosisFinalInputs,
) -> DiagnosisEvaluation:
    """사업 건강도를 4개 축으로 평가하고 총점·등급·신호등을 계산한다.

    [평가 구조]
    재무건전성 × 0.40
    + 성장잠재력 × 0.20
    + 운영안정성 × 0.25
    + 리스크관리 × 0.15
    = 총점 (0~100)

    [총점 상한선 규칙]
    - 체납 이력: 최대 34점
    - 부채비율 ≥ 300%: 최대 42점
    """
    debt_ratio = _resolve_debt_ratio(inputs)
    business_age_years = _business_age_years(business)

    financial = _financial_health_score(inputs.annual_revenue, debt_ratio, inputs.has_tax_arrears)
    growth = _growth_potential_score(
        annual_revenue=inputs.annual_revenue,
        employee_count=inputs.employee_count,
        business_age_years=business_age_years,
        has_patent=inputs.has_patent,
        is_ventured=inputs.is_ventured,
        is_female_ent=inputs.is_female_ent,
    )
    stability = _operational_stability_score(
        annual_revenue=inputs.annual_revenue,
        employee_count=inputs.employee_count,
        debt_ratio=debt_ratio,
        business_age_years=business_age_years,
        has_tax_arrears=inputs.has_tax_arrears,
    )
    risk = _risk_management_score(
        has_tax_arrears=inputs.has_tax_arrears,
        debt_ratio=debt_ratio,
        annual_revenue=inputs.annual_revenue,
        total_debt=inputs.total_debt,
    )

    total = round(
        financial * 0.40
        + growth * 0.20
        + stability * 0.25
        + risk * 0.15,
        1,
    )

    if inputs.has_tax_arrears:
        total = min(total, 34.0)
    elif debt_ratio is not None and debt_ratio >= _DEBT_CRITICAL:
        total = min(total, 42.0)

    grade = _grade_for_score(total)
    traffic_light = _traffic_for_state(
        total_score=total,
        has_tax_arrears=inputs.has_tax_arrears,
        debt_ratio=debt_ratio,
    )

    strengths = _build_strengths(
        annual_revenue=inputs.annual_revenue,
        debt_ratio=debt_ratio,
        employee_count=inputs.employee_count,
        business_age_years=business_age_years,
        has_patent=inputs.has_patent,
        is_ventured=inputs.is_ventured,
        is_female_ent=inputs.is_female_ent,
    )
    risk_signals = _build_risk_signals(
        annual_revenue=inputs.annual_revenue,
        debt_ratio=debt_ratio,
        employee_count=inputs.employee_count,
        business_age_years=business_age_years,
        has_tax_arrears=inputs.has_tax_arrears,
    )
    action_items = _build_action_items(
        annual_revenue=inputs.annual_revenue,
        debt_ratio=debt_ratio,
        employee_count=inputs.employee_count,
        has_tax_arrears=inputs.has_tax_arrears,
        has_patent=inputs.has_patent,
        is_ventured=inputs.is_ventured,
    )
    summary = _build_summary(
        total_score=total,
        traffic_light=traffic_light,
        annual_revenue=inputs.annual_revenue,
        debt_ratio=debt_ratio,
        employee_count=inputs.employee_count,
        has_tax_arrears=inputs.has_tax_arrears,
    )

    return DiagnosisEvaluation(
        total_score=total,
        grade=grade,
        traffic_light=traffic_light,
        scores={
            "financial_health": financial,
            "growth_potential": growth,
            "operational_stability": stability,
            "risk_management": risk,
        },
        summary=summary,
        strengths=strengths,
        risk_signals=risk_signals,
        action_items=action_items,
    )


def _resolve_debt_ratio(inputs: DiagnosisFinalInputs) -> float | None:
    """부채비율을 결정한다.

    직접 입력된 debt_ratio 가 있으면 그대로 사용,
    없으면 (총부채 / 연매출 × 100) 으로 계산한다.
    필요한 값이 모두 없으면 None 을 반환한다.
    """
    if inputs.debt_ratio is not None:
        return inputs.debt_ratio
    if inputs.annual_revenue and inputs.annual_revenue > 0 and inputs.total_debt is not None:
        return round(inputs.total_debt / inputs.annual_revenue * 100, 2)
    return None


def _financial_health_score(
    annual_revenue: int | None,
    debt_ratio: float | None,
    has_tax_arrears: bool,
) -> float:
    """재무건전성 점수를 계산한다 (0~100점, 가중치 40%).

    [감점 조건]
    - 매출 미입력: -18점 / 5천만 미만: -26점 / 1억 미만: -12점
    - 부채비율 ≥ 300%: -44점 / ≥ 200%: -28점 / ≥ 100%: -14점
    - 체납 이력: -35점 (패널티)

    [가점 조건]
    - 매출 ≥ 5억: +8점 / ≥ 3억: +4점
    - 부채비율 ≤ 50%: +6점
    """
    score = 72.0

    if annual_revenue is None:
        score -= 18.0
    elif annual_revenue < 50_000_000:
        score -= 26.0
    elif annual_revenue < 100_000_000:
        score -= 12.0
    elif annual_revenue >= 500_000_000:
        score += 8.0
    elif annual_revenue >= 300_000_000:
        score += 4.0

    if debt_ratio is None:
        score -= 8.0
    elif debt_ratio >= _DEBT_CRITICAL:
        score -= 44.0
    elif debt_ratio >= _DEBT_HIGH:
        score -= 28.0
    elif debt_ratio >= _DEBT_WARN:
        score -= 14.0
    elif debt_ratio <= 50:
        score += 6.0

    if has_tax_arrears:
        score -= 35.0

    return _clamp(score)


def _growth_potential_score(
    *,
    annual_revenue: int | None,
    employee_count: int,
    business_age_years: int | None,
    has_patent: bool,
    is_ventured: bool,
    is_female_ent: bool,
) -> float:
    """성장잠재력 점수를 계산한다 (0~100점, 가중치 20%).

    [주요 가점 항목]
    - 특허 보유: +10점
    - 벤처 기업: +12점
    - 여성 기업: +5점
    - 직원 10명 이상: +10점
    - 업력 3~7년(성장기): +8점
    """
    score = 48.0

    if annual_revenue is None:
        score -= 10.0
    elif annual_revenue < 50_000_000:
        score -= 12.0
    elif annual_revenue < 100_000_000:
        score -= 4.0
    elif annual_revenue >= 300_000_000:
        score += 10.0
    elif annual_revenue >= 100_000_000:
        score += 5.0

    if employee_count >= 10:
        score += 10.0
    elif employee_count >= 5:
        score += 6.0
    elif employee_count <= 1:
        score -= 6.0

    if business_age_years is not None:
        if business_age_years < 1:
            score -= 6.0
        elif business_age_years < 3:
            score += 4.0
        elif business_age_years <= 7:
            score += 8.0
        else:
            score += 5.0

    if has_patent:
        score += 10.0
    if is_ventured:
        score += 12.0
    if is_female_ent:
        score += 5.0

    return _clamp(score)


def _operational_stability_score(
    *,
    annual_revenue: int | None,
    employee_count: int,
    debt_ratio: float | None,
    business_age_years: int | None,
    has_tax_arrears: bool,
) -> float:
    """운영안정성 점수를 계산한다 (0~100점, 가중치 25%).

    [핵심 감점 항목]
    - 직원 1명 이하(대표자 혼자): -18점 (단일 인물 의존 리스크)
    - 업력 1년 미만: -14점 (초기 불안정)
    - 체납: -20점 (운영 연속성 위협)
    """
    score = 52.0

    if employee_count <= 1:
        score -= 18.0
    elif employee_count < 5:
        score -= 4.0
    elif employee_count < 10:
        score += 6.0
    else:
        score += 12.0

    if business_age_years is not None:
        if business_age_years < 1:
            score -= 14.0
        elif business_age_years < 3:
            score -= 2.0
        elif business_age_years < 7:
            score += 8.0
        else:
            score += 12.0

    if annual_revenue is None:
        score -= 12.0
    elif annual_revenue >= 100_000_000:
        score += 8.0

    if debt_ratio is not None:
        if debt_ratio >= _DEBT_HIGH:
            score -= 18.0
        elif debt_ratio >= _DEBT_WARN:
            score -= 8.0

    if has_tax_arrears:
        score -= 20.0

    return _clamp(score)


def _risk_management_score(
    *,
    has_tax_arrears: bool,
    debt_ratio: float | None,
    annual_revenue: int | None,
    total_debt: int | None,
) -> float:
    """리스크관리 점수를 계산한다 (0~100점, 가중치 15%).

    체납 이력이 있으면 즉시 5점으로 고정 (리스크 관리 실패).
    이외에는 부채비율·재무 정보 유무에 따라 감점한다.
    """
    if has_tax_arrears:
        return 5.0

    score = 82.0

    if debt_ratio is None:
        score -= 12.0
    elif debt_ratio >= _DEBT_CRITICAL:
        score -= 58.0
    elif debt_ratio >= _DEBT_HIGH:
        score -= 36.0
    elif debt_ratio >= _DEBT_WARN:
        score -= 18.0
    elif debt_ratio <= 50:
        score += 5.0

    if annual_revenue is None:
        score -= 10.0
    if total_debt is None:
        score -= 6.0

    return _clamp(score)


def _build_summary(
    *,
    total_score: float,
    traffic_light: str,
    annual_revenue: int | None,
    debt_ratio: float | None,
    employee_count: int,
    has_tax_arrears: bool,
) -> str:
    if has_tax_arrears:
        return "체납 이력이 있어 사업장 건전성이 크게 떨어진 상태입니다. 세무 리스크를 먼저 해소해야 다음 단계 개선이 가능합니다."
    if debt_ratio is not None and debt_ratio >= _DEBT_CRITICAL:
        return f"부채비율이 {debt_ratio:.0f}%로 매우 높아 재무 체력이 약한 상태입니다. 상환 부담을 낮추는 조치가 가장 시급합니다."
    if annual_revenue is not None and annual_revenue < 50_000_000:
        return "매출 규모가 아직 작아 고정비와 차입 부담에 취약한 초기 단계입니다. 안정적인 매출 기반 확보가 우선입니다."
    if employee_count <= 1:
        return "대표자 중심으로 운영되는 소규모 구조라 운영 안정성이 낮습니다. 핵심 업무를 분산할 인력 기반이 필요합니다."
    if traffic_light == "GREEN" and total_score >= 75:
        return "재무와 운영 지표가 비교적 안정적입니다. 지금은 성장 투자와 정책 활용을 병행하기 좋은 구간입니다."
    return "사업장 상태는 보통 수준이지만 재무와 운영에서 몇 가지 보완 포인트가 보입니다. 핵심 리스크를 먼저 줄이는 것이 좋습니다."


def _build_strengths(
    *,
    annual_revenue: int | None,
    debt_ratio: float | None,
    employee_count: int,
    business_age_years: int | None,
    has_patent: bool,
    is_ventured: bool,
    is_female_ent: bool,
) -> list[str]:
    strengths: list[str] = []

    if annual_revenue is not None and annual_revenue >= 300_000_000:
        strengths.append("매출 규모가 일정 수준 이상이라 기본적인 현금 창출력이 있습니다.")
    if debt_ratio is not None and debt_ratio < 100:
        strengths.append("부채비율이 과도하지 않아 재무 부담이 상대적으로 안정적입니다.")
    if employee_count >= 5:
        strengths.append("상시 인력이 확보돼 있어 운영이 대표자 1인에게만 의존하지 않습니다.")
    if business_age_years is not None and business_age_years >= 3:
        strengths.append("업력이 누적돼 운영 경험과 거래 신뢰를 쌓아온 편입니다.")
    if has_patent or is_ventured:
        strengths.append("기술성 또는 혁신성 신호가 있어 성장 잠재력을 설명하기 좋습니다.")
    if is_female_ent:
        strengths.append("여성기업 지위는 외부 지원과 사업 확장 스토리에서 강점이 될 수 있습니다.")

    if not strengths:
        strengths.append("아직 큰 강점보다는 기본 체력을 쌓아가는 단계로 보입니다.")

    return strengths[:4]


def _build_risk_signals(
    *,
    annual_revenue: int | None,
    debt_ratio: float | None,
    employee_count: int,
    business_age_years: int | None,
    has_tax_arrears: bool,
) -> list[str]:
    risks: list[str] = []

    if has_tax_arrears:
        risks.append("체납 이력으로 인해 대외 신용과 각종 심사에서 즉시 불이익을 받을 수 있습니다.")
    if annual_revenue is None:
        risks.append("매출 정보가 없어 재무 진단의 신뢰도가 떨어집니다.")
    elif annual_revenue < 50_000_000:
        risks.append("매출 규모가 작아 고정비 상승이나 일시적 매출 하락에 취약합니다.")
    if debt_ratio is None:
        risks.append("부채 정보가 충분하지 않아 실제 재무 위험을 보수적으로 판단했습니다.")
    elif debt_ratio >= _DEBT_CRITICAL:
        risks.append(f"부채비율 {debt_ratio:.0f}%로 상환 부담이 매우 큰 상태입니다.")
    elif debt_ratio >= _DEBT_HIGH:
        risks.append(f"부채비율 {debt_ratio:.0f}%로 차입 구조 개선이 필요합니다.")
    elif debt_ratio >= _DEBT_WARN:
        risks.append(f"부채비율 {debt_ratio:.0f}%로 재무 여력이 다소 줄어든 상태입니다.")
    if employee_count <= 1:
        risks.append("대표자 의존도가 높아 운영 공백 리스크가 큽니다.")
    elif employee_count < 3:
        risks.append("인력층이 얇아 업무 분산과 확장 대응력이 제한적입니다.")
    if business_age_years is not None and business_age_years < 1:
        risks.append("업력이 짧아 거래 안정성과 수익 구조가 아직 검증되지 않았습니다.")

    if not risks:
        risks.append("현재 기준으로 치명적인 리스크는 크지 않지만 정기적인 재무 점검은 필요합니다.")

    return risks[:4]


def _build_action_items(
    *,
    annual_revenue: int | None,
    debt_ratio: float | None,
    employee_count: int,
    has_tax_arrears: bool,
    has_patent: bool,
    is_ventured: bool,
) -> list[str]:
    actions: list[str] = []

    if has_tax_arrears:
        actions.append("체납 세목 정리와 분할 납부 계획을 먼저 확정하세요.")
    if debt_ratio is not None and debt_ratio >= _DEBT_HIGH:
        actions.append("고금리 차입을 줄이고 상환 스케줄을 재조정해 부채비율을 낮추세요.")
    elif debt_ratio is None:
        actions.append("최근 부채와 매출 자료를 정리해 정확한 재무 상태를 먼저 확인하세요.")

    if annual_revenue is None or annual_revenue < 100_000_000:
        actions.append("월별 매출 흐름을 관리해 안정적인 반복 매출원을 늘리세요.")
    if employee_count <= 1:
        actions.append("대표자에게 몰린 핵심 업무를 분산할 최소 인력 또는 외주 체계를 확보하세요.")
    if not has_patent and not is_ventured:
        actions.append("기술성 또는 혁신성을 증명할 수 있는 인증·특허 전략을 검토하세요.")

    if not actions:
        actions.append("현재 체력을 유지하면서 성장 투자 우선순위를 점검하세요.")

    return actions[:4]


def _build_gain_factors(
    base_eval: DiagnosisEvaluation,
    simulated_eval: DiagnosisEvaluation,
    base_inputs: dict,
    virtual_inputs: dict,
) -> list[str]:
    """시뮬레이션에서 점수 변화 원인을 사람이 읽을 수 있는 문장으로 정리한다.

    [분석 항목]
    - 4개 축(재무건전성·성장성·운영안정성·리스크관리)의 점수 변화 (±3점 이상만 표기)
    - 체납 발생/해소 여부
    - 매출·부채·인력 변화 감지
    - 총점 변화 요약

    최대 6개 항목만 반환 (UI 공간 제한).
    """
    factors: list[str] = []
    diff = round(simulated_eval.total_score - base_eval.total_score, 1)

    for label, key in (
        ("재무건전성", "financial_health"),
        ("성장성", "growth_potential"),
        ("운영안정성", "operational_stability"),
        ("리스크관리", "risk_management"),
    ):
        axis_diff = round(
            simulated_eval.scores[key] - base_eval.scores[key],
            1,
        )
        if abs(axis_diff) >= 3:
            sign = "+" if axis_diff > 0 else ""
            factors.append(f"{label} {sign}{axis_diff}점 변화")

    if virtual_inputs.get("has_tax_arrears") and not base_inputs.get("has_tax_arrears"):
        factors.append("체납 발생으로 전체 건전성이 크게 악화됩니다.")
    elif base_inputs.get("has_tax_arrears") and not virtual_inputs.get("has_tax_arrears"):
        factors.append("체납 해소 시 리스크 관리 점수가 크게 회복됩니다.")

    base_revenue = base_inputs.get("annual_revenue") or 0
    new_revenue = virtual_inputs.get("annual_revenue") or 0
    if new_revenue != base_revenue:
        direction = "증가" if new_revenue > base_revenue else "감소"
        factors.append(f"매출 {direction}가 성장성과 운영안정성에 반영됩니다.")

    base_debt = base_inputs.get("total_debt") or 0
    new_debt = virtual_inputs.get("total_debt") or 0
    if new_debt != base_debt:
        direction = "감소" if new_debt < base_debt else "증가"
        factors.append(f"부채 {direction}가 재무건전성에 직접 반영됩니다.")

    base_employee = int(base_inputs.get("employee_count") or 0)
    new_employee = int(virtual_inputs.get("employee_count") or 0)
    if new_employee != base_employee:
        factors.append("인력 변화가 운영안정성과 성장성에 영향을 줍니다.")

    if diff > 0:
        factors.append(f"종합 진단 점수가 +{diff}점 개선됩니다.")
    elif diff < 0:
        factors.append(f"종합 진단 점수가 {diff}점 하락합니다.")
    else:
        factors.append("종합 진단 점수 변화는 크지 않습니다.")

    deduped: list[str] = []
    seen: set[str] = set()
    for factor in factors:
        if factor not in seen:
            seen.add(factor)
            deduped.append(factor)
    return deduped[:6]


def _grade_for_score(score: float) -> str:
    """총점을 등급 문자열로 변환한다.

    EXCELLENT (≥85) / GOOD (≥70) / NORMAL (≥55) / RISK (<55)
    """
    if score >= 85:
        return "EXCELLENT"
    if score >= 70:
        return "GOOD"
    if score >= 55:
        return "NORMAL"
    return "RISK"


def _traffic_for_state(
    *,
    total_score: float,
    has_tax_arrears: bool,
    debt_ratio: float | None,
) -> str:
    """신호등 색상을 결정한다.

    RED    : 체납 이력 있거나 부채비율 ≥ 300% (즉각 위험 신호)
    YELLOW : 총점 60 미만이거나 부채비율 ≥ 100% (주의 필요)
    GREEN  : 그 외 안정 상태
    """
    if has_tax_arrears or (debt_ratio is not None and debt_ratio >= _DEBT_CRITICAL):
        return "RED"
    if total_score < 60 or (debt_ratio is not None and debt_ratio >= _DEBT_WARN):
        return "YELLOW"
    return "GREEN"


def _business_age_years(business: Business) -> int | None:
    """개업일로부터 오늘까지의 업력(연)을 계산한다.

    establishment_date 가 없으면 None 을 반환한다.
    생일 기념일 방식(생월·일이 지나야 +1년)으로 계산한다.
    """
    if not business.establishment_date:
        return None
    today = date.today()
    established = business.establishment_date
    years = today.year - established.year
    if (today.month, today.day) < (established.month, established.day):
        years -= 1
    return max(years, 0)


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    """점수를 [minimum, maximum] 범위로 제한하고 소수 첫째 자리로 반올림한다."""
    return round(max(minimum, min(maximum, value)), 1)
