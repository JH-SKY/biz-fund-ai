# src/app/domains/admin/repository.py
"""관리자 기능 DB 접근 전용 계층."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone
from typing import Any, Sequence

from src.app.domains.policy.model import Policy
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.domains.auth.model import Admin, AdminAuditLog, User


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

    async def list_audit_logs(self, limit: int = 500) -> Sequence[AdminAuditLog]:
        stmt = (
            select(AdminAuditLog)
            .order_by(desc(AdminAuditLog.created_at))
            .limit(limit)
        )
        res = await self._session.execute(stmt)
        return res.scalars().all()

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

    async def count_new_users_since(self, since: datetime) -> int:
        from sqlalchemy import func
        stmt = select(func.count()).select_from(User).where(User.created_at >= since)
        res = await self._session.execute(stmt)
        return int(res.scalar_one())

    async def list_users_page(
        self,
        *,
        page: int,
        size: int,
        search_keyword: str | None,
        only_active: bool = True,
    ) -> tuple[Sequence[User], int]:
        from typing import Sequence
        from sqlalchemy import func, or_, desc
        filters = []
        if only_active:
            filters.append(User.is_active.is_(True))
        if search_keyword and search_keyword.strip():
            kw = f"%{search_keyword.strip()}%"
            filters.append(or_(User.name.ilike(kw), User.email.ilike(kw)))
        
        count_stmt = select(func.count()).select_from(User)
        stmt = select(User)
        for f in filters:
            count_stmt = count_stmt.where(f)
            stmt = stmt.where(f)
            
        total = int((await self._session.execute(count_stmt)).scalar_one())
        stmt = stmt.order_by(desc(User.created_at)).offset((page - 1) * size).limit(size)
        rows = (await self._session.execute(stmt)).scalars().all()
        return rows, total



def utc_start_of_today() -> datetime:
    """UTC 기준 당일 00:00 (대시보드 일일 집계)."""

    now = datetime.now(timezone.utc)
    return datetime.combine(now.date(), time.min, tzinfo=timezone.utc)


    # ── 3. Admin & Internal (추후 분리 예정) ──────────────────────────────────────
    
async def create_policy_internal(
    self,
    *,
    title: str,
    agency_name: str,
    support_type: str | None,
    content_raw: str,
    start_date: date | None,
    end_date: date | None,
    target_logic: dict | None,
    status: str,
) -> Policy:
    """시스템 내부용 정책 등록 (관리자 도구 전용)"""
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

async def patch_policy_internal(
    self,
    policy: Policy,
    **kwargs,
) -> None:
    """정책 정보 수정 (넘겨받은 필드만 동적으로 업데이트)"""
    for key, value in kwargs.items():
        if hasattr(policy, key) and value is not None:
            setattr(policy, key, value)
    await self._session.flush()

async def list_top_policies_by_views(self, limit: int) -> list[Policy]:
    """인기 정책 TOP N을 조회합니다. (대시보드 노출용)"""
    stmt = (
        select(Policy)
        .where(Policy.is_active.is_(True))
        .order_by(Policy.view_count.desc())
        .limit(limit)
    )
    res = await self._session.execute(stmt)
    return list(res.scalars().all())