"""채팅 도메인 리포지토리."""

import uuid
from typing import List, Optional
from datetime import datetime

from sqlalchemy import select
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
            ChatRoom.status != "DELETED"  # 삭제되지 않은 세션만 조회
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_chat_rooms_by_business(self, business_id: uuid.UUID) -> List[ChatRoom]:
        """
        3. 특정 사업장의 활성 상담 목록을 최신순으로 조회합니다.
        """
        stmt = (
            select(ChatRoom)
            .where(
                ChatRoom.business_id == business_id,
                ChatRoom.status != "DELETED"
            )
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

    async def delete_chat_room(self, room: ChatRoom) -> None:
        """
        9. 상담 세션을 삭제 처리합니다.
        설계 의도: 실무에서는 데이터를 실제로 지우지 않고 상태값만 바꿔 보관하는 'Soft Delete'를 기본으로 합니다.
        """
        room.status = "DELETED"
        await self._session.flush()