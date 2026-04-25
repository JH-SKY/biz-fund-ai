# src/app/api/v1/admin_router.py
"""관리자 센터 API (cusor_docs/api_spec/admin.md)."""

from __future__ import annotations

import random
import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from src.app.api.deps.admin_auth import CurrentAdmin, get_admin_service
from src.app.api.deps.policy_deps import EmbeddingServiceDep, PolicyServiceDep, SyncServiceDep
from src.app.core.response import api_json
from src.app.domains.admin.schema import (
    AdminLoginRequest,
    CorrectionNoteRequest,
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


@router.get("/contents")
async def admin_list_contents(
    _: CurrentAdmin,
    svc: Annotated[AdminService, Depends(get_admin_service)],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    category: str | None = Query(None),
):
    data = await svc.list_contents(page=page, size=size, category=category)
    return api_json(http_status=200, data=data, message="success")


@router.get("/contents/{content_id}")
async def admin_content_detail(
    content_id: uuid.UUID,
    _: CurrentAdmin,
    svc: Annotated[AdminService, Depends(get_admin_service)],
):
    data = await svc.get_content_detail(content_id)
    return api_json(http_status=200, data=data, message="success")


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


@router.delete("/contents/{content_id}")
async def admin_delete_content(
    request: Request,
    content_id: uuid.UUID,
    admin: CurrentAdmin,
    svc: Annotated[AdminService, Depends(get_admin_service)],
):
    await svc.delete_content(
        content_id=content_id,
        admin=admin,
        client_ip=_client_ip(request),
    )
    return api_json(http_status=200, data={"success": True}, message="success")


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


@router.get("/feedback")
async def admin_feedback_list(
    _: CurrentAdmin,
    svc: Annotated[AdminService, Depends(get_admin_service)],
    reason: str | None = Query(None),
    is_resolved: bool = Query(False),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
):
    data = await svc.list_feedback(
        reason=reason,
        is_resolved=is_resolved,
        page=page,
        size=size,
    )
    return api_json(http_status=200, data=data, message="success")


@router.get("/feedback/{feedback_id}/context")
async def admin_feedback_context(
    feedback_id: uuid.UUID,
    _: CurrentAdmin,
    svc: Annotated[AdminService, Depends(get_admin_service)],
):
    data = await svc.get_feedback_context(feedback_id)
    return api_json(http_status=200, data=data, message="success")


@router.post("/feedback/{feedback_id}/correction")
async def admin_feedback_correction(
    request: Request,
    feedback_id: uuid.UUID,
    admin: CurrentAdmin,
    body: CorrectionNoteRequest,
    svc: Annotated[AdminService, Depends(get_admin_service)],
):
    data = await svc.create_correction_note(
        feedback_id=feedback_id,
        body=body,
        admin_id=admin.id,
        client_ip=_client_ip(request),
    )
    return api_json(http_status=201, data=data, message="success")


@router.get("/corrections")
async def admin_corrections(
    _: CurrentAdmin,
    svc: Annotated[AdminService, Depends(get_admin_service)],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
):
    data = await svc.list_corrections(page=page, size=size)
    return api_json(http_status=200, data=data, message="success")


@router.get("/monitoring/health")
async def admin_monitoring_health(
    _: CurrentAdmin,
    svc: Annotated[AdminService, Depends(get_admin_service)],
):
    data = await svc.monitoring_health()
    return api_json(http_status=200, data=data, message="success")


@router.get("/monitoring/latency")
async def admin_monitoring_latency(
    _: CurrentAdmin,
    svc: Annotated[AdminService, Depends(get_admin_service)],
    range: str = Query("24h"),
):
    data = await svc.monitoring_latency(range_value=range)
    return api_json(http_status=200, data=data, message="success")


@router.get("/monitoring/cost")
async def admin_monitoring_cost(
    _: CurrentAdmin,
    svc: Annotated[AdminService, Depends(get_admin_service)],
    date_value: date | None = Query(None, alias="date"),
):
    data = await svc.monitoring_cost(target_date=date_value)
    return api_json(http_status=200, data=data, message="success")


@router.get("/insights/unmet-demand")
async def admin_unmet_demand(
    _: CurrentAdmin,
    svc: Annotated[AdminService, Depends(get_admin_service)],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
):
    data = await svc.list_unmet_demand(page=page, size=size)
    return api_json(http_status=200, data=data, message="success")


@router.get("/insights/conversion")
async def admin_conversion_stats(
    _: CurrentAdmin,
    svc: Annotated[AdminService, Depends(get_admin_service)],
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
):
    data = await svc.conversion_stats(from_date=from_date, to_date=to_date)
    return api_json(http_status=200, data=data, message="success")


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
        client_ip=_client_ip(
            request
        ),  # 수정: ip_address → client_ip (service 규약 통일)
        page=page,
        size=size,
        search_keyword=search_keyword,
        only_active=not include_inactive_users,
    )
    return api_json(http_status=200, data=data.model_dump(), message="success")


