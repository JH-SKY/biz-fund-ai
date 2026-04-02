# src/app/domains/auth/schema.py
"""인증·사용자 API Pydantic 스키마 (auth.md)."""

from __future__ import annotations


from pydantic import BaseModel, ConfigDict, Field


# ── 소셜 로그인 공통 ────────────────────────────────────

class SocialLoginRequest(BaseModel):
    """카카오·네이버 공통 로그인 요청 Body."""

    access_token: str = Field(..., description="소셜 플랫폼에서 발급한 Access Token")
    device_type: str = Field(..., description="클라이언트 디바이스 타입 (WEB / IOS / ANDROID)")


class SocialLoginResponseData(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
    is_new_user: bool


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
