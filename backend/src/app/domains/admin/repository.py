# src/app/domains/admin/repository.py
"""관리자 기능 DB 접근 전용 계층."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone
from typing import Any, Sequence

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.auth.admin import Admin
from src.app.models.auth.admin_audit_log import AdminAuditLog
from src.app.models.auth.user import User
from src.app.models.chat.chat_log import ChatLog
from src.app.models.policy.biz_pick import BizPick
from src.app.models.policy.policy import Policy, PolicyStatus
from src.app.models.system.batch_log import BatchLog


class AdminRepository:
    """관리자 도메인 Repository. 비즈니스 판단은 하지 않는다."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_admin_by_id(self, admin_id: uuid.UUID) -> Admin | None:
        stmt = select(Admin).where(
            Admin.id == admin_id,
            Admin.is_active.is_(True),
        )
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_admin_by_login_id(self, login_id: str) -> Admin | None:
        stmt = select(Admin).where(Admin.login_id == login_id)
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def create_policy(
        self,
        *,
        title: str,
        agency_name: str,
        support_type: str | None,
        content_raw: str,
        start_date: date | None,
        end_date: date | None,
        target_logic: dict[str, Any] | None,
        status: PolicyStatus,
    ) -> Policy:
        row = Policy(
            title=title,
            agency_name=agency_name,
            support_type=support_type,
            content_raw=content_raw,
            start_date=start_date,
            end_date=end_date,
            target_logic=target_logic,
            status=status,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get_policy_by_id(self, policy_id: uuid.UUID) -> Policy | None:
        stmt = select(Policy).where(Policy.id == policy_id)
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def patch_policy(
        self,
        policy: Policy,
        *,
        title: str | None,
        apply_end_date: date | None,
        content: str | None,
    ) -> None:
        if title is not None:
            policy.title = title
        if apply_end_date is not None:
            policy.end_date = apply_end_date
        if content is not None:
            policy.content_raw = content
        await self._session.flush()

    async def create_biz_pick(
        self,
        *,
        title: str,
        category: str,
        content_html: str,
        thumbnail_url: str | None,
        is_published: bool,
    ) -> BizPick:
        row = BizPick(
            title=title,
            category=category,
            content_html=content_html,
            thumbnail_url=thumbnail_url,
            is_published=is_published,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get_biz_pick_by_id(self, content_id: uuid.UUID) -> BizPick | None:
        stmt = select(BizPick).where(BizPick.id == content_id)
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def patch_biz_pick(
        self,
        row: BizPick,
        *,
        title: str | None,
        body_html: str | None,
        thumbnail_url: str | None,
        is_published: bool | None,
    ) -> None:
        if title is not None:
            row.title = title
        if body_html is not None:
            row.content_html = body_html
        if thumbnail_url is not None:
            row.thumbnail_url = thumbnail_url
        if is_published is not None:
            row.is_published = is_published
        await self._session.flush()

    async def find_first_assistant_after(
        self,
        *,
        room_id: uuid.UUID,
        after: datetime,
    ) -> ChatLog | None:
        stmt = (
            select(ChatLog)
            .where(
                ChatLog.room_id == room_id,
                ChatLog.role == "assistant",
                ChatLog.created_at > after,
            )
            .order_by(ChatLog.created_at.asc())
            .limit(1)
        )
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_user_chat_logs_page(
        self,
        *,
        user_id: uuid.UUID | None,
        page: int,
        size: int,
    ) -> Sequence[ChatLog]:
        stmt = select(ChatLog).where(ChatLog.role == "user")
        if user_id is not None:
            stmt = stmt.where(ChatLog.user_id == user_id)
        stmt = (
            stmt.order_by(desc(ChatLog.created_at))
            .offset((page - 1) * size)
            .limit(size)
        )
        res = await self._session.execute(stmt)
        return res.scalars().all()

    async def count_new_users_since(self, since: datetime) -> int:
        stmt = select(func.count()).select_from(User).where(User.created_at >= since)
        res = await self._session.execute(stmt)
        return int(res.scalar_one())

    async def count_chat_logs_since(self, since: datetime) -> int:
        stmt = select(func.count()).select_from(ChatLog).where(ChatLog.created_at >= since)
        res = await self._session.execute(stmt)
        return int(res.scalar_one())

    async def list_top_policies_by_views(self, limit: int) -> Sequence[Policy]:
        stmt = (
            select(Policy)
            .order_by(desc(Policy.view_count))
            .limit(limit)
        )
        res = await self._session.execute(stmt)
        return res.scalars().all()

    async def list_audit_logs(self, limit: int = 500) -> Sequence[AdminAuditLog]:
        stmt = (
            select(AdminAuditLog)
            .order_by(desc(AdminAuditLog.created_at))
            .limit(limit)
        )
        res = await self._session.execute(stmt)
        return res.scalars().all()

    async def list_latest_batch_per_job(self) -> Sequence[BatchLog]:
        """PostgreSQL DISTINCT ON(job_name) — 최신 started_at 기준."""

        sub = (
            select(BatchLog)
            .distinct(BatchLog.job_name)
            .order_by(BatchLog.job_name, desc(BatchLog.started_at))
        )
        res = await self._session.execute(sub)
        return res.scalars().all()

    async def get_batch_log_by_id(self, job_id: uuid.UUID) -> BatchLog | None:
        stmt = select(BatchLog).where(BatchLog.id == job_id)
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_users(
        self,
        *,
        page: int,
        size: int,
        search_keyword: str | None,
    ) -> tuple[Sequence[User], int]:
        filters = []
        if search_keyword and search_keyword.strip():
            kw = f"%{search_keyword.strip()}%"
            filters.append(
                or_(
                    User.name.ilike(kw),
                    User.email.ilike(kw),
                )
            )
        count_stmt = select(func.count()).select_from(User)
        stmt = select(User)
        for f in filters:
            count_stmt = count_stmt.where(f)
            stmt = stmt.where(f)
        total = int((await self._session.execute(count_stmt)).scalar_one())
        stmt = (
            stmt.order_by(desc(User.created_at))
            .offset((page - 1) * size)
            .limit(size)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return rows, total

    async def add_audit_log(
        self,
        *,
        admin_id: uuid.UUID,
        action_type: str,
        target_id: uuid.UUID | None,
        changes: dict[str, Any] | None,
        ip_address: str | None,
    ) -> None:
        log = AdminAuditLog(
            admin_id=admin_id,
            action_type=action_type,
            target_id=target_id,
            changes=changes,
            ip_address=ip_address,
        )
        self._session.add(log)


def utc_start_of_today() -> datetime:
    """UTC 기준 당일 00:00 (대시보드 일일 집계)."""

    now = datetime.now(timezone.utc)
    return datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
