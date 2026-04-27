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


def user_already_has_business() -> HTTPException:
    """1인 1사업장 정책: 이미 활성 사업장이 있는 경우 추가 온보딩 차단."""
    return HTTPException(
        status_code=409,
        detail="이미 등록된 사업장이 있습니다. 계정당 하나의 사업장만 등록할 수 있습니다.",
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


def biz_no_closed() -> HTTPException:
    """폐업 상태 사업자번호 — 정책 지원 불가 (AI 진단 필터링 기준)."""
    return HTTPException(
        status_code=422,
        detail=(
            "폐업한 사업자번호로는 서비스에 등록할 수 없습니다. "
            "사업장이 계속사업자 상태인지 확인해 주세요."
        ),
    )


def biz_no_suspended() -> HTTPException:
    """휴업 상태 사업자번호 — 등록은 허용하지 않음 (정책 자금 지원 불가)."""
    return HTTPException(
        status_code=422,
        detail=(
            "현재 휴업 중인 사업자번호입니다. "
            "정책 지원을 받으려면 사업장이 계속사업자 상태여야 합니다."
        ),
    )


def biz_no_api_unavailable() -> HTTPException:
    """국세청 API 점검 중 또는 응답 지연 — 수동 등록(is_manual=True) 안내."""
    return HTTPException(
        status_code=503,
        detail=(
            "현재 국세청 서버가 응답하지 않습니다. "
            "잠시 후 다시 시도하거나, '수동 입력 모드'로 등록을 진행해 주세요."
        ),
    )
