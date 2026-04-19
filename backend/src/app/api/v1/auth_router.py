# src/app/api/v1/auth_router.py
"""인증 API (auth.md #1~#3)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException

from src.app.api.deps.user_auth import CurrentUser, get_auth_service
from src.app.core.config import APP_ENV
from src.app.core.response import api_json
from src.app.domains.auth.schema import SocialAuthRequest, TestLoginRequest
from src.app.domains.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


# ── 프로덕션 가드 ──────────────────────────────────────────
# 테스트 전용 엔드포인트를 프로덕션에서 완전히 숨기는 의존성.
# 403(권한 없음) 대신 404를 반환하여 엔드포인트 존재 자체를 노출하지 않는다.
async def _dev_only() -> None:
    if APP_ENV == "production":
        raise HTTPException(status_code=404, detail="Not Found")


# ── 소셜 로그인 ────────────────────────────────────────────

@router.post("/social-login")
async def social_login(
    body: SocialAuthRequest,
    svc: Annotated[AuthService, Depends(get_auth_service)],
):
    """카카오·네이버 통합 소셜 로그인.

    - `provider`: KAKAO 또는 NAVER
    - `is_new_user=True` 응답 시 프론트에서 온보딩 페이지로 이동.
    """
    data = await svc.social_login(body)
    return api_json(http_status=200, data=data.model_dump())


# ── 테스트 전용 로그인 (개발/스테이징 환경 한정) ──────────────

@router.post("/test-login", dependencies=[Depends(_dev_only)])
async def test_login(
    body: TestLoginRequest,
    svc: Annotated[AuthService, Depends(get_auth_service)],
):
    """[DEV ONLY] 실제 소셜 서버 없이 즉시 JWT 발급.

    - 동일한 `test_user_key`로 반복 호출하면 항상 같은 유저가 반환된다.
    - `APP_ENV=production` 환경에서는 404를 반환한다.
    - Swagger UI에서 바로 테스트 가능.
    """
    data = await svc.test_login(body)
    return api_json(http_status=200, data=data.model_dump())


# ── 로그아웃 ───────────────────────────────────────────────

@router.post("/logout")
async def logout(
    _: CurrentUser,
    svc: Annotated[AuthService, Depends(get_auth_service)],
    refresh_token: str = Body(..., embed=True, description="로그아웃할 Refresh Token"),
):
    """Refresh Token DB 무효화. Access Token은 만료까지 Stateless 유효."""
    await svc.logout(refresh_token=refresh_token)
    return api_json(http_status=200, message="성공적으로 로그아웃되었습니다.")
