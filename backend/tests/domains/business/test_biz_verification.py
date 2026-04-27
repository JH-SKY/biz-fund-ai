# backend/tests/domains/business/test_biz_verification.py
"""국세청 API 사업자번호 검증 유닛 테스트.

테스트 범위:
  - RealBizVerificationService.verify(): 계속사업자 / 휴업자 / 폐업자 / 미등록 / 타임아웃 / HTTP 오류
  - BusinessService.register_business(): 상태별 차단 로직, DB 저장, 재호출 방지, is_manual 스킵

[설계 의도]
  - 외부 HTTP 통신은 unittest.mock.AsyncMock / httpx.MockTransport 로 대체한다.
  - DB I/O는 MockRepository 를 사용하여 Service 로직만 격리 테스트한다.
  - 실제 국세청 API 를 호출하는 통합 테스트는 별도 파일(test_nts_integration.py)에서 관리한다.
"""

from __future__ import annotations

import pytest
import httpx

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.app.domains.business.interfaces import (
    BizVerificationResult,
    NTS_ERR_TIMEOUT,
    NTS_ERR_API_ERROR,
    NTS_ERR_NOT_REGISTERED,
    NTS_ERR_SERVER_CONFIG,
    NTS_ERR_NO_DATA,
    RealBizVerificationService,
)


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def _nts_response(b_stt: str, tax_type: str = "부가가치세 일반과세자") -> dict:
    """국세청 API 응답 본문 픽스처."""
    return {
        "status_code": "OK",
        "data": [
            {
                "b_no": "1234567890",
                "b_stt": b_stt,
                "b_stt_cd": "01",
                "tax_type": tax_type,
                "tax_type_cd": "1",
                "end_dt": "",
                "utcc_yn": "N",
                "tax_type_change_dt": "",
                "invoice_apply_dt": "",
                "rbf_tax_type": "",
                "rbf_tax_type_cd": "",
            }
        ],
    }


# ── RealBizVerificationService 단위 테스트 ────────────────────────────────────


class TestRealBizVerificationService:
    """국세청 API 직접 호출 서비스 — HTTP 응답 Mock 기반 테스트."""

    @pytest.mark.asyncio
    async def test_계속사업자_is_valid_true(self):
        """계속사업자: is_valid=True, error_code=None."""
        svc = RealBizVerificationService()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _nts_response("계속사업자")
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            httpx.AsyncClient, "post", new=AsyncMock(return_value=mock_response)
        ), patch("src.app.domains.business.interfaces.NTS_API_KEY", "fake-key"):
            result = await svc.verify("1234567890")

        assert result.is_valid is True
        assert result.biz_status == "계속사업자"
        assert result.tax_type == "부가가치세 일반과세자"
        assert result.error_code is None

    @pytest.mark.asyncio
    async def test_휴업자_is_valid_false(self):
        """휴업자: is_valid=False, error_code=None (상태 값 그대로 반환)."""
        svc = RealBizVerificationService()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _nts_response("휴업자")
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            httpx.AsyncClient, "post", new=AsyncMock(return_value=mock_response)
        ), patch("src.app.domains.business.interfaces.NTS_API_KEY", "fake-key"):
            result = await svc.verify("1234567890")

        assert result.is_valid is False
        assert result.biz_status == "휴업자"
        assert result.error_code is None

    @pytest.mark.asyncio
    async def test_폐업자_is_valid_false(self):
        """폐업자: is_valid=False, error_code=None (상태 값 그대로 반환)."""
        svc = RealBizVerificationService()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _nts_response("폐업자")
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            httpx.AsyncClient, "post", new=AsyncMock(return_value=mock_response)
        ), patch("src.app.domains.business.interfaces.NTS_API_KEY", "fake-key"):
            result = await svc.verify("1234567890")

        assert result.is_valid is False
        assert result.biz_status == "폐업자"
        assert result.error_code is None

    @pytest.mark.asyncio
    async def test_국세청_미등록_번호(self):
        """미등록 번호: is_valid=False, error_code=NOT_REGISTERED."""
        svc = RealBizVerificationService()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _nts_response(
            "국세청에 등록되지 않은 사업자등록번호입니다."
        )
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            httpx.AsyncClient, "post", new=AsyncMock(return_value=mock_response)
        ), patch("src.app.domains.business.interfaces.NTS_API_KEY", "fake-key"):
            result = await svc.verify("0000000000")

        assert result.is_valid is False
        assert result.error_code == NTS_ERR_NOT_REGISTERED

    @pytest.mark.asyncio
    async def test_data_배열_비어있음(self):
        """data 배열 없음: error_code=NO_DATA."""
        svc = RealBizVerificationService()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status_code": "OK", "data": []}
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            httpx.AsyncClient, "post", new=AsyncMock(return_value=mock_response)
        ), patch("src.app.domains.business.interfaces.NTS_API_KEY", "fake-key"):
            result = await svc.verify("1234567890")

        assert result.is_valid is False
        assert result.error_code == NTS_ERR_NO_DATA

    @pytest.mark.asyncio
    async def test_타임아웃_error_code_반환(self):
        """API 타임아웃: error_code=TIMEOUT, is_valid=False."""
        svc = RealBizVerificationService()

        with patch.object(
            httpx.AsyncClient,
            "post",
            new=AsyncMock(side_effect=httpx.TimeoutException("timeout")),
        ), patch("src.app.domains.business.interfaces.NTS_API_KEY", "fake-key"):
            result = await svc.verify("1234567890")

        assert result.is_valid is False
        assert result.error_code == NTS_ERR_TIMEOUT
        assert "지연" in result.biz_status

    @pytest.mark.asyncio
    async def test_HTTP_오류_응답(self):
        """5xx 응답: error_code=API_ERROR."""
        svc = RealBizVerificationService()

        mock_response = MagicMock()
        mock_response.status_code = 500
        http_error = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )

        with patch.object(
            httpx.AsyncClient,
            "post",
            new=AsyncMock(side_effect=http_error),
        ), patch("src.app.domains.business.interfaces.NTS_API_KEY", "fake-key"):
            result = await svc.verify("1234567890")

        assert result.is_valid is False
        assert result.error_code == NTS_ERR_API_ERROR

    @pytest.mark.asyncio
    async def test_API_키_없음_서버_설정_오류(self):
        """NTS_API_KEY 미설정: error_code=SERVER_CONFIG."""
        svc = RealBizVerificationService()

        with patch("src.app.domains.business.interfaces.NTS_API_KEY", ""):
            result = await svc.verify("1234567890")

        assert result.is_valid is False
        assert result.error_code == NTS_ERR_SERVER_CONFIG


