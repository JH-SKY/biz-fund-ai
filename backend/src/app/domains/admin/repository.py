# src/app/domains/admin/repository.py
"""관리자 기능 DB 접근 전용 계층."""

from __future__ import annotations

import uuid
from datetime import datetime, time, timezone
from typing import Any, Sequence

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

# [수정됨] User, Policy 등 타 도메인 모델 임포트 완전 삭제
from src.app.domains.auth.model import Admin, AdminAuditLog


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
            select(AdminAuditLog).order_by(desc(AdminAuditLog.created_at)).limit(limit)
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


def utc_start_of_today() -> datetime:
    """UTC 기준 당일 00:00 (대시보드 일일 집계)."""

    now = datetime.now(timezone.utc)
    return datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
