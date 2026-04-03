# src/app/domains/business/exception.py
"""사업장 도메인 커스텀 예외 팩토리."""

from fastapi import HTTPException


def business_not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="등록된 사업장 정보가 없습니다.")


def onboarding_required() -> HTTPException:
    """[도메인 규칙 1.1] 온보딩 미완료 유저의 대시보드 접근 차단."""
    return HTTPException(
        status_code=403,
        detail="대시보드 접근을 위해 온보딩(사업장 등록)을 먼저 완료해 주세요.",
    )


def business_already_registered() -> HTTPException:
    return HTTPException(
        status_code=409,
        detail="이미 등록된 사업자번호입니다.",
    )


def finance_not_found(year: int) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail=f"{year}년도 재무 데이터가 없습니다.",
    )


def finance_already_exists(year: int) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail=f"{year}년도 재무 데이터가 이미 존재합니다. PATCH /businesses/finance/{year} 를 사용하세요.",
    )


def document_not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="해당 서류를 찾을 수 없습니다.")


def document_forbidden() -> HTTPException:
    return HTTPException(
        status_code=403,
        detail="해당 서류에 대한 접근 권한이 없습니다.",
    )
