# src/app/core/exceptions.py
"""FastAPI 전역 예외 처리 — 프론트엔드([PAGE 03] 등)와 공통 계약 유지."""

from __future__ import annotations

from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _friendly_message_for_validation_errors(errors: list) -> str:
    """
    [주석 1. 입력값 검증 메시지 처리]
    사용자가 폼을 잘못 채웠을 때, 딱딱한 개발 용어 대신 사장님이 이해하기 쉬운 말로 바꿔주는 '통역사' 역할이에요.
    """
    for err in errors:
        if not isinstance(err, dict):
            continue
        loc = err.get("loc") or ()
        parts = list(loc) if isinstance(loc, (list, tuple)) else []
        
        # 1. 특정 필드(사업자번호 등)에 맞춤형 메시지 제공
        if parts and parts[-1] == "biz_no":
            return "사장님, 번호를 다시 확인해주세요."
            
    # 2. 그 외 기본 메시지
    return "입력값을 다시 확인해주세요."


async def request_validation_exception_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """
    [주석 2. 422 에러 핸들러]
    입력값 형식이 틀렸을 때(422) 호출되며, 에러 정보를 예쁘게 포장해서 프론트엔드로 전달하는 '포장지'입니다.
    """
    raw_errors = exc.errors()
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "message": _friendly_message_for_validation_errors(raw_errors),
            "detail": jsonable_encoder(raw_errors),
        },
    )


async def base_app_exception_handler(
    _request: Request,
    exc: "BaseAppException",
) -> JSONResponse:
    """도메인 예외를 공통 응답 형식으로 변환한다."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": exc.status_code,
            "message": exc.message,
        },
    )


# --- 커스텀 예외 정의 구간 ---

class BaseAppException(Exception):
    """
    [주석 3. 에러의 큰 뿌리 (부모 클래스)]
    우리 서비스에서 발생하는 모든 예외들이 공통적으로 가져야 할 '상태 코드'와 '안내 문구'라는 그릇을 미리 만들어 둔 것이에요.
    """
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message


class ForbiddenException(BaseAppException):
    """1. 권한 없음: '사장님, 여기는 들어오실 수 없어요' (403)"""
    def __init__(self, message: str = "권한이 없습니다."):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, message=message)


class NotFoundException(BaseAppException):
    """2. 찾지 못함: '요청하신 데이터를 찾을 수 없어요' (404)"""
    def __init__(self, message: str = "존재하지 않는 리소스입니다."):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, message=message)


class RateLimitException(BaseAppException):
    """
    3. 요청 횟수 초과: '사장님, 너무 빨리 요청하셨어요' (429)
    이 에러는 식당의 '웨이팅 대기표'와 같아요. 서버 부하와 AI API 비용 폭탄을 막기 위해 잠시 멈추게 합니다.
    """
    def __init__(self, message: str = "요청 횟수가 너무 많습니다. 잠시 후 다시 시도해주세요."):
        super().__init__(status_code=status.HTTP_429_TOO_MANY_REQUESTS, message=message)


class ServiceUnavailableException(BaseAppException):
    """4. 서비스 점검 중: '잠시 후 다시 시도해주세요' (503)"""
    def __init__(self, message: str = "서비스를 일시적으로 사용할 수 없습니다."):
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, message=message)

    
