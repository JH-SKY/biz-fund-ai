# src/app/domains/policy/exception.py
"""정책 도메인 커스텀 예외 팩토리."""

from fastapi import HTTPException


def policy_not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="해당 정책을 찾을 수 없습니다.")


def policy_inactive() -> HTTPException:
    return HTTPException(status_code=410, detail="이미 마감된 정책입니다.")


def bookmark_business_required() -> HTTPException:
    """[도메인 규칙 2.2] 북마크는 사업장 컨텍스트(X-Business-Id)가 필수."""
    return HTTPException(
        status_code=400,
        detail="북마크 기능은 X-Business-Id 헤더가 필요합니다.",
    )
