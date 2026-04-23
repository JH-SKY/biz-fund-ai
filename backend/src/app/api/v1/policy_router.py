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
  - `recommend` / `bookmarks` / `search`는 `{policy_id}` 라우트보다 반드시 먼저 선언해야 함.
  - FastAPI는 등록된 순서대로 경로 매칭을 시도함.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from src.app.api.deps.policy_deps import (
    OptionalBusinessId,
    PolicyServiceDep,
    RequiredBusinessId,
)
from src.app.api.deps.business_deps import ActiveBusiness
from src.app.core.response import api_json

router = APIRouter(prefix="/policies", tags=["policies"])


# ── 1. 전체 정책 목록 조회 ─────────────────────────────────────────────────


@router.get("")
async def get_all_policies(
    svc: PolicyServiceDep,
    business_id: OptionalBusinessId,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
):
    """시스템에 등록된 전체 정책 목록 (최신순, 페이징).

    설계 의도:
      - [도메인 규칙 0] 비로그인 사용자도 조회 가능해야 함.
      - business_id 존재 시 각 아이템의 북마크 여부를 포함하여 반환.
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
# ⚠️ /recommend 는 /{policy_id} 보다 앞에 선언 (경로 충돌 방지)


@router.get("/recommend")
async def get_recommended_policies(
    svc: PolicyServiceDep,
    business_id: RequiredBusinessId,
    biz: ActiveBusiness,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
):
    """사업장 맞춤 추천 — 신호등 로직(RED/YELLOW/GREEN) 적용.

    수정 사항: 
      - [A5 권한 격리] biz.id와 business_id 일치 여부 검증 로직을 
        Router가 아닌 Service 계층으로 위임하여 '비즈니스 판단'의 응집도를 높임.
    """
    # 💡 설계 의도: business_id와 biz 객체 간의 정합성 검증은 Service 내부에서 수행하여 
    #    라우터는 요청 전달과 응답 반환에만 집중하게 함.
    data = await svc.get_recommended_policies(
        business=biz,
        requested_business_id=business_id, 
        page=page, 
        size=size
    )
    return api_json(
        http_status=status.HTTP_200_OK,
        data=data.model_dump(),
        message="success",
    )


# ── 3. 찜한 정책 목록 조회 ─────────────────────────────────────────────────
# ⚠️ /bookmarks 는 /{policy_id} 보다 앞에 선언 (경로 충돌 방지)


@router.get("/bookmarks")
async def get_bookmarked_policies(
    svc: PolicyServiceDep,
    business_id: RequiredBusinessId,
    biz: ActiveBusiness,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
):
    """사업장 기준 북마크된 정책 목록.

    설계 의도: 
      - [도메인 규칙 2.2] 특정 사업장에 귀속된 북마크만 격리 조회.
    """
    data = await svc.get_bookmarked_policies(
        business=biz,
        requested_business_id=business_id,
        page=page,
        size=size,
    )
    return api_json(
        http_status=status.HTTP_200_OK,
        data=data.model_dump(),
        message="success",
    )


# ── 4. 정책 키워드 검색 ────────────────────────────────────────────────────
# ⚠️ /search 는 /{policy_id} 보다 앞에 선언 (경로 충돌 방지)


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
    """제목·내용 키워드 / 지역 / 카테고리 복합 검색."""
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


# ── 4-2. 정책 벡터(하이브리드) 검색 ──────────────────────────────────────────
# ⚠️ /vector-search 는 /{policy_id} 보다 앞에 선언 (경로 충돌 방지)


@router.get("/vector-search")
async def vector_search_policies(
    svc: PolicyServiceDep,
    business_id: OptionalBusinessId,
    query: str = Query(..., min_length=2, description="자연어 검색 쿼리 (예: 서울 IT 기업 지원금)"),
    region: str | None = Query(None, description="지역 필터 (예: 서울) — SQL 필터 우선 적용"),
    category: str | None = Query(None, description="카테고리 필터 (예: 금융)"),
    status_filter: str | None = Query("RECRUITING", description="공고 상태 (기본: RECRUITING)"),
    limit: int = Query(10, ge=1, le=50, description="반환할 최대 결과 수"),
    offset: int = Query(0, ge=0, description="페이지 오프셋"),
):
    """
    [하이브리드 검색] 자연어 쿼리를 임베딩하고 SQL 필터 + 벡터 유사도로 정책을 검색합니다.

    처리 흐름:
      1. 쿼리를 text-embedding-3-small로 임베딩합니다.
      2. SQL 필터(지역·카테고리·상태)를 먼저 적용합니다.
      3. 필터된 범위에서 Cosine Similarity 기준으로 정렬하여 반환합니다.

    일반 키워드 검색(/search)과의 차이:
      - 동의어·의미적 유사성을 이해합니다. (예: '청년 창업' → '예비창업자 지원')
      - region/category 필터를 반드시 함께 사용하면 검색 품질이 향상됩니다.
    """
    data = await svc.vector_search_policies(
        query,
        region=region,
        category=category,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
        business_id=business_id,
    )
    return api_json(
        http_status=status.HTTP_200_OK,
        data=data.model_dump(),
        message="success",
    )


# ── 5. 정책 상세 정보 조회 ─────────────────────────────────────────────────


@router.get("/{policy_id}")
async def get_policy_detail(
    policy_id: uuid.UUID,
    svc: PolicyServiceDep,
    business_id: OptionalBusinessId,
):
    """특정 정책 상세 공고 + 북마크 여부 반환.

    설계 의도:
      - 상세 조회 시 조회수가 카운팅되며(비즈니스 로직), 
      - 반환 전 데이터 만료(Expired) 방지를 위해 Service에서 DTO 변환이 선행됨.
    """
    data = await svc.get_policy_detail(policy_id, business_id=business_id)
    return api_json(
        http_status=status.HTTP_200_OK,
        data=data.model_dump(),
        message="success",
    )


# ── 6. 관심 정책 북마크 토글 ────────────────────────────────────────────────


@router.post("/{policy_id}/bookmark")
async def toggle_bookmark(
    policy_id: uuid.UUID,
    svc: PolicyServiceDep,
    business_id: RequiredBusinessId,
    biz: ActiveBusiness,
):
    """정책 북마크 토글 — 이미 있으면 삭제, 없으면 추가.

    수정 사항:
      - [A4 물리 삭제] 취소 시 즉시 반영되며, 응답 규격을 명세서와 일치시킴.
    """
    data = await svc.toggle_bookmark(
        policy_id,
        business=biz,
        requested_business_id=business_id,
    )
    return api_json(
        http_status=status.HTTP_200_OK,
        data=data.model_dump(),
        message="success",
    )
