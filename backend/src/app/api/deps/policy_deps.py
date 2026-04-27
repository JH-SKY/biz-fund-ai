# src/app/api/deps/policy_deps.py
"""정책 도메인 FastAPI 의존성(Depends) 모음.

핵심 설계:
  - OptionalBusinessId: X-Business-Id 헤더를 선택 수신.
    북마크 상태 포함 여부는 헤더 유무에 따라 자동 결정된다.
  - RequiredBusinessId: X-Business-Id 헤더를 필수 수신.
    북마크 토글, 추천 API 등 사업장 컨텍스트가 반드시 필요한 엔드포인트에 사용.
  - SyncServiceDep: BizinfoSyncService 에 PolicySyncAgent 를 주입하여 반환한다.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.agents.policy_sync_agent import PolicySyncAgent
from src.app.database.postgres.database import get_db
from src.app.domains.business.repository import BusinessRepository
from src.app.domains.policy.embedding_service import PolicyEmbeddingService
from src.app.domains.policy.interfaces import MockMatchEngine, RDBPolicySearcher, VectorPolicySearcher
from src.app.domains.policy.repository import PolicyRepository
from src.app.domains.policy.service import PolicyService
from src.app.domains.policy.sync_service import BizinfoSyncService

# ── Repository & Service DI ────────────────────────────────────────────────


async def get_policy_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PolicyRepository:
    return PolicyRepository(db)


async def get_policy_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    repo: Annotated[PolicyRepository, Depends(get_policy_repo)],
) -> PolicyService:
    searcher = RDBPolicySearcher(repo)
    match_engine = MockMatchEngine()
    vector_searcher = VectorPolicySearcher(repo)
    biz_repo = BusinessRepository(db)
    return PolicyService(
        session=db,
        repo=repo,
        searcher=searcher,
        match_engine=match_engine,
        vector_searcher=vector_searcher,
        biz_repo=biz_repo,
    )


async def get_embedding_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    repo: Annotated[PolicyRepository, Depends(get_policy_repo)],
) -> PolicyEmbeddingService:
    """PolicyEmbeddingService — 청킹·임베딩 전용 서비스를 반환합니다."""
    return PolicyEmbeddingService(db, repo)


# ── X-Business-Id 헤더 파싱 ────────────────────────────────────────────────


async def get_optional_business_id(
    x_business_id: Annotated[Optional[str], Header(alias="X-Business-Id")] = None,
) -> Optional[uuid.UUID]:
    """X-Business-Id 헤더 선택 파싱 — 없으면 None 반환.

    사용 대상: 목록 조회, 상세 조회 (북마크 여부 선택 반환).
    """
    if x_business_id is None:
        return None
    try:
        return uuid.UUID(x_business_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="X-Business-Id 헤더 형식이 올바르지 않습니다. (UUID 형식 필요)",
        )


async def get_required_business_id(
    x_business_id: Annotated[str, Header(alias="X-Business-Id")],
) -> uuid.UUID:
    """X-Business-Id 헤더 필수 파싱 — 없거나 잘못된 형식이면 400/422.

    사용 대상: 추천 API, 북마크 토글, 북마크 목록 조회.
    """
    try:
        return uuid.UUID(x_business_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="X-Business-Id 헤더 형식이 올바르지 않습니다. (UUID 형식 필요)",
        )


async def get_sync_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    repo: Annotated[PolicyRepository, Depends(get_policy_repo)],
) -> BizinfoSyncService:
    """BizinfoSyncService 에 PolicySyncAgent 와 PolicyEmbeddingService 를 주입하여 반환한다.

    PolicySyncAgent 는 내부에서 AsyncOpenAI 클라이언트를 생성한다.
    그래프는 __init__ 시 1회 컴파일되므로 요청마다 재컴파일 비용이 없다.
    """
    agent = PolicySyncAgent()
    embedding_service = PolicyEmbeddingService(db, repo)
    return BizinfoSyncService(db, repo, agent, embedding_service)


# ── 편의 타입 별칭 ─────────────────────────────────────────────────────────
PolicyServiceDep = Annotated[PolicyService, Depends(get_policy_service)]
OptionalBusinessId = Annotated[Optional[uuid.UUID], Depends(get_optional_business_id)]
RequiredBusinessId = Annotated[uuid.UUID, Depends(get_required_business_id)]
SyncServiceDep = Annotated[BizinfoSyncService, Depends(get_sync_service)]
EmbeddingServiceDep = Annotated[PolicyEmbeddingService, Depends(get_embedding_service)]
