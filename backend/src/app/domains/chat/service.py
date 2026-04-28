"""Business logic for BizMong chat."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.app.domains.business.model import Business
from src.app.domains.chat.exception import (
    chat_room_closed,
    chat_room_forbidden,
    chat_room_not_found,
)
from src.app.domains.chat.interfaces import ILLMEngine, LLMResponse
from src.app.domains.chat.model import ChatLog, ChatRoom
from src.app.domains.chat.repository import ChatRepository
from src.app.domains.chat.schema import (
    AutoSummaryResponseData,
    ChatMessageItem,
    ChatSessionItem,
    CreateSessionRequest,
    CreateSessionResponseData,
    ReferencedPolicy,
    SendMessageRequest,
    SendMessageResponseData,
)
from src.app.domains.policy.service import PolicyService


class ChatService:
    def __init__(
        self,
        session: AsyncSession,
        repo: ChatRepository,
        policy_service: PolicyService,
        llm_engine: ILLMEngine,
    ) -> None:
        self._session = session
        self._repo = repo
        self._policy_service = policy_service
        self._llm_engine = llm_engine

    async def _verify_ownership_and_status(
        self,
        business: Business,
        session_id: uuid.UUID,
    ) -> ChatRoom:
        room = await self._repo.get_chat_room_by_id(session_id)
        if not room:
            raise chat_room_not_found()
        if room.business_id != business.id:
            raise chat_room_forbidden()
        if room.status == "CLOSED":
            raise chat_room_closed()
        return room

    async def _save_ai_response(
        self,
        business: Business,
        room_id: uuid.UUID,
        ai_resp: LLMResponse,
    ) -> ChatLog:
        ref_policy_id = (
            uuid.UUID(ai_resp.referenced_policy_ids[0])
            if ai_resp.referenced_policy_ids
            else None
        )
        safe_cost = (
            Decimal(str(ai_resp.total_cost)) if ai_resp.total_cost else Decimal("0.0")
        )

        return await self._repo.create_chat_log(
            user_id=business.user_id,
            room_id=room_id,
            role="assistant",
            content=ai_resp.content,
            ref_policy_id=ref_policy_id,
            trace_id=ai_resp.trace_id,
            total_cost=safe_cost,
        )

    async def create_session(
        self,
        business: Business,
        req: CreateSessionRequest,
    ) -> CreateSessionResponseData:
        # Only create the room here. The actual first user message and assistant
        # response are handled by the streaming endpoint to avoid duplicate turns.
        existing_rooms = await self._repo.get_chat_rooms_by_business(business.id)
        for old_room in existing_rooms:
            if old_room.status == "IN_PROGRESS":
                await self._repo.update_chat_room_status(old_room, "CLOSED")

        room = await self._repo.create_chat_room(
            user_id=business.user_id,
            business_id=business.id,
            title=(req.initial_message[:30] or "새로운 상담"),
        )
        await self._session.commit()

        return CreateSessionResponseData(
            session_id=str(room.id),
            title=room.title,
            created_at=room.created_at,
        )

    async def get_sessions(self, business: Business) -> list[ChatSessionItem]:
        rooms = await self._repo.get_chat_rooms_by_business(business.id)
        items: list[ChatSessionItem] = []
        for room in rooms:
            last_msg = await self._repo.get_last_message_by_room(room.id)
            items.append(
                ChatSessionItem(
                    session_id=str(room.id),
                    title=room.title or "새로운 상담",
                    last_message=last_msg.content if last_msg else None,
                    updated_at=last_msg.created_at if last_msg else room.created_at,
                )
            )
        return items

    async def send_message(
        self,
        business: Business,
        session_id: uuid.UUID,
        req: SendMessageRequest,
    ) -> SendMessageResponseData:
        room = await self._verify_ownership_and_status(business, session_id)

        await self._repo.create_chat_log(
            user_id=business.user_id,
            room_id=room.id,
            role="user",
            content=req.message,
        )
        await self._session.commit()

        ai_resp = await self._llm_engine.generate_reply(
            session_id=str(room.id),
            user_message=req.message,
            business_context={
                "biz_name": business.biz_name,
                "score": business.profile_score,
            },
        )

        ai_log = await self._save_ai_response(business, room.id, ai_resp)
        await self._session.commit()

        referenced_policies: list[ReferencedPolicy] = []
        if ai_log.ref_policy_id:
            policy = await self._policy_service.get_policy_by_id_internal(
                ai_log.ref_policy_id
            )
            if policy:
                referenced_policies.append(
                    ReferencedPolicy(id=str(policy.id), title=policy.title)
                )

        return SendMessageResponseData(
            message_id=str(ai_log.id),
            role="assistant",
            content=ai_resp.content,
            referenced_policies=referenced_policies,
            created_at=ai_log.created_at,
        )

    async def get_messages(
        self,
        business: Business,
        session_id: uuid.UUID,
    ) -> list[ChatMessageItem]:
        room = await self._verify_ownership_and_status(business, session_id)
        logs = await self._repo.get_chat_logs_by_room(room.id)
        return [
            ChatMessageItem(
                role=log.role,
                content=log.content,
                created_at=log.created_at,
            )
            for log in logs
            if log.role in {"user", "assistant"}
        ]

    async def auto_summary(
        self,
        business: Business,
        session_id: uuid.UUID,
    ) -> AutoSummaryResponseData:
        room = await self._verify_ownership_and_status(business, session_id)
        logs = await self._repo.get_chat_logs_by_room(room.id)
        if not logs:
            return AutoSummaryResponseData(new_title="새로운 상담")

        messages = [log.content for log in logs[-5:]]
        new_title = await self._llm_engine.summarize_title(messages)

        await self._repo.update_chat_room_title(room, new_title)
        await self._session.commit()

        return AutoSummaryResponseData(new_title=new_title)

    async def delete_session(self, business: Business, session_id: uuid.UUID) -> None:
        room = await self._verify_ownership_and_status(business, session_id)
        await self._repo.delete_chat_room(room)
        await self._session.commit()

    async def auto_close_inactive_sessions(self) -> int:
        return 0

    async def count_chat_logs_since(self, since: datetime) -> int:
        return await self._repo.count_chats_since(since)

    async def list_user_chat_logs_page(
        self,
        user_id: uuid.UUID | None,
        page: int,
        size: int,
    ) -> list[ChatLog]:
        return await self._repo.list_user_chat_logs_page(user_id, page, size)

    async def find_first_assistant_after(
        self,
        room_id: uuid.UUID,
        after: datetime,
    ) -> Optional[ChatLog]:
        return await self._repo.find_first_assistant_after(room_id, after)
