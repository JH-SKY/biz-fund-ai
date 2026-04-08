# src/app/api/deps/business_deps.py
"""사업장 도메인 FastAPI 의존성(Depends) 모음.

핵심 설계:
  - ActiveBusiness: [도메인 규칙 1.1] 온보딩 완료 가드.
    반드시 사업장이 등록되어야 하는 기능(대시보드 등)에 사용.
  - OptionalBusiness: 사업장이 없어도 에러를 내지 않는 유연한 가드.
    알림(Notification)처럼 '있으면 좋고 없어도 그만'인 기능에 사용.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.app.api.deps.user_auth import CurrentUser, get_current_user
from src.app.database.postgres.database import get_db
from src.app.domains.business.exception import onboarding_required
from src.app.domains.business.interfaces import (
    IBizVerificationService,
    IFileStorageService,
    IStatsValidationService,
    MockFileStorageService,
    MockStatsValidationService,
    RealBizVerificationService,
)
from src.app.domains.business.model import Business
from src.app.domains.business.repository import BusinessRepository
from src.app.domains.business.service import BusinessService

# ── 외부 서비스 DI Factory (인프라 교체 지점) ──────────────────────────────────


def get_biz_verification_service() -> IBizVerificationService:
    """국세청 사업자번호 진위 확인 서비스 (Mock/Real 교체 지점)"""
    return RealBizVerificationService()


def get_stats_validation_service() -> IStatsValidationService:
    """업종 평균 대비 이상치 검증 서비스 (AI 모델 연동 지점)"""
    return MockStatsValidationService()


def get_file_storage_service() -> IFileStorageService:
    """파일 저장소 서비스 (S3/Local 교체 지점)"""
    return MockFileStorageService()


# ── Repository & Service DI (로직 주입) ────────────────────────────────────────────────


async def get_business_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BusinessRepository:
    """1. DB 세션을 받아 리포지토리를 생성합니다."""
    return BusinessRepository(db)


async def get_business_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    repo: Annotated[BusinessRepository, Depends(get_business_repo)],
    biz_verification: Annotated[
        IBizVerificationService, Depends(get_biz_verification_service)
    ],
    stats_validation: Annotated[
        IStatsValidationService, Depends(get_stats_validation_service)
    ],
    file_storage: Annotated[IFileStorageService, Depends(get_file_storage_service)],
) -> BusinessService:
    """2. 모든 외부 인터페이스를 조립하여 비즈니스 서비스 객체를 생성합니다."""
    return BusinessService(
        session=db,
        repo=repo,
        biz_verification=biz_verification,
        stats_validation=stats_validation,
        file_storage=file_storage,
    )


# ── 비즈니스 가드 로직 (Business Guard Logic) ───────────────────────────────────────────


async def get_optional_business(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated["CurrentUser", Depends(get_current_user)],
) -> Business | None:
    """
    [주석 1. 비엄격 모드]
    사업장이 등록되지 않았더라도 에러(403)를 던지지 않고 None을 반환합니다.
    알림 서비스처럼 사업장 유무에 따라 기능을 '선택적'으로 보여줄 때 사용합니다.
    """
    repo = BusinessRepository(db)
    return await repo.get_active_business_by_user_id(user.id)


async def get_active_business(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated["CurrentUser", Depends(get_current_user)],
) -> Business | None:
    """
    [주석 2. 엄격 모드]
    [도메인 규칙 1.1] 사업장이 없으면 즉시 onboarding_required(403) 예외를 발생시킵니다.
    프론트엔드는 이 에러를 받으면 사용자를 온보딩 페이지로 보냅니다.
    """
    biz = await get_optional_business(user=user, db=db)
    if biz is None:
        raise onboarding_required()
    return biz


# ── 실무형 타입 별칭 (Type Aliases) ─────────────────────────────────────────────────────────

# 1. '사업장이 반드시 있어야 함'을 보장하는 타입
ActiveBusiness = Annotated[Business, Depends(get_active_business)]

# 2. '사업장이 있으면 가져오고 없으면 말기'를 지원하는 타입 (에러 해결 포인트)
OptionalBusiness = Annotated[Business | None, Depends(get_optional_business)]

# 3. 서비스 레이어 주입용 타입
BusinessServiceDep = Annotated[BusinessService, Depends(get_business_service)]
