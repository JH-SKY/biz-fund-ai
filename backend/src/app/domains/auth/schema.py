# src/app/domains/auth/schema.py
"""인증·사용자 API Pydantic 스키마 (auth.md)."""

from __future__ import annotations


from pydantic import BaseModel, ConfigDict, Field

from src.app.domains.auth.model import SocialProvider


# ── 소셜 로그인 공통 ────────────────────────────────────

class NaverCallbackRequest(BaseModel):
    """POST /auth/naver/callback 전용 요청 Body.

    네이버 OAuth 인가 코드 플로우에서 프론트가 전달하는 code + state.
    백엔드에서 네이버 토큰 교환 후 우리 서비스 JWT를 발급한다.
    """

    code: str = Field(..., description="네이버 인가 서버에서 전달한 인증 코드")
    state: str = Field(..., description="CSRF 방지용 state 값")


class SocialLoginRequest(BaseModel):
    """카카오·네이버 공통 로그인 요청 Body. (내부 메서드용)"""

    access_token: str = Field(..., description="소셜 플랫폼에서 발급한 Access Token")
    device_type: str = Field(..., description="클라이언트 디바이스 타입 (WEB / IOS / ANDROID)")


class SocialAuthRequest(BaseModel):
    """POST /auth/social-login 통합 엔드포인트 요청 Body.

    provider 필드 하나로 카카오·네이버를 모두 처리한다.
    """

    access_token: str = Field(..., description="소셜 플랫폼에서 발급한 Access Token")
    provider: SocialProvider = Field(..., description="소셜 로그인 제공자 (KAKAO / NAVER)")
    device_type: str = Field(..., description="클라이언트 디바이스 타입 (WEB / IOS / ANDROID)")


class SocialLoginResponseData(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
    is_new_user: bool


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="재발급에 사용할 Refresh Token")


class RefreshTokenResponseData(BaseModel):
    access_token: str


# ── 테스트 전용 로그인 (개발/스테이징 환경 한정) ──────────

class TestLoginRequest(BaseModel):
    """POST /auth/test-login 전용 요청 Body.

    실제 소셜 서버를 거치지 않고 즉시 JWT를 발급한다.
    APP_ENV=production 환경에서는 이 엔드포인트 자체가 비노출(404)된다.
    """

    test_user_key: str = Field(
        ...,
        description=(
            "테스트 유저 식별 키. 동일한 키로 반복 호출하면 같은 유저가 반환된다. "
            "예: 'alice', 'bob', 'admin_tester'"
        ),
    )


# ── 로그아웃 ────────────────────────────────────────────

class LogoutResponse(BaseModel):
    status: int = 200
    message: str = "성공적으로 로그아웃되었습니다."


# ── 내 프로필 조회 (/users/me) ──────────────────────────

class MyProfileData(BaseModel):
    user_id: str
    name: str
    email: str
    profile_image: str | None
    interest_sectors: list[str]
    is_profile_completed: bool


# ── 추가 프로필 설정 (/users/profile PATCH) ─────────────

class ProfilePatchRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    military_service: str | None = Field(
        None,
        description="군필 여부: COMPLETED / EXEMPTED / IN_PROGRESS / NA",
    )
    interest_sectors: list[str] | None = Field(
        None, description="관심 분야 리스트"
    )
    is_non_major: bool | None = None
    tech_stack: list[str] | None = Field(None, description="기술 스택 리스트")


class ProfilePatchResponseData(BaseModel):
    updated_at: str
