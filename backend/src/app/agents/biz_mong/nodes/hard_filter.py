# src/app/agents/biz_mong/nodes/hard_filter.py
"""Node 1: Hard Filter — LLM 없는 Rule-based 정책 필터링.

처리 흐름:
  [1] biz_info / financial_data 가 State 에 없으면 DB 에서 로드한다.
  [2] 활성·접수중(RECRUITING) 정책을 DB 에서 최대 MAX_POLICIES 개 조회한다.
  [3] 각 정책의 target_logic JSONB 를 parse_target_logic() 으로 정규화한다.
  [4] 4가지 Rule 을 적용하여 탈락 정책을 제거한다.

필터 Rule:
  R1. 세금 체납(tax_arrears_yn=True) → 즉시 탈락
  R2. 지역 불일치 (region_restricted=True 이고 사업장 지역과 불일치)
  R3. 업력 미달 (policy.min_business_age_months > 사업장 업력)
  R4. 매출 또는 인원 초과 (policy.max_revenue, policy.max_employees)

[핵심] parse_target_logic():
  Policy.target_logic 은 GPT-4o 가 생성한 JSONB 이므로 스키마 일관성을 보장할 수 없다.
  이 함수는 가능한 모든 타입 불일치와 키 누락을 방어적으로 처리한다.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.agents.biz_mong.tools.get_biz_info import get_biz_info
from src.app.domains.policy.model import Policy, PolicyStatus

logger = logging.getLogger(__name__)

MAX_POLICIES = 200       # 한 번에 불러올 최대 정책 수 (성능 방어)
MAX_ACTIVE_MONTHS = 9999 # 업력 상한 없음 표기용


# ═══════════════════════════════════════════════════════════════════════════════
# parse_target_logic — JSONB 정합성 검증 및 정규화
# ═══════════════════════════════════════════════════════════════════════════════

class NormalizedTargetLogic:
    """parse_target_logic() 의 반환 타입. None 필드는 '조건 없음'을 의미한다."""

    def __init__(self) -> None:
        self.sectors: list[str] | None = None
        self.min_revenue: int | None = None
        self.max_revenue: int | None = None
        self.max_debt_ratio: float | None = None
        self.min_employees: int | None = None
        self.max_employees: int | None = None
        self.min_business_age_months: int | None = None
        self.region_restricted: bool = False
        self.allowed_regions: list[str] = []
        self.require_patent: bool | None = None
        self.require_ventured: bool | None = None

    def __repr__(self) -> str:
        return (
            f"NormalizedTargetLogic("
            f"sectors={self.sectors}, "
            f"min_revenue={self.min_revenue}, "
            f"max_revenue={self.max_revenue}, "
            f"max_debt_ratio={self.max_debt_ratio}, "
            f"max_employees={self.max_employees}, "
            f"min_age_months={self.min_business_age_months}, "
            f"region_restricted={self.region_restricted})"
        )


def parse_target_logic(raw: Any) -> NormalizedTargetLogic | None:
    """Policy.target_logic JSONB 를 정합성 검증하고 정규화된 객체로 변환한다.

    반환이 None 인 경우: raw 가 비정형이어서 필터 적용 불가 → 정책은 '통과'로 처리.

    정규화 규칙:
      - None, 비 dict → None 반환 (통과)
      - 금액 필드: "5억", "5억원", "50,000,000", 50000000 → int
      - 비율 필드: "200%", 200.0 → float
      - 리스트 필드: "IT,제조", ["IT", "제조"], None → list[str]
      - bool 필드: 0/1/"true"/"false" → bool
      - 정합성 실패 시 해당 키만 None 으로 대체 (전체 필터 무효화 방지)
    """
    if not isinstance(raw, dict):
        return None

    tl = NormalizedTargetLogic()

    # ── sectors ──────────────────────────────────────────────────────────
    tl.sectors = _parse_str_list(raw.get("sectors"))

    # ── 금액 필드 ──────────────────────────────────────────────────────────
    tl.min_revenue = _parse_amount(raw.get("min_revenue"))
    tl.max_revenue = _parse_amount(raw.get("max_revenue"))

    # ── 비율 필드 ──────────────────────────────────────────────────────────
    tl.max_debt_ratio = _parse_ratio(raw.get("max_debt_ratio"))

    # ── 인원 필드 ──────────────────────────────────────────────────────────
    tl.min_employees = _parse_int_safe(raw.get("min_employees"))
    tl.max_employees = _parse_int_safe(raw.get("max_employees"))

    # ── 업력 필드 (개월 / 연 모두 허용) ──────────────────────────────────
    min_age_raw = raw.get("min_business_age_months") or raw.get("min_business_age_years")
    if raw.get("min_business_age_years") is not None:
        years = _parse_int_safe(raw.get("min_business_age_years"))
        tl.min_business_age_months = years * 12 if years else None
    else:
        tl.min_business_age_months = _parse_int_safe(min_age_raw)

    # ── 지역 제한 ─────────────────────────────────────────────────────────
    region_val = raw.get("region_restricted")
    tl.region_restricted = _parse_bool_safe(region_val) or False

    region_list = raw.get("allowed_regions") or raw.get("regions") or []
    tl.allowed_regions = _parse_str_list(region_list) or []

    # ── 가점 조건 ─────────────────────────────────────────────────────────
    tl.require_patent = _parse_bool_safe(raw.get("require_patent"))
    tl.require_ventured = _parse_bool_safe(raw.get("require_ventured"))

    return tl


# ── 파싱 헬퍼 (순수 함수) ──────────────────────────────────────────────────────

_AMOUNT_UNITS = {
    "억": 1_0000_0000,
    "천만": 1000_0000,
    "백만": 100_0000,
    "만": 1_0000,
}


def _parse_amount(val: Any) -> int | None:
    """금액 문자열/숫자를 int(원) 으로 변환한다."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str):
        cleaned = val.replace(",", "").replace(" ", "").replace("원", "")
        for unit, multiplier in _AMOUNT_UNITS.items():
            if unit in cleaned:
                num_part = cleaned.replace(unit, "").strip()
                try:
                    return int(float(num_part) * multiplier)
                except (ValueError, TypeError):
                    pass
        try:
            return int(float(cleaned))
        except (ValueError, TypeError):
            logger.debug("[parse_target_logic] 금액 파싱 실패: %s", val)
            return None
    return None


