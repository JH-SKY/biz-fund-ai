# src/app/core/config.py
"""애플리케이션 설정. 민감 값은 환경 변수로만 주입한다."""

import os

from dotenv import load_dotenv

load_dotenv()

# ── 애플리케이션 환경 ────────────────────────────────────
# .env에서 APP_ENV=production 으로 설정하면 테스트 전용 API가 비활성화된다.
APP_ENV: str = os.getenv("APP_ENV", "development")


def _parse_csv_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]

# ── 관리자 JWT ─────────────────────────────────────────
# 운영 시 반드시 강한 시크릿으로 교체.
ADMIN_JWT_SECRET: str = os.getenv("ADMIN_JWT_SECRET", "dev-admin-jwt-change-me")
ADMIN_JWT_EXPIRE_HOURS: int = int(os.getenv("ADMIN_JWT_EXPIRE_HOURS", "8"))

# 수동 등록 정책에 붙는 기관명 기본값
ADMIN_POLICY_AGENCY_NAME: str = os.getenv("ADMIN_POLICY_AGENCY_NAME", "관리자 등록")

# ── 사용자 JWT ─────────────────────────────────────────
# Access Token: 30분 / Refresh Token: 7일 (architecture doc 기준)
USER_JWT_SECRET: str = os.getenv("USER_JWT_SECRET", "dev-user-jwt-change-me")
USER_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
    os.getenv("USER_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
)
USER_REFRESH_TOKEN_EXPIRE_DAYS: int = int(
    os.getenv("USER_REFRESH_TOKEN_EXPIRE_DAYS", "7")
)

# ── 소셜 로그인 API ────────────────────────────────────
KAKAO_PROFILE_URL: str = "https://kapi.kakao.com/v2/user/me"
NAVER_PROFILE_URL: str = "https://openapi.naver.com/v1/nid/me"

# ── 외부 API 키 ────────────────────────────────────────
# 국세청(사업자번호) API
NTS_API_KEY: str = os.getenv("NTS_API_KEY", "")

# 기업마당(정책공고) API
BIZINFO_API_KEY: str = os.getenv("BIZINFO_API_KEY", "")

# 오픈 AI API
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

# 프론트엔드 배포/개발 주소. 여러 개면 콤마로 구분.
FRONTEND_ORIGINS: list[str] = _parse_csv_env(
    "FRONTEND_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
)
