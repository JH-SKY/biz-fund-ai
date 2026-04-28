"""Pydantic schemas for diagnosis and simulation APIs."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


class SnapshotData(BaseModel):
    revenue: int | None = None
    employee_count: int | None = None
    biz_sector: str | None = None


class PrepareDiagnosisResponseData(BaseModel):
    current_snapshot: SnapshotData
    missing_fields: list[str]
    message: str
    suggest_nts_reverification: bool = Field(
        False,
        description="사업자 상태 재검증 안내가 필요한 경우 True.",
    )


class DiagnosisFinalInputs(BaseModel):
    """Minimum set of inputs used by the business diagnosis engine."""

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
    def _derive_debt_ratio(self) -> DiagnosisFinalInputs:
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
    year: int = Field(..., description="진단 기준 연도")
    use_ai_analysis: bool = Field(default=True, description="AI 분석 사용 여부")
    final_inputs: DiagnosisFinalInputs = Field(..., description="최종 입력값")


class ExecuteDiagnosisResponseData(BaseModel):
    diagnosis_id: str
    total_score: float
    grade: str
    created_at: datetime
    traffic_light: str = Field(
        "GREEN",
        description="RED | YELLOW | GREEN",
    )


class DiagnosisScores(BaseModel):
    financial_health: float
    growth_potential: float
    operational_stability: float
    risk_management: float


class DiagnosisDetailResponseData(BaseModel):
    diagnosis_id: str
    total_score: float
    grade: str
    traffic_light: str
    scores: DiagnosisScores
    summary: str
    strengths: list[str]
    risk_signals: list[str]
    action_items: list[str]
    snapshot: dict[str, Any]


class DiagnosisHistoryItem(BaseModel):
    diagnosis_id: str
    score: float
    date: str


class ExecuteSimulationRequest(BaseModel):
    policy_id: uuid.UUID | None = Field(
        None,
        description="정책별이 아닌 전체 진단 시뮬레이션이면 생략.",
    )
    virtual_conditions: dict[str, Any]


class ExecuteSimulationResponseData(BaseModel):
    base_rate: float
    simulated_rate: float
    gain_factors: list[str]


class SimulationHistoryItem(BaseModel):
    policy_title: str
    sim_rate: float
    created_at: str
