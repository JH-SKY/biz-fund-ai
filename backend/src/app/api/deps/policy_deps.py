# src/app/api/deps/policy_deps.py
"""정책 도메인 FastAPI 의존성(Depends) 모음.

핵심 설계:
  - OptionalBusinessId: X-Business-Id 헤더를 선택 수신.
    북마크 상태 포함 여부는 헤더 유무에 따라 자동 결정된다.
  - RequiredBusinessId: X-Business-Id 헤더를 필수 수신.
    북마크 토글, 추천 API 등 사업장 컨텍스트가 반드시 필요한 엔드포인트에 사용.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.database.postgres.database import get_db

# [추가] AI 보강 구현체 임포트
from src.app.domains.policy.infrastructure import OpenAIPolicyEnricher
from src.app.domains.policy.interfaces import MockMatchEngine, RDBPolicySearcher
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
    return PolicyService(
        session=db,
        repo=repo,
        searcher=searcher,
        match_engine=match_engine,
    )


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


# [수정] AI Enricher 의존성 주입 추가
async def get_sync_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    repo: Annotated[PolicyRepository, Depends(get_policy_repo)],
) -> BizinfoSyncService:
    """
    정책 동기화(Bizinfo) 서비스를 생성하여 반환합니다.
    admin_auth.py에서 이 함수를 통해 서비스 객체를 주입받습니다.
    """
    enricher = OpenAIPolicyEnricher()  # AI PDF 분석 객체 생성
    return BizinfoSyncService(db, repo, enricher)  # SyncService에 조립해서 반환


# ── 편의 타입 별칭 ─────────────────────────────────────────────────────────

PolicyServiceDep = Annotated[PolicyService, Depends(get_policy_service)]
OptionalBusinessId = Annotated[Optional[uuid.UUID], Depends(get_optional_business_id)]
RequiredBusinessId = Annotated[uuid.UUID, Depends(get_required_business_id)]
SyncServiceDep = Annotated[BizinfoSyncService, Depends(get_sync_service)]
