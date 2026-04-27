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

from src.app.domains.business.model import Business
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
    ) -> None:
        self.policy_id = policy_id
        self.match_level = match_level
        self.match_score = match_score
        self.reason = reason


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


class MockMatchEngine(IMatchEngine):
    """테스트 및 초기 개발용 Mock 매칭 엔진."""

    async def compute_match(
        self,
        *,
        policy: Policy,
        business: Business,
    ) -> MatchResult:
        if is_ksic_policy_excluded(business.ksic_code):
            return MatchResult(
                policy_id=policy.id,
                match_level=MatchLevel.RED,
                match_score=0.0,
                reason="현재 KSIC(업종)는 정책자금 지원 제외(또는 별도 심사) 대상에 해당할 수 있습니다.",
            )

        raw_score = business.profile_score if business.profile_score is not None else 0
        score = float(raw_score)
        if business.employee_count is None:
            score = min(score, 45.0)
        elif business.employee_count < 5:
            score = min(100.0, score + 3.0)

        if score >= 70:
            level = MatchLevel.GREEN
            reason = "사업장 정보·규모(근로자)를 바탕으로 주요 자격을 충족하는 것으로 보입니다."
        elif score >= 40:
            level = MatchLevel.YELLOW
            reason = "일부 요건(재무·가점) 보완 시 유리한 공고로 올릴 수 있습니다. 정밀진단을 권장합니다."
        else:
            level = MatchLevel.RED
            reason = "프로필(업종·인원·지역) 정보를 보강한 뒤 다시 맞춤을 받아보세요."

        return MatchResult(
            policy_id=policy.id,
            match_level=level,
            match_score=round(score, 1),
            reason=reason,
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
