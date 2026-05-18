# src/app/core/security.py
"""인증 핵심 유틸: bcrypt, 관리자 JWT, 사용자 JWT, opaque Refresh Token."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from src.app.core.config import (
    ADMIN_JWT_EXPIRE_HOURS,
    ADMIN_JWT_SECRET,
    USER_ACCESS_TOKEN_EXPIRE_MINUTES,
    USER_JWT_SECRET,
    USER_REFRESH_TOKEN_EXPIRE_DAYS,
)

ALGORITHM = "HS256"  # JWT 암호화 방식


# ── bcrypt ─────────────────────────────────────────────

def verify_password(plain_password: str, password_hash: str) -> bool:
    """저장된 해시와 평문 비밀번호 일치 여부."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        password_hash.encode("utf-8"),
    )


def hash_password(plain_password: str) -> str:
    """신규 관리자 생성·시드용 단방향 해시."""
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


# ── 관리자 JWT ─────────────────────────────────────────

def create_admin_access_token(*, admin_id: uuid.UUID) -> str:
    """ADMIN_TOKEN 페이로드: sub + is_admin."""
    # 일반 사용자 토큰과 관리자 토큰을 분리해 두면
    # 권한 검증에서 관리자 전용 클레임을 명확하게 구분할 수 있다.
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(admin_id),
        "is_admin": True,
        "iat": now,
        "exp": now + timedelta(hours=ADMIN_JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, ADMIN_JWT_SECRET, algorithm=ALGORITHM)


def decode_admin_token(token: str) -> dict:
    """JWT 디코드. 만료·서명 오류는 jwt.PyJWTError 로 상위에서 처리."""
    return jwt.decode(token, ADMIN_JWT_SECRET, algorithms=[ALGORITHM])


# ── 사용자 JWT (Access Token) ──────────────────────────

def create_user_access_token(*, user_id: uuid.UUID) -> str:
    """사용자 Access Token (30분). 페이로드: sub=user_id."""
    # access token 은 짧게, refresh token 은 길게 두어
    # 탈취 피해 범위와 재로그인 불편 사이를 절충한다.
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=USER_ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, USER_JWT_SECRET, algorithm=ALGORITHM)


def decode_user_access_token(token: str) -> dict:
    """사용자 Access Token 디코드. PyJWTError 는 호출부에서 처리."""
    return jwt.decode(token, USER_JWT_SECRET, algorithms=[ALGORITHM])


# ── Refresh Token (opaque) ─────────────────────────────

def generate_refresh_token() -> str:
    """64바이트 랜덤 opaque 토큰 생성 (URL-safe base64)."""
    # refresh token 은 JWT 처럼 자체 해석 가능한 토큰이 아니라
    # 서버 DB 와 대조해야 하는 불투명 문자열로 만들어 유출 시 노출 정보를 줄인다.
    return secrets.token_urlsafe(64)


def refresh_token_expires_at() -> datetime:
    """Refresh Token 만료 datetime (UTC)."""
    return datetime.now(timezone.utc) + timedelta(days=USER_REFRESH_TOKEN_EXPIRE_DAYS)
