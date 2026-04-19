# src/app/domains/policy/repository.py
"""정책 도메인 DB 접근 계층.

원칙:
  - 비즈니스 판단(예외 발생, 조건 분기)은 Service에서, I/O(쿼리 실행)만 여기에 담습니다.
  - [도메인 규칙 0] 모든 일반 사용자용 조회에는 is_active=True 필터를 강제합니다. (Soft Delete 대응)
  -[도메인 규칙 2.2] 북마크 조회는 반드시 business_id를 기준으로 격리하여 보안을 유지합니다.

최적화 전략 (2026.04 적용):
  - 관리자의 수동 정책 생성 시 AI 분석 필드가 유실되지 않도록 모델 매핑 추가.
  - patch_policy_internal 에서 의도적인 Null(None) 업데이트를 허용하여 관리자 수정 기능 정상화.
"""

from __future__ import annotations

import math
import uuid
from datetime import date
from typing import Optional

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.app.domains.policy.model import Policy, PolicyBookmark, PolicyChunk, PolicyStatus


class PolicyRepository:
    """정책 도메인의 '창고 관리자'입니다.

    데이터를 넣고(C), 찾고(R), 고치고(U), 치우는(D) 일만 수행합니다.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── 1. Policy 조회 (사용자용) ──────────────────────────────────────────────

    async def get_active_policies(
        self,
        *,
        page: int = 1,
        size: int = 10,
    ) -> tuple[list[Policy], int, int]:
        """활성 상태인 정책 목록을 '최신 등록순'으로 가져옵니다. (배달 전 포장 작업)"""
        # 1. 기본 필터링 (활성 상태만)
        base = select(Policy).where(Policy.is_active.is_(True))

        # 2. 전체 개수 파악 (전체 페이지 계산용)
        count_stmt = select(func.count()).select_from(base.subquery())
        total_count: int = (await self._session.execute(count_stmt)).scalar_one()

        total_pages = max(1, math.ceil(total_count / size))

        # 3. 데이터 페이징 조회
        stmt = (
            base.order_by(Policy.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())

        return items, total_count, total_pages

    async def get_policy_by_id(self, policy_id: uuid.UUID) -> Policy | None:
        """아이디로 정책 하나를 찾습니다. (비유: 특정 학번 학생 찾기)"""
        stmt = select(Policy).where(Policy.id == policy_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def increase_view_count(self, policy_id: uuid.UUID) -> None:
        """조회수를 안전하게 1 올립니다.

        설계 의도:
          - 여러 명의 사용자가 동시에 조회할 때 데이터가 씹히지 않도록
            DB가 직접 '+ 1'을 수행하게 합니다. (Atomic Update)
        """
        stmt = (
            update(Policy)
            .where(Policy.id == policy_id)
            .values(view_count=Policy.view_count + 1)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def search_policies(
        self,
        *,
        keyword: Optional[str] = None,
        region: Optional[str] = None,
        category: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> tuple[list[Policy], int, int]:
        """제목, 지역, 카테고리 등 여러 조건으로 정책을 검색합니다."""
        conditions = [Policy.is_active.is_(True)]

        # 1. 키워드 검색 (제목 또는 원문 포함 여부)
        if keyword:
            pattern = f"%{keyword}%"
            conditions.append(
                or_(
                    Policy.title.ilike(pattern),
                    Policy.content_raw.ilike(pattern),
                )
            )

        # 2. 필터링 조건 추가 (지역, 카테고리)
        if region:
            conditions.append(Policy.region.ilike(f"%{region}%"))
        if category:
            conditions.append(Policy.category == category)

        base = select(Policy).where(*conditions)

        # 3. 페이징 및 결과 반환
        count_stmt = select(func.count()).select_from(base.subquery())
        total_count: int = (await self._session.execute(count_stmt)).scalar_one()
        total_pages = max(1, math.ceil(total_count / size))

        stmt = (
            base.order_by(Policy.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total_count, total_pages

    # ── 2. PolicyBookmark (찜하기 로직) ──────────────────────────────────────────

    async def get_bookmark(
        self,
        *,
        business_id: uuid.UUID,
        policy_id: uuid.UUID,
    ) -> PolicyBookmark | None:
        """특정 사업장이 이 정책을 찜했는지 확인합니다."""
        stmt = select(PolicyBookmark).where(
            PolicyBookmark.business_id == business_id,
            PolicyBookmark.policy_id == policy_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_bookmarked_policy_ids(
        self,
        *,
        business_id: uuid.UUID,
        policy_ids: list[uuid.UUID],
    ) -> set[uuid.UUID]:
        """주어진 정책들 중 찜한 것들만 골라냅니다. (목록에서 '빨간 하트' 표시용)"""
        if not policy_ids:
            return set()

        stmt = select(PolicyBookmark.policy_id).where(
            PolicyBookmark.business_id == business_id,
            PolicyBookmark.policy_id.in_(policy_ids),
        )
        result = await self._session.execute(stmt)
        return set(result.scalars().all())

    async def get_bookmarked_policies(
        self,
        *,
        business_id: uuid.UUID,
        page: int = 1,
        size: int = 10,
    ) -> tuple[list[Policy], int, int]:
        """해당 사업장의 북마크 목록을 가져옵니다."""
        base = (
            select(Policy)
            .join(
                PolicyBookmark,
                (PolicyBookmark.policy_id == Policy.id)
                & (PolicyBookmark.business_id == business_id),
            )
            .where(Policy.is_active.is_(True))
        )

        count_stmt = select(func.count()).select_from(base.subquery())
        total_count: int = (await self._session.execute(count_stmt)).scalar_one()
        total_pages = max(1, math.ceil(total_count / size))

        stmt = (
            base.order_by(PolicyBookmark.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total_count, total_pages

    async def create_bookmark(
        self,
        *,
        business_id: uuid.UUID,
        policy_id: uuid.UUID,
    ) -> PolicyBookmark:
        """북마크 정보를 창고에 새로 등록합니다."""
        bookmark = PolicyBookmark(
            business_id=business_id,
            policy_id=policy_id,
        )
        self._session.add(bookmark)
        await self._session.flush()
        await self._session.refresh(bookmark)
        return bookmark

    async def delete_bookmark(self, bookmark: PolicyBookmark) -> None:
        """북마크를 영구히 삭제합니다."""
        stmt = delete(PolicyBookmark).where(PolicyBookmark.id == bookmark.id)
        await self._session.execute(stmt)
        await self._session.flush()

    async def toggle_bookmark(
        self,
        *,
        business_id: uuid.UUID,
        policy_id: uuid.UUID,
    ) -> bool:
        """찜하기 스위치를 끄거나 켭니다. (이미 있으면 삭제, 없으면 추가)"""
        bookmark = await self.get_bookmark(business_id=business_id, policy_id=policy_id)
        if bookmark:
            await self.delete_bookmark(bookmark)
            return False

        await self.create_bookmark(business_id=business_id, policy_id=policy_id)
        return True

    async def get_top_policies_by_views(self, limit: int = 5) -> list[Policy]:
        """조회수 상위 정책 리스트 조회 (실무 랭킹 로직)"""
        stmt = (
            select(Policy)
            .where(Policy.is_active == True)
            .order_by(Policy.view_count.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create_policy(
        self,
        *,
        title: str,
        content_raw: str,
        category: str,
        agency_name: str = "미정",
        apply_url: str | None = None,
        status: PolicyStatus = PolicyStatus.RECRUITING,
        closed_at: date | None = None,
        origin_id: str,
        **kwargs,
    ) -> Policy:
        """새로운 정책 데이터를 DB 모델로 변환하여 세션에 추가합니다.[버그 수정] 관리자가 수동으로 등록 시, kwargs로 넘어오는 AI 필드들도 
        모델에 매핑하여 서비스에서 정상적으로 보이도록 개선했습니다.
        """
        new_policy = Policy(
            title=title,
            content_raw=content_raw,
            category=category,
            agency_name=agency_name,
            apply_url=apply_url,
            status=status,
            closed_at=closed_at or date(9999, 12, 31),
            is_active=True,
            view_count=0,
            origin_id=origin_id,
            # 아래 AI 관련 및 기타 필드들을 kwargs에서 추출하여 안전하게 저장
            target_logic=kwargs.get("target_logic"),
            bonus_logic=kwargs.get("bonus_logic"),
            ai_summary=kwargs.get("ai_summary"),
            ai_full_explanation=kwargs.get("ai_full_explanation"),
            required_documents=kwargs.get("required_documents"),
        )

        self._session.add(new_policy)
        await self._session.flush()
        return new_policy

    # ── 3. 중복 검증용 조회 ──────────────────────────────────────────────────

    async def get_policy_by_origin_id(self, origin_id: str) -> Optional[Policy]:
        """기업마당 고유 번호(origin_id)로 이미 저장된 공고인지 확인합니다."""
        stmt = select(Policy).where(Policy.origin_id == origin_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def patch_policy_internal(
        self,
        policy: Policy,
        **kwargs,
    ) -> None:
        """[Internal] 관리자 도메인 등에서 정책 정보를 부분 수정(업데이트)합니다.
        
        [버그 수정] 기존의 `and value is not None` 조건 삭제.
        API 스키마 계층(Pydantic)에서 `exclude_unset=True`를 통해 클라이언트가 
        명시적으로 보낸 필드만 `kwargs`로 들어오도록 통제되므로, 
        여기로 전달된 `None` 값은 "필드를 지우겠다"는 명시적 의도로 받아들이고 덮어씌웁니다.
        """
        for key, value in kwargs.items():
            if hasattr(policy, key):
                setattr(policy, key, value)
        await self._session.flush()

    # ── 4. PolicyChunk (벡터 임베딩 청크) ──────────────────────────────────────

    async def create_chunk(
        self,
        *,
        policy_id: uuid.UUID,
        chunk_index: int,
        chunk_type: str,
        chunk_text: str,
        embedding: list[float],
    ) -> PolicyChunk:
        """정책 청크와 임베딩 벡터를 생성합니다."""
        chunk = PolicyChunk(
            policy_id=policy_id,
            chunk_index=chunk_index,
            chunk_type=chunk_type,
            chunk_text=chunk_text,
            embedding=embedding,
        )
        self._session.add(chunk)
        await self._session.flush()
        return chunk

    async def delete_chunks_by_policy_id(self, policy_id: uuid.UUID) -> None:
        """특정 정책의 청크를 전부 삭제합니다 (내용 변경 시 교체 전략)."""
        stmt = delete(PolicyChunk).where(PolicyChunk.policy_id == policy_id)
        await self._session.execute(stmt)
        await self._session.flush()

    async def update_content_hash(self, policy_id: uuid.UUID, content_hash: str) -> None:
        """임베딩 변경 감지용 content_hash를 업데이트합니다."""
        stmt = (
            update(Policy)
            .where(Policy.id == policy_id)
            .values(content_hash=content_hash)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def get_policies_without_hash(self, limit: int = 500) -> list[Policy]:
        """content_hash가 없는 정책을 조회합니다 (초기 일괄 임베딩 배치용)."""
        stmt = (
            select(Policy)
            .where(Policy.is_active.is_(True), Policy.content_hash.is_(None))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def vector_search(
        self,
        query_vector: list[float],
        *,
        region: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[PolicyStatus] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> list[tuple[Policy, float]]:
        """
        [하이브리드 검색] SQL 필터 → 벡터 코사인 유사도 검색을 순서대로 수행합니다.

        설계 의도:
          - SQL 필터를 먼저 적용하여 관련 없는 지역·카테고리의 정책을 제외합니다.
          - 필터링된 집합에서만 벡터 거리(Cosine Distance)를 계산하여
            "부산 IT 지원금" 같은 엉뚱한 결과가 섞이지 않게 합니다.
          - 한 정책이 여러 청크를 가지므로 MIN(거리) 기준으로 대표값을 선택합니다.

        Returns:
            [(Policy, cosine_distance), ...] — 거리 오름차순 정렬
        """
        # [1] 정책 조건 필터 구성
        policy_conditions = [Policy.is_active.is_(True)]
        if region:
            policy_conditions.append(Policy.region.ilike(f"%{region}%"))
        if category:
            policy_conditions.append(Policy.category == category)
        if status:
            policy_conditions.append(Policy.status == status)

        # [2] 청크 테이블과 JOIN 후 정책별 최소 코사인 거리 계산
        #     <=> 연산자: pgvector Cosine Distance (0 = 동일, 2 = 반대)
        min_dist_label = func.min(
            PolicyChunk.embedding.cosine_distance(query_vector)
        ).label("min_dist")

        stmt = (
            select(Policy, min_dist_label)
            .join(PolicyChunk, PolicyChunk.policy_id == Policy.id)
            .where(*policy_conditions)
            .group_by(Policy.id)
            .order_by(min_dist_label)
            .limit(limit)
            .offset(offset)
        )

        result = await self._session.execute(stmt)
        rows = result.all()
        return [(row[0], float(row[1])) for row in rows]