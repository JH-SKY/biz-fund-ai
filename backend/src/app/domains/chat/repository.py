"""채팅 도메인 리포지토리."""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.app.domains.chat.model import ChatLog, ChatRoom


class ChatRepository:
    """
    비즈몽 AI 상담(Chat) 도메인의 데이터 액세스를 담당하는 리포지토리입니다.
    사용자 측면의 CRUD 로직에 집중하며, 관리자용 기능은 Admin 도메인에서 별도로 다룹니다.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_chat_room(
        self,
        user_id: uuid.UUID,
        business_id: uuid.UUID,
        title: str,
        status: str = "IN_PROGRESS",
    ) -> ChatRoom:
        """
        1. 새로운 상담 세션(대화방)을 생성합니다.
        비유: '상담 일지'의 새 장을 펼치고 제목을 적는 단계입니다.
        """
        room = ChatRoom(
            user_id=user_id,
            business_id=business_id,
            title=title,
            status=status,
        )
        self._session.add(room)
        # flush를 사용해 DB에 즉시 반영하되 트랜잭션은 유지하여 ID값을 확보합니다.
        await self._session.flush()
        return room

    async def get_chat_room_by_id(self, room_id: uuid.UUID) -> Optional[ChatRoom]:
        """
        2. 특정 ID의 상담 세션을 조회합니다. (삭제된 세션 제외)
        실무 관점: Soft Delete 된 데이터는 사용자에게 보이지 않아야 하므로 status 체크가 필수입니다.
        """
        stmt = select(ChatRoom).where(
            ChatRoom.id == room_id,
            ChatRoom.status != "DELETED",  # 삭제되지 않은 세션만 조회
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_chat_rooms_by_business(
        self, business_id: uuid.UUID
    ) -> List[ChatRoom]:
        """
        3. 특정 사업장의 활성 상담 목록을 최신순으로 조회합니다.
        """
        stmt = (
            select(ChatRoom)
            .where(ChatRoom.business_id == business_id, ChatRoom.status != "DELETED")
            .order_by(ChatRoom.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create_chat_log(
        self,
        user_id: uuid.UUID,
        room_id: uuid.UUID,
        role: str,
        content: str,
        ref_policy_id: Optional[uuid.UUID] = None,
        trace_id: Optional[str] = None,
        total_cost: Optional[float] = None,
    ) -> ChatLog:
        """
        4. 대화 메시지(유저/AI)를 기록합니다.
        AI 추적성: trace_id와 total_cost를 함께 저장하여 향후 분석 및 비용 정산의 근거로 활용합니다.
        """
        log = ChatLog(
            user_id=user_id,
            room_id=room_id,
            role=role,
            content=content,
            ref_policy_id=ref_policy_id,
            trace_id=trace_id,
            total_cost=total_cost,
        )
        self._session.add(log)
        await self._session.flush()
        return log

    async def get_chat_logs_by_room(self, room_id: uuid.UUID) -> List[ChatLog]:
        """
        5. 특정 상담 세션의 모든 대화 내역을 시간순으로 불러옵니다.
        최적화: selectinload를 사용하여 참조된 정책(Policy) 정보를 N+1 문제 없이 효율적으로 가져옵니다.
        """
        stmt = (
            select(ChatLog)
            .options(selectinload(ChatLog.ref_policy))
            .where(ChatLog.room_id == room_id)
            .order_by(ChatLog.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_chat_log_by_id(self, log_id: uuid.UUID) -> Optional[ChatLog]:
        stmt = select(ChatLog).where(ChatLog.id == log_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_last_message_by_room(self, room_id: uuid.UUID) -> Optional[ChatLog]:
        """
        6. 상담 세션의 마지막 메시지를 확인합니다. (세션 자동 종료 로직 등에서 활용)
        """
        stmt = (
            select(ChatLog)
            .where(ChatLog.room_id == room_id)
            .order_by(ChatLog.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_chat_room_title(self, room: ChatRoom, title: str) -> None:
        """
        7. AI가 요약한 내용으로 상담 제목을 업데이트합니다.
        """
        room.title = title
        await self._session.flush()

    async def update_chat_room_status(self, room: ChatRoom, status: str) -> None:
        """
        8. 상담 상태(진행중, 종료 등)를 변경합니다.
        """
        room.status = status
        await self._session.flush()

    async def close_inactive_chat_rooms(self, cutoff: datetime) -> int:
        """마지막 메시지 또는 생성 시각이 cutoff 이전인 진행 중 상담을 종료합니다."""
        if cutoff.tzinfo is not None:
            # DB 컬럼이 timezone-naive TIMESTAMP 이므로 비교 전에 tzinfo 를 제거한다.
            # 이 보정이 없으면 PostgreSQL/드라이버 조합에 따라 datetime 비교 오류가 날 수 있다.
            cutoff = cutoff.replace(tzinfo=None)

        # 마지막 메시지 시각을 방 단위로 먼저 집계한다.
        # 메시지가 하나도 없는 방은 created_at 을 기준으로 판단해야 하므로 outer join 을 사용한다.
        last_message_subq = (
            select(
                ChatLog.room_id.label("room_id"),
                func.max(ChatLog.created_at).label("last_message_at"),
            )
            .group_by(ChatLog.room_id)
            .subquery()
        )

        stmt = (
            select(ChatRoom)
            .outerjoin(last_message_subq, last_message_subq.c.room_id == ChatRoom.id)
            .where(
                ChatRoom.status.in_(("IN_PROGRESS", "active")),
                or_(
                    # 메시지가 있는 방: 마지막 메시지가 cutoff 이전이면 비활성으로 본다.
                    last_message_subq.c.last_message_at < cutoff,
                    # 메시지가 없는 방: 방 생성 시각이 cutoff 이전이면 비활성으로 본다.
                    and_(
                        last_message_subq.c.last_message_at.is_(None),
                        ChatRoom.created_at < cutoff,
                    ),
                ),
            )
        )
        result = await self._session.execute(stmt)
        rooms = list(result.scalars().all())
        for room in rooms:
            # 삭제가 아니라 종료 처리만 한다.
            # 상담 기록은 포트폴리오/품질 분석/관리자 모니터링에 계속 필요하다.
            room.status = "CLOSED"
        await self._session.flush()
        return len(rooms)

    async def delete_chat_room(self, room: ChatRoom) -> None:
        """
        9. 상담 세션을 삭제 처리합니다.
        설계 의도: 실무에서는 데이터를 실제로 지우지 않고 상태값만 바꿔 보관하는 'Soft Delete'를 기본으로 합니다.
        """
        room.status = "DELETED"
        await self._session.flush()

    async def count_chats_since(self, since: datetime) -> int:
        """특정 시점 이후 생성된 채팅 로그 수 조회"""

        # [복습!] 시차 정보 제거 (PostgreSQL 규격 맞춤)
        if since.tzinfo is not None:
            since = since.replace(tzinfo=None)

        query = select(func.count(ChatLog.id)).where(
            ChatLog.created_at >= since
        )  # ChatLog는 실제 모델명에 맞춰주세요!
        result = await self._session.execute(query)
        return result.scalar() or 0

    # ── Admin 전용 (Internal) ─────────────────────────────────────────────

    async def list_user_chat_logs_page(
        self, user_id: uuid.UUID | None, page: int, size: int
    ) -> tuple[list[ChatLog], int]:
        """[Internal] 관리자 모니터링용: 사용자의 질문 메시지만 페이징 조회"""
        stmt = select(ChatLog).where(ChatLog.role == "user")
        if user_id:
            stmt = stmt.where(ChatLog.user_id == user_id)
        total_stmt = select(func.count()).select_from(stmt.subquery())
        total = int((await self._session.execute(total_stmt)).scalar() or 0)
        stmt = stmt.order_by(ChatLog.created_at.desc()).offset((page - 1) * size).limit(size)
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def find_first_assistant_after(
        self, room_id: uuid.UUID, after: datetime
    ) -> Optional[ChatLog]:
        """[Internal] 관리자 모니터링용: 유저 질문 직후에 달린 AI의 첫 답변 조회"""
        stmt = select(ChatLog).where(
            ChatLog.room_id == room_id,
            ChatLog.role == "assistant",
            ChatLog.created_at > after
        ).order_by(ChatLog.created_at.asc()).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
