# src/app/domains/admin/service.py
"""관리자 비즈니스 로직 및 트랜잭션 경계."""

from __future__ import annotations

import json
import uuid
from datetime import timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import ADMIN_POLICY_AGENCY_NAME
from src.app.core.security import create_admin_access_token, verify_password
from src.app.domains.admin.model import Admin
from src.app.domains.admin.repository import AdminRepository, utc_start_of_today
from src.app.domains.admin.schema import (
    AdminLoginRequest,
    AdminUserItem,
    AdminUserListData,
    AuditLogItem,
    BatchDetailData,
    BatchStatusItem,
    ChatMonitorItem,
    ChatMonitorResponseData,
    ContentPatchRequest,
    ContentPublishRequest,
    ContentPublishResponseData,
    DashboardStatsData,
    PolicyCreateRequest,
    PolicyCreateResponseData,
    PolicyPatchRequest,
)
from src.app.domains.auth.model import User
from src.app.domains.auth.service import AuthService
from src.app.domains.biz_pick.service import BizPickService
from src.app.domains.chat.service import ChatService
from src.app.domains.diagnosis.service import DiagnosisService
from src.app.domains.policy.model import PolicyStatus
from src.app.domains.policy.service import PolicyService
from src.app.domains.policy.sync_service import BizinfoSyncService
from src.app.domains.system.service import SystemService


