# src/app/api/deps/user_auth.py
"""사용자 Bearer Access Token 검증 및 DI."""

from __future__ import annotations

import uuid
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.security import decode_user_access_token
from src.app.database.postgres.database import get_db
from src.app.domains.auth.exception import auth_unauthorized
from src.app.domains.auth.repository import AuthRepository
from src.app.domains.auth.service import AuthService
from src.app.domains.auth.model import User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_auth_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthRepository:
    return AuthRepository(db)


async def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    repo: Annotated[AuthRepository, Depends(get_auth_repo)],
) -> AuthService:
    return AuthService(db, repo)


async def get_current_user(
    cred: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Authorization: Bearer {ACCESS_TOKEN} 검증 후 활성 사용자 반환."""
    if cred is None or not cred.credentials:
        raise auth_unauthorized()
    try:
        payload = decode_user_access_token(cred.credentials)
    except jwt.PyJWTError:
        raise auth_unauthorized()

    if payload.get("type") != "access":
        raise auth_unauthorized("올바른 Access Token이 아닙니다.")

    sub = payload.get("sub")
    if not sub:
        raise auth_unauthorized()
    try:
        uid = uuid.UUID(str(sub))
    except ValueError:
        raise auth_unauthorized()

    repo = AuthRepository(db)
    user = await repo.get_user_by_id(uid)
    if user is None:
        raise auth_unauthorized("존재하지 않거나 탈퇴한 계정입니다.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
