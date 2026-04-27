# src/app/domains/business/schema.py
"""사업장 도메인 Pydantic 요청/응답 스키마.

검증 규칙:
  - biz_no: 하이픈·공백 제거 후 반드시 10자리 숫자 (사업자등록번호 형식)
  - 금액 필드(annual_revenue, total_debt 등): 0 이상의 정수
  - employee_count: 0 이상의 정수 (0명 포함 가능)
"""

from __future__ import annotations

import re
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class FundingPurpose(StrEnum):
    """자금(지원) 용도 — 온보딩/매칭 시설·운전 구분에 사용."""

    FACILITY = "FACILITY"  # 시설·기계·도입
    OPERATING = "OPERATING"  # 운영·인건비
    WORKING = "WORKING"  # 운전(유동) 자금
    MIXED = "MIXED"  # 복합
    UNSURE = "UNSURE"  # 미정


# ── 공통 사업자번호 Validator ───────────────────────────────────────────────


def _normalize_biz_no(v: str) -> str:
    """하이픈·공백 제거 후 10자리 숫자 검증.

    허용 입력: "1234567890" 또는 "123-45-67890"
    저장 형태: "1234567890" (10자리 숫자, 하이픈 없음)
    """
    cleaned = re.sub(r"[-\s]", "", v)
    if not re.fullmatch(r"\d{10}", cleaned):
        raise ValueError(
            "사업자등록번호는 10자리 숫자여야 합니다. (예: 1234567890 또는 123-45-67890)"
        )
    return cleaned


# ── 온보딩 ─────────────────────────────────────────────────────────────────


