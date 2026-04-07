# src/app/domains/auth/service.py
"""인증 도메인 비즈니스 로직 및 트랜잭션 경계."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

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
from src.app.domains.auth.model import SocialProvider, User
from src.app.domains.auth.repository import AuthRepository
from src.app.domains.auth.schema import (
    MyProfileData,
    ProfilePatchRequest,
    ProfilePatchResponseData,
    SocialLoginRequest,
    SocialLoginResponseData,
)
from src.app.domains.business.service import BusinessService

if TYPE_CHECKING:
    from src.app.api.deps.user_auth import CurrentUser


class AuthService:
    """인증·사용자 유스케이스. Repository만 통해 DB에 접근한다."""

    def __init__(
        self,
        session: AsyncSession,
        repo: AuthRepository,
        business_service: BusinessService,
    ) -> None:
        self._session = session
        self._repo = repo
        self._business_service = business_service

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
        """소셜 정보로 로그인 또는 가입 처리 후, 온보딩 대상 여부를 판단하여 토큰 발급.

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

        # 2. [실무 포인트] 온보딩 대상 여부 판단 로직
        # 단순히 신규 생성이었거나, 기존 유저라도 필수 정보(예: 관심분야)가 없다면 신규 유저로 간주
        # user.interest_sectors가 None이거나 빈 리스트([])인 경우 체크
        is_profile_incomplete = not user.nickname
        should_redirect_to_onboarding = is_new or is_profile_incomplete

        access_token = create_user_access_token(user_id=user.id)
        refresh_token = generate_refresh_token()
        expires_at = refresh_token_expires_at()

        await self._repo.create_token(
            user_id=user.id,
            token=refresh_token,
            expires_at=expires_at,
        )
        await self._session.commit()
        await self._session.refresh(user)

        return SocialLoginResponseData(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=str(user.id),
            is_new_user=should_redirect_to_onboarding,
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

    # # ── 네이버 로그인 실제코드 ──────────────────────────────────────

    # async def naver_login(self, body: SocialLoginRequest) -> SocialLoginResponseData:
    #     """네이버 Access Token → 유저 프로필 조회 → 로그인/가입."""
    #     try:
    #         async with httpx.AsyncClient(timeout=10.0) as client:
    #             resp = await client.get(
    #                 NAVER_PROFILE_URL,
    #                 headers={"Authorization": f"Bearer {body.access_token}"},
    #             )
    #     except httpx.RequestError:
    #         raise social_api_error("네이버")

    #     if resp.status_code == 401:
    #         raise invalid_social_token("네이버")
    #     if resp.status_code != 200:
    #         raise social_api_error("네이버")

    #     data = resp.json()
    #     if data.get("resultcode") != "00":
    #         raise invalid_social_token("네이버")
    #     profile = data.get("response", {})
    #     social_id: str = str(profile.get("id", ""))
    #     email: str = profile.get("email", f"{social_id}@naver.local")
    #     name: str = profile.get("name") or "네이버 사용자"
    #     image: str | None = profile.get("profile_image")

    #     return await self._social_login(
    #         social_id=social_id,
    #         provider=SocialProvider.NAVER,
    #         email=email,
    #         name=name,
    #         profile_image_url=image,
    #     )

    # ── 네이버 로그인 테스트 추가코드 ──────────────────────────────────────

    async def naver_login(self, body: SocialLoginRequest) -> SocialLoginResponseData:
        """네이버 Access Token → 유저 프로필 조회 → 로그인/가입."""
        # ── [테스트용 뒷문 시작] ────────────────────────────

        # 1. 만약 포스트맨에서 'naver_test'라고 토큰을 보내면 네이버에 안 물어봅니다.
        if body.access_token == "naver_test":
            return await self._social_login(
                social_id="test_12345",
                provider=SocialProvider.NAVER,
                email="ryan_test@naver.com",  # 테스트하고 싶은 이메일
                name="테스터라이언",
                profile_image_url=None,
            )
        # ── [테스트용 뒷문 끝] ──────────────────────────────
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

    async def withdraw(self, user: User, reason: Optional[str] = None) -> None:
        """도메인 규칙: 물리 삭제 금지 → Soft Delete.

        회원 탈퇴 처리 (Soft Delete).

        1. 연결된 모든 토큰 무효화: 즉시 접근 차단 (출입증 회수)
        2. 유저 상태·시각 기록: Repository `soft_delete_user`에서
           `is_active=False`, `status='DELETED'`, `deleted_at=now(UTC)` 반영
           — [도메인 규칙 1.2] ① 5년 후 물리 삭제를 위한 타임스탬프 기록
           (비유: 보관 기한이 찍힌 '폐기 예정' 각인).

        ※ 설계 의도:
        재가입 시 데이터 복구 편의성과 통계 목적을 위해
        연관된 사업장(Business)이나 채팅 이력은 삭제하거나 연결을 끊지 않고 그대로 유지함.

        cascade: 해당 유저의 모든 토큰도 함께 무효화.
        """
        await self._repo.revoke_all_user_tokens(user.id)
        await self._repo.soft_delete_user(user)
        if self._business_service:
            await self._business_service.deactivate_all_businesses_by_user_internal(
                user.id
            )
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

    async def count_new_users_since(self, since: datetime) -> int:
        """Admin Dashboard를 위한 신규 유저 카운트 로직"""
        return await self._repo.count_users_since(since)

    # ── Admin 전용 (Internal) ─────────────────────────────────────────────

    async def list_users_page(
        self,
        *,
        page: int,
        size: int,
        search_keyword: str | None,
        only_active: bool = True,
    ) -> tuple[list[User], int]:
        """[Internal] 관리자 도메인에서 유저 목록을 조회하기 위한 인터페이스"""
        return await self._repo.list_users_page(
            page=page, size=size, search_keyword=search_keyword, only_active=only_active
        )

    # ── 타 도메인 지원용 (Internal) ───────────────────────────────────────────

    async def get_all_active_user_ids_internal(self) -> list[uuid.UUID]:
        """[Internal] 전체 시스템 공지 대상자 추출용 브릿지"""
        return await self._repo.get_all_active_user_ids()

    async def update_notification_settings_internal(
        self,
        user: User,
        push_enabled: bool | None = None,
        marketing_enabled: bool | None = None,
        policy_update_enabled: bool | None = None,
        chat_answer_enabled: bool | None = None,
    ) -> None:
        """[Internal] 알림 도메인에서 알림 설정 변경 요청 시 호출하는 브릿지 인터페이스"""
        await self._repo.update_notification_settings_internal(
            user=user,
            push_enabled=push_enabled,
            marketing_enabled=marketing_enabled,
            policy_update_enabled=policy_update_enabled,
            chat_answer_enabled=chat_answer_enabled,
        )
        await self._session.commit()
