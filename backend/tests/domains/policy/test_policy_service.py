from __future__ import annotations

import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.app.domains.policy.interfaces import MockMatchEngine, RDBPolicySearcher
from src.app.domains.policy.service import PolicyService


class _FakePolicyRepo:
    def __init__(self) -> None:
        self._policies = [
            SimpleNamespace(
                id=uuid.uuid4(),
                title="정책 A",
                category="금융",
                closed_at=date(9999, 12, 31),
                is_active=True,
            ),
            SimpleNamespace(
                id=uuid.uuid4(),
                title="정책 B",
                category="바우처",
                closed_at=date(2026, 12, 31),
                is_active=True,
            ),
        ]
        self.toggled_with: tuple[uuid.UUID, uuid.UUID] | None = None

    async def get_active_policies(self, *, page: int = 1, size: int = 10):
        return self._policies[:size], len(self._policies), 1

    async def get_bookmarked_policy_ids(
        self, *, business_id: uuid.UUID, policy_ids: list[uuid.UUID]
    ):
        return {policy_ids[0]} if policy_ids else set()

    async def get_bookmarked_policies(
        self, *, business_id: uuid.UUID, page: int = 1, size: int = 10
    ):
        return self._policies[:size], len(self._policies), 1

    async def get_recommendation_candidates(self, limit: int):
        # 테스트용 가짜 정책 리스트 반환 (기존에 쓰던 데이터가 있다면 활용)
        return self._policies[:limit]

    async def get_policy_by_id(self, policy_id: uuid.UUID):
        return SimpleNamespace(id=policy_id, is_active=True)

    async def toggle_bookmark(self, *, business_id: uuid.UUID, policy_id: uuid.UUID):
        self.toggled_with = (business_id, policy_id)
        return True

    async def search_policies(self, **kwargs):
        return self._policies, len(self._policies), 1


def _make_policy_service(repo: _FakePolicyRepo) -> PolicyService:
    session = AsyncMock()
    session.commit = AsyncMock()
    return PolicyService(
        session=session,
        repo=repo,
        searcher=RDBPolicySearcher(repo),
        match_engine=MockMatchEngine(),
        vector_searcher=None,
    )


def _make_business() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        profile_score=80,
        is_biz_no_verified=True,
        employee_count=3,
        ksic_code="56111",
    )


@pytest.mark.asyncio
async def test_get_recommended_policies_validates_requested_business_id():
    repo = _FakePolicyRepo()
    svc = _make_policy_service(repo)
    business = _make_business()

    with pytest.raises(Exception) as exc_info:
        await svc.get_recommended_policies(
            business=business,
            requested_business_id=uuid.uuid4(),
            page=1,
            size=10,
        )

    assert getattr(exc_info.value, "status_code", None) == 404


@pytest.mark.asyncio
async def test_get_bookmarked_policies_returns_items_for_matching_business():
    repo = _FakePolicyRepo()
    svc = _make_policy_service(repo)
    business = _make_business()

    data = await svc.get_bookmarked_policies(
        business=business,
        requested_business_id=business.id,
        page=1,
        size=10,
    )

    assert data.total_count == 2
    assert len(data.items) == 2
    assert all(item.is_bookmarked is True for item in data.items)


@pytest.mark.asyncio
async def test_toggle_bookmark_uses_authenticated_business_context():
    repo = _FakePolicyRepo()
    svc = _make_policy_service(repo)
    business = _make_business()
    policy_id = uuid.uuid4()

    data = await svc.toggle_bookmark(
        policy_id,
        business=business,
        requested_business_id=business.id,
    )

    assert data.is_bookmarked is True
    assert repo.toggled_with == (business.id, policy_id)


@pytest.mark.asyncio
async def test_get_recommended_policies_unverified_notice_when_not_verified():
    repo = _FakePolicyRepo()
    svc = _make_policy_service(repo)
    business = SimpleNamespace(
        id=uuid.uuid4(),
        profile_score=80,
        is_biz_no_verified=False,
        employee_count=2,
        ksic_code="56111",
    )

    data = await svc.get_recommended_policies(
        business=business,
        requested_business_id=business.id,
        page=1,
        size=10,
    )

    assert data.unverified_notice == "미검증 사업자 정보 기반 추천입니다"


@pytest.mark.asyncio
async def test_get_recommended_policies_no_notice_when_verified():
    repo = _FakePolicyRepo()
    svc = _make_policy_service(repo)
    business = _make_business()

    data = await svc.get_recommended_policies(
        business=business,
        requested_business_id=business.id,
        page=1,
        size=10,
    )

    assert data.unverified_notice is None
