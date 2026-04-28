# src/app/agents/biz_mong/nodes/stats_node.py
"""Node 4 (Stats): DB Aggregate — 동종업계 통계 비교 인사이트.

데이터 소스:
  - business_financial_snapshots 테이블의 동일 ksic_code(표준산업분류) 사업장 집계
  - 비교 지표: 연매출, 직원 수, 부채비율
  - 백분위(Percentile) 계산으로 사용자 사업장의 상대적 위치를 표시

[설계 의도]:
  - 외부 API 없이 서비스 내 누적 데이터만 활용 (인프라 비용 0원).
  - 최소 5개 이상의 동종 데이터가 있을 때만 비교 통계를 제공한다.
  - 데이터 부족 시 전국 평균 통계를 폴백으로 제공한다.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import time
from typing import Any

from sqlalchemy import Float, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.agents.biz_mong.telemetry import build_node_log
from src.app.domains.business.model import Business, BusinessFinancialSnapshot

logger = logging.getLogger(__name__)

MIN_PEER_COUNT = 5   # 동종업계 비교를 위한 최소 샘플 수


# ═══════════════════════════════════════════════════════════════════════════════
# 노드 함수
# ═══════════════════════════════════════════════════════════════════════════════

async def stats_node(
    state: dict,
    session: AsyncSession,
) -> dict:
    """동종업계 매출/인원/부채비율 통계를 집계하여 State 에 저장한다.

    State 입력:
        biz_info: ksic_code 포함
        financial_data: 현재 사업장 재무 데이터
    State 출력:
        stats_insight: {market_trend, peer_comparison, percentile}
    """
    started_at = datetime.now(timezone.utc)
    started_mono = time.monotonic()
    biz_info: dict = state.get("biz_info") or {}
    financial_data: dict = state.get("financial_data") or {}

    ksic_code: str | None = biz_info.get("ksic_code")
    snapshot_year: int | None = financial_data.get("snapshot_year")

    # ── 동종업계 통계 집계 ──────────────────────────────────────────────
    peer_stats = await _aggregate_peer_stats(session, ksic_code, snapshot_year)

    if peer_stats["peer_count"] < MIN_PEER_COUNT:
        logger.info(
            "[stats_node] 동종업계 데이터 부족 (ksic=%s, count=%d) → 전국 집계 사용",
            ksic_code, peer_stats["peer_count"],
        )
        peer_stats = await _aggregate_peer_stats(session, ksic_code=None, year=snapshot_year)

    # ── 백분위 계산 ──────────────────────────────────────────────────────
    percentile = _calculate_percentile(financial_data, peer_stats)

    # ── 인사이트 텍스트 생성 ──────────────────────────────────────────────
    market_trend = _build_market_trend_text(peer_stats, ksic_code)
    peer_comparison = _build_comparison_text(financial_data, peer_stats, percentile)

    stats_insight: dict[str, Any] = {
        "peer_count": peer_stats["peer_count"],
        "ksic_code": ksic_code,
        "avg_revenue": peer_stats.get("avg_revenue"),
        "avg_employees": peer_stats.get("avg_employees"),
        "avg_debt_ratio": peer_stats.get("avg_debt_ratio"),
        "percentile": percentile,
        "market_trend": market_trend,
        "peer_comparison": peer_comparison,
    }

    logger.info(
        "[stats_node] 동종업계(%s) %d 개 사업장 비교 완료",
        ksic_code or "전업종", peer_stats["peer_count"],
    )

    return {
        "stats_insight": stats_insight,
        "node_logs": [
            build_node_log(
                node_name="stats",
                sequence=2,
                status="SUCCESS",
                latency_ms=int((time.monotonic() - started_mono) * 1000),
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                metadata={
                    "peer_count": peer_stats["peer_count"],
                    "ksic_code": ksic_code,
                },
            )
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 내부 함수
# ═══════════════════════════════════════════════════════════════════════════════

async def _aggregate_peer_stats(
    session: AsyncSession,
    ksic_code: str | None,
    year: int | None,
) -> dict[str, Any]:
    """동종업계(또는 전체) 재무 집계값을 반환한다."""

    # 대상 연도 결정 (없으면 최근 2개년 데이터 허용)
    year_conditions = []
    if year:
        year_conditions = [BusinessFinancialSnapshot.snapshot_year.in_([year, year - 1])]

    join_conditions = [BusinessFinancialSnapshot.business_id == Business.id]
    if ksic_code:
        join_conditions.append(Business.ksic_code == ksic_code)

    stmt = (
        select(
            func.count(BusinessFinancialSnapshot.id).label("peer_count"),
            func.avg(cast(BusinessFinancialSnapshot.annual_revenue, Float)).label("avg_revenue"),
            func.avg(cast(BusinessFinancialSnapshot.employee_count, Float)).label("avg_employees"),
            func.avg(cast(BusinessFinancialSnapshot.debt_ratio, Float)).label("avg_debt_ratio"),
            func.max(BusinessFinancialSnapshot.annual_revenue).label("max_revenue"),
            func.min(
                func.nullif(BusinessFinancialSnapshot.annual_revenue, 0)
            ).label("min_revenue"),
        )
        .join(Business, *join_conditions)
        .where(
            BusinessFinancialSnapshot.is_active.is_(True),
            Business.is_active.is_(True),
            *year_conditions,
        )
    )

    result = await session.execute(stmt)
    row = result.one()

    return {
        "peer_count": row.peer_count or 0,
        "avg_revenue": int(row.avg_revenue) if row.avg_revenue else None,
        "avg_employees": round(float(row.avg_employees), 1) if row.avg_employees else None,
        "avg_debt_ratio": round(float(row.avg_debt_ratio), 1) if row.avg_debt_ratio else None,
        "max_revenue": row.max_revenue,
        "min_revenue": row.min_revenue,
    }


def _calculate_percentile(
    financial_data: dict,
    peer_stats: dict,
) -> dict[str, float | None]:
    """사업장의 매출/직원수가 동종업계 대비 상위 몇 %인지 간이 계산한다.

    정확한 percentile 은 전체 데이터가 필요하지만, 평균값으로 간이 추정한다.
    평균보다 높으면 상위 50%, 2배 이상이면 상위 25% 로 간략 분류한다.
    """
    revenue = financial_data.get("annual_revenue")
    avg_rev = peer_stats.get("avg_revenue")
    employees = financial_data.get("employee_count")
    avg_emp = peer_stats.get("avg_employees")

    rev_pct: float | None = None
    if revenue is not None and avg_rev and avg_rev > 0:
        ratio = revenue / avg_rev
        if ratio >= 3:
            rev_pct = 10.0
        elif ratio >= 2:
            rev_pct = 25.0
        elif ratio >= 1:
            rev_pct = 50.0
        else:
            rev_pct = 75.0

    emp_pct: float | None = None
    if employees is not None and avg_emp and avg_emp > 0:
        ratio = employees / avg_emp
        if ratio >= 3:
            emp_pct = 10.0
        elif ratio >= 2:
            emp_pct = 25.0
        elif ratio >= 1:
            emp_pct = 50.0
        else:
            emp_pct = 75.0

    return {"revenue_percentile": rev_pct, "employee_percentile": emp_pct}


def _build_market_trend_text(peer_stats: dict, ksic_code: str | None) -> str:
    """시장 동향 텍스트를 생성한다."""
    sector = f"업종({ksic_code})" if ksic_code else "전체 업종"
    avg_rev = peer_stats.get("avg_revenue")
    avg_emp = peer_stats.get("avg_employees")
    count = peer_stats.get("peer_count", 0)

    if not avg_rev:
        return f"{sector} 데이터가 충분하지 않아 시장 동향 비교가 어렵습니다."

    return (
        f"{sector} 동종 사업장 {count}개 기준: "
        f"평균 연매출 {_fmt(avg_rev)}, "
        f"평균 직원 수 {avg_emp:.1f}명" if avg_emp else f"평균 연매출 {_fmt(avg_rev)}"
    )


def _build_comparison_text(
    financial_data: dict,
    peer_stats: dict,
    percentile: dict,
) -> str:
    """동종업계 대비 현재 사업장 위치를 설명하는 텍스트를 생성한다."""
    rev = financial_data.get("annual_revenue")
    avg_rev = peer_stats.get("avg_revenue")
    rev_pct = percentile.get("revenue_percentile")

    if not rev or not avg_rev:
        return "재무 데이터를 등록하면 동종업계와 비교할 수 있습니다."

    parts = []
    if rev_pct is not None:
        parts.append(f"현재 매출은 동종업계 상위 {rev_pct:.0f}% 수준입니다.")
    if rev > avg_rev:
        parts.append(f"평균({_fmt(avg_rev)}) 대비 {_fmt(rev - avg_rev)} 높습니다.")
    else:
        parts.append(f"평균({_fmt(avg_rev)}) 대비 {_fmt(avg_rev - rev)} 낮습니다.")

    emp_pct = percentile.get("employee_percentile")
    if emp_pct is not None:
        parts.append(f"직원 수는 동종업계 상위 {emp_pct:.0f}% 수준입니다.")

    return " ".join(parts)


def _fmt(amount: int | None) -> str:
    if amount is None:
        return "미상"
    if amount >= 1_0000_0000:
        return f"{amount / 1_0000_0000:.1f}억원"
    if amount >= 1_0000:
        return f"{amount // 1_0000}만원"
    return f"{amount:,}원"
