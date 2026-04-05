"""채팅 도메인 의존성 주입(Depends)."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.database.postgres.database import get_db
from src.app.domains.chat.interfaces import MockLLMEngine
from src.app.domains.chat.repository import ChatRepository
from src.app.domains.chat.service import ChatService
from src.app.api.deps.policy_deps import get_policy_service
from src.app.domains.policy.service import PolicyService


async def get_chat_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChatRepository:
    return ChatRepository(db)


async def get_chat_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    repo: Annotated[ChatRepository, Depends(get_chat_repo)],
    policy_service: Annotated[PolicyService, Depends(get_policy_service)],
) -> ChatService:
    llm_engine = MockLLMEngine()
    return ChatService(
        session=db,
        repo=repo,
        policy_service=policy_service,
        llm_engine=llm_engine,
    )


ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
