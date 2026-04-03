# src/app/domains/business/interfaces.py
"""외부 서비스 인터페이스 (Protocol) 및 Mock 구현체.

아키텍처 원칙 (확장성 중심):
  - 국세청 진위 확인 / 파일 저장소(S3) / 통계 검증 같은 외부 의존성은
    모두 ABC 인터페이스 뒤에 숨긴다.
  - 현재는 Mock 구현체를 사용하며, 실제 서비스 연동 시에는
    새 구현 클래스만 추가하고 DI factory(business_deps.py)만 교체한다.
  - Service 레이어는 인터페이스만 알고 구현체를 모른다.

RAG/LangGraph 연동 준비:
  - IStatsValidationService 는 추후 AI 추론 서비스로 교체 가능.
  - IFileStorageService 는 추후 실제 S3 + 비동기 OCR 큐로 교체 가능.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


# ── 데이터 클래스 (내부 통신 DTO) ──────────────────────────────────────────


@dataclass
class BizVerificationResult:
    """국세청 진위 확인 / 상태조회 결과.

    - nts_status_row: 공공데이터포털 「사업자등록정보 상태조회 API」 응답의
      `data` 배열 원소와 동일한 키를 갖는 dict (문서·샘플 기준).
      실연동 시 파서가 이 dict를 채우고, 프론트는 기존 필드 + 원본 행을 동시에 쓸 수 있다.
    """

    is_valid: bool
    company_name: str | None = None
    biz_status: str | None = None
    open_date: str | None = None
    nts_status_row: dict[str, Any] | None = None


# 국세청 사업자등록정보 상태조회 API — 응답 `data[]` 항목 필드명 샘플
# (공공데이터포털 OpenAPI 명세·연동 가이드와 동일한 스키마를 목표로 함)
_NTS_STATUS_ROW_KEYS = (
    "b_no",
    "b_stt",
    "b_stt_cd",
    "tax_type",
    "tax_type_cd",
    "end_dt",
    "utcc_yn",
    "tax_type_change_dt",
    "invoice_apply_dt",
    "rprs_nm",
    "hq_yn",
    "b_nm",
    "corp_no",
)


@dataclass
class StatsValidationResult:
    """매출·인원 이상치 검증 결과."""

    is_valid: bool
    message: str


# ── 인터페이스 (ABC) ────────────────────────────────────────────────────────


class IBizVerificationService(ABC):
    """사업자번호 진위 확인 외부 API 인터페이스.

    실제 연동 대상: 국세청 사업자등록정보 진위확인 API
    (https://www.data.go.kr/tcs/dss/selectApiDataDetailView.do?publicDataPk=15081808)
    """

    @abstractmethod
    async def verify(self, biz_no: str) -> BizVerificationResult:
        """10자리 숫자 사업자번호를 받아 활동 여부 및 기본 정보를 반환."""
        ...


class IStatsValidationService(ABC):
    """업종 평균 대비 매출·인원 이상치 검증 인터페이스.

    추후 AI 추론 모델 또는 통계 API로 교체 가능.
    RAG/LangGraph 연동 시 이 인터페이스에 컨텍스트(sector_code 등)를 전달한다.
    """

    @abstractmethod
    async def validate(
        self,
        stat_type: str,
        value: int,
        sector_code: str | None = None,
    ) -> StatsValidationResult:
        ...


class IFileStorageService(ABC):
    """파일 저장소(S3 등) 인터페이스.

    실제 연동: AWS S3 또는 GCS. 비동기 OCR 큐 디스패치도 여기서 처리.
    """

    @abstractmethod
    async def upload(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        """파일을 저장하고 접근 가능한 URL을 반환."""
        ...

    @abstractmethod
    async def delete(self, file_url: str) -> None:
        """저장소에서 파일을 영구 삭제."""
        ...


# ── Mock 구현체 ─────────────────────────────────────────────────────────────


class MockBizVerificationService(IBizVerificationService):
    """국세청 API Mock.

    [도메인 규칙 2.1 Fallback]: 외부 API 미연동 단계에서 고정 응답 반환.
    실제 API 연동 시: RealBizVerificationService 구현 후 business_deps.py만 교체.

    nts_status_row 는 상태조회 API의 data[] 한 행과 필드명을 맞춘다
    (b_stt=계속사업자, rprs_nm, b_nm 등). 진위확인 전용 코드값은 연동 시 별도 매핑.
    """

    async def verify(self, biz_no: str) -> BizVerificationResult:
        row: dict[str, Any] = {
            "b_no": biz_no,
            "b_stt": "계속사업자",
            "b_stt_cd": "01",
            "tax_type": "부가가치세 일반과세자",
            "tax_type_cd": "01",
            "end_dt": "",
            "utcc_yn": "N",
            "tax_type_change_dt": "",
            "invoice_apply_dt": "",
            "rprs_nm": "이종혁",
            "hq_yn": "N",
            "b_nm": "라이언테크",
            "corp_no": "",
        }
        # 키 누락 방지(실연동 파서도 동일 스키마로 normalize 권장)
        for k in _NTS_STATUS_ROW_KEYS:
            row.setdefault(k, "")
        return BizVerificationResult(
            is_valid=True,
            company_name=row.get("b_nm"),
            biz_status=row.get("b_stt"),
            open_date="20240101",
            nts_status_row=row,
        )


class MockStatsValidationService(IStatsValidationService):
    """통계 검증 Mock — 단순 임계값 초과 시 경고.

    추후 AI 기반 업종별 평균 비교 로직으로 교체 가능.
    컨텍스트 pass-through: sector_code는 현재 미사용이지만
    실제 AI 엔진 연결 시 그대로 전달될 수 있도록 시그니처에 유지.
    """

    _THRESHOLDS: dict[str, int] = {
        "REVENUE": 100_000_000_000,  # 1,000억 원 초과 시 경고
        "EMPLOYEE_COUNT": 5_000,      # 5,000명 초과 시 경고
    }

    async def validate(
        self,
        stat_type: str,
        value: int,
        sector_code: str | None = None,
    ) -> StatsValidationResult:
        threshold = self._THRESHOLDS.get(stat_type)
        if threshold and value > threshold:
            return StatsValidationResult(
                is_valid=False,
                message="입력하신 값이 업종 평균을 크게 초과합니다. 단위(원)를 다시 확인해 주세요.",
            )
        return StatsValidationResult(
            is_valid=True,
            message="정상 범위의 입력값입니다.",
        )


class MockFileStorageService(IFileStorageService):
    """S3 Mock — 로컬/개발 환경용 가짜 URL 반환.

    실제 연동 시: boto3 기반 S3FileStorageService 구현 후 교체.
    OCR 비동기 큐(Celery/ARQ 등) 디스패치도 upload() 완료 후 여기에 추가.
    """

    async def upload(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        return f"https://mock-s3.bizup.com/docs/{filename}"

    async def delete(self, file_url: str) -> None:
        pass