# ── BusinessService.register_business 단위 테스트 ────────────────────────────


class _MockRepo:
    """BusinessRepository 의존성 대체 Mock."""

    def __init__(self, verified_cache: "BizVerificationResult | None" = None):
        self._verified_cache = verified_cache
        self.created_biz: MagicMock | None = None
        self.created_snap: MagicMock | None = None
        self._active_biz_for_user = None  # 1인 1사업장: 기본 없음

    async def get_active_business_by_user_id(self, _user_id):
        return self._active_biz_for_user

    async def get_business_by_biz_no(self, biz_no: str):
        return None  # 중복 없음

    async def get_verified_business_by_biz_no(self, biz_no: str):
        if self._verified_cache:
            biz = MagicMock()
            biz.biz_verified_status = self._verified_cache.biz_status
            biz.tax_type = self._verified_cache.tax_type
            biz.biz_verified_at = datetime.now(timezone.utc)
            return biz
        return None

    async def create_business(self, **kwargs):
        biz = MagicMock()
        for k, v in kwargs.items():
            setattr(biz, k, v)
        biz.id = "fake-uuid"
        biz.biz_name = kwargs.get("biz_name", "테스트 업체")
        biz.biz_no = kwargs.get("biz_no", "1234567890")
        self.created_biz = biz
        return biz

    async def create_financial_snapshot(self, **kwargs):
        snap = MagicMock()
        self.created_snap = snap
        return snap

    async def update_business(self, biz, **kwargs):
        for k, v in kwargs.items():
            setattr(biz, k, v)


def _make_service(mock_repo, biz_verification_result: BizVerificationResult):
    """BusinessService 조립 헬퍼."""
    from src.app.domains.business.service import BusinessService

    session = AsyncMock()
    session.commit = AsyncMock()

    biz_svc = AsyncMock()
    biz_svc.verify = AsyncMock(return_value=biz_verification_result)

    return BusinessService(
        session=session,
        repo=mock_repo,
        biz_verification=biz_svc,
        stats_validation=AsyncMock(),
        file_storage=AsyncMock(),
    )


def _make_register_body(is_manual: bool = False):
    from datetime import date

    from src.app.domains.business.schema import OnboardingRegisterRequest

    return OnboardingRegisterRequest(
        biz_name="테스트 업체",
        biz_no="1234567890",
        ksic_code="56111",
        ksic_name="한식 일반 음식점업",
        establishment_date=date(2020, 1, 1),
        is_manual=is_manual,
    )


