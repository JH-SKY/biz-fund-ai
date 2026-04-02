# src/app/api/deps/admin_auth.py
"""관리자 Bearer JWT 검증."""

from __future__ import annotations

import uuid
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.database.postgres.database import get_db
from src.app.domains.admin.exception import admin_forbidden, admin_unauthorized
from src.app.domains.admin.repository import AdminRepository
from src.app.domains.admin.service import AdminService
from src.app.core.security import decode_admin_token
from src.app.domains.auth.model import Admin

bearer_scheme = HTTPBearer(auto_error=False)


async def get_admin_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminRepository:
    return AdminRepository(db)


async def get_admin_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    repo: Annotated[AdminRepository, Depends(get_admin_repo)],
) -> AdminService:
    return AdminService(db, repo)


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
