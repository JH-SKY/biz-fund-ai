# src/app/domains/diagnosis/schema.py
"""정밀진단 및 시뮬레이션 API Pydantic 요청/응답 스키마.

[스키마 구조]
- SnapshotData                   : 진단 준비 단계에서 현재 재무 스냅샷 요약
- PrepareDiagnosisResponseData   : 진단 준비 응답 (부족 항목, 재검증 안내 포함)
- DiagnosisFinalInputs           : 진단 실행 시 사용자가 최종 확인한 입력값
- ExecuteDiagnosisRequest/Response: 진단 실행 요청/응답
- DiagnosisDetailResponseData    : 진단 결과 상세 (점수·등급·신호등·강점·리스크)
- ExecuteSimulationRequest/Response: 가상 조건 시뮬레이션 요청/응답
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Self

from pydantic import BaseModel, Field, model_validator


class SnapshotData(BaseModel):
    """진단 준비 단계에서 현재 재무 스냅샷 현황을 담는 DTO."""

    revenue: int | None = None          # 연매출액 (원)
    total_debt: int | None = None       # 총부채액 (원)
    employee_count: int | None = None   # 상시 근로자 수
    biz_sector: str | None = None       # 업종 코드


class PrepareDiagnosisResponseData(BaseModel):
    """진단 준비 점검 결과 응답 DTO."""

    current_snapshot: SnapshotData      # 현재 저장된 재무 데이터
    missing_fields: list[str]           # 진단에 필요하지만 비어있는 필드 목록
    message: str                        # 사용자에게 안내할 메시지
    suggest_nts_reverification: bool = Field(
        False,
        description="사업자 상태 재검증 안내가 필요한 경우 True.",
    )


class DiagnosisFinalInputs(BaseModel):
    """진단 엔진이 사용하는 최소 입력값 집합.

    사용자가 '진단 시작' 버튼을 누르기 전 최종 확인·수정한 값을 담는다.
    debt_ratio 가 없으면 annual_revenue / total_debt 로 자동 계산한다.
    """

    has_tax_arrears: bool = Field(
        ...,
        description="현재 체납 중인 세금 또는 4대 보험료가 있는지 여부.",
    )
    annual_revenue: int | None = Field(
        None,
        ge=0,
        description="연 매출액(원).",
    )
    total_debt: int | None = Field(
        None,
        ge=0,
        description="총 부채(원).",
    )
    debt_ratio: float | None = Field(
        None,
        ge=0,
        le=100_000,
        description="부채비율(%). 미입력 시 매출/부채로 계산.",
    )
    employee_count: int = Field(..., ge=0, description="상시 근로자 수.")
    has_patent: bool = False
    is_female_ent: bool = False
    is_ventured: bool = False

    @model_validator(mode="after")
    def _derive_debt_ratio(self) -> Self:
        """debt_ratio 가 없으면 annual_revenue 와 total_debt 로 자동 계산한다."""
        if self.debt_ratio is not None:
            return self
        if (
            self.annual_revenue is not None
            and self.annual_revenue > 0
            and self.total_debt is not None
        ):
            return self.model_copy(
                update={
                    "debt_ratio": round(
                        self.total_debt / self.annual_revenue * 100,
                        2,
                    )
                }
            )
        return self


class ExecuteDiagnosisRequest(BaseModel):
    """진단 실행 요청 Body."""

    year: int = Field(..., description="진단 기준 연도")
    use_ai_analysis: bool = Field(default=True, description="AI 분석 사용 여부")
    final_inputs: DiagnosisFinalInputs = Field(..., description="최종 입력값")


class ExecuteDiagnosisResponseData(BaseModel):
    """진단 실행 응답 — 요약 결과만 포함 (상세는 별도 API로 조회)."""

    diagnosis_id: str
    total_score: float
    grade: str
    created_at: datetime
    traffic_light: str = Field(
        "GREEN",
        description="RED | YELLOW | GREEN",
    )


class DiagnosisScores(BaseModel):
    """4개 축 진단 점수 DTO."""

    financial_health: float       # 재무건전성 (가중치 40%)
    growth_potential: float       # 성장잠재력 (가중치 20%)
    operational_stability: float  # 운영안정성 (가중치 25%)
    risk_management: float        # 리스크관리 (가중치 15%)


class DiagnosisDetailResponseData(BaseModel):
    """진단 상세 결과 응답 DTO."""

    diagnosis_id: str
    total_score: float
    grade: str
    traffic_light: str
    scores: DiagnosisScores
    summary: str               # 사람이 읽을 수 있는 진단 종합 요약
    strengths: list[str]       # 강점 목록 (최대 4개)
    risk_signals: list[str]    # 리스크 신호 목록 (최대 4개)
    action_items: list[str]    # 권장 행동 목록 (최대 4개)
    snapshot: dict[str, Any]   # 진단 시점의 입력값 원본


class DiagnosisHistoryItem(BaseModel):
    """진단 이력 목록 아이템."""

    diagnosis_id: str
    score: float    # 해당 시점 총점
    date: str       # 진단 일자 (YYYY-MM-DD)


class ExecuteSimulationRequest(BaseModel):
    """시뮬레이션 실행 요청 Body."""

    policy_id: uuid.UUID | None = Field(
        None,
        description="정책별이 아닌 전체 진단 시뮬레이션이면 생략.",
    )
    virtual_conditions: dict[str, Any]  # 가상으로 바꿔볼 조건 (예: {"annual_revenue": 300000000})


class ExecuteSimulationResponseData(BaseModel):
    """시뮬레이션 결과 응답 DTO."""

    base_rate: float          # 현재 조건 점수
    simulated_rate: float     # 가상 조건 적용 후 점수
    gain_factors: list[str]   # 점수 변화 원인 설명 목록


class SimulationHistoryItem(BaseModel):
    """시뮬레이션 이력 목록 아이템."""

    policy_title: str   # 대상 정책 제목
    sim_rate: float     # 시뮬레이션 결과 점수
    created_at: str     # 실행 일자 (YYYY-MM-DD)
