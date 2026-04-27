"""정밀진단 도메인 Pydantic 스키마."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class SnapshotData(BaseModel):
    revenue: Optional[int] = None
    employee_count: Optional[int] = None
    biz_sector: Optional[str] = None


class PrepareDiagnosisResponseData(BaseModel):
    current_snapshot: SnapshotData
    missing_fields: List[str]
    message: str
    suggest_nts_reverification: bool = Field(
        False,
        description="사업자번호 국세청 미검증이면 True — 재검증(POST /businesses/verify-biz-retry) 안내에 사용",
    )


class DiagnosisFinalInputs(BaseModel):
    """정밀진단 최종 입력 — 신호등·심사형 로직에 필요한 최소 항목을 고정한다."""

    has_tax_arrears: bool = Field(
        ...,
        description="국세·지방세 체납(미완납) 여부. True면 사실상 결격(빨강) 축.",
    )
    annual_revenue: Optional[int] = Field(None, ge=0, description="연매출(원, 근사)")
    total_debt: Optional[int] = Field(None, ge=0, description="총부채(원, 근사)")
    debt_ratio: Optional[float] = Field(
        None, ge=0, le=100_000, description="부채비율(%) — 미입력 시 매출·부채로 산정"
    )
    employee_count: int = Field(..., ge=0, description="상시 근로자 수(대략)")
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
            dr = round(self.total_debt / self.annual_revenue * 100, 2)
            return self.model_copy(update={"debt_ratio": dr})
        return self


class ExecuteDiagnosisRequest(BaseModel):
    year: int = Field(..., description="진단 기준 연도")
    use_ai_analysis: bool = Field(default=True, description="AI 분석 사용 여부")
    final_inputs: DiagnosisFinalInputs = Field(..., description="최종 확정 심사형 입력")


class ExecuteDiagnosisResponseData(BaseModel):
    diagnosis_id: str
    total_score: float
    grade: str
    created_at: datetime
    traffic_light: str = Field(
        "GREEN",
        description="심사형 신호등: RED | YELLOW | GREEN",
    )


class DiagnosisScores(BaseModel):
    stability: float
    growth: float
    tech: float


class DiagnosisDetailResponseData(BaseModel):
    diagnosis_id: str
    scores: DiagnosisScores
    ai_comment: str
    snapshot: Dict[str, Any]


class DiagnosisHistoryItem(BaseModel):
    diagnosis_id: str
    score: float
    date: str


class ExecuteSimulationRequest(BaseModel):
    policy_id: uuid.UUID
    virtual_conditions: Dict[str, Any]


class ExecuteSimulationResponseData(BaseModel):
    base_rate: float
    simulated_rate: float
    gain_factors: List[str]


class SimulationHistoryItem(BaseModel):
    policy_title: str
    sim_rate: float
    created_at: str
