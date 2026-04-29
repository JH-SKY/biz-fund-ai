# src/app/api/deps/admin_auth.py
"""관리자 Bearer JWT 검증 및 FastAPI 의존성(Depends) 모음.

[역할]
관리자 전용 라우터에서 사용되는 인증/DI 모듈.
- get_current_admin: 관리자 JWT 토큰을 검증하고 활성 Admin 객체 반환
- get_admin_service: AdminService 에 필요한 모든 서비스를 조립하여 반환

[관리자 토큰 검증 흐름]
1. Authorization: Bearer <token> 에서 토큰 추출
2. JWT 디코딩 후 is_admin=True 확인 (is_admin=False 면 403 Forbidden)
3. sub(admin UUID)로 DB 조회 → 존재하지 않으면 403

[CurrentAdmin]
라우터 파라미터에 `Annotated[Admin, Depends(get_current_admin)]` 대신
`CurrentAdmin` 타입 별칭을 사용하면 코드가 간결해진다.
"""

from __future__ import annotations

import uuid
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.api.deps.biz_pick_deps import get_biz_pick_service
from src.app.api.deps.chat_deps import get_chat_service
from src.app.api.deps.diagnosis_deps import get_diagnosis_service
from src.app.api.deps.policy_deps import get_policy_service, get_sync_service
from src.app.api.deps.system_deps import get_system_service
from src.app.api.deps.user_auth import get_auth_service
from src.app.core.security import decode_admin_token
from src.app.database.postgres.database import get_db
from src.app.domains.admin.exception import admin_forbidden, admin_unauthorized
from src.app.domains.admin.model import Admin
from src.app.domains.admin.repository import AdminRepository
from src.app.domains.admin.service import AdminService
from src.app.domains.auth.service import AuthService
from src.app.domains.biz_pick.service import BizPickService
from src.app.domains.chat.service import ChatService
from src.app.domains.diagnosis.service import DiagnosisService
from src.app.domains.policy.service import PolicyService
from src.app.domains.policy.sync_service import BizinfoSyncService
from src.app.domains.system.service import SystemService

bearer_scheme = HTTPBearer(auto_error=False)


async def get_admin_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminRepository:
    """DB 세션으로 AdminRepository 인스턴스를 생성한다."""
    return AdminRepository(db)


async def get_admin_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    repo: Annotated[AdminRepository, Depends(get_admin_repo)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
    policy_service: Annotated[PolicyService, Depends(get_policy_service)],
    biz_pick_service: Annotated[BizPickService, Depends(get_biz_pick_service)],
    system_service: Annotated[SystemService, Depends(get_system_service)],
    diagnosis_service: Annotated[DiagnosisService, Depends(get_diagnosis_service)],
    sync_service: Annotated[BizinfoSyncService, Depends(get_sync_service)],
) -> AdminService:
    """AdminService 에 필요한 모든 하위 서비스를 조립하여 반환한다.

    AdminService 는 여러 도메인 서비스에 의존하므로 DI에서 한꺼번에 조립한다.
    """
    return AdminService(
        session=db,
        repo=repo,
        auth_service=auth_service,
        chat_service=chat_service,
        policy_service=policy_service,
        biz_pick_service=biz_pick_service,
        system_service=system_service,
        diagnosis_service=diagnosis_service,
        sync_service=sync_service,
    )


async def get_current_admin(
    cred: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Admin:
    """Authorization: Bearer {ADMIN_TOKEN} — 페이로드 is_admin=True 및 admins 활성 계정."""

    if cred is None or not cred.credentials:
        raise admin_forbidden()
    try:
        payload = decode_admin_token(cred.credentials)
    except jwt.PyJWTError:
        raise admin_unauthorized()
    if not payload.get("is_admin"):
        raise admin_forbidden()
    sub = payload.get("sub")
    if not sub:
        raise admin_unauthorized()
    try:
        aid = uuid.UUID(str(sub))
    except ValueError:
        raise admin_unauthorized()
    repo = AdminRepository(db)
    admin = await repo.get_admin_by_id(aid)
    if admin is None:
        raise admin_forbidden()
    return admin


CurrentAdmin = Annotated[Admin, Depends(get_current_admin)]
