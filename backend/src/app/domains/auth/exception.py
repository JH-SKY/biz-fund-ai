# src/app/domains/auth/exception.py
"""인증 도메인 커스텀 예외."""

from fastapi import HTTPException


def auth_unauthorized(detail: str = "인증이 필요하거나 토큰이 만료되었습니다.") -> HTTPException:
    return HTTPException(status_code=401, detail=detail)


def social_api_error(provider: str) -> HTTPException:
    return HTTPException(
        status_code=500,
        detail=f"{provider} API 서버와의 통신에 실패했습니다.",
    )


def invalid_social_token(provider: str) -> HTTPException:
    return HTTPException(
        status_code=401,
        detail=f"유효하지 않거나 만료된 {provider} 토큰입니다.",
    )


def unsupported_provider(provider: str) -> HTTPException:
    """Pydantic enum 검증 이후 도달하는 최후 방어선."""
    return HTTPException(
        status_code=400,
        detail=f"지원하지 않는 소셜 로그인 제공자입니다: {provider}",
    )
