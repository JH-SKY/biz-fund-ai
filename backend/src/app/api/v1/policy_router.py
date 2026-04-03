# src/app/api/v1/policy_router.py
"""정책 API 라우터 (policies.md v2.3 전체 구현).

엔드포인트 접근 권한 구분:
  - 인증 불필요 (공개):
      GET  /policies          — 전체 목록 조회 (X-Business-Id 선택)
      GET  /policies/search   — 키워드 검색    (X-Business-Id 선택)
      GET  /policies/{id}     — 상세 조회      (X-Business-Id 선택)

  - 인증 + X-Business-Id 필수:
      GET  /policies/recommend         — 맞춤 추천 (신호등 로직)
      POST /policies/{id}/bookmark     — 북마크 토글
      GET  /policies/bookmarks         — 북마크 목록 조회

경로 충돌 주의:
  `recommend` / `bookmarks`는 `{id}` 라우트보다 먼저 선언해야
  FastAPI가 리터럴 경로로 먼저 매칭한다.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.api.deps.policy_deps import (
    OptionalBusinessId,
    PolicyServiceDep,
    RequiredBusinessId,
)
from src.app.api.deps.user_auth import CurrentUser
from src.app.core.response import api_json
from src.app.database.postgres.database import get_db
from src.app.domains.business.exception import business_not_found
from src.app.domains.business.repository import BusinessRepository

router = APIRouter(prefix="/policies", tags=["policies"])


# ── 1. 전체 정책 목록 조회 ─────────────────────────────────────────────────


@router.get("")
async def get_all_policies(
    svc: PolicyServiceDep,
    business_id: OptionalBusinessId,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    sort: str = Query("latest"),
):
    """시스템에 등록된 전체 정책 목록 (최신순, 페이징).

    X-Business-Id 헤더가 있으면 북마크 여부를 함께 반환한다.
    """
    data = await svc.get_active_policies(
        page=page, size=size, business_id=business_id
    )
    return api_json(
        http_status=status.HTTP_200_OK,
        data=data.model_dump(),
        message="success",
    )


# ── 2. 맞춤형 정책 추천 목록 ────────────────────────────────────────────────
# ⚠️ /recommend 는 /{id} 보다 앞에 선언 (경로 충돌 방지)


@router.get("/recommend")
async def get_recommended_policies(
    svc: PolicyServiceDep,
    business_id: RequiredBusinessId,
    _current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
):
    """사업장 맞춤 추천 — 신호등 로직(RED/YELLOW/GREEN) 적용.

    [도메인 규칙 2.2] X-Business-Id 필수.
    """
    repo = BusinessRepository(db)
    biz = await repo.get_active_business_by_user_id(_current_user.id)
    if biz is None or biz.id != business_id:
        raise business_not_found()

    data = await svc.get_recommended_policies(biz, page=page, size=size)
    return api_json(
        http_status=status.HTTP_200_OK,
        data=data.model_dump(),
        message="success",
    )


# ── 6. 찜한 정책 목록 조회 ─────────────────────────────────────────────────
# ⚠️ /bookmarks 는 /{id} 보다 앞에 선언 (경로 충돌 방지)


@router.get("/bookmarks")
async def get_bookmarked_policies(
    svc: PolicyServiceDep,
    business_id: RequiredBusinessId,
    _current_user: CurrentUser,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
):
    """사업장 기준 북마크된 정책 목록.

    [도메인 규칙 2.2] X-Business-Id 필수.
    """
    data = await svc.get_bookmarked_policies(
        business_id, page=page, size=size
    )
    return api_json(
        http_status=status.HTTP_200_OK,
        data=data.model_dump(),
        message="success",
    )


# ── 4. 정책 키워드 검색 ────────────────────────────────────────────────────
# ⚠️ /search 는 /{id} 보다 앞에 선언 (경로 충돌 방지)


@router.get("/search")
async def search_policies(
    svc: PolicyServiceDep,
    business_id: OptionalBusinessId,
    keyword: str | None = Query(None, min_length=1, description="검색 키워드"),
    region: str | None = Query(None, description="지역 필터 (예: 서울)"),
    category: str | None = Query(None, description="카테고리 필터 (예: R&D)"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
):
    """제목·내용 키워드 / 지역 / 카테고리 복합 검색.

    응답 규격: 전체 목록 조회와 동일 (PolicyListResponse).
    """
    data = await svc.search_policies(
        keyword=keyword,
        region=region,
        category=category,
        page=page,
        size=size,
        business_id=business_id,
    )
    return api_json(
        http_status=status.HTTP_200_OK,
        data=data.model_dump(),
        message="success",
    )


# ── 3. 정책 상세 정보 조회 ─────────────────────────────────────────────────


@router.get("/{policy_id}")
async def get_policy_detail(
    policy_id: uuid.UUID,
    svc: PolicyServiceDep,
    business_id: OptionalBusinessId,
):
    """특정 정책 상세 공고 + 북마크 여부 반환.

    X-Business-Id 헤더가 있으면 북마크 상태를 함께 반환한다.
    """
    data = await svc.get_policy_detail(policy_id, business_id=business_id)
    return api_json(
        http_status=status.HTTP_200_OK,
        data=data.model_dump(),
        message="success",
    )


# ── 5. 관심 정책 북마크 토글 ────────────────────────────────────────────────


@router.post("/{policy_id}/bookmark")
async def toggle_bookmark(
    policy_id: uuid.UUID,
    svc: PolicyServiceDep,
    business_id: RequiredBusinessId,
    _current_user: CurrentUser,
):
    """정책 북마크 토글 — 이미 있으면 삭제, 없으면 추가.

    [도메인 규칙 2.2] X-Business-Id 필수.
    """
    data = await svc.toggle_bookmark(policy_id, business_id)
    return api_json(
        http_status=status.HTTP_200_OK,
        data=data.model_dump(),
        message="success",
    )
