# src/app/core/response.py
"""API 공통 응답 envelope (status / data / message)."""

from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse


def api_json(
    *,
    http_status: int,
    data: Any | None = None,
    message: str | None = None,
) -> JSONResponse:
    """문서 및 .cursorrules 공통 포맷에 맞춘 JSON 응답."""

    body: dict[str, Any] = {"status": http_status}
    if data is not None:
        body["data"] = data
    if message is not None:
        body["message"] = message
    return JSONResponse(status_code=http_status, content=body)
