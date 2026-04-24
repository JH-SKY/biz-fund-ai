# src/app/api/deps/user_auth.py
"""사용자 Bearer Access Token 검증 및 DI."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from src.app.core.security import decode_user_access_token
from src.app.database.postgres.database import get_db
from src.app.domains.auth.exception import auth_unauthorized
from src.app.domains.auth.model import User
from src.app.domains.auth.repository import AuthRepository

if TYPE_CHECKING:
    from src.app.domains.auth.model import User
    from src.app.domains.auth.service import AuthService

bearer_scheme = HTTPBearer(auto_error=False)


async def get_auth_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthRepository:
    return AuthRepository(db)


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


async def get_optional_current_user(
    cred: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User | None:
    """공개 API에서 선택적으로 사용자 정보를 읽는다. 실패 시 None을 반환한다."""
    if cred is None or not cred.credentials:
        return None
    try:
        payload = decode_user_access_token(cred.credentials)
    except jwt.PyJWTError:
        return None

    if payload.get("type") != "access":
        return None

    sub = payload.get("sub")
    if not sub:
        return None
    try:
        uid = uuid.UUID(str(sub))
    except ValueError:
        return None

    repo = AuthRepository(db)
    return await repo.get_user_by_id(uid)


OptionalCurrentUser = Annotated[User | None, Depends(get_optional_current_user)]


async def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    repo: Annotated[AuthRepository, Depends(get_auth_repo)],
) -> "AuthService":
    # 🔥 함수 안에서 임포트 (Local Import)
    # 이렇게 해야 '순환 참조' 에러가 안 나고 서버가 켜집니다!
    from src.app.domains.auth.service import AuthService

    return AuthService(db, repo)
