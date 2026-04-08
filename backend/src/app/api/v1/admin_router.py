# src/app/api/v1/admin_router.py
"""관리자 센터 API (cusor_docs/api_spec/admin.md)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from src.app.api.deps.admin_auth import CurrentAdmin, get_admin_service
from src.app.core.response import api_json
from src.app.domains.admin.schema import (
    AdminLoginRequest,
    ContentPatchRequest,
    ContentPublishRequest,
    PolicyCreateRequest,
    PolicyPatchRequest,
)
from src.app.domains.admin.service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])


def _client_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host


@router.post("/login")
async def admin_login(
    body: AdminLoginRequest,
    svc: Annotated[AdminService, Depends(get_admin_service)],
):
    """운영 편의: ADMIN_TOKEN 발급 (명세 본문에는 없으나 토큰 획득 경로)."""

    data = await svc.login(body)
    return api_json(http_status=200, data=data, message="success")


@router.post("/policies")
async def admin_create_policy(
    request: Request,
    body: PolicyCreateRequest,
    admin: CurrentAdmin,
    svc: Annotated[AdminService, Depends(get_admin_service)],
):
    data = await svc.create_policy(
        body,
        admin=admin,
        client_ip=_client_ip(request),
    )
    return api_json(http_status=201, data=data.model_dump(), message="success")


@router.patch("/policies/{policy_id}")
async def admin_patch_policy(
    request: Request,
    policy_id: uuid.UUID,
    body: PolicyPatchRequest,
    admin: CurrentAdmin,
    svc: Annotated[AdminService, Depends(get_admin_service)],
):
    await svc.patch_policy(
        policy_id,
        body,
        admin=admin,
        client_ip=_client_ip(request),
    )
    return api_json(
        http_status=200,
        message="정책 정보가 성공적으로 수정되었습니다.",
    )


@router.post("/contents")
async def admin_publish_content(
    request: Request,
    body: ContentPublishRequest,
    admin: CurrentAdmin,
    svc: Annotated[AdminService, Depends(get_admin_service)],
):
    data = await svc.publish_content(
        body,
        admin=admin,
        client_ip=_client_ip(request),
    )
    return api_json(http_status=201, data=data.model_dump(), message="success")


@router.patch("/contents/{content_id}")
async def admin_patch_content(
    request: Request,
    content_id: uuid.UUID,
    body: ContentPatchRequest,
    admin: CurrentAdmin,
    svc: Annotated[AdminService, Depends(get_admin_service)],
):
    await svc.patch_content(
        content_id,
        body,
        admin=admin,
        client_ip=_client_ip(request),
    )
    return api_json(
        http_status=200,
        message="콘텐츠 상태가 업데이트되었습니다.",
    )


@router.get("/chats/logs")
async def admin_chat_logs(
    request: Request,
    admin: CurrentAdmin,
    svc: Annotated[AdminService, Depends(get_admin_service)],
    user_id: uuid.UUID | None = Query(None, description="특정 사용자 대화만"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
):
    data = await svc.list_chat_monitor(
        admin_id=admin.id,
        client_ip=_client_ip(request),
        user_id=user_id,
        page=page,
        size=size,
    )
    return api_json(http_status=200, data=data.model_dump(), message="success")


@router.get("/stats/dashboard")
async def admin_stats_dashboard(
    _: CurrentAdmin,
    svc: Annotated[AdminService, Depends(get_admin_service)],
):
    data = await svc.dashboard_stats()
    return api_json(http_status=200, data=data.model_dump(), message="success")


@router.get("/audit-logs")
async def admin_audit_logs(
    request: Request,
    admin: CurrentAdmin,
    svc: Annotated[AdminService, Depends(get_admin_service)],
):
    rows = await svc.list_audit_logs(admin_id=admin.id, client_ip=_client_ip(request))
    return api_json(
        http_status=200,
        data=[r.model_dump() for r in rows],
        message="success",
    )


@router.get("/batch/status")
async def admin_batch_status(
    _: CurrentAdmin,
    svc: Annotated[AdminService, Depends(get_admin_service)],
):
    rows = await svc.batch_status()
    return api_json(
        http_status=200,
        data=[r.model_dump() for r in rows],
        message="success",
    )


@router.get("/batch/logs/{job_id}")
async def admin_batch_log_detail(
    job_id: uuid.UUID,
    _: CurrentAdmin,
    svc: Annotated[AdminService, Depends(get_admin_service)],
):
    data = await svc.batch_detail(job_id)
    return api_json(http_status=200, data=data.model_dump(), message="success")


@router.get("/users")
async def admin_list_users(
    request: Request,
    admin: CurrentAdmin,
    svc: Annotated[AdminService, Depends(get_admin_service)],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    search_keyword: str | None = Query(None),
    include_inactive_users: bool = Query(
        False,
        description="True면 탈퇴(비활성) 유저까지 포함. 기본은 활성만(격리 펜스).",
    ),
):
    data = await svc.list_users(
        admin_id=admin.id,
        client_ip=_client_ip(request),
        page=page,
        size=size,
        search_keyword=search_keyword,
        only_active=not include_inactive_users,
    )
    return api_json(http_status=200, data=data.model_dump(), message="success")


############ 테스트용 코드
# 파일 상단에 필요한 import 추가 (이미 있다면 패스)
from sqlalchemy.ext.asyncio import AsyncSession
from src.app.database.postgres.database import get_db
from src.app.domains.policy.repository import PolicyRepository
from src.app.domains.policy.sync_service import BizinfoSyncService

# ... 기존 코드들 ...


@router.post(
    "/policies/sync",
    summary="[테스트] 기업마당 정책 공고 동기화",
    description="기업마당 API를 찔러서 최신 공고 100개를 가져와 DB에 넣습니다.",
)
async def sync_bizinfo_policies_test(
    db: AsyncSession = Depends(get_db),
    # current_admin = Depends(get_current_admin) # 만약 관리자 인증이 필요하다면 주석 해제
):
    # 1. 레포지토리와 서비스 조립
    repo = PolicyRepository(db)
    sync_service = BizinfoSyncService(session=db, repo=repo)

    # 2. 기업마당에서 100개 끌어오기 실행!
    result = await sync_service.sync_policies(display_count=100)

    # 3. 결과 반환
    if result["status"] == "error":
        return api_json(http_status=500, message=result["message"])

    return api_json(
        http_status=200, message="성공적으로 동기화되었습니다.", data=result
    )
