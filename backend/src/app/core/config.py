# src/app/core/config.py
"""애플리케이션 설정. 민감 값은 환경 변수로만 주입한다."""

import os

from dotenv import load_dotenv

load_dotenv()

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