def _parse_ratio(val: Any) -> float | None:
    """부채비율 등을 float 으로 변환한다 (예: "200%", 200.0)."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        cleaned = val.replace("%", "").strip()
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return None
    return None


def _parse_int_safe(val: Any) -> int | None:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _parse_bool_safe(val: Any) -> bool | None:
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, int):
        return bool(val)
    if isinstance(val, str):
        return val.lower() in ("true", "yes", "1", "y")
    return None


def _parse_str_list(val: Any) -> list[str] | None:
    """섹터 목록 등을 list[str] 으로 변환한다."""
    if val is None:
        return None
    if isinstance(val, list):
        return [str(v) for v in val if v]
    if isinstance(val, str):
        if "," in val:
            return [s.strip() for s in val.split(",") if s.strip()]
        return [val.strip()] if val.strip() else None
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# hard_filter_node — 노드 함수
# ═══════════════════════════════════════════════════════════════════════════════

async def hard_filter_node(
    state: dict,
    session: AsyncSession,
) -> dict:
    """Rule-based 필터를 적용하여 candidate_policies 를 State 에 저장한다.

    State 입력:
        biz_info, financial_data (없으면 자동 로드)
        business_id
    State 출력:
        biz_info, financial_data (신규 로드 시 갱신)
        candidate_policies: 필터 통과 정책 list[dict]
        is_error, error_message
    """
    business_id: str = state.get("business_id", "")

    # ── Step 1: 사업장 정보 로드 ──────────────────────────────────────────
    biz_info: dict = state.get("biz_info") or {}
    financial_data: dict = state.get("financial_data") or {}

    if not biz_info:
        logger.info("[hard_filter] biz_info 없음 → DB 조회 시작 (business_id=%s)", business_id)
        biz_info, financial_data = await get_biz_info(business_id, session)

    if not biz_info:
        return {
            "is_error": True,
            "error_message": f"business_id={business_id} 에 해당하는 사업장을 찾을 수 없습니다.",
            "candidate_policies": [],
        }

    # ── Step 2: 정책 목록 조회 ──────────────────────────────────────────
    policies = await _fetch_recruiting_policies(session, biz_info, limit=MAX_POLICIES)

    if not policies:
        logger.info("[hard_filter] 활성 정책 없음")
        return {
            "biz_info": biz_info,
            "financial_data": financial_data,
            "candidate_policies": [],
        }

    # ── Step 3 & 4: parse_target_logic + 필터 적용 ──────────────────────
    candidates: list[dict] = []
    disqualified = 0

    # R1 체납 사전 차단
    if financial_data.get("tax_arrears_yn") is True:
        logger.info("[hard_filter] 세금 체납 확인 → 전 정책 탈락")
        return {
            "biz_info": biz_info,
            "financial_data": financial_data,
            "candidate_policies": [],
            "diagnosis_report": {
                "score": 0,
                "reason": "세금 체납 이력이 있어 대부분의 정책 자금 신청이 불가합니다.",
                "advice": "체납 세금을 먼저 해결하신 후 재진단 받으시기 바랍니다.",
            },
        }

    for policy in policies:
        raw_logic = policy.target_logic
        tl = parse_target_logic(raw_logic)

        reject_reason = _apply_filter_rules(tl, biz_info, financial_data)
        if reject_reason:
            disqualified += 1
            logger.debug("[hard_filter] 탈락: %s — %s", policy.title[:40], reject_reason)
            continue

        candidates.append(_policy_to_dict(policy))

    logger.info(
        "[hard_filter] 총 %d 개 정책 중 %d 개 통과 (%d 개 탈락)",
        len(policies), len(candidates), disqualified,
    )

    return {
        "biz_info": biz_info,
        "financial_data": financial_data,
        "candidate_policies": candidates,
    }


# ── 필터 룰 적용 ──────────────────────────────────────────────────────────────

def _apply_filter_rules(
    tl: NormalizedTargetLogic | None,
    biz_info: dict,
    financial_data: dict,
) -> str | None:
    """필터 룰 적용. 탈락 사유 문자열 반환. 통과 시 None 반환.

    tl 이 None 인 경우 (비정형 target_logic): 조건 판단 불가 → 통과.
    """
    if tl is None:
        return None

    # R2. 지역 제한
    if tl.region_restricted and tl.allowed_regions:
        biz_region = (biz_info.get("region_sido") or "").strip()
        matched = any(
            r in biz_region or biz_region in r
            for r in tl.allowed_regions
        )
        if not matched:
            return f"지역 불일치 (사업장: {biz_region}, 허용: {tl.allowed_regions})"

    # R3. 업력 미달
    if tl.min_business_age_months is not None:
        age_months = _calc_biz_age_months(biz_info.get("establishment_date"))
        if age_months is not None and age_months < tl.min_business_age_months:
            return (
                f"업력 미달 (현재: {age_months}개월, 최소: {tl.min_business_age_months}개월)"
            )

    # R4-a. 매출 초과
    if tl.max_revenue is not None:
        revenue = financial_data.get("annual_revenue")
        if revenue is not None and revenue > tl.max_revenue:
            return f"매출 초과 (현재: {revenue:,}원, 한도: {tl.max_revenue:,}원)"

    # R4-b. 인원 초과
    if tl.max_employees is not None:
        emp = financial_data.get("employee_count")
        if emp is not None and emp > tl.max_employees:
            return f"인원 초과 (현재: {emp}명, 한도: {tl.max_employees}명)"

    return None


def _calc_biz_age_months(establishment_date_str: Any) -> int | None:
    """설립일 문자열을 오늘 기준 업력(개월 수)으로 변환한다."""
    if not establishment_date_str:
        return None
    try:
        if isinstance(establishment_date_str, date):
            est = establishment_date_str
        else:
            est = date.fromisoformat(str(establishment_date_str))
        today = date.today()
        return (today.year - est.year) * 12 + (today.month - est.month)
    except (ValueError, TypeError):
        return None


# ── DB 조회 헬퍼 ──────────────────────────────────────────────────────────────

async def _fetch_recruiting_policies(
    session: AsyncSession,
    biz_info: dict,
    *,
    limit: int,
) -> list[Policy]:
    """활성·접수중 정책을 조회한다. 가능하면 지역 필터를 선적용한다."""
    region_sido = biz_info.get("region_sido") or ""
    from sqlalchemy import or_

    base_conditions = [
        Policy.is_active.is_(True),
        Policy.status == PolicyStatus.RECRUITING,
    ]

    # 지역 pre-filter: 전국 OR 사업장 시도 포함
    if region_sido:
        base_conditions.append(
            or_(
                Policy.region.ilike("%전국%"),
                Policy.region.ilike(f"%{region_sido}%"),
                Policy.region.is_(None),
            )
        )

    stmt = (
        select(Policy)
        .where(*base_conditions)
        .order_by(Policy.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


def _policy_to_dict(policy: Policy) -> dict:
    """Policy ORM 객체를 에이전트가 사용 가능한 dict 로 직렬화한다."""
    return {
        "policy_id": str(policy.id),
        "title": policy.title,
        "agency_name": policy.agency_name,
        "category": policy.category,
        "support_type": policy.support_type,
        "region": policy.region,
        "max_support": policy.max_support,
        "min_support": policy.min_support,
        "support_amount_desc": policy.support_amount_desc,
        "ai_summary": policy.ai_summary or "",
        "target_logic": policy.target_logic,
        "bonus_logic": policy.bonus_logic,
        "end_date": policy.closed_at.isoformat() if policy.closed_at else "",
        "apply_url": policy.apply_url or "",
    }
