from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from src.app.domains.chat.service import ChatService


class _FakeChatRepo:
    def __init__(self, closed_count: int) -> None:
        self.closed_count = closed_count
        self.cutoff: datetime | None = None

    async def close_inactive_chat_rooms(self, cutoff: datetime) -> int:
        self.cutoff = cutoff
        return self.closed_count


@pytest.mark.asyncio
async def test_auto_close_inactive_sessions_commits_when_rooms_closed():
    repo = _FakeChatRepo(closed_count=2)
    session = AsyncMock()
    svc = ChatService(
        session=session,
        repo=repo,
        policy_service=AsyncMock(),
        llm_engine=AsyncMock(),
    )

    closed_count = await svc.auto_close_inactive_sessions(inactive_hours=12)

    assert closed_count == 2
    assert repo.cutoff is not None
    assert repo.cutoff.tzinfo == timezone.utc
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_auto_close_inactive_sessions_skips_commit_when_nothing_closed():
    repo = _FakeChatRepo(closed_count=0)
    session = AsyncMock()
    svc = ChatService(
        session=session,
        repo=repo,
        policy_service=AsyncMock(),
        llm_engine=AsyncMock(),
    )

    closed_count = await svc.auto_close_inactive_sessions()

    assert closed_count == 0
    session.commit.assert_not_awaited()
