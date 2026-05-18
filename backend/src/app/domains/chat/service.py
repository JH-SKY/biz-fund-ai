# src/app/domains/chat/service.py
"""비즈몽 AI 상담 채팅 도메인 비즈니스 로직.

설계 원칙:
  - ChatRepository(DB 접근), PolicyService(정책 조회), ILLMEngine(AI 응답 생성)을
    생성자 주입으로 받아 서로 독립적인 구현체로 교체할 수 있도록 구성한다.
  - 모든 DB 커밋은 이 Service에서만 발생한다 (Repository는 flush만 수행).
  - '1세션 = 1대화 흐름' 원칙: 새 세션 생성 시 기존 IN_PROGRESS 세션은 자동 종료 처리.
"""

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
    """비즈몽 AI 상담 유스케이스.

    의존성:
      - ChatRepository  : DB 접근
      - PolicyService   : 참조 정책 정보 조회
      - ILLMEngine      : AI 답변 생성 (LangGraph/OpenAI 등 교체 가능)
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
        self,
        business: Business,
        session_id: uuid.UUID,
        *,
        allow_closed: bool = False,
    ) -> ChatRoom:
        """[내부 헬퍼] 상담방 존재 여부·소유권·상태를 한 번에 검증한다.

        [로직]
        1. 상담방이 존재하지 않으면 404 반환
        2. 요청 사업장의 상담방이 아니면 403 반환 (타인 데이터 접근 차단)
        3. 이미 종료된 상담방에 메시지를 보내려 하면 403 반환
           - allow_closed=True 이면 종료 상담방 조회 허용 (이전 대화 내역 확인 등)
        """
        room = await self._repo.get_chat_room_by_id(session_id)
        if not room:
            raise chat_room_not_found()
        if room.business_id != business.id:
            raise chat_room_forbidden()
        if room.status == "CLOSED" and not allow_closed:
            raise chat_room_closed()
        return room

    async def _save_ai_response(
        self,
        business: Business,
        room_id: uuid.UUID,
        ai_resp: LLMResponse,
    ) -> ChatLog:
        """[내부 헬퍼] AI 응답을 chat_logs 테이블에 저장하고 반환한다.

        [처리 내용]
        - referenced_policy_ids 첫 번째 항목을 ref_policy_id로 변환해 저장
        - total_cost 는 Decimal 타입으로 변환 (DB Numeric 타입 대응)
        """
        # 참조 정책 ID가 있으면 첫 번째 항목을 UUID로 변환
        ref_policy_id = (
            uuid.UUID(ai_resp.referenced_policy_ids[0])
            if ai_resp.referenced_policy_ids
            else None
        )
        # float → Decimal 변환 (DB Numeric 컬럼 타입 규격 맞춤)
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
        """새 상담 세션(대화방)을 생성한다.

        [로직 순서]
        1. 이미 진행 중(IN_PROGRESS)인 세션이 있으면 자동으로 CLOSED 처리
           - 1사용자 1활성 세션 원칙: 여러 탭에서 중복 생성 방지
        2. 새 대화방 생성 후 세션 ID·제목·생성 일시 반환
        
        [설계 의도]
        첫 번째 유저 메시지와 AI 응답은 스트리밍 엔드포인트에서 처리하므로
        여기서는 방(Room)만 생성하여 중복 턴 저장을 방지한다.
        """
        # [1] 기존 IN_PROGRESS 세션 자동 종료
        existing_rooms = await self._repo.get_chat_rooms_by_business(business.id)
        for old_room in existing_rooms:
            if old_room.status == "IN_PROGRESS":
                await self._repo.update_chat_room_status(old_room, "CLOSED")

        # [2] 새 대화방 생성 (제목은 첫 메시지 앞 30자로 자동 설정)
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
        """사업장의 상담 세션 목록을 조회한다.

        각 세션에 '마지막 메시지'와 '마지막 업데이트 시간'을 포함하여
        목록 화면(상담 히스토리)에서 미리보기를 보여줄 수 있도록 구성한다.
        """
        rooms = await self._repo.get_chat_rooms_by_business(business.id)
        items: list[ChatSessionItem] = []
        for room in rooms:
            # 마지막 메시지 조회 (미리보기 및 업데이트 시간 기준)
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
        """사용자 메시지 전송 → AI 응답 생성 → 저장 후 응답 반환.

        [로직 순서]
        1. 세션 소유권·상태 검증
        2. 유저 메시지를 chat_logs에 저장 (role='user')
        3. LLM 엔진에 AI 응답 요청
        4. AI 응답을 chat_logs에 저장 (role='assistant')
        5. 참조 정책이 있으면 정책 정보 조회 후 응답에 포함
        """
        # [1] 세션 유효성 검증
        room = await self._verify_ownership_and_status(business, session_id)

        # [2] 유저 메시지 저장
        await self._repo.create_chat_log(
            user_id=business.user_id,
            room_id=room.id,
            role="user",
            content=req.message,
        )
        await self._session.commit()

        # [3] AI 응답 생성 (사업장 이름·점수를 컨텍스트로 전달하여 맞춤 답변 유도)
        ai_resp = await self._llm_engine.generate_reply(
            session_id=str(room.id),
            user_message=req.message,
            business_context={
                "biz_name": business.biz_name,
                "score": business.profile_score,
            },
        )

        # [4] AI 응답 저장
        ai_log = await self._save_ai_response(business, room.id, ai_resp)
        await self._session.commit()

        # [5] 참조 정책 정보 조회 (답변에 연관 정책이 있을 경우 제목과 ID 포함)
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
        """특정 상담 세션의 대화 내역을 전체 조회한다.

        [설계 의도]
        - allow_closed=True: 종료된 상담방의 이전 대화도 확인할 수 있어야 한다.
        - role 필터: system 메시지(내부 관측 로그)는 사용자에게 노출하지 않는다.
        """
        # 종료된 세션도 조회 허용 (대화 이력 열람 목적)
        room = await self._verify_ownership_and_status(
            business,
            session_id,
            allow_closed=True,
        )
        logs = await self._repo.get_chat_logs_by_room(room.id)
        # user·assistant 역할만 필터링하여 반환 (system 로그 제외)
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
        """최근 대화 내용으로 상담방 제목을 AI가 자동 요약·갱신한다.

        [로직]
        1. 대화 내역이 없으면 '새로운 상담' 고정 반환
        2. 최근 5개 메시지를 LLM에 전달해 20자 이내 제목 생성
        3. 생성된 제목으로 chat_rooms.title 업데이트
        """
        room = await self._verify_ownership_and_status(business, session_id)
        logs = await self._repo.get_chat_logs_by_room(room.id)
        if not logs:
            return AutoSummaryResponseData(new_title="새로운 상담")

        # 최근 5개 메시지 내용만 추출하여 LLM에 전달
        messages = [log.content for log in logs[-5:]]
        new_title = await self._llm_engine.summarize_title(messages)

        await self._repo.update_chat_room_title(room, new_title)
        await self._session.commit()

        return AutoSummaryResponseData(new_title=new_title)

    async def delete_session(self, business: Business, session_id: uuid.UUID) -> None:
        """상담 세션을 삭제(Soft Delete: status='DELETED') 처리한다."""
        room = await self._verify_ownership_and_status(business, session_id)
        await self._repo.delete_chat_room(room)
        await self._session.commit()

    async def auto_close_inactive_sessions(self) -> int:
        """비활성 세션 자동 종료 (향후 배치 연동 예정, 현재 미구현).

        [설계 의도]
        일정 시간 동안 메시지가 없는 세션을 자동으로 CLOSED 처리하는 배치용 메서드.
        현재는 0을 반환하는 스텁(Stub) 상태이며, 스케줄러 연동 시 구현 예정.
        """
        return 0

    async def count_chat_logs_since(self, since: datetime) -> int:
        """[Admin] 특정 시점 이후 생성된 채팅 로그 수를 반환한다 (대시보드 통계용)."""
        return await self._repo.count_chats_since(since)

    async def list_user_chat_logs_page(
        self,
        user_id: uuid.UUID | None,
        page: int,
        size: int,
    ) -> tuple[list[ChatLog], int]:
        """[Admin] 사용자별 채팅 로그 페이징 조회 (관리자 모니터링 화면용)."""
        return await self._repo.list_user_chat_logs_page(user_id, page, size)

    async def find_first_assistant_after(
        self,
        room_id: uuid.UUID,
        after: datetime,
    ) -> Optional[ChatLog]:
        """[Admin] 특정 시각 이후 AI가 처음 보낸 응답 메시지를 조회한다.

        [용도]
        관리자 채팅 모니터링 화면에서 유저 질문 직후의 AI 응답을 페어링할 때 사용한다.
        """
        return await self._repo.find_first_assistant_after(room_id, after)
