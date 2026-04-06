"""정밀진단 도메인 FastAPI 의존성(Depends)."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.app.api.deps.business_deps import get_business_service
from src.app.api.deps.policy_deps import get_policy_service
from src.app.database.postgres.database import get_db
from src.app.domains.business.service import BusinessService
from src.app.domains.diagnosis.interfaces import MockDiagnosisEngine
from src.app.domains.diagnosis.repository import DiagnosisRepository
from src.app.domains.diagnosis.service import DiagnosisService
from src.app.domains.policy.service import PolicyService


async def get_diagnosis_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DiagnosisRepository:
    return DiagnosisRepository(db)


async def get_diagnosis_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    repo: Annotated[DiagnosisRepository, Depends(get_diagnosis_repo)],
    policy_service: Annotated[PolicyService, Depends(get_policy_service)],
    business_service: Annotated[BusinessService, Depends(get_business_service)],
) -> DiagnosisService:
    engine = MockDiagnosisEngine()
    return DiagnosisService(
        session=db,
        repo=repo,
        business_service=business_service,
        policy_service=policy_service,
        engine=engine,
    )


DiagnosisServiceDep = Annotated[DiagnosisService, Depends(get_diagnosis_service)]