class AdminService:
    """관리자 유스케이스. 타 도메인은 Service를 통해 통신한다."""

    def __init__(
        self,
        session: AsyncSession,
        repo: AdminRepository,
        auth_service: AuthService,
        chat_service: ChatService,
        policy_service: PolicyService,
        biz_pick_service: BizPickService,
        system_service: SystemService,
        diagnosis_service: DiagnosisService,
        sync_service: BizinfoSyncService,
    ) -> None:
        self._session = session
        self._repo = repo
        self._auth_service = auth_service
        self._chat_service = chat_service
        self._policy_service = policy_service
        self._biz_pick_service = biz_pick_service
        self._system_service = system_service
        self._diagnosis_service = diagnosis_service
        self._sync_service = sync_service

    async def login(self, body: AdminLoginRequest) -> dict:
        admin = await self._repo.get_admin_by_login_id(body.login_id)
        if admin is None or not admin.is_active:
            raise HTTPException(
                status_code=401, detail="로그인 정보가 올바르지 않습니다."
            )
        if not verify_password(body.password, admin.password):
            raise HTTPException(
                status_code=401, detail="로그인 정보가 올바르지 않습니다."
            )
        token = create_admin_access_token(admin_id=admin.id)
        return {"access_token": token, "token_type": "bearer"}

    async def create_policy(
        self,
        body: PolicyCreateRequest,
        *,
        admin: Admin,
        client_ip: str | None,
    ) -> PolicyCreateResponseData:
        target_logic = {"target_region": body.target_region}
        row = await self._policy_service.create_policy_internal(
            title=body.title,
            agency_name=ADMIN_POLICY_AGENCY_NAME,
            support_type=body.category,
            content_raw=body.content,
            start_date=body.apply_start_date,
            end_date=body.apply_end_date,
            target_logic=target_logic,
            status=PolicyStatus.RECRUITING,
        )
        ts = row.created_at
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        created_at = ts.isoformat().replace("+00:00", "Z")
        await self._repo.add_audit_log(
            admin_id=admin.id,
            action_type="CREATE_POLICY",
            target_id=row.id,
            changes={"title": body.title},
            ip_address=client_ip,
        )
        await self._session.commit()
        return PolicyCreateResponseData(policy_id=str(row.id), created_at=created_at)

    async def patch_policy(
        self,
        policy_id: uuid.UUID,
        body: PolicyPatchRequest,
        *,
        admin: Admin,
        client_ip: str | None,
    ) -> None:
        row = await self._policy_service.get_policy_by_id_internal(policy_id)
        if row is None:
            raise HTTPException(status_code=404, detail="정책을 찾을 수 없습니다.")
        await self._policy_service.patch_policy_internal(
            row,
            title=body.title,
            apply_end_date=body.apply_end_date,
            content=body.content,
        )
        await self._repo.add_audit_log(
            admin_id=admin.id,
            action_type="UPDATE_POLICY",
            target_id=row.id,
            changes=body.model_dump(exclude_unset=True),
            ip_address=client_ip,
        )
        await self._session.commit()

    async def publish_content(
        self,
        body: ContentPublishRequest,
        *,
        admin: Admin,
        client_ip: str | None,
    ) -> ContentPublishResponseData:
        row = await self._biz_pick_service.create_biz_pick_internal(
            title=body.title,
            category="GENERAL",
            content_html=body.body_html,
            thumbnail_url=body.thumbnail_url,
            is_published=body.is_published,
        )
        await self._repo.add_audit_log(
            admin_id=admin.id,
            action_type="PUBLISH_CONTENT",
            target_id=row.id,
            changes={"title": body.title, "is_published": body.is_published},
            ip_address=client_ip,
        )
        await self._session.commit()
        return ContentPublishResponseData(content_id=str(row.id))

    async def patch_content(
        self,
        content_id: uuid.UUID,
        body: ContentPatchRequest,
        *,
        admin: Admin,
        client_ip: str | None,
    ) -> None:
        row = await self._biz_pick_service.get_biz_pick_by_id_internal(content_id)
        if row is None:
            raise HTTPException(status_code=404, detail="콘텐츠를 찾을 수 없습니다.")
        await self._biz_pick_service.patch_biz_pick_internal(
            row,
            title=body.title,
            body_html=body.body_html,
            thumbnail_url=body.thumbnail_url,
            is_published=body.is_published,
        )
        await self._repo.add_audit_log(
            admin_id=admin.id,
            action_type="UPDATE_CONTENT",
            target_id=row.id,
            changes=body.model_dump(exclude_unset=True),
            ip_address=client_ip,
        )
        await self._session.commit()

    async def list_chat_monitor(
        self,
        *,
        user_id: uuid.UUID | None,
        admin_id: uuid.UUID,  # [추가] 로그용
        client_ip: str | None,
        page: int,
        size: int,
    ) -> ChatMonitorResponseData:
        logs = await self._chat_service.list_user_chat_logs_page(
            user_id=user_id,
            page=page,
            size=size,
        )
        await self._repo.add_audit_log(
            admin_id=admin_id,
            action_type="CHAT_MONITOR_VIEW",
            target_id=user_id,
            changes={"page": page, "size": size},
            ip_address=client_ip,
        )
        # 중요: 조회의 경우 session.commit()은 필수는 아니나,
        # 로그 저장(INSERT)을 확정하기 위해 commit을 호출하는 것이 실무적 안전책입니다.
        await self._session.commit()
        items: list[ChatMonitorItem] = []
        for ulog in logs:
            assistant = await self._chat_service.find_first_assistant_after(
                room_id=ulog.room_id,
                after=ulog.created_at,
            )
            ts = ulog.created_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            items.append(
                ChatMonitorItem(
                    session_id=str(ulog.room_id),
                    user_msg=ulog.content,
                    ai_res=assistant.content if assistant else "",
                    timestamp=ts.isoformat().replace("+00:00", "Z"),
                )
            )
        return ChatMonitorResponseData(items=items)

    async def dashboard_stats(self) -> DashboardStatsData:
        start = utc_start_of_today()
        new_users = await self._auth_service.count_new_users_since(start)
        active_chats = await self._chat_service.count_chat_logs_since(start)
        top = await self._policy_service.list_top_policies_by_views(5)
        popular = [{"id": str(p.id), "hits": p.view_count} for p in top]
        return DashboardStatsData(
            new_users_today=new_users,
            active_chats_today=active_chats,
            popular_policies=popular,
        )

    async def list_audit_logs(
        self,
        *,
        admin_id: uuid.UUID,  # [추가] 로그용
        client_ip: str | None,
    ) -> list[AuditLogItem]:
        rows = await self._repo.list_audit_logs()
        out: list[AuditLogItem] = []
        for r in rows:
            ts = r.created_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            out.append(
                AuditLogItem(
                    admin_id=str(r.admin_id),
                    action=r.action_type,
                    target=str(r.target_id) if r.target_id else None,
                    created_at=ts.isoformat().replace("+00:00", "Z"),
                )
            )
        return out

    async def batch_status(self) -> list[BatchStatusItem]:
        rows = await self._system_service.list_latest_batch_per_job()
        items: list[BatchStatusItem] = []
        for r in rows:
            lr = r.started_at
            if lr.tzinfo is None:
                lr = lr.replace(tzinfo=timezone.utc)
            last_run = lr.strftime("%Y-%m-%d %H:%M")
            items.append(
                BatchStatusItem(
                    job_name=r.job_name,
                    last_run=last_run,
                    status=r.status,
                )
            )
        return items

    async def batch_detail(self, job_id: uuid.UUID) -> BatchDetailData:
        row = await self._system_service.get_batch_log_by_id(job_id)
        if row is None:
            raise HTTPException(status_code=404, detail="배치 로그를 찾을 수 없습니다.")
        raw = row.error_details
        if raw is None:
            raw_log = ""
        elif isinstance(raw, str):
            raw_log = raw
        else:
            raw_log = json.dumps(raw, ensure_ascii=False)
        return BatchDetailData(job_id=str(row.id), raw_log=raw_log)

    async def list_users(
        self,
        *,
        page: int,
        size: int,
        admin_id: uuid.UUID,
        client_ip: str | None,  # 수정: ip_address → client_ip (router 호출 규약 통일)
        search_keyword: str | None,
        only_active: bool = True,
    ) -> AdminUserListData:
        rows, total = await self._auth_service.list_users_page(
            page=page,
            size=size,
            search_keyword=search_keyword,
            only_active=only_active,
        )

        await self._repo.add_audit_log(
            admin_id=admin_id,
            action_type="USER_LIST_VIEW",
            target_id=None,
            changes={"page": page, "search": search_keyword},
            ip_address=client_ip,
        )
        total_pages = (total + size - 1) // size if size > 0 else 0
        items: list[AdminUserItem] = []
        for u in rows:
            ts = u.created_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            items.append(
                AdminUserItem(
                    user_id=str(u.id),
                    name=u.name,
                    email=u.email,
                    status=u.status,
                    is_active=u.is_active,
                    created_at=ts.isoformat().replace("+00:00", "Z"),
                )
            )
        return AdminUserListData(
            items=items,
            total_count=total,
            total_pages=total_pages,
        )

    async def list_users_page(
        self,
        *,
        page: int,
        size: int,
        search_keyword: str | None,
        only_active: bool = True,
    ) -> tuple[list[User], int]:
        rows, total = await self._repo.list_users_page(
            page=page, size=size, search_keyword=search_keyword, only_active=only_active
        )
        return list(rows), total

    # ---------------------------------------------------------
    # [신규] 진단 및 시뮬레이션 모니터링 (Diagnosis Domain 협력)
    # ---------------------------------------------------------

    async def list_diagnosis_monitor(
        self,
        *,
        admin_id: uuid.UUID,
        client_ip: str | None,
        sim_type: str | None = "DIAGNOSIS",
    ) -> list:
        """
        1. 기능: [관리자] 전수 진단/시뮬레이션 로그 모니터링.
        2. 설계 의도: 시스템 전체에서 발생하는 AI 진단 비용과 결과의 적절성을 관리자가 감시합니다.
        3. 메커니즘: DiagnosisService의 관리 전용 메서드를 호출하여 도메인 경계를 준수합니다.
        """
        # DiagnosisService에 관리자용 조회 로직이 구현되어 있어야 함
        logs = await self._diagnosis_service.get_all_logs_for_admin(sim_type=sim_type)

        await self._repo.add_audit_log(
            admin_id=admin_id,
            action_type="DIAGNOSIS_MONITOR_VIEW",
            target_id=None,
            changes={"sim_type": sim_type},
            ip_address=client_ip,
        )
        await self._session.commit()

        # 실무에서는 여기서 전용 Admin Schema로 변환하여 리턴합니다.
        return logs

    async def get_diagnosis_detail_admin(
        self,
        diagnosis_id: uuid.UUID,
        admin_id: uuid.UUID,
        client_ip: str | None,
    ) -> Any:
        """
        1. 기능: 특정 진단 결과 상세 조회 (관리용).
        2. 설계 의도: 사용자 권한 체크 없이 관리자가 기술적 문제나 CS 대응을 위해 상세 로그를 확인합니다.
        """
        log = await self._diagnosis_service.get_log_detail_for_admin(diagnosis_id)

        await self._repo.add_audit_log(
            admin_id=admin_id,
            action_type="DIAGNOSIS_DETAIL_VIEW",
            target_id=diagnosis_id,
            changes={},
            ip_address=client_ip,
        )
        await self._session.commit()
        return log

    async def sync_bootstrap_policies(self, count: int = 1000):
        """과거 데이터 대량 적재 위임"""
        return await self._sync_service.bootstrap_historical_policies(count=count)

    async def sync_daily_policies(self):
        """일일 최신 정책 업데이트 위임"""
        return await self._sync_service.sync_recent_policies()

    async def run_policy_sync(
        self,
        *,
        page_start: int = 1,
        page_end: int = 1,
        rows_per_page: int = 100,
        with_ai: bool = False,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict:
        """관리자 수동 트리거용 정책 수집 실행.

        run_policy_sync 의 모든 파라미터를 그대로 노출하여,
        관리자가 API 를 통해 원하는 범위·옵션으로 수집을 실행할 수 있도록 한다.
        """
        return await self._sync_service.run_policy_sync(
            job_name="POLICY_ADMIN_MANUAL",
            page_start=page_start,
            page_end=page_end,
            rows_per_page=rows_per_page,
            with_ai=with_ai,
            date_from=date_from,
            date_to=date_to,
        )
