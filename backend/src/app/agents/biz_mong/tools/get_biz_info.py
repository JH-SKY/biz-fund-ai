# src/app/agents/biz_mong/tools/get_biz_info.py
"""Tool: DB에서 사업장 정보와 최신 재무 스냅샷을 조회한다.

계층 원칙:
  - 이 파일은 '데이터 수집' 전담 도구입니다. 비즈니스 판단 없이 DB 조회만 수행합니다.
  - Business 모델과 BusinessFinancialSnapshot 모델의 필드를 그대로 dict 로 직렬화하여 반환합니다.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.app.domains.business.repository import BusinessRepository

logger = logging.getLogger(__name__)


async def get_biz_info(
    business_id: str,
    session: AsyncSession,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """business_id 에 해당하는 사업장 정보와 최신 재무 스냅샷을 dict 로 반환한다.

    Returns:
        (biz_info, financial_data) 튜플.
        정보가 없을 경우 빈 dict {} 를 반환한다.

    biz_info 예시:
        {
            "biz_name": "비즈몽 테스트",
            "region_sido": "서울",
            "region_sigungu": "강남구",
            "region_code": "1168000000",
            "establishment_date": "2021-03-15",
            "has_patent": False,
            "is_ventured": True,
            "is_female_ent": False,
            "ksic_code": "J5811",
            "sector_code": "IT",
        }

    financial_data 예시:
        {
            "annual_revenue": 500_000_000,
            "employee_count": 8,
            "total_debt": 50_000_000,
            "debt_ratio": 10.0,
            "tax_arrears_yn": False,
            "snapshot_year": 2024,
        }
    """
    try:
        biz_uuid = uuid.UUID(business_id)
    except (ValueError, AttributeError):
        logger.warning("[get_biz_info] 유효하지 않은 business_id: %s", business_id)
        return {}, {}

    repo = BusinessRepository(session)

    # 사업장 기본 정보 조회 (ID 직접 조회)
    from sqlalchemy import select
    from src.app.domains.business.model import Business
    stmt = select(Business).where(Business.id == biz_uuid, Business.is_active.is_(True))
    result = await session.execute(stmt)
    biz = result.scalar_one_or_none()

    if biz is None:
        logger.warning("[get_biz_info] business_id=%s 에 해당하는 사업장 없음", business_id)
        return {}, {}

    biz_info: dict[str, Any] = {
        "biz_name": biz.biz_name,
        "representative_name": biz.representative_name,
        "region_sido": biz.region_sido,
        "region_sigungu": biz.region_sigungu,
        "region_code": biz.region_code,
        "establishment_date": (
            biz.establishment_date.isoformat() if isinstance(biz.establishment_date, date) else biz.establishment_date
        ),
        "has_patent": biz.has_patent,
        "is_ventured": biz.is_ventured,
        "is_female_ent": biz.is_female_ent,
        "ksic_code": biz.ksic_code,
        "sector_code": biz.sector_code,
        "biz_verified_status": biz.biz_verified_status,
    }

    # 2. 최신 재무 스냅샷 조회
    snap = await repo.get_latest_financial_snapshot_internal(biz_uuid)

    if snap is None:
        logger.info("[get_biz_info] business_id=%s 재무 스냅샷 없음", business_id)
        return biz_info, {}

    financial_data: dict[str, Any] = {
        "snapshot_year": snap.snapshot_year,
        "annual_revenue": snap.annual_revenue,
        "operating_profit": snap.operating_profit,
        "net_income": snap.net_income,
        "total_debt": snap.total_debt,
        "capital": snap.capital,
        "debt_ratio": float(snap.debt_ratio) if snap.debt_ratio is not None else None,
        "employee_count": snap.employee_count,
        "tax_arrears_yn": snap.tax_arrears_yn,
    }

    logger.debug("[get_biz_info] business_id=%s 조회 완료", business_id)
    return biz_info, financial_data
