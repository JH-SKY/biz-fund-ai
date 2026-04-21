"""비즈픽 API 라우터."""

import uuid

from fastapi import APIRouter, Query, status

from src.app.api.deps.biz_pick_deps import BizPickServiceDep
from src.app.api.deps.user_auth import CurrentUser, OptionalCurrentUser
from src.app.core.response import api_json

router = APIRouter(prefix="/contents", tags=["biz_picks"])


@router.get("")
async def get_biz_picks(
    svc: BizPickServiceDep,
    current_user: OptionalCurrentUser = None,
    category: str | None = Query(None, description="카테고리 필터"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
):
    """비즈픽 콘텐츠 목록 조회. 비로그인 사용자도 접근 가능하다."""
    data = await svc.get_published_contents(
        current_user=current_user,
        category=category,
        page=page,
        size=size,
    )
    return api_json(
        http_status=status.HTTP_200_OK,
        data=data.model_dump(),
        message="success",
    )


@router.get("/today")
async def get_todays_picks(
    svc: BizPickServiceDep,
):
    """오늘의 추천 콘텐츠 조회."""
    data = await svc.get_todays_picks()
    return api_json(
        http_status=status.HTTP_200_OK,
        data=[d.model_dump() for d in data],
        message="success",
    )


@router.get("/categories")
async def get_content_categories(
    svc: BizPickServiceDep,
):
    """콘텐츠 카테고리 목록 조회."""
    data = svc.get_categories()
    return api_json(
        http_status=status.HTTP_200_OK,
        data=[d.model_dump() for d in data],
        message="success",
    )


@router.get("/{content_id}")
async def get_content_detail(
    content_id: uuid.UUID,
    svc: BizPickServiceDep,
    current_user: OptionalCurrentUser = None,
):
    """콘텐츠 상세 조회. 비로그인 사용자는 공개 정보만 본다."""
    data = await svc.get_content_detail(content_id, current_user=current_user)
    return api_json(
        http_status=status.HTTP_200_OK,
        data=data.model_dump(),
        message="success",
    )


@router.post("/{content_id}/like")
async def toggle_content_like(
    content_id: uuid.UUID,
    svc: BizPickServiceDep,
    current_user: CurrentUser,
):
    """콘텐츠 좋아요 토글. 로그인 사용자가 아니면 사용할 수 없다."""
    data = await svc.toggle_like(content_id, current_user=current_user)
    return api_json(
        http_status=status.HTTP_200_OK,
        data=data.model_dump(),
        message="success",
    )
