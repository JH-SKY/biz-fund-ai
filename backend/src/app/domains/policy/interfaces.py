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
        raw_score = business.profile_score if business.profile_score is not None else 0
        score = float(raw_score)

        if score >= 70:
            level = MatchLevel.GREEN
            reason = "사업장 정보 완성도가 높아 필수 요건을 충족합니다."
        elif score >= 40:
            level = MatchLevel.YELLOW
            reason = "일부 가점 요건 미충족 — 추가 정보 입력 시 GREEN 상향 가능합니다."
        else:
            level = MatchLevel.RED
            reason = (
                "사업장 정보가 부족하여 자격 판단이 어렵습니다. 온보딩을 완료해 주세요."
            )

        return MatchResult(
            policy_id=policy.id,
            match_level=level,
            match_score=round(score, 1),
            reason=reason,
        )
