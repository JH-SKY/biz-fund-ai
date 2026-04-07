# src/app/domains/auth/repository.py
"""인증 도메인 DB 접근 계층."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.app.domains.auth.model import SocialProvider, User, UserToken


class AuthRepository:
    """인증 도메인 Repository. 비즈니스 판단은 하지 않는다."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── User CRUD ──────────────────────────────────────

    async def get_user_by_social(
        self, *, social_id: str, provider: SocialProvider
    ) -> User | None:
        """도메인 규칙: social_id + social_provider 가 유니크 키."""
        stmt = select(User).where(
            User.social_id == social_id,
            User.social_provider == provider,
        )
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        stmt = select(User).where(User.id == user_id, User.is_active.is_(True))
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def create_user(
        self,
        *,
        email: str,
        name: str,
        social_id: str,
        social_provider: SocialProvider,
        profile_image_url: str | None,
    ) -> User:
        user = User(
            email=email,
            name=name,
            social_id=social_id,
            social_provider=social_provider,
            profile_image_url=profile_image_url,
            status="active",
            is_active=True,
        )
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def update_user_profile(
        self,
        user: User,
        *,
        military_service: str | None,
        interest_sectors: list[str] | None,
        is_non_major: bool | None,
        tech_stack: list[str] | None,
    ) -> None:
        """제공된 필드만 선택적으로 업데이트한다."""
        if military_service is not None:
            user.military_service = military_service
        if interest_sectors is not None:
            user.interest_sectors = interest_sectors
        if is_non_major is not None:
            user.is_non_major = is_non_major
        if tech_stack is not None:
            user.tech_stack = tech_stack
        await self._session.flush()

    async def soft_delete_user(self, user: User) -> None:
        """도메인 규칙: 물리 삭제 금지 → status='DELETED' + is_active=False + deleted_at(UTC)."""
        withdrawn_at = datetime.now(timezone.utc)
        user.status = "DELETED"
        user.is_active = False
        # [도메인 규칙 1.2] ① 5년 후 물리 삭제를 위한 타임스탬프 기록 — 비유: 보관함에 '폐기 예정일' 각인.
        user.deleted_at = withdrawn_at
        await self._session.flush()

    # ── UserToken (Refresh Token) ──────────────────────

    async def create_token(
        self,
        *,
        user_id: uuid.UUID,
        token: str,
        expires_at: datetime,
    ) -> UserToken:
        clean_expires_at = expires_at.replace(tzinfo=None)
        row = UserToken(
            user_id=user_id,
            token=token,
            expires_at=clean_expires_at,
            is_revoked=False,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_valid_token(self, token: str) -> UserToken | None:
        """유효(미만료·미무효화)한 Refresh Token 조회."""
        # 비교를 위해 timezone 정보를 뺀 현재 시각 생성
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        stmt = select(UserToken).where(
            UserToken.token == token,
            UserToken.is_revoked.is_(False),
            UserToken.expires_at > now,
        )
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def revoke_token(self, token_row: UserToken) -> None:
        token_row.is_revoked = True
        await self._session.flush()

    async def revoke_all_user_tokens(self, user_id: uuid.UUID) -> None:
        """회원탈퇴 시 해당 사용자의 모든 토큰 무효화."""
        stmt = (
            update(UserToken)
            .where(UserToken.user_id == user_id, UserToken.is_revoked.is_(False))
            .values(is_revoked=True)
        )
        await self._session.execute(stmt)

    async def get_by_email(self, email: str) -> Optional[User]:
        """이메일로 사용자 조회."""
        stmt = select(User).where(User.email == email, User.is_active == True)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_users_since(self, since: datetime) -> int:
        """특정 시점 이후 가입한 활성 유저 수 조회"""

        # [핵심!] 시차 정보(tzinfo)가 있다면 제거해서 DB 규격에 맞춥니다. (Naive datetime으로 변환)
        if since.tzinfo is not None:
            since = since.replace(tzinfo=None)

        query = (
            select(func.count(User.id))
            .where(User.created_at >= since)
            .where(User.is_active == True)
        )
        result = await self._session.execute(query)
        return result.scalar() or 0

    # ── Admin 전용 (Internal) ─────────────────────────────────────────────

    async def list_users_page(
        self,
        *,
        page: int,
        size: int,
        search_keyword: str | None,
        only_active: bool = True,
    ) -> tuple[list[User], int]:
        """[Internal] 관리자용 전체 유저 목록 페이징 조회"""

        filters = []
        if only_active:
            filters.append(User.is_active.is_(True))
        if search_keyword and search_keyword.strip():
            kw = f"%{search_keyword.strip()}%"
            filters.append(or_(User.name.ilike(kw), User.email.ilike(kw)))

        count_stmt = select(func.count()).select_from(User)
        stmt = select(User)
        for f in filters:
            count_stmt = count_stmt.where(f)
            stmt = stmt.where(f)

        total = int((await self._session.execute(count_stmt)).scalar_one())
        stmt = (
            stmt.order_by(User.created_at.desc()).offset((page - 1) * size).limit(size)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return list(rows), total

    # ── 타 도메인 지원용 (Internal) ───────────────────────────────────────────

    async def get_all_active_user_ids(self) -> list[uuid.UUID]:
        """[Internal] 전체 시스템 공지 발송 등을 위한 활성 유저 ID만 추출"""
        stmt = select(User.id).where(User.is_active.is_(True))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_notification_settings_internal(
        self,
        user: User,
        push_enabled: bool | None,
        marketing_enabled: bool | None,
        policy_update_enabled: bool | None,
        chat_answer_enabled: bool | None,
    ) -> None:
        """[Internal] 알림 설정 상태만 선택적으로 업데이트합니다."""
        if push_enabled is not None:
            user.push_enabled = push_enabled
        if marketing_enabled is not None:
            user.marketing_enabled = marketing_enabled
        if policy_update_enabled is not None:
            user.policy_update_enabled = policy_update_enabled
        if chat_answer_enabled is not None:
            user.chat_answer_enabled = chat_answer_enabled
            
        await self._session.flush()