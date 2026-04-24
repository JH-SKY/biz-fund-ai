from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.app.domains.business.service import BusinessService


class _FakeBusinessRepo:
    def __init__(self, snapshots: list[SimpleNamespace]) -> None:
        self._snapshots = snapshots

    async def get_financial_history(self, business_id: uuid.UUID):
        return self._snapshots


@pytest.mark.asyncio
async def test_get_financial_history_returns_full_snapshot_fields():
    business_id = uuid.uuid4()
    snapshot_id = uuid.uuid4()
    created_at = datetime(2026, 4, 23, 10, 30, tzinfo=timezone.utc)

    repo = _FakeBusinessRepo(
        snapshots=[
            SimpleNamespace(
                id=snapshot_id,
                business_id=business_id,
                snapshot_year=2026,
                snapshot_period="ANNUAL",
                annual_revenue=120000000,
                operating_profit=15000000,
                net_income=12000000,
                total_debt=30000000,
                capital=50000000,
                debt_ratio=25.0,
                employee_count=7,
                tax_arrears_yn=False,
                is_verified=False,
                created_at=created_at,
            )
        ]
    )

    svc = BusinessService(
        session=AsyncMock(),
        repo=repo,
        biz_verification=AsyncMock(),
        stats_validation=AsyncMock(),
        file_storage=AsyncMock(),
    )

    business = SimpleNamespace(id=business_id)
    result = await svc.get_financial_history(business)

    assert len(result) == 1
    item = result[0]
    assert item.finance_id == str(snapshot_id)
    assert item.snapshot_year == 2026
    assert item.snapshot_period == "ANNUAL"
    assert item.debt_ratio == 25.0
    assert item.employee_count == 7
    assert item.created_at == created_at
