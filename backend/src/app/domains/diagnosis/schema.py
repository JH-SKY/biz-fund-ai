"""정밀진단 도메인 Pydantic 스키마."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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


class ExecuteDiagnosisRequest(BaseModel):
    year: int = Field(..., description="진단 기준 연도")
    use_ai_analysis: bool = Field(default=True, description="AI 분석 사용 여부")
    final_inputs: Dict[str, Any] = Field(..., description="최종 확인된 데이터")


class ExecuteDiagnosisResponseData(BaseModel):
    diagnosis_id: str
    total_score: float
    grade: str
    created_at: datetime


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
