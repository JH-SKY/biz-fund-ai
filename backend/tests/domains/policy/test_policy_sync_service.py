from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock

from src.app.domains.policy.sync_service import BizinfoSyncService


def test_extract_ai_policy_fields_maps_dates_and_support_columns():
    sync_service = BizinfoSyncService(
        session=AsyncMock(),
        repo=AsyncMock(),
        agent=AsyncMock(),
        embedding_service=None,
    )

    enriched = {
        "title": "AI 추출 제목",
        "agency_name": "중진공",
        "category": "금융",
        "support_type": "융자",
        "region": "서울",
        "dates": {
            "start_date": "2026-05-01",
            "end_date": "2026-05-31",
        },
        "support_amount": {
            "min": "1000000",
            "max": 50000000,
            "description": "최대 5천만원",
        },
    }

    mapped = sync_service._extract_ai_policy_fields(enriched)

    assert mapped["title"] == "AI 추출 제목"
    assert mapped["agency_name"] == "중진공"
    assert mapped["support_type"] == "융자"
    assert mapped["start_date"] == date(2026, 5, 1)
    assert mapped["end_date"] == date(2026, 5, 31)
    assert sync_service._coerce_int(enriched["support_amount"]["min"]) == 1000000
    assert sync_service._coerce_int(enriched["support_amount"]["max"]) == 50000000
