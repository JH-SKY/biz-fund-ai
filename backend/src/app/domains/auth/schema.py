# src/app/domains/auth/schema.py
"""인증 및 사용자 API Pydantic 스키마."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.app.domains.auth.model import SocialProvider


class KakaoCallbackRequest(BaseModel):
    """POST /auth/kakao/callback 요청 Body."""

    code: str = Field(..., description="카카오 인가 코드")
    redirect_uri: str = Field(..., description="카카오 개발자센터에 등록한 Redirect URI")


class NaverCallbackRequest(BaseModel):
    """POST /auth/naver/callback 요청 Body."""

    code: str = Field(..., description="네이버 인가 코드")
    state: str = Field(..., description="CSRF 방지용 state 값")


class SocialLoginRequest(BaseModel):
    """소셜 로그인 내부 공통 요청 Body."""

    access_token: str = Field(..., description="소셜 Access Token")
    device_type: str = Field(..., description="WEB / IOS / ANDROID")


class SocialAuthRequest(BaseModel):
    """POST /auth/social-login 요청 Body."""

    access_token: str = Field(..., description="소셜 Access Token")
    provider: SocialProvider = Field(..., description="KAKAO / NAVER")
    device_type: str = Field(..., description="WEB / IOS / ANDROID")


class SocialLoginResponseData(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
    name: str
    is_new_user: bool


class DevLoginRequest(BaseModel):
    scenario_key: str = Field(..., description="개발용 테스트 시나리오 키")


class DevTestAccountItem(BaseModel):
    scenario_key: str
    display_name: str
    email: str
    business_name: str
    summary: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="갱신에 사용할 Refresh Token")


class RefreshTokenResponseData(BaseModel):
    access_token: str


class LogoutResponse(BaseModel):
    status: int = 200
    message: str = "성공적으로 로그아웃되었습니다."


class MyProfileData(BaseModel):
    user_id: str
    name: str
    email: str
    profile_image: str | None
    interest_sectors: list[str]
    is_profile_completed: bool


class ProfilePatchRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    military_service: str | None = Field(
        None,
        description="COMPLETED / EXEMPTED / IN_PROGRESS / NA",
    )
    interest_sectors: list[str] | None = Field(
        None,
        description="관심 분야 리스트",
    )
    is_non_major: bool | None = None
    tech_stack: list[str] | None = Field(None, description="기술 스택 리스트")


class ProfilePatchResponseData(BaseModel):
    updated_at: str
