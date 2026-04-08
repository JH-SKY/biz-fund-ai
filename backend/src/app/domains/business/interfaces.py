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

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx
from src.app.core.config import NTS_API_KEY
# ── 데이터 클래스 (내부 통신 DTO) ──────────────────────────────────────────


@dataclass
class BizVerificationResult:
    """국세청 진위 확인 / 상태조회 결과.

    - nts_status_row: 공공데이터포털 「사업자등록정보 상태조회 API」 응답의
      `data` 배열 원소와 동일한 키를 갖는 dict (문서·샘플 기준).
      실연동 시 파서가 이 dict를 채우고, 프론트는 기존 필드 + 원본 행을 동시에 쓸 수 있다.
    """

    is_valid: bool
    biz_status: str | None = None
    tax_type: str | None = None


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
    """국세청 공공데이터포털 사업자등록정보 상태조회 실연동"""

    async def verify(self, biz_no: str) -> BizVerificationResult:

        if not NTS_API_KEY:
            return BizVerificationResult(is_valid=False, biz_status="서버 설정 오류")

        url = "https://api.odcloud.kr/api/nts-businessman/v1/status"

        # 공공데이터포털은 Decoding 된 키 또는 Encoding 된 키 처리가 까다롭습니다.
        # 파라미터로 넘길 때 httpx가 자동 인코딩하므로 디코딩된 키를 사용하는 것이 좋습니다.
        params = {"serviceKey": NTS_API_KEY}
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        payload = {"b_no": [biz_no]}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, params=params, json=payload, headers=headers, timeout=5.0
                )
                response.raise_for_status()
                data = response.json()

                # data 배열이 비어있으면 조회가 안된 것
                if not data.get("data"):
                    return BizVerificationResult(
                        is_valid=False, biz_status="조회 결과 없음"
                    )

                item = data["data"][0]
                b_stt = item.get("b_stt", "")
                tax_type = item.get("tax_type", "")

                # 국세청 미등록 번호 처리
                if b_stt == "국세청에 등록되지 않은 사업자등록번호입니다.":
                    return BizVerificationResult(is_valid=False, biz_status=b_stt)

                # 기획 정책: '계속사업자'만 valid 처리할 것인지, 휴업/폐업도 통과시킬 것인지 결정
                # 정책자금 매칭이므로 '계속사업자'만 가입/온보딩 가능하게 설계하는 것을 추천합니다.
                is_valid = b_stt == "계속사업자"

                return BizVerificationResult(
                    is_valid=is_valid, biz_status=b_stt, tax_type=tax_type
                )
            except Exception as e:
                # API 호출 실패 시 (타임아웃 등) Fallback (is_manual=True로 우회할 수 있게)
                print(f"국세청 API 호출 에러: {e}")
                return BizVerificationResult(
                    is_valid=False, biz_status="국세청 서버 통신 지연"
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
