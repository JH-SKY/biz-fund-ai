# src/app/domains/auth/service.py
"""인증 도메인 비즈니스 로직 및 트랜잭션 경계."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import KAKAO_PROFILE_URL, NAVER_PROFILE_URL
from src.app.core.security import (
    create_user_access_token,
    generate_refresh_token,
    refresh_token_expires_at,
)
from src.app.domains.auth.exception import (
    auth_unauthorized,
    invalid_social_token,
    social_api_error,
)
from src.app.domains.auth.repository import AuthRepository
from src.app.domains.auth.schema import (
    MyProfileData,
    ProfilePatchRequest,
    ProfilePatchResponseData,
    SocialLoginRequest,
    SocialLoginResponseData,
)
from src.app.models.auth.user import SocialProvider, User


class AuthService:
    """인증·사용자 유스케이스. Repository만 통해 DB에 접근한다."""

    def __init__(self, session: AsyncSession, repo: AuthRepository) -> None:
        self._session = session
        self._repo = repo

    # ── 소셜 로그인 공통 내부 로직 ────────────────────────

    async def _social_login(
        self,
        *,
        social_id: str,
        provider: SocialProvider,
        email: str,
        name: str,
        profile_image_url: str | None,
    ) -> SocialLoginResponseData:
        """소셜 정보로 기존 유저 로그인 또는 신규 유저 생성 후 토큰 발급.

        도메인 규칙: social_id + social_provider 유니크 키 사용.
        """
        user = await self._repo.get_user_by_social(
            social_id=social_id, provider=provider
        )
        is_new = user is None
        if is_new:
            user = await self._repo.create_user(
                email=email,
                name=name,
                social_id=social_id,
                social_provider=provider,
                profile_image_url=profile_image_url,
            )
        elif not user.is_active:
            raise auth_unauthorized("탈퇴 처리된 계정입니다.")

        access_token = create_user_access_token(user_id=user.id)
        refresh_token = generate_refresh_token()
        expires_at = refresh_token_expires_at()
        await self._repo.create_token(
            user_id=user.id,
            token=refresh_token,
            expires_at=expires_at,
        )
        await self._session.commit()
        return SocialLoginResponseData(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=str(user.id),
            is_new_user=is_new,
        )

    # ── 카카오 로그인 ──────────────────────────────────────

    async def kakao_login(self, body: SocialLoginRequest) -> SocialLoginResponseData:
        """카카오 Access Token → 유저 프로필 조회 → 로그인/가입."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    KAKAO_PROFILE_URL,
                    headers={"Authorization": f"Bearer {body.access_token}"},
                )
        except httpx.RequestError:
            raise social_api_error("카카오")

        if resp.status_code == 401:
            raise invalid_social_token("카카오")
        if resp.status_code != 200:
            raise social_api_error("카카오")

        data = resp.json()
        social_id = str(data.get("id", ""))
        kakao_account = data.get("kakao_account", {})
        profile = kakao_account.get("profile", {})
        email: str = kakao_account.get("email", f"{social_id}@kakao.local")
        name: str = profile.get("nickname") or profile.get("name") or "카카오 사용자"
        image: str | None = profile.get("profile_image_url")

        return await self._social_login(
            social_id=social_id,
            provider=SocialProvider.KAKAO,
            email=email,
            name=name,
            profile_image_url=image,
        )

    # ── 네이버 로그인 ──────────────────────────────────────

    async def naver_login(self, body: SocialLoginRequest) -> SocialLoginResponseData:
        """네이버 Access Token → 유저 프로필 조회 → 로그인/가입."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    NAVER_PROFILE_URL,
                    headers={"Authorization": f"Bearer {body.access_token}"},
                )
        except httpx.RequestError:
            raise social_api_error("네이버")

        if resp.status_code == 401:
            raise invalid_social_token("네이버")
        if resp.status_code != 200:
            raise social_api_error("네이버")

        data = resp.json()
        if data.get("resultcode") != "00":
            raise invalid_social_token("네이버")
        profile = data.get("response", {})
        social_id: str = str(profile.get("id", ""))
        email: str = profile.get("email", f"{social_id}@naver.local")
        name: str = profile.get("name") or "네이버 사용자"
        image: str | None = profile.get("profile_image")

        return await self._social_login(
            social_id=social_id,
            provider=SocialProvider.NAVER,
            email=email,
            name=name,
            profile_image_url=image,
        )

    # ── 로그아웃 ───────────────────────────────────────────

    async def logout(self, *, refresh_token: str) -> None:
        """Refresh Token 무효화. Access Token은 만료 시간까지 유효(Stateless).

        보안 아키텍처: Refresh는 DB 저장 → 로그아웃 시 revoke 처리.
        """
        token_row = await self._repo.get_valid_token(refresh_token)
        if token_row is None:
            raise auth_unauthorized("유효하지 않은 리프레시 토큰입니다.")
        await self._repo.revoke_token(token_row)
        await self._session.commit()

    # ── 회원 탈퇴 ─────────────────────────────────────────

    async def withdraw(self, user: User) -> None:
        """도메인 규칙: 물리 삭제 금지 → Soft Delete.

        cascade: 해당 유저의 모든 토큰도 함께 무효화.
        """
        await self._repo.revoke_all_user_tokens(user.id)
        await self._repo.soft_delete_user(user)
        await self._session.commit()

    # ── 내 프로필 조회 ─────────────────────────────────────

    async def get_my_profile(self, user: User) -> MyProfileData:
        """interest_sectors 가 1개 이상이면 프로필 완성으로 간주."""
        sectors: list[str] = user.interest_sectors or []
        return MyProfileData(
            user_id=str(user.id),
            name=user.name,
            email=user.email,
            profile_image=user.profile_image_url,
            interest_sectors=sectors,
            is_profile_completed=bool(sectors),
        )

    # ── 추가 프로필 설정 ───────────────────────────────────

    async def patch_profile(
        self, user: User, body: ProfilePatchRequest
    ) -> ProfilePatchResponseData:
        await self._repo.update_user_profile(
            user,
            military_service=body.military_service,
            interest_sectors=body.interest_sectors,
            is_non_major=body.is_non_major,
            tech_stack=body.tech_stack,
        )
        await self._session.commit()
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return ProfilePatchResponseData(updated_at=now)
