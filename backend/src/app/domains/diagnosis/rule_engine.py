"""Rule-based business health diagnosis engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.app.domains.business.model import Business
from src.app.domains.diagnosis.interfaces import DiagnosisResult, IDiagnosisEngine
from src.app.domains.diagnosis.schema import DiagnosisFinalInputs
from src.app.domains.policy.model import Policy

_DEBT_CRITICAL = 300.0
_DEBT_HIGH = 200.0
_DEBT_WARN = 100.0


@dataclass(slots=True)
class DiagnosisEvaluation:
    total_score: float
    grade: str
    traffic_light: str
    scores: dict[str, float]
    summary: str
    strengths: list[str]
    risk_signals: list[str]
    action_items: list[str]


class RuleBasedDiagnosisEngine(IDiagnosisEngine):
    """Diagnose the health of the business itself, not policy fitness."""

    async def execute_diagnosis(
        self,
        business: Business,
        year: int,
        inputs: DiagnosisFinalInputs,
        use_ai: bool = True,
    ) -> DiagnosisResult:
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
        from src.app.domains.diagnosis.interfaces import SimulationResult

        _ = policy
        base_inputs = conditions.get("base_inputs", {})
        base_eval = _evaluate_from_mapping(base_inputs, business)

        virtual_inputs = {**base_inputs, **conditions.get("virtual_conditions", {})}
        simulated_eval = _evaluate_from_mapping(virtual_inputs, business)

        return SimulationResult(
            base_rate=base_eval.total_score,
            simulated_rate=simulated_eval.total_score,
            gain_factors=_build_gain_factors(base_eval, simulated_eval, base_inputs, virtual_inputs),
        )


def _evaluate_from_mapping(raw: dict, business: Business) -> DiagnosisEvaluation:
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
    if has_tax_arrears or (debt_ratio is not None and debt_ratio >= _DEBT_CRITICAL):
        return "RED"
    if total_score < 60 or (debt_ratio is not None and debt_ratio >= _DEBT_WARN):
        return "YELLOW"
    return "GREEN"


def _business_age_years(business: Business) -> int | None:
    if not business.establishment_date:
        return None
    today = date.today()
    established = business.establishment_date
    years = today.year - established.year
    if (today.month, today.day) < (established.month, established.day):
        years -= 1
    return max(years, 0)


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return round(max(minimum, min(maximum, value)), 1)
