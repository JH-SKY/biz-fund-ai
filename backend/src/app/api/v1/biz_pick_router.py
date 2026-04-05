"""비즈픽 API 라우터."""

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status

from src.app.api.deps.biz_pick_deps import BizPickServiceDep
from src.app.api.deps.user_auth import CurrentUser
from src.app.core.response import api_json

router = APIRouter(prefix="/contents", tags=["biz_picks"])


@router.get("")
async def get_biz_picks(
    svc: BizPickServiceDep,
    # 1. 로그인하지 않은 사용자도 목록은 볼 수 있어야 하므로 Optional로 설정합니다.
    current_user: Annotated[Optional[CurrentUser], Depends(CurrentUser)] = None,
    category: str | None = Query(None, description="카테고리 필터"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
):
    """비즈픽 콘텐츠 목록 조회 (찜 여부 포함)."""
    # 서비스에 유저 정보를 넘겨서 내가 '찜'한 글인지 확인할 수 있게 합니다.
    data = await svc.get_published_contents(
        current_user=current_user, 
        category=category, 
        page=page, 
        size=size
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
    """오늘의 추천 콘텐츠 (3개 랜덤)."""
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
    # 2. 상세 페이지에서도 내가 찜한 글인지 확인하기 위해 유저 정보를 받습니다.
    current_user: Annotated[Optional[CurrentUser], Depends(CurrentUser)] = None,
):
    """특정 콘텐츠 상세 조회 (조회수 1 증가)."""
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
    # 3. 찜하기는 '로그인한 사람'만 가능하므로 Optional이 아닌 필수값으로 받습니다.
    current_user: CurrentUser,
):
    """콘텐츠 좋아요 토글 (명세서 4번 기능 구현)."""
    # 서비스 로직에서 유저 ID와 콘텐츠 ID를 매핑하여 토글 처리합니다.
    data = await svc.toggle_like(content_id, current_user=current_user)
    return api_json(
        http_status=status.HTTP_200_OK,
        data=data.model_dump(),
        message="success",
    )