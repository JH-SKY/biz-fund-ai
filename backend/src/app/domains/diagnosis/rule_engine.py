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

        _ = business, policy
        return SimulationResult(60.0, 78.0, ["(시뮬) 가점 가정: 특허 +10%p"])


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