def _make_user():
    user = MagicMock()
    user.id = "fake-user-uuid"
    return user


class TestBusinessServiceRegister:
    """BusinessService.register_business 상태별 동작 검증."""

    @pytest.mark.asyncio
    async def test_계속사업자_등록_성공(self):
        """계속사업자: DB 저장 성공, is_biz_no_verified=True."""
        repo = _MockRepo()
        result = BizVerificationResult(
            is_valid=True, biz_status="계속사업자", tax_type="부가가치세 일반과세자"
        )
        svc = _make_service(repo, result)

        data = await svc.register_business(_make_user(), _make_register_body())

        assert data.biz_no == "1234567890"
        assert repo.created_biz.is_biz_no_verified is True
        assert repo.created_biz.biz_verified_status == "계속사업자"

    @pytest.mark.asyncio
    async def test_폐업자_등록_차단_422(self):
        """폐업자: HTTPException 422 발생."""
        from fastapi import HTTPException

        repo = _MockRepo()
        result = BizVerificationResult(is_valid=False, biz_status="폐업자")
        svc = _make_service(repo, result)

        with pytest.raises(HTTPException) as exc_info:
            await svc.register_business(_make_user(), _make_register_body())

        assert exc_info.value.status_code == 422
        assert "폐업" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_휴업자_등록_차단_422(self):
        """휴업자: HTTPException 422 발생."""
        from fastapi import HTTPException

        repo = _MockRepo()
        result = BizVerificationResult(is_valid=False, biz_status="휴업자")
        svc = _make_service(repo, result)

        with pytest.raises(HTTPException) as exc_info:
            await svc.register_business(_make_user(), _make_register_body())

        assert exc_info.value.status_code == 422
        assert "휴업" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_타임아웃_503_반환(self):
        """API 타임아웃: HTTPException 503 발생."""
        from fastapi import HTTPException

        repo = _MockRepo()
        result = BizVerificationResult(
            is_valid=False,
            biz_status="국세청 서버 응답 지연",
            error_code=NTS_ERR_TIMEOUT,
        )
        svc = _make_service(repo, result)

        with pytest.raises(HTTPException) as exc_info:
            await svc.register_business(_make_user(), _make_register_body())

        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_API_오류_503_반환(self):
        """API 오류(5xx): HTTPException 503 발생."""
        from fastapi import HTTPException

        repo = _MockRepo()
        result = BizVerificationResult(
            is_valid=False,
            biz_status="국세청 API 오류 (500)",
            error_code=NTS_ERR_API_ERROR,
        )
        svc = _make_service(repo, result)

        with pytest.raises(HTTPException) as exc_info:
            await svc.register_business(_make_user(), _make_register_body())

        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_is_manual_True_API_호출_생략(self):
        """is_manual=True: 국세청 API 미호출, is_biz_no_verified=False 로 저장."""
        repo = _MockRepo()
        # verify 가 호출되지 않아야 하므로 어떤 결과를 넣어도 무관
        svc_mock_biz = AsyncMock()
        svc_mock_biz.verify = AsyncMock(
            return_value=BizVerificationResult(is_valid=True, biz_status="계속사업자")
        )

        from src.app.domains.business.service import BusinessService

        session = AsyncMock()
        session.commit = AsyncMock()
        svc = BusinessService(
            session=session,
            repo=repo,
            biz_verification=svc_mock_biz,
            stats_validation=AsyncMock(),
            file_storage=AsyncMock(),
        )

        await svc.register_business(_make_user(), _make_register_body(is_manual=True))

        # is_manual=True 이면 verify 를 호출하지 않아야 한다
        svc_mock_biz.verify.assert_not_called()
        assert repo.created_biz.is_biz_no_verified is False

    @pytest.mark.asyncio
    async def test_이미_검증된_번호_재호출_생략(self):
        """DB 캐시(is_biz_no_verified=True) 히트 시 verify 미호출."""
        cached_result = BizVerificationResult(
            is_valid=True, biz_status="계속사업자", tax_type="부가가치세 일반과세자"
        )
        repo = _MockRepo(verified_cache=cached_result)
        svc = _make_service(repo, BizVerificationResult(is_valid=False))  # 호출되면 안 됨

        # svc._biz_verification.verify 가 호출되지 않아야 함
        await svc.register_business(_make_user(), _make_register_body())

        svc._biz_verification.verify.assert_not_called()
        assert repo.created_biz.is_biz_no_verified is True
