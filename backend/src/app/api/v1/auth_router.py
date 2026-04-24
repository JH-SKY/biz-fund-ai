# src/app/api/v1/auth_router.py
"""인증 API (auth.md #1~#3)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends

from src.app.api.deps.user_auth import CurrentUser, get_auth_service
from src.app.core.response import api_json
from src.app.domains.auth.schema import (
    NaverCallbackRequest,
    RefreshTokenRequest,
    SocialAuthRequest,
)
from src.app.domains.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/naver/callback")
async def naver_oauth_callback(
    body: NaverCallbackRequest,
    svc: Annotated[AuthService, Depends(get_auth_service)],
):
    """네이버 OAuth 인가 코드를 처리한다."""
    data = await svc.naver_callback(body)
    return api_json(http_status=200, data=data.model_dump())


@router.post("/social-login")
async def social_login(
    body: SocialAuthRequest,
    svc: Annotated[AuthService, Depends(get_auth_service)],
):
    """카카오/네이버 소셜 로그인을 처리한다."""
    data = await svc.social_login(body)
    return api_json(http_status=200, data=data.model_dump())


@router.post("/logout")
async def logout(
    _: CurrentUser,
    svc: Annotated[AuthService, Depends(get_auth_service)],
    refresh_token: str = Body(..., embed=True, description="로그아웃할 Refresh Token"),
):
    """Refresh Token을 무효화한다."""
    await svc.logout(refresh_token=refresh_token)
    return api_json(http_status=200, message="성공적으로 로그아웃되었습니다.")


@router.post("/refresh")
async def refresh_access_token(
    body: RefreshTokenRequest,
    svc: Annotated[AuthService, Depends(get_auth_service)],
):
    """유효한 Refresh Token으로 새 Access Token을 발급한다."""
    data = await svc.refresh_access_token(refresh_token=body.refresh_token)
    return api_json(http_status=200, data=data.model_dump())
