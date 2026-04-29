# src/app/domains/diagnosis/interfaces.py
"""정밀진단 엔진 인터페이스(ABC) 및 목(Mock) 구현체.

아키텍처 원칙:
  - IDiagnosisEngine 을 통해 DiagnosisService 는 엔진 구현을 모른다.
  - 현재 운영 엔진: RuleBasedDiagnosisEngine (rule_engine.py)
  - 테스트·개발 환경에서는 MockDiagnosisEngine 을 사용할 수 있다.
"""

from abc import ABC, abstractmethod
from typing import Any

from src.app.domains.business.model import Business
from src.app.domains.diagnosis.schema import DiagnosisFinalInputs
from src.app.domains.policy.model import Policy


class DiagnosisResult:
    """진단 엔진이 반환하는 결과 DTO.

    [필드 설명]
    - total_score  : 총점 (0~100)
    - grade        : 등급 (EXCELLENT / GOOD / NORMAL / RISK)
    - scores       : 4개 축별 점수 딕셔너리
    - summary      : 사람이 읽을 수 있는 진단 요약 문장
    - strengths    : 강점 목록 (최대 4개)
    - risk_signals : 리스크 신호 목록 (최대 4개)
    - action_items : 개선 행동 목록 (최대 4개)
    - traffic_light: 신호등 (RED / YELLOW / GREEN)
    """

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
    """시뮬레이션 엔진이 반환하는 결과 DTO.

    [필드 설명]
    - base_rate      : 현재 조건 기준 점수
    - simulated_rate : 가상 조건 적용 후 점수
    - gain_factors   : 점수 변화 원인 설명 문장 목록
    """

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
    """사업 진단 및 시뮬레이션 엔진 인터페이스.

    이 인터페이스를 구현하면 규칙 기반, AI 기반 등 다양한 엔진을
    Service 코드 변경 없이 교체할 수 있다.
    """

    @abstractmethod
    async def execute_diagnosis(
        self,
        business: Business,
        year: int,
        inputs: DiagnosisFinalInputs,
        use_ai: bool = True,
    ) -> DiagnosisResult:
        """사업 건강도 진단을 실행하고 결과를 반환한다."""

    @abstractmethod
    async def execute_simulation(
        self,
        business: Business,
        policy: Policy | None,
        conditions: dict[str, Any],
    ) -> SimulationResult:
        """가상 조건 시뮬레이션을 실행하고 결과를 반환한다."""


class MockDiagnosisEngine(IDiagnosisEngine):
    """하위 호환성 유지를 위해 남겨둔 레거시 목(Mock) 엔진.

    실제 서비스에서는 RuleBasedDiagnosisEngine 을 사용하며,
    이 클래스는 의존성 주입 테스트나 CI 환경에서만 활용한다.
    """

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
