# src/app/api/v1/users_router.py
"""사용자 관련 API (auth.md #4~#6)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from src.app.api.deps.user_auth import CurrentUser, get_auth_service
from src.app.core.response import api_json
from src.app.domains.auth.schema import ProfilePatchRequest
from src.app.domains.auth.service import AuthService

router = APIRouter(prefix="/users", tags=["users"])


@router.delete("/withdraw", status_code=204)
async def withdraw(
    current_user: CurrentUser,
    svc: Annotated[AuthService, Depends(get_auth_service)],
):
    """회원 탈퇴. 도메인 규칙: Soft Delete(status=DELETED). 204 No Content."""
    await svc.withdraw(current_user)
    return Response(status_code=204)


@router.get("/me")
async def get_my_profile(
    current_user: CurrentUser,
    svc: Annotated[AuthService, Depends(get_auth_service)],
):
    """내 프로필 정보 조회. 마이페이지 구성 기본 데이터."""
    data = await svc.get_my_profile(current_user)
    return api_json(http_status=200, data=data.model_dump())


@router.patch("/profile")
async def patch_profile(
    current_user: CurrentUser,
    body: ProfilePatchRequest,
    svc: Annotated[AuthService, Depends(get_auth_service)],
):
    """추가 프로필 설정. 정밀 매칭을 위한 군필·관심분야·기술스택 저장."""
    data = await svc.patch_profile(current_user, body)
    return api_json(http_status=200, data=data.model_dump())
