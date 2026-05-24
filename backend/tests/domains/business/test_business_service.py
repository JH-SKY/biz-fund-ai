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
from src.app.domains.business.schema import BusinessUpdateRequest, FinanceCreateRequest, FundingPurpose


class _FakeBusinessRepo:
    def __init__(self, snapshots: list[SimpleNamespace]) -> None:
        self._snapshots = snapshots
        self.updated_business_calls: list[dict] = []
        self.latest_snapshot: SimpleNamespace | None = snapshots[0] if snapshots else None
        self.created_snapshot: SimpleNamespace | None = None

    async def get_financial_history(self, business_id: uuid.UUID):
        return self._snapshots

    async def update_business(self, biz: SimpleNamespace, **kwargs) -> None:
        self.updated_business_calls.append(kwargs)
        for key, value in kwargs.items():
            if value is not None:
                setattr(biz, key, value)

    async def get_latest_financial_snapshot_internal(self, business_id: uuid.UUID):
        return self.latest_snapshot

    async def get_financial_snapshot_by_year(self, business_id: uuid.UUID, year: int):
        return None

    async def create_financial_snapshot(self, **kwargs):
        snapshot = SimpleNamespace(
            id=uuid.uuid4(),
            is_verified=False,
            created_at=datetime(2026, 4, 23, 10, 30, tzinfo=timezone.utc),
            **kwargs,
        )
        self.created_snapshot = snapshot
        return snapshot


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


@pytest.mark.asyncio
async def test_update_my_business_recalculates_profile_score_from_latest_finance_snapshot():
    business_id = uuid.uuid4()
    repo = _FakeBusinessRepo(
        snapshots=[
            SimpleNamespace(
                annual_revenue=120000000,
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
    business = SimpleNamespace(
        id=business_id,
        biz_name="기존 상호",
        representative_name="홍길동",
        biz_no="1234567890",
        ksic_code="56111",
        ksic_name="음식점업",
        sector_code="FOOD",
        region_sido="서울",
        region_sigungu="도봉구",
        establishment_date=datetime(2024, 1, 1, tzinfo=timezone.utc).date(),
        employee_count=5,
        funding_purpose="OPERATING",
        has_tax_arrears=False,
        has_patent=False,
        is_female_ent=False,
        is_ventured=False,
        profile_score=0,
    )

    body = BusinessUpdateRequest(
        biz_name="새 상호",
        representative_name="김대표",
        funding_purpose=FundingPurpose.OPERATING,
        employee_count=5,
        has_tax_arrears=False,
    )

    await svc.update_my_business(business, body)

    assert repo.updated_business_calls[-1]["profile_score"] == 100
    assert business.profile_score == 100


@pytest.mark.asyncio
async def test_create_financial_snapshot_always_syncs_profile_score_from_revenue_input():
    business_id = uuid.uuid4()
    repo = _FakeBusinessRepo(snapshots=[])
    session = AsyncMock()
    svc = BusinessService(
        session=session,
        repo=repo,
        biz_verification=AsyncMock(),
        stats_validation=AsyncMock(),
        file_storage=AsyncMock(),
    )
    business = SimpleNamespace(
        id=business_id,
        biz_name="성장기업",
        representative_name="이대표",
        biz_no="1234567890",
        ksic_code="56111",
        ksic_name="음식점업",
        sector_code="FOOD",
        region_sido="서울",
        region_sigungu="도봉구",
        establishment_date=datetime(2024, 1, 1, tzinfo=timezone.utc).date(),
        employee_count=3,
        funding_purpose="OPERATING",
        has_tax_arrears=False,
        has_patent=False,
        is_female_ent=False,
        is_ventured=False,
        profile_score=0,
    )

    body = FinanceCreateRequest(
        snapshot_year=2026,
        snapshot_period="ANNUAL",
        term_type="ANNUAL",
        annual_revenue=100_000_000,
        operating_profit=10_000_000,
        net_income=8_000_000,
        total_debt=20_000_000,
        capital=30_000_000,
        employee_count=3,
        tax_arrears_yn=False,
    )

    result = await svc.create_financial_snapshot(business, body)

    assert repo.created_snapshot is not None
    assert repo.updated_business_calls[-1]["profile_score"] == 100
    assert business.profile_score == 100
    assert result.annual_revenue == 100_000_000
    session.commit.assert_awaited()
