# src/app/domains/admin/service.py
"""관리자 비즈니스 로직 및 트랜잭션 경계."""

from __future__ import annotations

import json
import uuid
from datetime import timezone

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import ADMIN_POLICY_AGENCY_NAME
from src.app.core.security import create_admin_access_token, verify_password
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
from src.app.domains.auth.model import Admin
from src.app.domains.policy.model import PolicyStatus


class AdminService:
    """관리자 유스케이스. Repository만 통해 DB에 접근한다."""

    def __init__(self, session: AsyncSession, repo: AdminRepository) -> None:
        self._session = session
        self._repo = repo

    async def login(self, body: AdminLoginRequest) -> dict:
        admin = await self._repo.get_admin_by_login_id(body.login_id)
        if admin is None or not admin.is_active:
            raise HTTPException(status_code=401, detail="로그인 정보가 올바르지 않습니다.")
        if not verify_password(body.password, admin.password):
            raise HTTPException(status_code=401, detail="로그인 정보가 올바르지 않습니다.")
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
        row = await self._repo.create_policy(
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
        row = await self._repo.get_policy_by_id(policy_id)
        if row is None:
            raise HTTPException(status_code=404, detail="정책을 찾을 수 없습니다.")
        await self._repo.patch_policy(
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
        row = await self._repo.create_biz_pick(
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
        row = await self._repo.get_biz_pick_by_id(content_id)
        if row is None:
            raise HTTPException(status_code=404, detail="콘텐츠를 찾을 수 없습니다.")
        await self._repo.patch_biz_pick(
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
        page: int,
        size: int,
    ) -> ChatMonitorResponseData:
        logs = await self._repo.list_user_chat_logs_page(
            user_id=user_id,
            page=page,
            size=size,
        )
        items: list[ChatMonitorItem] = []
        for ulog in logs:
            assistant = await self._repo.find_first_assistant_after(
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
        new_users = await self._repo.count_new_users_since(start)
        active_chats = await self._repo.count_chat_logs_since(start)
        top = await self._repo.list_top_policies_by_views(5)
        popular = [
            {"id": str(p.id), "hits": p.view_count}
            for p in top
        ]
        return DashboardStatsData(
            new_users_today=new_users,
            active_chats_today=active_chats,
            popular_policies=popular,
        )

    async def list_audit_logs(self) -> list[AuditLogItem]:
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
        rows = await self._repo.list_latest_batch_per_job()
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
        row = await self._repo.get_batch_log_by_id(job_id)
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
        search_keyword: str | None,
        only_active: bool = True,
    ) -> AdminUserListData:
        rows, total = await self._repo.list_users(
            page=page,
            size=size,
            search_keyword=search_keyword,
            only_active=only_active,
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
