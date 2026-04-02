# src/app/domains/admin/exception.py
"""관리자 도메인 예외 (확장 시 커스텀 예외·핸들러 연결)."""

from fastapi import HTTPException


def admin_forbidden() -> HTTPException:
    return HTTPException(status_code=403, detail="관리자 권한이 없습니다.")


def admin_unauthorized(detail: str = "인증이 필요하거나 토큰이 만료되었습니다.") -> HTTPException:
    return HTTPException(status_code=401, detail=detail)