class OnboardingRegisterRequest(BaseModel):
    """[PAGE 03] 온보딩 완료 시 사업장 최초 등록."""

    biz_name: str = Field(..., min_length=1, max_length=100, description="상호명")
    biz_no: str = Field(
        ...,
        description="사업자등록번호 (10자리 숫자 또는 000-00-00000 형식)",
    )
    representative_name: Optional[str] = Field(None, max_length=50, description="대표자명")
    ksic_code: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="KSIC 세세분류 코드 (예: 56111)",
    )
    ksic_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="KSIC 세세분류 표시명 (예: 한식 일반 음식점업)",
    )
    sector_code: Optional[str] = Field(
        None,
        max_length=20,
        description="세부 업종 코드 (미전달 시 ksic_code와 동일하게 저장될 수 있음)",
    )
    region_sido: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="시·도 (필수 — 프론트에서 반드시 선택)",
    )
    region_sigungu: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="시·군·구 (필수)",
    )
    establishment_date: date = Field(
        ...,
        description="개업일 (필수 — 정책 매칭·업력 산정)",
    )
    employee_count: int = Field(
        ...,
        ge=0,
        description="상시 근로자 수(대략) — 소상공인/중소 구분·추천에 필수",
    )
    funding_purpose: FundingPurpose = Field(
        default=FundingPurpose.UNSURE,
        description="필요 자금 용도(시설/운영/운전 등)",
    )
    has_patent: bool = Field(False, description="특허 보유 여부")
    is_female_ent: bool = Field(False, description="여성 기업 여부")
    is_ventured: bool = Field(False, description="벤처 기업 여부")
    is_manual: bool = Field(
        False,
        description="수동 입력 모드 플래그 (외부 API 호출 실패 시 True)",
    )

    @field_validator("region_sido", "region_sigungu", mode="before")
    @classmethod
    def _strip_region(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("biz_no")
    @classmethod
    def validate_biz_no(cls, v: str) -> str:
        return _normalize_biz_no(v)


class OnboardingRegisterResponseData(BaseModel):
    biz_id: str
    biz_name: str
    biz_no: str
    is_manual: bool
    profile_score: int


class VerifyBizNumberRequest(BaseModel):
    """사업자번호 진위 확인 요청."""

    biz_no: str = Field(..., description="사업자등록번호")

    @field_validator("biz_no")
    @classmethod
    def validate_biz_no(cls, v: str) -> str:
        return _normalize_biz_no(v)


class VerifyBizNumberResponseData(BaseModel):
    is_valid: bool = Field(..., description="유효한 계속사업자 여부")
    biz_status: Optional[str] = Field(None, description="계속사업자, 휴업자, 폐업자 등 국세청 상태")
    tax_type: Optional[str] = Field(None, description="부가가치세 일반과세자 등")
    error_code: Optional[str] = Field(
        None,
        description=(
            "API 실패 원인 코드. 성공 시 null. "
            "TIMEOUT | API_ERROR | NO_DATA | NOT_REGISTERED | SERVER_CONFIG"
        ),
    )
    # 기획 변경에 따라 company_name, open_date 등은 서버가 주지 않고 유저가 직접 입력합니다.

# ── 사업장 조회 / 수정 ──────────────────────────────────────────────────────


class BusinessInfoResponseData(BaseModel):
    biz_id: str
    biz_name: str
    biz_no: Optional[str] = None
    representative_name: Optional[str] = None
    region_sido: Optional[str] = None
    region_sigungu: Optional[str] = None
    establishment_date: Optional[date] = None
    ksic_code: Optional[str] = None
    ksic_name: Optional[str] = None
    sector_code: Optional[str] = None
    is_biz_no_verified: bool = Field(
        False, description="국세청 사업자진위·상태검증 완료 여부"
    )
    employee_count: Optional[int] = None
    funding_purpose: Optional[str] = None
    has_tax_arrears: bool = False
    has_patent: bool
    is_female_ent: bool
    is_ventured: bool
    profile_score: int
    created_at: datetime


class BusinessUpdateRequest(BaseModel):
    """사업장 부분 수정 (PATCH). None 필드는 수정하지 않는다."""

    biz_name: Optional[str] = Field(None, min_length=1, max_length=100)
    representative_name: Optional[str] = Field(None, max_length=50)
    region_sido: Optional[str] = Field(None, max_length=50)
    region_sigungu: Optional[str] = Field(None, max_length=50)
    establishment_date: Optional[date] = None
    ksic_code: Optional[str] = Field(None, max_length=20)
    ksic_name: Optional[str] = Field(None, max_length=200)
    sector_code: Optional[str] = Field(None, max_length=20)
    has_patent: Optional[bool] = None
    is_female_ent: Optional[bool] = None
    is_ventured: Optional[bool] = None
    employee_count: Optional[int] = Field(None, ge=0)
    funding_purpose: Optional[FundingPurpose] = None
    has_tax_arrears: Optional[bool] = None

    @field_validator("biz_name", "representative_name", mode="before")
    @classmethod
    def strip_strings(cls, v: str | None) -> str | None:
        return v.strip() if isinstance(v, str) else v


# ── 재무 스냅샷 ────────────────────────────────────────────────────────────


class FinanceCreateRequest(BaseModel):
    """신규 재무 스냅샷 등록 (API 명세서 #4 대응)."""

    snapshot_year: int = Field(..., ge=2000, le=2100, description="기준 연도")
    snapshot_period: str = Field(
        "ANNUAL",
        description="기준 시기 (ANNUAL | 1Q | 2Q | 3Q | 4Q)",
    )
    term_type: str = Field(
        "ANNUAL",
        description="공시 주기 (ANNUAL | QUARTERLY)",
    )
    annual_revenue: Optional[int] = Field(None, ge=0, description="연매출액 (원)")
    operating_profit: Optional[int] = Field(None, description="영업이익 (원, 음수 가능)")
    net_income: Optional[int] = Field(None, description="당기순이익 (원, 음수 가능)")
    total_debt: Optional[int] = Field(None, ge=0, description="총 부채액 (원)")
    capital: Optional[int] = Field(None, ge=0, description="자본금 (원)")
    employee_count: Optional[int] = Field(None, ge=0, description="직원 수")
    tax_arrears_yn: bool = Field(False, description="세금 체납 여부")


class FinanceUpdateRequest(BaseModel):
    """기존 재무 스냅샷 부분 수정 (API 명세서 #5 대응). None 필드는 수정하지 않는다."""

    annual_revenue: Optional[int] = Field(None, ge=0)
    operating_profit: Optional[int] = None
    net_income: Optional[int] = None
    total_debt: Optional[int] = Field(None, ge=0)
    capital: Optional[int] = Field(None, ge=0)
    employee_count: Optional[int] = Field(None, ge=0)
    tax_arrears_yn: Optional[bool] = None


class FinanceSnapshotResponseData(BaseModel):
    finance_id: str
    snapshot_year: int
    snapshot_period: str
    annual_revenue: Optional[int]
    operating_profit: Optional[int]
    net_income: Optional[int]
    total_debt: Optional[int]
    capital: Optional[int]
    debt_ratio: Optional[float]
    employee_count: Optional[int]
    tax_arrears_yn: bool
    is_verified: bool
    created_at: datetime


class FinanceHistoryItemData(BaseModel):
    snapshot_year: int
    annual_revenue: Optional[int]
    operating_profit: Optional[int]
    net_income: Optional[int]
    capital: Optional[int]
    employee_count: Optional[int]
    is_verified: bool


# ── 통계 검증 ──────────────────────────────────────────────────────────────


class ValidateStatsRequest(BaseModel):
    type: str = Field(..., description="검증 유형 (REVENUE | EMPLOYEE_COUNT)")
    value: int = Field(..., ge=0)


class ValidateStatsResponseData(BaseModel):
    is_valid: bool
    message: str


# ── 서류 ───────────────────────────────────────────────────────────────────


class DocumentListItemData(BaseModel):
    document_id: str
    doc_type: str
    ocr_status: str
    created_at: datetime


class DocumentDetailResponseData(BaseModel):
    """API 명세서 #11 상세 조회 응답 — ocr_result 로 OCR 원본 데이터 제공."""

    document_id: str
    doc_type: str
    file_url: str
    ocr_status: str
    ocr_result: Optional[dict[str, Any]] = Field(
        None,
        description="OCR 추출 원본 데이터 (COMPLETED 상태일 때 채워짐)",
    )
    issued_at: Optional[date]
    created_at: datetime