# ─────────────────────────────────────────────────────────────────────────────
# 정책 수집 엔드포인트 (Policy Sync)
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/policies/sync/bootstrap",
    summary="[초기 세팅] 과거 정책 대량 적재",
    description=(
        "최초 세팅 시 사용합니다. 기업마당 API 에서 최대 1000건을 페이지네이션으로 수집합니다. "
        "AI 보강 없이 빠른 수집을 우선합니다. (소요 시간: 약 1~3분)"
    ),
)
async def bootstrap_bizinfo_policies(
    admin: CurrentAdmin,
    svc: Annotated[AdminService, Depends(get_admin_service)],
):
    result = await svc.sync_bootstrap_policies(count=1000)
    return api_json(http_status=200, data=result)


@router.post(
    "/policies/sync/daily",
    summary="[스마트 동기화] 일일 최신 정책 업데이트",
    description=(
        "스케줄러(매일 03:00)가 자동 실행하는 로직을 수동으로 즉시 트리거합니다. "
        "최신 2페이지(200건)를 수집하고 origin_id 기준 upsert 합니다."
    ),
)
async def sync_daily_bizinfo_policies(
    admin: CurrentAdmin,
    svc: Annotated[AdminService, Depends(get_admin_service)],
):
    result = await svc.sync_daily_policies()
    return api_json(http_status=200, data=result)


@router.post(
    "/policies/sync/run",
    summary="[고급] 수집 범위·옵션 직접 지정 실행",
    description=(
        "페이지 범위, AI 보강 여부, 날짜 필터를 자유롭게 설정하여 수집을 실행합니다. "
        "대용량 초기 적재나 특정 기간 재수집 시 사용합니다.\n\n"
        "- `with_ai=true` 설정 시 첨부파일(PDF/HWP/이미지)을 파싱하고 GPT-4o 로 구조화합니다. "
        "공고 1건당 약 3~10초 소요되므로 100건 이상 시 타임아웃 주의.\n"
        "- `date_from` / `date_to` 는 YYYYMMDD 형식입니다. (예: 20250101)"
    ),
)
async def run_policy_sync(
    admin: CurrentAdmin,
    svc: Annotated[AdminService, Depends(get_admin_service)],
    page_start: int = Query(1, ge=1, description="수집 시작 페이지"),
    page_end: int = Query(1, ge=1, description="수집 종료 페이지 (포함)"),
    rows_per_page: int = Query(100, ge=1, le=1000, description="페이지당 공고 수"),
    with_ai: bool = Query(
        False, description="True 이면 첨부파일 파싱 + AI 구조화 실행"
    ),
    date_from: str | None = Query(None, description="공고 시작일 필터 (YYYYMMDD)"),
    date_to: str | None = Query(None, description="공고 종료일 필터 (YYYYMMDD)"),
):
    result = await svc.run_policy_sync(
        page_start=page_start,
        page_end=page_end,
        rows_per_page=rows_per_page,
        with_ai=with_ai,
        date_from=date_from,
        date_to=date_to,
    )
    return api_json(http_status=200, data=result)


