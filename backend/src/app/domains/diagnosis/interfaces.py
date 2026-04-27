"""정밀진단 도메인 외부 의존성 인터페이스."""

from abc import ABC, abstractmethod
from typing import Any, Dict

from src.app.domains.business.model import Business
from src.app.domains.diagnosis.schema import DiagnosisFinalInputs
from src.app.domains.policy.model import Policy


class DiagnosisResult:
    """진단 엔진 결과 DTO."""

    def __init__(
        self,
        total_score: float,
        grade: str,
        scores: Dict[str, float],
        ai_comment: str,
        *,
        traffic_light: str = "GREEN",
    ) -> None:
        self.total_score = total_score
        self.grade = grade
        self.scores = scores
        self.ai_comment = ai_comment
        self.traffic_light = traffic_light


class SimulationResult:
    """시뮬레이션 엔진 결과 DTO."""
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
    """정밀진단 및 시뮬레이션 엔진 인터페이스."""

    @abstractmethod
    async def execute_diagnosis(
        self,
        business: Business,
        year: int,
        inputs: DiagnosisFinalInputs,
        use_ai: bool = True,
    ) -> DiagnosisResult:
        """정밀진단 실행"""
        pass

    @abstractmethod
    async def execute_simulation(
        self,
        business: Business,
        policy: Policy,
        conditions: Dict[str, Any],
    ) -> SimulationResult:
        """가산점 시뮬레이션 실행"""
        pass


class MockDiagnosisEngine(IDiagnosisEngine):
    """호환용 — RuleBased로 교체됨. 테스트는 RuleBased 권장."""

    async def execute_diagnosis(
        self,
        business: Business,
        year: int,
        inputs: DiagnosisFinalInputs,
        use_ai: bool = True,
    ) -> DiagnosisResult:
        _ = business, year, use_ai, inputs
        return DiagnosisResult(
            total_score=85.5,
            grade="EXCELLENT",
            scores={"stability": 80.0, "growth": 90.0, "tech": 85.0},
            ai_comment="Mock — RuleBasedDiagnosisEngine 사용을 권장합니다.",
            traffic_light="GREEN",
        )

    async def execute_simulation(
        self,
        business: Business,
        policy: Policy,
        conditions: Dict[str, Any],
    ) -> SimulationResult:
        return SimulationResult(
            base_rate=65.0,
            simulated_rate=88.5,
            gain_factors=["신규 고용 가점 +15점", "특허 보유 가점 +8.5점"]
        )
