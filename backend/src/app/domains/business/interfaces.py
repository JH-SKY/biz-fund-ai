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

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import httpx
from src.app.core.config import NTS_API_KEY

logger = logging.getLogger(__name__)

# 국세청 API 호출 타임아웃 (초). 점검 시 응답 지연을 방어한다.
_NTS_TIMEOUT_SECONDS: float = 5.0

# 국세청 API 에러 코드 상수 — schema/service에서 분기 판단에 사용
NTS_ERR_TIMEOUT = "TIMEOUT"            # 응답 없음 / 점검 중
NTS_ERR_API_ERROR = "API_ERROR"        # HTTP 4xx/5xx
NTS_ERR_NO_DATA = "NO_DATA"            # 조회 결과 없음
NTS_ERR_NOT_REGISTERED = "NOT_REGISTERED"  # 국세청 미등록 번호
NTS_ERR_SERVER_CONFIG = "SERVER_CONFIG"    # 서버 환경 변수 누락


# ── 데이터 클래스 (내부 통신 DTO) ──────────────────────────────────────────


@dataclass
class BizVerificationResult:
    """국세청 진위 확인 / 상태조회 결과.

    error_code: 실패 원인 코드. None 이면 정상 응답.
      - NTS_ERR_TIMEOUT        : 국세청 API 응답 없음 (점검 / 느린 응답)
      - NTS_ERR_API_ERROR      : HTTP 오류 응답
      - NTS_ERR_NO_DATA        : data 배열이 비어 있음
      - NTS_ERR_NOT_REGISTERED : 국세청 미등록 사업자번호
      - NTS_ERR_SERVER_CONFIG  : NTS_API_KEY 환경변수 미설정
    """

    is_valid: bool
    biz_status: str | None = None
    tax_type: str | None = None
    error_code: str | None = None


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
    ) -> StatsValidationResult: ...


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


class RealBizVerificationService(IBizVerificationService):
    """국세청 공공데이터포털 사업자등록정보 상태조회 실연동.

    설계 원칙:
      - httpx.TimeoutException 을 별도 처리하여 API 점검 중 상황을 명확히 전달.
      - 이미 검증된 사업자번호(is_biz_no_verified=True)는 Service 레이어에서 이
        메서드를 호출하지 않으므로, 여기서는 매번 실제 API를 호출한다.
    """

    async def verify(self, biz_no: str) -> BizVerificationResult:
        # [1] 환경 변수 누락 — 서버 설정 문제
        if not NTS_API_KEY:
            logger.error("NTS_API_KEY 환경변수가 설정되지 않았습니다.")
            return BizVerificationResult(
                is_valid=False,
                biz_status="서버 설정 오류",
                error_code=NTS_ERR_SERVER_CONFIG,
            )

        url = "https://api.odcloud.kr/api/nts-businessman/v1/status"
        params = {"serviceKey": NTS_API_KEY}
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        payload = {"b_no": [biz_no]}

        async with httpx.AsyncClient(timeout=_NTS_TIMEOUT_SECONDS) as client:
            try:
                response = await client.post(
                    url, params=params, json=payload, headers=headers
                )
                response.raise_for_status()
                data = response.json()

                # [2] data 배열 비어있음 — 조회 불가
                if not data.get("data"):
                    return BizVerificationResult(
                        is_valid=False,
                        biz_status="조회 결과 없음",
                        error_code=NTS_ERR_NO_DATA,
                    )

                item = data["data"][0]
                b_stt: str = item.get("b_stt", "")
                tax_type: str = item.get("tax_type", "")

                # [3] 국세청 미등록 번호
                if "등록되지 않은" in b_stt:
                    return BizVerificationResult(
                        is_valid=False,
                        biz_status=b_stt,
                        error_code=NTS_ERR_NOT_REGISTERED,
                    )

                # [4] 상태별 is_valid 판정
                #   정책 지원 기준: '계속사업자'만 유효, 휴업·폐업은 False
                is_valid = b_stt == "계속사업자"
                return BizVerificationResult(
                    is_valid=is_valid,
                    biz_status=b_stt,
                    tax_type=tax_type or None,
                )

            except httpx.TimeoutException:
                # [5] 타임아웃 — 국세청 점검 또는 응답 지연
                logger.warning("국세청 API 타임아웃 (biz_no=%s)", biz_no)
                return BizVerificationResult(
                    is_valid=False,
                    biz_status="국세청 서버 응답 지연",
                    error_code=NTS_ERR_TIMEOUT,
                )
            except httpx.HTTPStatusError as exc:
                # [6] 4xx/5xx HTTP 오류 응답
                logger.error(
                    "국세청 API HTTP 오류 (biz_no=%s, status=%s)",
                    biz_no,
                    exc.response.status_code,
                )
                return BizVerificationResult(
                    is_valid=False,
                    biz_status=f"국세청 API 오류 ({exc.response.status_code})",
                    error_code=NTS_ERR_API_ERROR,
                )
            except Exception:
                # [7] 그 외 네트워크 장애 등
                logger.exception("국세청 API 알 수 없는 오류 (biz_no=%s)", biz_no)
                return BizVerificationResult(
                    is_valid=False,
                    biz_status="국세청 서버 통신 장애",
                    error_code=NTS_ERR_API_ERROR,
                )


# ── Mock 구현체 ─────────────────────────────────────────────────────────────


class MockStatsValidationService(IStatsValidationService):
    """통계 검증 Mock — 단순 임계값 초과 시 경고.

    추후 AI 기반 업종별 평균 비교 로직으로 교체 가능.
    컨텍스트 pass-through: sector_code는 현재 미사용이지만
    실제 AI 엔진 연결 시 그대로 전달될 수 있도록 시그니처에 유지.
    """

    _THRESHOLDS: dict[str, int] = {
        "REVENUE": 100_000_000_000,  # 1,000억 원 초과 시 경고
        "EMPLOYEE_COUNT": 5_000,  # 5,000명 초과 시 경고
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
