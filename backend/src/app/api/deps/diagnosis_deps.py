# src/app/api/deps/diagnosis_deps.py
"""정밀진단 도메인 FastAPI 의존성(Depends) 모음.

[역할]
- DiagnosisServiceDep: DiagnosisService 인스턴스를 요청마다 생성하여 라우터에 주입
- RuleBasedDiagnosisEngine 을 IDiagnosisEngine 으로 주입 (AI/규칙 엔진 교체 지점)

[엔진 교체 방법]
테스트 환경에서는 `get_diagnosis_service` 함수를 오버라이드하여
MockDiagnosisEngine 을 주입하면 LLM 없이 테스트할 수 있다.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.app.api.deps.business_deps import get_business_service
from src.app.api.deps.policy_deps import get_policy_service
from src.app.database.postgres.database import get_db
from src.app.domains.business.service import BusinessService
from src.app.domains.diagnosis.rule_engine import RuleBasedDiagnosisEngine
from src.app.domains.diagnosis.repository import DiagnosisRepository
from src.app.domains.diagnosis.service import DiagnosisService
from src.app.domains.policy.service import PolicyService


async def get_diagnosis_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DiagnosisRepository:
    """DB 세션으로 DiagnosisRepository 인스턴스를 생성한다."""
    return DiagnosisRepository(db)


async def get_diagnosis_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    repo: Annotated[DiagnosisRepository, Depends(get_diagnosis_repo)],
    policy_service: Annotated[PolicyService, Depends(get_policy_service)],
    business_service: Annotated[BusinessService, Depends(get_business_service)],
) -> DiagnosisService:
    """규칙 기반 진단 엔진을 주입하여 DiagnosisService 를 생성한다."""
    engine = RuleBasedDiagnosisEngine()  # 운영 환경: RuleBasedDiagnosisEngine
    return DiagnosisService(
        session=db,
        repo=repo,
        business_service=business_service,
        policy_service=policy_service,
        engine=engine,
    )


DiagnosisServiceDep = Annotated[DiagnosisService, Depends(get_diagnosis_service)]
