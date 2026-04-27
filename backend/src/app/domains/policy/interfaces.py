# src/app/domains/policy/interfaces.py
"""정책 도메인 AI 및 검색 엔진 확장을 위한 인터페이스 정의.

설계 의도:
  1. Engine Agnostic: 서비스 로직은 구체적인 기술(Elasticsearch, FAISS, AI Model)에 의존하지 않습니다.
  2. Testability: Mock 구현체를 통해 실제 인프라 없이도 유닛 테스트가 가능합니다.
  3. Scalability: 향후 RAG 기반 검색이나 ML 기반 추천 엔진으로의 확장을 보장합니다.

참고:
  정책 공고 AI 구조화(파싱·GPT 분석·Self-Correction)는 PolicySyncAgent 에서 담당합니다.
  (src/app/agents/policy_sync_agent.py)
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import date
from typing import Optional, Tuple

from src.app.domains.business.model import Business, BusinessFinancialSnapshot
from src.app.domains.policy.ksic_rules import is_ksic_policy_excluded
from src.app.domains.policy.model import Policy
from src.app.domains.policy.repository import PolicyRepository
from src.app.domains.policy.schema import MatchLevel
from src.app.domains.policy.target_logic import parse_target_logic


class MatchResult:
    """매칭 엔진의 계산 결과를 담는 데이터 전송 객체(DTO).

    이 객체는 정책과 사업장 간의 연관성을 수치와 텍스트로 요약합니다.
    """

    def __init__(
        self,
        policy_id: uuid.UUID,
        match_level: MatchLevel,
        match_score: float,
        reason: str,
        estimated_probability: Optional[float] = None,
    ) -> None:
        self.policy_id = policy_id
        self.match_level = match_level
        self.match_score = match_score
        self.reason = reason
        self.estimated_probability = estimated_probability


class IPolicySearcher(ABC):
    """정책 검색 엔진의 표준 인터페이스."""

    @abstractmethod
    async def search(
        self,
        *,
        keyword: Optional[str] = None,
        region: Optional[str] = None,
        category: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> Tuple[list[Policy], int, int]:
        pass


class IMatchEngine(ABC):
    """사업장 맞춤형 정책 매칭 엔진의 표준 인터페이스."""

    @abstractmethod
    async def compute_match(
        self,
        *,
        policy: Policy,
        business: Business,
        financial_snapshot: Optional[BusinessFinancialSnapshot] = None,
    ) -> MatchResult:
        pass


# ── 구현체 (Implementation) ────────────────────────────────────────────────


class RDBPolicySearcher(IPolicySearcher):
    """기존 PostgreSQL(RDB) 인덱스를 활용한 검색 구현체."""

    def __init__(self, repo: PolicyRepository) -> None:
        self._repo = repo

    async def search(
        self,
        *,
        keyword: Optional[str] = None,
        region: Optional[str] = None,
        category: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> Tuple[list[Policy], int, int]:
        return await self._repo.search_policies(
            keyword=keyword,
            region=region,
            category=category,
            page=page,
            size=size,
        )


# L2 재무 기반 확률 추정 상수
_PROB_BASE = 40.0        # L2 시작 기저
_PROB_DEBT_PENALTY = 20.0   # 부채비율 > 200% 시 차감
_PROB_TAX_PENALTY = 30.0    # 체납 시 차감
_PROB_REVENUE_BONUS = 10.0  # 매출 > 1억 가점
_PROB_PATENT_BONUS = 5.0    # 특허·벤처 가점


class MockMatchEngine(IMatchEngine):
    """테스트 및 초기 개발용 Mock 매칭 엔진.

    L1(프로필만): score 최대 60 캡, estimated_probability=None
    L2(재무 있음): 부채·체납·매출 룰 적용, estimated_probability 산출
    """

    async def compute_match(
        self,
        *,
        policy: Policy,
        business: Business,
        financial_snapshot: Optional[BusinessFinancialSnapshot] = None,
    ) -> MatchResult:
        # ── 제외 업종 우선 처리 ──
        if is_ksic_policy_excluded(business.ksic_code):
            return MatchResult(
                policy_id=policy.id,
                match_level=MatchLevel.RED,
                match_score=0.0,
                reason="현재 KSIC(업종)는 정책자금 지원 제외(또는 별도 심사) 대상에 해당할 수 있습니다.",
                estimated_probability=None,
            )

        raw_score = float(business.profile_score or 0)

        # ── L1 전용 로직 (재무 없음) ──
        if financial_snapshot is None:
            score = min(raw_score, 60.0)
            if business.employee_count is None:
                score = min(score, 45.0)
            elif business.employee_count < 5:
                score = min(score, score + 3.0)

            if score >= 50:
                level = MatchLevel.YELLOW
                reason = "기본 프로필 기준 잠재적 적합 공고입니다. 재무정보를 입력하면 정확도가 올라갑니다."
            elif score >= 30:
                level = MatchLevel.YELLOW
                reason = "프로필 정보가 일부 부족합니다. 재무·인원 정보를 보완해 주세요."
            else:
                level = MatchLevel.RED
                reason = "프로필(업종·인원·지역) 정보를 보강한 뒤 다시 맞춤을 받아보세요."

            return MatchResult(
                policy_id=policy.id,
                match_level=level,
                match_score=round(score, 1),
                reason=reason,
                estimated_probability=None,
            )

        # ── L2 로직 (재무 있음) ──
        score = raw_score
        if business.employee_count is not None and business.employee_count < 5:
            score = min(100.0, score + 3.0)

        # 부채비율 패널티 (200% 초과 시 감점, 400% 초과 시 추가)
        debt = float(financial_snapshot.debt_ratio or 0)
        if debt > 400:
            score = max(0.0, score - 25.0)
        elif debt > 200:
            score = max(0.0, score - 12.0)

        # 체납 패널티
        tax_arrears = financial_snapshot.tax_arrears_yn or business.has_tax_arrears
        if tax_arrears:
            score = max(0.0, score - 20.0)

        # 매출 보너스 (1억 이상)
        if financial_snapshot.annual_revenue and financial_snapshot.annual_revenue >= 100_000_000:
            score = min(100.0, score + 5.0)

        # 확률 추정 (참고용)
        prob = _PROB_BASE + (score - 50) * 0.6
        if debt > 200:
            prob -= _PROB_DEBT_PENALTY
        if tax_arrears:
            prob -= _PROB_TAX_PENALTY
        if financial_snapshot.annual_revenue and financial_snapshot.annual_revenue >= 100_000_000:
            prob += _PROB_REVENUE_BONUS
        if business.has_patent or business.is_ventured:
            prob += _PROB_PATENT_BONUS
        prob = round(max(5.0, min(95.0, prob)), 1)

        # 신호등 판정
        if score >= 70:
            level = MatchLevel.GREEN
            if tax_arrears:
                reason = "프로필 적합도는 높지만 체납 이력이 불리하게 작용할 수 있습니다."
            elif debt > 200:
                reason = "적합도는 양호하나 부채비율 개선 시 추정 확률이 올라갑니다."
            else:
                reason = "사업장 정보·재무 기준을 충족하는 것으로 보입니다."
        elif score >= 40:
            level = MatchLevel.YELLOW
            if tax_arrears:
                reason = "체납 해소 후 재신청 시 승인 가능성이 높아집니다."
            elif debt > 200:
                reason = f"부채비율({debt:.0f}%)을 낮추면 추정 확률이 약 {_PROB_DEBT_PENALTY:.0f}%p 개선됩니다."
            else:
                reason = "일부 재무 요건 보완 시 유리한 공고로 상향됩니다."
        else:
            level = MatchLevel.RED
            reason = "재무 상태(부채·체납)를 개선한 뒤 다시 맞춤을 받아보세요."

        return MatchResult(
            policy_id=policy.id,
            match_level=level,
            match_score=round(score, 1),
            reason=reason,
            estimated_probability=prob,
        )


# ── 벡터 검색 인터페이스 ───────────────────────────────────────────────────────


class RuleBasedMatchEngine(IMatchEngine):
    """Policy-aware recommendation engine for L1 candidateing and L2 scoring."""

    async def compute_match(
        self,
        *,
        policy: Policy,
        business: Business,
        financial_snapshot: Optional[BusinessFinancialSnapshot] = None,
    ) -> MatchResult:
        if is_ksic_policy_excluded(business.ksic_code):
            return MatchResult(
                policy_id=policy.id,
                match_level=MatchLevel.RED,
                match_score=0.0,
                reason="현재 업종은 이 정책의 지원 제외 업종으로 보입니다.",
                estimated_probability=None,
            )

        logic = parse_target_logic(policy.target_logic)
        employee_count = (
            financial_snapshot.employee_count
            if financial_snapshot and financial_snapshot.employee_count is not None
            else business.employee_count
        )
        annual_revenue = financial_snapshot.annual_revenue if financial_snapshot else None
        debt_ratio = (
            float(financial_snapshot.debt_ratio)
            if financial_snapshot and financial_snapshot.debt_ratio is not None
            else None
        )
        tax_arrears = (
            bool(financial_snapshot.tax_arrears_yn)
            if financial_snapshot is not None
            else bool(business.has_tax_arrears)
        )
        business_age_months = _business_age_months(business.establishment_date)

        hard_fail_reason = _evaluate_hard_failures(
            policy=policy,
            business=business,
            logic=logic,
            employee_count=employee_count,
            annual_revenue=annual_revenue,
            debt_ratio=debt_ratio,
            business_age_months=business_age_months,
        )
        if hard_fail_reason:
            return MatchResult(
                policy_id=policy.id,
                match_level=MatchLevel.RED,
                match_score=0.0,
                reason=hard_fail_reason,
                estimated_probability=None,
            )

        if financial_snapshot is None:
            score, reasons = _score_l1(
                policy=policy,
                business=business,
                logic=logic,
                employee_count=employee_count,
                business_age_months=business_age_months,
            )
            return MatchResult(
                policy_id=policy.id,
                match_level=MatchLevel.GREEN if score >= 68 else MatchLevel.YELLOW,
                match_score=score,
                reason=_build_reason(reasons, fallback="1차 정보 기준으로는 지원 가능성이 있는 후보 정책입니다."),
                estimated_probability=None,
            )

        score, reasons = _score_l2(
            policy=policy,
            business=business,
            logic=logic,
            employee_count=employee_count,
            annual_revenue=annual_revenue,
            debt_ratio=debt_ratio,
            business_age_months=business_age_months,
            tax_arrears=tax_arrears,
        )
        probability = round(max(12.0, min(92.0, score - 5.0)), 1)
        level = MatchLevel.GREEN if score >= 78 else MatchLevel.YELLOW if score >= 58 else MatchLevel.RED
        return MatchResult(
            policy_id=policy.id,
            match_level=level,
            match_score=score,
            reason=_build_reason(reasons, fallback="재무와 사업 정보 기준으로 일부 조건이 맞는 정책입니다."),
            estimated_probability=probability,
        )


def _business_age_months(establishment_date: date | None) -> int | None:
    if establishment_date is None:
        return None
    today = date.today()
    months = (today.year - establishment_date.year) * 12 + (today.month - establishment_date.month)
    if today.day < establishment_date.day:
        months -= 1
    return max(0, months)


def _evaluate_hard_failures(
    *,
    policy: Policy,
    business: Business,
    logic,
    employee_count: int | None,
    annual_revenue: int | None,
    debt_ratio: float | None,
    business_age_months: int | None,
) -> str | None:
    if logic is not None:
        if logic.sectors and not _sector_matches(business, logic.sectors):
            return "정책 대상 업종과 현재 업종 정보가 맞지 않습니다."
        if logic.region_restricted and logic.allowed_regions and not _region_matches(business, logic.allowed_regions):
            return "정책 지원 지역과 사업장 소재지가 맞지 않습니다."
        if (
            logic.min_business_age_months is not None
            and business_age_months is not None
            and business_age_months < logic.min_business_age_months
        ):
            return "정책이 요구하는 업력 조건에 아직 도달하지 않았습니다."
        if logic.min_employees is not None and employee_count is not None and employee_count < logic.min_employees:
            return "정책이 요구하는 최소 고용 인원 조건을 충족하지 못합니다."
        if logic.max_employees is not None and employee_count is not None and employee_count > logic.max_employees:
            return "정책이 허용하는 고용 인원 범위를 초과했습니다."
        if logic.require_patent and not business.has_patent:
            return "특허 보유 기업을 우대하거나 필수로 보는 정책입니다."
        if logic.require_ventured and not business.is_ventured:
            return "벤처기업 확인 조건이 필요한 정책입니다."
        if logic.min_revenue is not None and annual_revenue is not None and annual_revenue < logic.min_revenue:
            return "정책이 요구하는 최소 매출 기준에 미달합니다."
        if logic.max_revenue is not None and annual_revenue is not None and annual_revenue > logic.max_revenue:
            return "정책이 허용하는 매출 구간을 초과했습니다."
        if logic.max_debt_ratio is not None and debt_ratio is not None and debt_ratio > logic.max_debt_ratio:
            return "정책이 허용하는 부채비율 기준을 초과했습니다."

    return None


def _score_l1(
    *,
    policy: Policy,
    business: Business,
    logic,
    employee_count: int | None,
    business_age_months: int | None,
) -> tuple[float, list[str]]:
    score = 32.0
    reasons: list[str] = []

    if logic is not None:
        score += 8.0
    else:
        score -= 4.0

    if logic is not None and logic.sectors and _sector_matches(business, logic.sectors):
        score += 20.0
        reasons.append("정책 대상 업종 조건과 현재 업종이 잘 맞습니다.")

    if _policy_region_positive_match(policy, business, logic):
        score += 15.0
        reasons.append("사업장 지역 기준으로 지원 대상일 가능성이 높습니다.")

    if business_age_months is not None:
        score += 6.0
        if logic is not None and logic.min_business_age_months is not None:
            score += 8.0
            reasons.append("업력 조건을 이미 충족하고 있습니다.")

    if employee_count is not None:
        score += 6.0
        if logic is not None and (logic.min_employees is not None or logic.max_employees is not None):
            score += 8.0
            reasons.append("고용 인원 기준과도 크게 어긋나지 않습니다.")

    if _funding_purpose_matches(policy, business):
        score += 10.0
        reasons.append("정책 지원 목적과 현재 자금 용도가 가깝습니다.")

    if _special_flag_matches(policy, business):
        score += 6.0
        reasons.append("보유 자격이나 기업 특성 우대 요소가 반영될 수 있습니다.")

    if business.is_biz_no_verified:
        score += 3.0
    else:
        score -= 5.0

    return round(max(25.0, min(78.0, score)), 1), reasons


def _score_l2(
    *,
    policy: Policy,
    business: Business,
    logic,
    employee_count: int | None,
    annual_revenue: int | None,
    debt_ratio: float | None,
    business_age_months: int | None,
    tax_arrears: bool,
) -> tuple[float, list[str]]:
    score = 48.0
    reasons: list[str] = []

    if logic is not None and logic.sectors and _sector_matches(business, logic.sectors):
        score += 16.0
        reasons.append("업종 조건이 정책 대상과 직접 맞닿아 있습니다.")
    elif logic is not None:
        score += 5.0

    if _policy_region_positive_match(policy, business, logic):
        score += 10.0
        reasons.append("지역 조건도 충족하고 있습니다.")

    if business_age_months is not None:
        score += 5.0
        if logic is not None and logic.min_business_age_months is not None:
            score += 6.0
            reasons.append("업력 기준도 안정적으로 통과합니다.")

    if employee_count is not None:
        score += 5.0
        if logic is not None and (logic.min_employees is not None or logic.max_employees is not None):
            score += 7.0
            reasons.append("고용 인원 범위와의 정합성이 좋습니다.")

    if _funding_purpose_matches(policy, business):
        score += 8.0
        reasons.append("자금 용도와 정책 목적이 가깝습니다.")

    if annual_revenue is not None:
        if logic is not None and (logic.min_revenue is not None or logic.max_revenue is not None):
            score += 10.0
            reasons.append("매출 구간 조건도 확인 가능한 상태입니다.")
        elif annual_revenue > 0:
            score += 4.0

    if debt_ratio is not None:
        if logic is not None and logic.max_debt_ratio is not None:
            score += 8.0
            reasons.append("부채비율 기준도 허용 범위 안에 있습니다.")
        elif debt_ratio <= 150:
            score += 5.0
        elif debt_ratio >= 250:
            score -= 8.0
            reasons.append("부채비율이 높아 실제 선정 가능성은 낮아질 수 있습니다.")

    if tax_arrears:
        score -= 25.0
        reasons.append("세금 체납 이력은 심사에서 큰 불이익 요인입니다.")

    if _special_flag_matches(policy, business):
        score += 5.0
        reasons.append("보유 자격이나 인증 우대 요소가 있습니다.")

    if business.is_biz_no_verified:
        score += 2.0

    return round(max(20.0, min(95.0, score)), 1), reasons


def _build_reason(reasons: list[str], *, fallback: str) -> str:
    if not reasons:
        return fallback
    return " ".join(reasons[:2])


def _policy_region_positive_match(policy: Policy, business: Business, logic) -> bool:
    if logic is not None and logic.region_restricted and logic.allowed_regions:
        return _region_matches(business, logic.allowed_regions)
    if not business.region_sido or not policy.region:
        return False
    return business.region_sido in policy.region


def _region_matches(business: Business, allowed_regions: list[str]) -> bool:
    region_tokens = [token for token in (business.region_sido, business.region_sigungu) if token]
    if not region_tokens:
        return False
    normalized_allowed = [item.lower() for item in allowed_regions]
    return any(token.lower() in allowed for token in region_tokens for allowed in normalized_allowed)


def _sector_matches(business: Business, sectors: list[str]) -> bool:
    haystack = " ".join(filter(None, [business.ksic_code, business.ksic_name, business.sector_code])).lower()
    return any(sector.lower() in haystack for sector in sectors)


def _funding_purpose_matches(policy: Policy, business: Business) -> bool:
    if not business.funding_purpose:
        return False
    purpose_keywords = {
        "FACILITY": ("시설", "장비", "설비"),
        "OPERATING": ("운영", "경영", "고정비"),
        "WORKING": ("운전자금", "원자재", "인건비"),
        "MIXED": ("자금", "운영", "시설"),
    }
    keywords = purpose_keywords.get(business.funding_purpose, ())
    if not keywords:
        return False
    haystack = " ".join(filter(None, [policy.title, policy.category, policy.support_type, policy.content_raw])).lower()
    return any(keyword in haystack for keyword in keywords)


def _special_flag_matches(policy: Policy, business: Business) -> bool:
    haystack = " ".join(filter(None, [policy.title, policy.content_raw])).lower()
    return (
        (business.has_patent and "특허" in haystack)
        or (business.is_ventured and "벤처" in haystack)
        or (business.is_female_ent and "여성" in haystack)
    )


class IVectorSearcher(ABC):
    """
    pgvector 기반 하이브리드 검색 엔진의 표준 인터페이스.

    설계 의도:
      - SQL 필터(region, category, status) + 벡터 코사인 유사도 검색을 결합합니다.
      - 미래에 Elasticsearch나 다른 벡터 DB로 교체 시 이 인터페이스만 재구현합니다.
    """

    @abstractmethod
    async def search(
        self,
        query_vector: list[float],
        *,
        region: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> list[tuple[Policy, float]]:
        """
        Returns:
            [(Policy, cosine_distance), ...] — 유사도 오름차순 정렬.
        """


class VectorPolicySearcher(IVectorSearcher):
    """
    pgvector를 사용한 하이브리드 검색 구현체.

    처리 흐름:
      [1] SQL WHERE 절로 region, category, status를 필터링합니다.
      [2] 남은 정책의 청크(policy_chunks)에서 쿼리 벡터와의 코사인 거리를 계산합니다.
      [3] 정책별 최소 거리(MIN)로 집계하여 대표값을 선정합니다.
      [4] 거리 오름차순 정렬 후 limit만큼 반환합니다.
    """

    def __init__(self, repo: PolicyRepository) -> None:
        self._repo = repo

    async def search(
        self,
        query_vector: list[float],
        *,
        region: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> list[tuple[Policy, float]]:
        from src.app.domains.policy.model import PolicyStatus

        status_enum = PolicyStatus(status) if status else None
        return await self._repo.vector_search(
            query_vector,
            region=region,
            category=category,
            status=status_enum,
            limit=limit,
            offset=offset,
        )
