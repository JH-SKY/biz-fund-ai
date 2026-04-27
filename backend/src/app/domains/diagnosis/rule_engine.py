"""규칙 기반 정밀진단 엔진 (실무 임계값)."""

from __future__ import annotations

from src.app.domains.business.model import Business
from src.app.domains.diagnosis.interfaces import DiagnosisResult, IDiagnosisEngine
from src.app.domains.diagnosis.schema import DiagnosisFinalInputs
from src.app.domains.policy.model import Policy

# 부채비율(%) — 매출·부채 기준 동일
_DEBT_SEVERE = 400.0  # 빨간불: 400% 이상
_DEBT_WARN = 200.0  # 노란불: 200% 이상 ~ 400% 미만


class RuleBasedDiagnosisEngine(IDiagnosisEngine):
    """체납(무조건 적색), 부채비율(적/황/록), 가점을 반영."""

    async def execute_diagnosis(
        self,
        business: Business,
        year: int,
        inputs: DiagnosisFinalInputs,
        use_ai: bool = True,
    ) -> DiagnosisResult:
        _ = use_ai, year, business
        if inputs.has_tax_arrears:
            return DiagnosisResult(
                total_score=0.0,
                grade="RISK",
                scores={"stability": 0.0, "growth": 0.0, "tech": 0.0},
                ai_comment=(
                    "국세·지방세 체납(미완납)이 있으면 대부분 정책자금·보증이 제한됩니다. "
                    "완납·증빙 확보 전까지는 🔴(결격)로 봅니다."
                ),
                traffic_light="RED",
            )

        dr = inputs.debt_ratio
        if dr is not None and dr >= _DEBT_SEVERE:
            return DiagnosisResult(
                total_score=min(20.0, 100.0),
                grade="RISK",
                scores={"stability": 5.0, "growth": 5.0, "tech": 5.0},
                ai_comment=(
                    f"부채비율 {dr:.1f}%는 심사상 매우 위험 구간(일반적으로 {_DEBT_SEVERE:.0f}% 이상)으로 "
                    "🔴(빨간불)에 가깝습니다. 상환·보완 계획이 거의 필수입니다."
                ),
                traffic_light="RED",
            )

        base = 45.0
        if inputs.employee_count < 5:
            base += 6.0
        elif inputs.employee_count < 10:
            base += 2.0

        if inputs.annual_revenue and inputs.annual_revenue >= 100_000_000:
            base += 4.0
        if inputs.has_patent:
            base += 10.0
        if inputs.is_female_ent:
            base += 4.0
        if inputs.is_ventured:
            base += 4.0

        traffic = "GREEN"
        if dr is not None and dr >= _DEBT_WARN:
            base -= 12.0
            traffic = "YELLOW"

        total = max(0.0, min(100.0, round(base, 1)))
        if dr is not None and _DEBT_WARN <= dr < _DEBT_SEVERE and traffic == "YELLOW":
            pass
        if total >= 80:
            g = "EXCELLENT"
        elif total >= 60:
            g = "GOOD"
        elif total >= 40:
            g = "NORMAL"
        else:
            g = "RISK"

        return DiagnosisResult(
            total_score=total,
            grade=g,
            scores={"stability": total * 0.35, "growth": total * 0.35, "tech": total * 0.3},
            ai_comment=_build_comment(inputs, dr, total, traffic),
            traffic_light=traffic,
        )

    async def execute_simulation(
        self, business: Business, policy: Policy, conditions: dict
    ):
        from src.app.domains.diagnosis.interfaces import SimulationResult

        _ = policy  # 종합 점수 시뮬에서는 미사용

        # ── 현재 기준 점수 계산 ─────────────────────────────────────
        # conditions 에 "base_inputs" 키로 현재 상태가 전달된다
        base_raw: dict = conditions.get("base_inputs", {})
        base = _score_from_dict(base_raw)

        # ── 가상 조건 적용 후 점수 계산 ─────────────────────────────
        virt_raw: dict = {**base_raw, **conditions.get("virtual_conditions", {})}
        simulated = _score_from_dict(virt_raw)

        # ── gain_factors 생성 ────────────────────────────────────────
        gain_factors = _build_gain_factors(base_raw, virt_raw)

        return SimulationResult(
            base_rate=float(base),
            simulated_rate=float(simulated),
            gain_factors=gain_factors,
        )


