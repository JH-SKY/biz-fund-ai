# src/app/api/v1/auth_router.py
"""인증 API (auth.md #1~#3)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends

from src.app.api.deps.user_auth import CurrentUser, get_auth_service
from src.app.core.response import api_json
from src.app.domains.auth.schema import SocialLoginRequest
from src.app.domains.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/kakao")
async def kakao_login(
    body: SocialLoginRequest,
    svc: Annotated[AuthService, Depends(get_auth_service)],
):
    """카카오 OAuth2 → 로그인/가입. is_new_user=True 면 온보딩으로 이동."""
    data = await svc.kakao_login(body)
    return api_json(http_status=200, data=data.model_dump())


@router.post("/naver")
async def naver_login(
    body: SocialLoginRequest,
    svc: Annotated[AuthService, Depends(get_auth_service)],
):
    """네이버 OAuth2 → 로그인/가입."""
    data = await svc.naver_login(body)
    return api_json(http_status=200, data=data.model_dump())


@router.post("/logout")
async def logout(
    _: CurrentUser,
    svc: Annotated[AuthService, Depends(get_auth_service)],
    refresh_token: str = Body(..., embed=True, description="로그아웃할 Refresh Token"),
):
    """Refresh Token DB 무효화. Access Token은 만료까지 Stateless 유효."""
    await svc.logout(refresh_token=refresh_token)
    return api_json(http_status=200, message="성공적으로 로그아웃되었습니다.")
