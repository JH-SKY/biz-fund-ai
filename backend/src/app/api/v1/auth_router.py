# src/app/api/v1/auth_router.py
"""인증(Auth) API 라우터.

[제공 엔드포인트]
  POST /auth/kakao/callback  — 카카오 OAuth 인가 코드 교환 → 사용자 인증
  POST /auth/naver/callback  — 네이버 OAuth 인가 코드 교환 → 사용자 인증
  POST /auth/social-login    — 소셜 액세스 토큰으로 로그인 (신규 가입 or 기존 로그인)
  POST /auth/logout          — Refresh Token 무효화 (로그아웃)
  POST /auth/refresh         — Refresh Token → 새 Access Token 발급

[인증 흐름]
프론트엔드 → OAuth 제공자 → 인가 코드 수신 → 이 API로 코드 전달
→ 서버가 OAuth 제공자에 토큰 교환 → 사용자 조회/생성 → JWT 발급
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException

from src.app.core.config import APP_ENV
from src.app.api.deps.user_auth import CurrentUser, get_auth_service
from src.app.core.response import api_json
from src.app.domains.auth.schema import (
    DevLoginRequest,
    KakaoCallbackRequest,
    NaverCallbackRequest,
    RefreshTokenRequest,
    SocialAuthRequest,
)
from src.app.domains.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _ensure_dev_auth_enabled() -> None:
    if APP_ENV == "production":
        raise HTTPException(status_code=404, detail="Not found")


@router.post("/kakao/callback")
async def kakao_oauth_callback(
    body: KakaoCallbackRequest,
    svc: Annotated[AuthService, Depends(get_auth_service)],
):
    """카카오 OAuth 인가 코드를 처리한다."""
    data = await svc.kakao_callback(body)
    return api_json(http_status=200, data=data.model_dump())


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


@router.get("/dev-test-accounts")
async def list_dev_test_accounts(
    svc: Annotated[AuthService, Depends(get_auth_service)],
):
    _ensure_dev_auth_enabled()
    data = await svc.list_dev_test_accounts()
    return api_json(http_status=200, data=[item.model_dump() for item in data])


@router.post("/dev-login")
async def dev_login(
    body: DevLoginRequest,
    svc: Annotated[AuthService, Depends(get_auth_service)],
):
    _ensure_dev_auth_enabled()
    data = await svc.dev_login(body)
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