def _build_comment(
    inputs: DiagnosisFinalInputs, debt_ratio: float | None, total: float, traffic: str
) -> str:
    parts: list[str] = []
    if traffic == "YELLOW" and debt_ratio is not None:
        parts.append(
            f"부채비율 {debt_ratio:.1f}%는 {_DEBT_WARN:.0f}% 이상으로 🟡(노란불) 구간입니다. "
            "보완·상환계획이 유리할 수 있습니다."
        )
    elif debt_ratio is not None and debt_ratio < _DEBT_WARN:
        parts.append("부채비율은 🟢(정상) 범위로 보는 편입니다.")
    if not inputs.has_patent and not inputs.is_ventured:
        parts.append("특허·벤처 가점이 없다면, 취득 시 시뮬레이션에서 효과를 비교해보세요.")
    parts.append(f"규칙 기반 총점 {total}점(참고)입니다. 최종은 기관·공고마다 다릅니다.")
    return " ".join(parts)


def _score_from_dict(d: dict) -> float:
    """virtual_conditions 또는 base_inputs dict 에서 점수를 계산한다."""
    if d.get("has_tax_arrears"):
        return 0.0

    total_debt = d.get("total_debt")
    annual_revenue = d.get("annual_revenue")
    if total_debt is not None and annual_revenue and annual_revenue > 0:
        dr: float | None = round(total_debt / annual_revenue * 100, 2)
    else:
        dr = d.get("debt_ratio")

    if dr is not None and dr >= _DEBT_SEVERE:
        return 20.0

    base = 45.0
    emp = d.get("employee_count", 0) or 0
    if emp < 5:
        base += 6.0
    elif emp < 10:
        base += 2.0

    if annual_revenue and annual_revenue >= 100_000_000:
        base += 4.0
    if d.get("has_patent"):
        base += 10.0
    if d.get("is_female_ent"):
        base += 4.0
    if d.get("is_ventured"):
        base += 4.0
    if dr is not None and dr >= _DEBT_WARN:
        base -= 12.0

    return float(max(0.0, min(100.0, round(base, 1))))


def _build_gain_factors(base: dict, virt: dict) -> list[str]:
    """변경 항목 기반으로 gain_factors 문자열 목록을 생성한다."""
    factors: list[str] = []
    base_score = _score_from_dict(base)
    virt_score = _score_from_dict(virt)
    diff = round(virt_score - base_score, 1)

    if virt.get("has_patent") and not base.get("has_patent"):
        factors.append("특허 등록 +10점")
    if virt.get("is_ventured") and not base.get("is_ventured"):
        factors.append("벤처 인증 +4점")
    if virt.get("is_female_ent") and not base.get("is_female_ent"):
        factors.append("여성기업 인증 +4점")

    b_emp = base.get("employee_count", 0) or 0
    v_emp = virt.get("employee_count", 0) or 0
    if v_emp != b_emp:
        factors.append(f"직원 수 {b_emp}명 → {v_emp}명 변경")

    b_rev = base.get("annual_revenue") or 0
    v_rev = virt.get("annual_revenue") or 0
    if v_rev != b_rev:
        factors.append(f"연매출 {b_rev // 10_000:,}만원 → {v_rev // 10_000:,}만원")

    b_debt = base.get("total_debt") or 0
    v_debt = virt.get("total_debt") or 0
    if v_debt != b_debt:
        factors.append(f"총부채 {b_debt // 10_000:,}만원 → {v_debt // 10_000:,}만원")

    if not base.get("has_tax_arrears") and virt.get("has_tax_arrears"):
        factors.append("세금 체납 → 결격")
    elif base.get("has_tax_arrears") and not virt.get("has_tax_arrears"):
        factors.append("세금 체납 해소")

    if diff > 0:
        factors.append(f"종합 점수 +{diff}점 예상")
    elif diff < 0:
        factors.append(f"종합 점수 {diff}점 예상")
    else:
        factors.append("점수 변화 없음")

    return factors