# ─────────────────────────────────────────────────────────────────────────────
# 정책 수집 테스트 엔드포인트 (Policy Sync - Test)
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/test-sync-one",
    summary="[TEST] 정책 1개 동기화 및 AI 분석 파이프라인 테스트",
    tags=["Admin - Test"],
    description=(
        "기업마당 API 에서 공고 1건을 가져와 전체 파이프라인을 검증합니다.\n\n"
        "1. API 에서 최신 공고 1건 수집\n"
        "2. 첨부파일(PDF/HWP/이미지) 다운로드 및 파싱\n"
        "3. GPT-4o 로 구조화(target_logic, bonus_logic, ai_summary)\n"
        "4. DB upsert 후 결과 반환\n"
        "5. 임베딩 청킹 + 벡터 저장 (pgvector)\n\n"
        "서버 콘솔 로그에서 단계별 진행 상황을 확인할 수 있습니다.\n"
        "`debug_output/{origin_id}/` 폴더에 단계별 파일이 저장됩니다."
    ),
)
async def test_sync_single_policy_endpoint(
    admin: CurrentAdmin,
    sync_service: SyncServiceDep,
    page_no: int | None = Query(
        None, description="테스트할 페이지 번호 (미입력 시 1~100 랜덤)"
    ),
):
    # page_no가 없으면 1~100 사이 랜덤 숫자 생성
    target_page = page_no if page_no is not None else random.randint(1, 100)

    result = await sync_service.test_sync_single_policy(page_no=target_page)

    # 어떤 페이지를 테스트했는지 결과에 추가해서 반환
    result["tested_page"] = target_page
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 임베딩 엔드포인트 (Policy Embedding)
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/policies/embed/all",
    summary="[임베딩] 미임베딩 정책 일괄 벡터화",
    tags=["Admin - Embedding"],
    description=(
        "content_hash가 없는 정책(아직 임베딩 안 된 것)을 최대 `limit`건 일괄 처리합니다.\n\n"
        "처리 흐름:\n"
        "  1. content_hash=NULL 인 정책을 조회합니다.\n"
        "  2. 각 정책의 content_raw를 섹션별 청킹합니다.\n"
        "  3. OpenAI text-embedding-3-small API로 벡터를 생성합니다.\n"
        "  4. policy_chunks 테이블에 저장합니다.\n\n"
        "처음 서비스를 세팅하거나 DB를 복구한 후에 실행하세요."
    ),
)
async def embed_all_unembedded_policies(
    _: CurrentAdmin,
    embedding_svc: EmbeddingServiceDep,
    limit: int = Query(500, ge=1, le=2000, description="한 번에 처리할 최대 정책 수"),
):
    result = await embedding_svc.sync_all_unembedded(limit=limit)
    return api_json(http_status=200, data=result)


@router.post(
    "/policies/{policy_id}/embed",
    summary="[임베딩] 특정 정책 단건 재벡터화",
    tags=["Admin - Embedding"],
    description=(
        "특정 정책 1건의 content_raw를 강제로 재임베딩합니다.\n\n"
        "- `force=true`이면 content_hash 변경 여부와 무관하게 재임베딩합니다.\n"
        "- 공고 내용이 수동 수정된 후 벡터를 갱신할 때 사용합니다."
    ),
)
async def embed_single_policy(
    policy_id: uuid.UUID,
    _: CurrentAdmin,
    embedding_svc: EmbeddingServiceDep,
    policy_svc: PolicyServiceDep,
    force: bool = Query(False, description="True이면 해시 비교 없이 강제 재임베딩"),
):
    policy = await policy_svc.get_policy_by_id_internal(policy_id)
    if policy is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="정책을 찾을 수 없습니다.")

    changed = await embedding_svc.sync_policy_chunks(
        policy_id=policy_id,
        content_raw=policy.content_raw,
        policy_title=policy.title or "",
        agency_name=policy.agency_name or "",
        support_type=policy.support_type or "",
        force=force,
    )
    await embedding_svc._session.commit()
    return api_json(
        http_status=200,
        data={"policy_id": str(policy_id), "re_embedded": changed},
        message="임베딩 완료" if changed else "변경 없음 (스킵)",
    )
