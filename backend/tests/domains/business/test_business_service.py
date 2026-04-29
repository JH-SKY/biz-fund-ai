# backend/tests/domains/business/test_business_service.py
"""BusinessService 유닛 테스트.

테스트 범위:
  - get_financial_history: 재무 이력 조회 응답 필드 검증

[설계 의도]
  - DB I/O 는 _FakeBusinessRepo(Mock) 로 대체하여 서비스 로직만 격리 테스트한다.
  - 각 테스트는 독립적으로 실행되며 외부 의존성이 없다.
"""

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
