# src/app/domains/policy/interfaces.py
"""정책 도메인 AI 및 검색 엔진 확장을 위한 인터페이스 정의.

설계 의도:
  1. Engine Agnostic: 서비스 로직은 구체적인 기술(Elasticsearch, FAISS, AI Model)에 의존하지 않습니다.
  2. Testability: Mock 구현체를 통해 실제 인프라 없이도 유닛 테스트가 가능합니다.
  3. Scalability: 향후 RAG 기반 검색이나 ML 기반 추천 엔진으로의 확장을 보장합니다.
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
    """정책 검색 엔진의 표준 인터페이스.
    
    RDB 검색 외에 벡터 검색(Vector Search) 등으로 확장될 수 있습니다.
    """

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
        """필터 조건에 맞는 정책 목록과 페이징 정보를 반환합니다.
        
        Returns:
            (검색된 정책 리스트, 전체 결과 수, 전체 페이지 수)
        """
        pass


class IMatchEngine(ABC):
    """사업장 맞춤형 정책 매칭 엔진의 표준 인터페이스.
    
    단순 점수 계산부터 LLM 기반의 복합 분석까지 다양한 구현이 가능합니다.
    """

    @abstractmethod
    async def compute_match(
        self,
        *,
        policy: Policy,
        business: Business,
    ) -> MatchResult:
        """단일 정책과 사업장 정보를 비교하여 매칭 스코어와 사유를 도출합니다."""
        pass


# ── 구현체 (Implementation) ────────────────────────────────────────────────


class RDBPolicySearcher(IPolicySearcher):
    """기존 PostgreSQL(RDB) 인덱스를 활용한 검색 구현체.
    
    1. 작동 방식: SQL의 LIKE 또는 ILIKE 연산자를 기반으로 필터링을 수행합니다.
    2. 장점: 정형 데이터(지역, 카테고리) 필터링에 매우 빠르고 정확합니다.
    """

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
        # Repository에 구현된 검색 로직을 대리(Delegate) 호출합니다.
        return await self._repo.search_policies(
            keyword=keyword,
            region=region,
            category=category,
            page=page,
            size=size,
        )


class MockMatchEngine(IMatchEngine):
    """테스트 및 초기 개발용 Mock 매칭 엔진.
    
    [도메인 규칙 5.3] 실제 AI 엔진 결합 전까지 사업장 프로필 점수를 기반으로 
    가상의 신호등 결과를 반환하여 전체 서비스 흐름을 검증합니다.
    """

    async def compute_match(
        self,
        *,
        policy: Policy,
        business: Business,
    ) -> MatchResult:
        """사업장의 프로필 점수에 따라 등급을 나눕니다.
        
        1. 70점 이상: GREEN (적극 추천)
        2. 40점 이상: YELLOW (추가 정보 필요)
        3. 그 외: RED (자격 미달 또는 정보 부족)
        """
        # 프로필 점수가 없을 경우 0점으로 처리하여 안전하게 계산합니다.
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
            reason = "사업장 정보가 부족하여 자격 판단이 어렵습니다. 온보딩을 완료해 주세요."

        return MatchResult(
            policy_id=policy.id,
            match_level=level,
            match_score=round(score, 1),
            reason=reason,
        )