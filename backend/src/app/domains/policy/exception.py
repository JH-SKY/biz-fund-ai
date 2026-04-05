# src/app/domains/policy/exception.py
"""정책 도메인 커스텀 예외 팩토리.

설계 의도:
  1. 명확한 에러 전달: HTTP 상태 코드를 통해 클라이언트가 다음 행동(로그인 유도 등)을 결정하게 합니다.
  2. 재사용성: 서비스 레이어에서 발생할 수 있는 다양한 비즈니스 예외를 표준화합니다.
"""

from fastapi import HTTPException, status


def policy_not_found() -> HTTPException:
    """정책이 데이터베이스에 존재하지 않을 때 발생합니다."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, 
        detail="해당 정책을 찾을 수 없습니다."
    )


def policy_inactive() -> HTTPException:
    """정책이 존재하지만 is_active=False(삭제 또는 비공개) 상태일 때 발생합니다."""
    return HTTPException(
        status_code=status.HTTP_410_GONE, 
        detail="이미 마감되었거나 삭제된 정책입니다."
    )


def bookmark_business_required() -> HTTPException:
    """[도메인 규칙 2.2] 북마크는 사업장 컨텍스트(X-Business-Id)가 필수입니다."""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="북마크 기능은 사업장 등록 및 X-Business-Id 헤더가 필요합니다.",
    )


# ── 조회수 및 권한 관련 예외 추가 ──────────────────────────────────────────


def policy_view_auth_required() -> HTTPException:
    """조회수 집계를 위해 로그인이 필요한 경우 발생합니다.
    
    설계 의도: 단순 조회는 비로그인도 가능하지만, 
    서비스 정책상 조회수 카운팅은 '인증된 사용자'만 기록할 때 구분하기 위함입니다.
    """
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="정책 상세 기록을 위해 로그인이 필요합니다.",
    )


def policy_already_viewed() -> HTTPException:
    """[어뷰징 방지] 24시간 이내에 이미 조회하여 카운트가 제한될 때 사용합니다.
    
    참고: 보통 상세 페이지 진입 자체를 막지는 않으므로, 
    로그상으로만 남기거나 429(Too Many Requests)를 선택적으로 사용합니다.
    """
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="조회수는 24시간에 한 번만 집계됩니다.",
    )