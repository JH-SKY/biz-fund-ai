# src/app/core/exceptions.py
"""FastAPI 전역 예외 처리 — 프론트엔드([PAGE 03] 등)와 공통 계약 유지."""

from __future__ import annotations

from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _friendly_message_for_validation_errors(errors: list) -> str:
    """Pydantic/FastAPI 검증 오류를 UX용 한 줄 메시지로 매핑.

    기본 422 응답의 detail[].msg 에도 원문이 들어가지만,
    사업자번호 등 민감 UX 구간은 톤을 통일한다.
    """
    for err in errors:
        if not isinstance(err, dict):
            continue
        loc = err.get("loc") or ()
        parts = list(loc) if isinstance(loc, (list, tuple)) else []
        if parts and parts[-1] == "biz_no":
            return "사장님, 번호를 다시 확인해주세요."
    return "입력값을 다시 확인해주세요."


async def request_validation_exception_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """RequestValidationError (422) — envelope + 표준 detail 유지.

    - message: 프론트에서 토스트/인라인에 바로 쓸 수 있는 한 줄 문구
    - detail: FastAPI 기본과 동일한 구조(jsonable_encoder 적용)
      Pydantic field_validator 의 ValueError 문구는 detail[].msg 에 포함됨
      (예: "Value error, 사업자등록번호는 10자리 ...")
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
