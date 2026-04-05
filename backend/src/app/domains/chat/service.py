"""채팅 도메인 서비스 계층 - 비즈몽 AI 상담 로직."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import List
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.app.domains.business.model import Business
from src.app.domains.chat.exception import (
    chat_room_closed,
    chat_room_forbidden,
    chat_room_not_found,
)
from src.app.domains.chat.interfaces import ILLMEngine, LLMResponse
from src.app.domains.chat.model import ChatRoom, ChatLog
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
    """
    비즈몽 AI 상담의 핵심 비즈니스 로직을 수행합니다.
    설계 원칙: 
    1. 외부 API(LLM) 호출 시 DB 트랜잭션을 최소한으로 유지합니다.
    2. 도메인 간 통신은 주입된 서비스를 통해서만 수행합니다.
    """

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
        self, business: Business, session_id: uuid.UUID
    ) -> ChatRoom:
        """[검증] 상담 세션의 소유권과 유효성을 확인합니다."""
        room = await self._repo.get_chat_room_by_id(session_id)
        if not room:
            raise chat_room_not_found()
        if room.business_id != business.id:
            raise chat_room_forbidden()
        if room.status == "CLOSED":
            raise chat_room_closed()
        return room

    async def _save_ai_response(
        self, business: Business, room_id: uuid.UUID, ai_resp: LLMResponse
    ) -> ChatLog:
        """[공통 로직] AI의 답변을 분석하여 로그로 저장합니다."""
        ref_policy_id = (
            uuid.UUID(ai_resp.referenced_policy_ids[0]) 
            if ai_resp.referenced_policy_ids else None
        )
        
        # 비용 데이터 무결성: 숫자가 아닌 값이 들어올 경우를 대비한 안전 장치
        safe_cost = Decimal(str(ai_resp.total_cost)) if ai_resp.total_cost else Decimal("0.0")

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
        """
        1. 새로운 상담 세션을 시작합니다. (기존 상담은 자동 종료)
        비유: 새로운 상담원과 연결하기 위해 이전 상담 전화를 끊는 과정입니다.
        """
        # [실무 패턴] 기존 세션 종료 로직 최적화
        existing_rooms = await self._repo.get_chat_rooms_by_business(business.id)
        for old_room in existing_rooms:
            if old_room.status == "IN_PROGRESS":
                await self._repo.update_chat_room_status(old_room, "CLOSED")

        # 상담방 및 유저 메시지 선 저장 (트랜잭션 1차 완료)
        room = await self._repo.create_chat_room(
            user_id=business.user_id,
            business_id=business.id,
            title="새로운 상담",
        )
        await self._repo.create_chat_log(
            user_id=business.user_id,
            room_id=room.id,
            role="user",
            content=req.initial_message,
        )
        await self._session.commit() # 유저 메시지 유실 방지를 위해 먼저 커밋

        # AI 답변 생성 (트랜잭션 외부 수행 - 성능 핵심)
        ai_resp = await self._llm_engine.generate_reply(
            session_id=str(room.id),
            user_message=req.initial_message,
            business_context={
                "biz_name": business.biz_name, 
                "score": business.profile_score,
                "sector": business.sector_code
            },
        )

        # AI 답변 저장 (트랜잭션 2차 시작)
        await self._save_ai_response(business, room.id, ai_resp)
        await self._session.commit()

        return CreateSessionResponseData(
            session_id=str(room.id),
            title=room.title,
            created_at=room.created_at,
        )

    async def get_sessions(self, business: Business) -> List[ChatSessionItem]:
        """2. 삭제되지 않은 상담 세션 목록을 최신순으로 조회합니다."""
        rooms = await self._repo.get_chat_rooms_by_business(business.id)
        items = []
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
        """
        3. 기존 상담 세션에서 메시지를 주고받습니다.
        설계 의도: 유저 질문 저장 -> LLM 호출 -> AI 답변 저장 순으로 처리하여 데이터 무결성을 보장합니다.
        """
        room = await self._verify_ownership_and_status(business, session_id)

        # 유저 질문 기록 및 1차 커밋
        await self._repo.create_chat_log(
            user_id=business.user_id,
            room_id=room.id,
            role="user",
            content=req.message,
        )
        await self._session.commit()

        # LLM 호출 (DB 부하 방지를 위해 트랜잭션 밖에서 실행)
        ai_resp = await self._llm_engine.generate_reply(
            session_id=str(room.id),
            user_message=req.message,
            business_context={"biz_name": business.biz_name, "score": business.profile_score},
        )

        # AI 답변 기록 및 2차 커밋
        ai_log = await self._save_ai_response(business, room.id, ai_resp)
        await self._session.commit()

        # 정책 정보 매핑 (Service-to-Service)
        referenced_policies = []
        if ai_log.ref_policy_id:
            policy = await self._policy_service.get_policy_by_id_internal(ai_log.ref_policy_id)
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
        self, business: Business, session_id: uuid.UUID
    ) -> List[ChatMessageItem]:
        """4. 특정 상담의 전체 대화 이력을 조회합니다."""
        room = await self._verify_ownership_and_status(business, session_id)
        logs = await self._repo.get_chat_logs_by_room(room.id)
        return [ChatMessageItem(role=log.role, content=log.content) for log in logs]

    async def auto_summary(
        self, business: Business, session_id: uuid.UUID
    ) -> AutoSummaryResponseData:
        """5. 대화 맥락을 파악하여 상담방의 제목을 자동 생성합니다."""
        room = await self._verify_ownership_and_status(business, session_id)
        logs = await self._repo.get_chat_logs_by_room(room.id)
        
        # 비용 효율성을 위해 마지막 5개 메시지만 요약에 사용
        messages = [log.content for log in logs[-5:]] 
        new_title = await self._llm_engine.summarize_title(messages)
        
        await self._repo.update_chat_room_title(room, new_title)
        await self._session.commit()

        return AutoSummaryResponseData(new_title=new_title)

    async def delete_session(self, business: Business, session_id: uuid.UUID) -> None:
        """6. 상담 세션을 논리 삭제(Soft Delete)합니다."""
        room = await self._verify_ownership_and_status(business, session_id)
        await self._repo.delete_chat_room(room)
        await self._session.commit()

    async def auto_close_inactive_sessions(self) -> int:
        """[배치 전용] 7일 이상 미활동 중인 세션을 정리하여 리소스를 확보합니다."""
        # 이 메서드는 Repository에서 관리자용 쿼리를 분리함에 따라 
        # 추후 AdminService로 이관하는 것이 좋습니다.
        return 0 # 현재는 인터페이스 유지를 위해 0 반환 (리팩토링 대상)