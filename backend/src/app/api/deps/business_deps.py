# src/app/api/deps/business_deps.py
"""사업장 도메인 FastAPI 의존성(Depends) 모음.

핵심 설계:
  - ActiveBusiness: [도메인 규칙 1.1] 온보딩 완료 가드.
    대시보드(PAGE 04)처럼 '사업장이 반드시 있어야 하는' 엔드포인트에 주입한다.
    미완료 시 → 403 (프론트엔드가 /onboarding 으로 리다이렉트)

  - 외부 서비스 DI factory: 국세청 API, S3, 통계 검증 등의 교체 지점.
    실제 서비스 연동 시 아래 factory 함수의 return 값만 교체하면 된다.
    (Service 레이어, Router 레이어는 전혀 수정하지 않아도 된다.)
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.api.deps.user_auth import CurrentUser
from src.app.database.postgres.database import get_db
from src.app.domains.business.exception import onboarding_required
from src.app.domains.business.interfaces import (
    IBizVerificationService,
    IFileStorageService,
    IStatsValidationService,
    MockBizVerificationService,
    MockFileStorageService,
    MockStatsValidationService,
)
from src.app.domains.business.model import Business
from src.app.domains.business.repository import BusinessRepository
from src.app.domains.business.service import BusinessService


# ── 외부 서비스 DI Factory (교체 포인트) ──────────────────────────────────


def get_biz_verification_service() -> IBizVerificationService:
    """국세청 사업자번호 진위 확인 서비스.

    TODO: 실제 API 연동 시 → return RealBizVerificationService()
    """
    return MockBizVerificationService()


def get_stats_validation_service() -> IStatsValidationService:
    """업종 평균 대비 이상치 검증 서비스.

    TODO: AI/통계 모델 연동 시 → return AIStatsValidationService()
    """
    return MockStatsValidationService()


def get_file_storage_service() -> IFileStorageService:
    """파일 저장소 서비스 (S3 업로드 + OCR 큐 디스패치).

    TODO: AWS S3 연동 시 → return S3FileStorageService()
    """
    return MockFileStorageService()


# ── Repository & Service DI ────────────────────────────────────────────────


async def get_business_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BusinessRepository:
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
    return BusinessService(
        session=db,
        repo=repo,
        biz_verification=biz_verification,
        stats_validation=stats_validation,
        file_storage=file_storage,
    )


# ── 온보딩 가드 (핵심 미들웨어) ───────────────────────────────────────────


async def get_active_business(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Business:
    """[도메인 규칙 1.1] 대시보드 접근 가드 — 온보딩(사업장 등록) 완료 여부 검증.

    사업장이 없으면 403 Forbidden → 프론트엔드가 /onboarding 으로 리다이렉트.
    사업장이 있으면 Business 객체를 그대로 반환하여 라우터에서 재사용 (이중 쿼리 방지).
    """
    repo = BusinessRepository(db)
    biz = await repo.get_active_business_by_user_id(user.id)
    if biz is None:
        raise onboarding_required()
    return biz


# ── 편의 타입 별칭 ─────────────────────────────────────────────────────────

ActiveBusiness = Annotated[Business, Depends(get_active_business)]
BusinessServiceDep = Annotated[BusinessService, Depends(get_business_service)]
