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
from typing import Optional, Tuple

from src.app.domains.business.model import Business, BusinessFinancialSnapshot
from src.app.domains.policy.ksic_rules import is_ksic_policy_excluded
from src.app.domains.policy.model import Policy
from src.app.domains.policy.repository import PolicyRepository
from src.app.domains.policy.schema import MatchLevel


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
