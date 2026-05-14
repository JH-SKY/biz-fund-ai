from __future__ import annotations

import uuid
from datetime import date
from types import SimpleNamespace

import pytest

from src.app.domains.policy.interfaces import RuleBasedMatchEngine
from src.app.domains.policy.schema import MatchLevel


def _business(**overrides):
    base = {
        "id": uuid.uuid4(),
        "ksic_code": "70209",
        "ksic_name": "경영 컨설팅업",
        "sector_code": "SERVICE",
        "region_sido": "부산",
        "region_sigungu": "해운대구",
        "establishment_date": date(2023, 2, 10),
        "employee_count": 4,
        "has_patent": False,
        "is_ventured": False,
        "is_female_ent": True,
        "has_tax_arrears": False,
        "is_biz_no_verified": True,
        "funding_purpose": "OPERATING",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _snapshot(**overrides):
    base = {
        "annual_revenue": 150_000_000,
        "employee_count": 4,
        "debt_ratio": 40.0,
        "tax_arrears_yn": False,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _policy(**overrides):
    base = {
        "id": uuid.uuid4(),
        "title": "부산 여성기업 성장 지원",
        "category": "성장지원",
        "support_type": "성장자금",
        "content_raw": "부산 지역 서비스업 또는 제조업 여성기업을 위한 성장 지원 자금",
        "ai_summary": "부산 여성기업 성장 지원 정책",
        "target_logic": {
            "region_restricted": True,
            "allowed_regions": ["부산"],
            "sectors": ["서비스", "제조"],
            "max_revenue": 300_000_000,
        },
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_rule_based_engine_matches_service_sector_aliases():
    engine = RuleBasedMatchEngine()

    result = await engine.compute_match(
        policy=_policy(),
        business=_business(),
        financial_snapshot=_snapshot(),
    )

    assert result.match_level in {MatchLevel.GREEN, MatchLevel.YELLOW}
    assert result.match_score > 0


@pytest.mark.asyncio
async def test_rule_based_engine_hard_fails_tax_arrears_for_funding_policies():
    engine = RuleBasedMatchEngine()

    result = await engine.compute_match(
        policy=_policy(title="전국 소상공인 운전자금", category="운영자금", support_type="운영자금"),
        business=_business(has_tax_arrears=True, is_female_ent=False),
        financial_snapshot=_snapshot(tax_arrears_yn=True),
    )

    assert result.match_level == MatchLevel.RED
    assert "체납" in result.reason
