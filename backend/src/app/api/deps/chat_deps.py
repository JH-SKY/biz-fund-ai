# src/app/api/deps/chat_deps.py
"""채팅 도메인 FastAPI 의존성(Depends) 모음.

[역할]
- ChatServiceDep  : ChatService 인스턴스를 요청마다 생성하여 라우터에 주입
- BizMongAgentDep : 비즈몽 LangGraph 에이전트를 요청마다 생성하여 라우터에 주입

[BizMongAgent 지연 임포트 이유]
BizMongAgent 는 초기화 시 DATABASE_URL 을 읽으므로, 앱 초기화 순서 문제로
임포트가 먼저 일어나면 오류가 발생할 수 있다.
함수 호출 시점에 임포트하여 이 문제를 방지한다.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import OPENAI_API_KEY
from src.app.database.postgres.database import get_db
from src.app.domains.chat.interfaces import OpenAILLMEngine
from src.app.domains.chat.repository import ChatRepository
from src.app.domains.chat.service import ChatService
from src.app.api.deps.policy_deps import get_policy_service
from src.app.domains.policy.service import PolicyService


async def get_chat_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChatRepository:
    """DB 세션으로 ChatRepository 인스턴스를 생성한다."""
    return ChatRepository(db)


async def get_chat_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    repo: Annotated[ChatRepository, Depends(get_chat_repo)],
    policy_service: Annotated[PolicyService, Depends(get_policy_service)],
) -> ChatService:
    """OpenAI LLM 엔진과 함께 ChatService 를 조립하여 반환한다."""
    llm_engine = OpenAILLMEngine(api_key=OPENAI_API_KEY)
    return ChatService(
        session=db,
        repo=repo,
        policy_service=policy_service,
        llm_engine=llm_engine,
    )


async def get_biz_mong_agent(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """요청마다 새 BizMongAgent 인스턴스를 생성한다.

    session 은 요청 스코프이지만 _MEMORY_SAVER 는 모듈 레벨 싱글톤이므로
    thread_id(= room_id) 기준의 대화 맥락은 요청 간 공유된다.

    지연 임포트(lazy import) 이유:
      - BizMongAgent(graph.py) → SessionLocal(database.py) 체인에서
        FastAPI 앱 초기화 시 DATABASE_URL 없이 임포트되는 경우 오류를 방지한다.
    """
    from src.app.agents.biz_mong.graph import BizMongAgent
    return await BizMongAgent.create(session=db)


ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]

# BizMongAgentDep: TYPE_CHECKING 시 타입 힌트만 제공 (런타임 임포트는 지연)
try:
    from src.app.agents.biz_mong.graph import BizMongAgent as _BizMongAgent
    BizMongAgentDep = Annotated[_BizMongAgent, Depends(get_biz_mong_agent)]
except Exception:
    # DATABASE_URL 없는 환경(테스트 등)에서 import 오류 방지
    BizMongAgentDep = Annotated[object, Depends(get_biz_mong_agent)]
