# src/app/core/config.py
"""Application configuration loaded from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()

APP_ENV: str = os.getenv("APP_ENV", "development")

DEFAULT_ADMIN_JWT_SECRET = "dev-admin-jwt-change-me"
DEFAULT_USER_JWT_SECRET = "dev-user-jwt-change-me"


def _parse_csv_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _parse_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


ADMIN_JWT_SECRET: str = os.getenv("ADMIN_JWT_SECRET", DEFAULT_ADMIN_JWT_SECRET)
ADMIN_JWT_EXPIRE_HOURS: int = int(os.getenv("ADMIN_JWT_EXPIRE_HOURS", "8"))
ADMIN_POLICY_AGENCY_NAME: str = os.getenv("ADMIN_POLICY_AGENCY_NAME", "관리자 등록")

USER_JWT_SECRET: str = os.getenv("USER_JWT_SECRET", DEFAULT_USER_JWT_SECRET)
USER_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
    os.getenv("USER_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
)
USER_REFRESH_TOKEN_EXPIRE_DAYS: int = int(
    os.getenv("USER_REFRESH_TOKEN_EXPIRE_DAYS", "7")
)

KAKAO_PROFILE_URL: str = "https://kapi.kakao.com/v2/user/me"
NAVER_PROFILE_URL: str = "https://openapi.naver.com/v1/nid/me"
NAVER_TOKEN_URL: str = "https://nid.naver.com/oauth2.0/token"
NAVER_AUTHORIZE_URL: str = "https://nid.naver.com/oauth2.0/authorize"
NAVER_CLIENT_ID: str = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET: str = os.getenv("NAVER_CLIENT_SECRET", "")

NTS_API_KEY: str = os.getenv("NTS_API_KEY", "")
BIZINFO_API_KEY: str = os.getenv("BIZINFO_API_KEY", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

FRONTEND_ORIGINS: list[str] = _parse_csv_env(
    "FRONTEND_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
)

RUN_SCHEDULER: bool = _parse_bool_env("RUN_SCHEDULER", APP_ENV != "production")
SCHEDULER_LOCK_ID: int = int(os.getenv("SCHEDULER_LOCK_ID", "24042103"))

if APP_ENV == "production":
    if ADMIN_JWT_SECRET == DEFAULT_ADMIN_JWT_SECRET:
        raise RuntimeError(
            "운영 환경에서는 기본 ADMIN_JWT_SECRET 값을 사용할 수 없습니다."
        )
    if USER_JWT_SECRET == DEFAULT_USER_JWT_SECRET:
        raise RuntimeError(
            "운영 환경에서는 기본 USER_JWT_SECRET 값을 사용할 수 없습니다."
        )
