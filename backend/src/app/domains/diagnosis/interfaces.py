"""Diagnosis and simulation engine interfaces."""

from abc import ABC, abstractmethod
from typing import Any

from src.app.domains.business.model import Business
from src.app.domains.diagnosis.schema import DiagnosisFinalInputs
from src.app.domains.policy.model import Policy


class DiagnosisResult:
    """Result DTO returned by the diagnosis engine."""

    def __init__(
        self,
        total_score: float,
        grade: str,
        scores: dict[str, float],
        summary: str,
        strengths: list[str],
        risk_signals: list[str],
        action_items: list[str],
        *,
        traffic_light: str = "GREEN",
    ) -> None:
        self.total_score = total_score
        self.grade = grade
        self.scores = scores
        self.summary = summary
        self.strengths = strengths
        self.risk_signals = risk_signals
        self.action_items = action_items
        self.traffic_light = traffic_light


class SimulationResult:
    """Result DTO returned by the simulation engine."""

    def __init__(
        self,
        base_rate: float,
        simulated_rate: float,
        gain_factors: list[str],
    ) -> None:
        self.base_rate = base_rate
        self.simulated_rate = simulated_rate
        self.gain_factors = gain_factors


class IDiagnosisEngine(ABC):
    """Business diagnosis and simulation engine interface."""

    @abstractmethod
    async def execute_diagnosis(
        self,
        business: Business,
        year: int,
        inputs: DiagnosisFinalInputs,
        use_ai: bool = True,
    ) -> DiagnosisResult:
        """Run the business diagnosis."""

    @abstractmethod
    async def execute_simulation(
        self,
        business: Business,
        policy: Policy | None,
        conditions: dict[str, Any],
    ) -> SimulationResult:
        """Run the diagnosis simulation."""


class MockDiagnosisEngine(IDiagnosisEngine):
    """Legacy mock engine kept only for compatibility."""

    async def execute_diagnosis(
        self,
        business: Business,
        year: int,
        inputs: DiagnosisFinalInputs,
        use_ai: bool = True,
    ) -> DiagnosisResult:
        _ = business, year, inputs, use_ai
        return DiagnosisResult(
            total_score=78.0,
            grade="GOOD",
            scores={
                "financial_health": 76.0,
                "growth_potential": 80.0,
                "operational_stability": 74.0,
                "risk_management": 82.0,
            },
            summary="기본 진단 엔진 대신 규칙 기반 진단 엔진 사용이 권장됩니다.",
            strengths=["재무와 운영 지표가 대체로 안정적입니다."],
            risk_signals=["세부 진단 근거는 실제 엔진에서만 정확히 계산됩니다."],
            action_items=["규칙 기반 진단 엔진으로 교체해 결과를 다시 계산하세요."],
            traffic_light="GREEN",
        )

    async def execute_simulation(
        self,
        business: Business,
        policy: Policy | None,
        conditions: dict[str, Any],
    ) -> SimulationResult:
        _ = business, policy, conditions
        return SimulationResult(
            base_rate=65.0,
            simulated_rate=78.0,
            gain_factors=["매출이 개선되면 재무 안정성이 올라갑니다."],
        )
