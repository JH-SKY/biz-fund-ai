"""LangGraph checkpointer bootstrap helpers."""

from __future__ import annotations

import os
from contextlib import AbstractAsyncContextManager
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

APP_ENV = os.getenv("APP_ENV", "development")
LANGGRAPH_CHECKPOINTER_BACKEND = os.getenv(
    "LANGGRAPH_CHECKPOINTER_BACKEND",
    "postgres" if APP_ENV == "production" else "memory",
).strip().lower()
LANGGRAPH_CHECKPOINTER_DSN = os.getenv(
    "LANGGRAPH_CHECKPOINTER_DSN",
    os.getenv("DATABASE_URL", ""),
)

_checkpointer: BaseCheckpointSaver | None = None
_checkpointer_ctx: AbstractAsyncContextManager[Any] | None = None


async def initialize_langgraph_checkpointer() -> BaseCheckpointSaver:
    """Initialize a singleton checkpointer for BizMong graphs."""
    global _checkpointer, _checkpointer_ctx

    if _checkpointer is not None:
        return _checkpointer

    if LANGGRAPH_CHECKPOINTER_BACKEND == "memory":
        _checkpointer = InMemorySaver()
        return _checkpointer

    if LANGGRAPH_CHECKPOINTER_BACKEND != "postgres":
        raise RuntimeError(
            f"Unsupported LANGGRAPH_CHECKPOINTER_BACKEND: {LANGGRAPH_CHECKPOINTER_BACKEND}"
        )

    if not LANGGRAPH_CHECKPOINTER_DSN:
        raise RuntimeError("LANGGRAPH_CHECKPOINTER_DSN is required for postgres checkpointer")

    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    except ImportError as exc:
        raise RuntimeError(
            "langgraph-checkpoint-postgres 패키지가 설치되지 않아 postgres checkpointer를 초기화할 수 없습니다."
        ) from exc

    _checkpointer_ctx = AsyncPostgresSaver.from_conn_string(LANGGRAPH_CHECKPOINTER_DSN)
    _checkpointer = await _checkpointer_ctx.__aenter__()

    setup = getattr(_checkpointer, "setup", None)
    if callable(setup):
        maybe_awaitable = setup()
        if maybe_awaitable is not None:
            await maybe_awaitable

    return _checkpointer


def get_langgraph_checkpointer() -> BaseCheckpointSaver:
    """Return the initialized singleton checkpointer."""
    if _checkpointer is None:
        raise RuntimeError("LangGraph checkpointer has not been initialized yet.")
    return _checkpointer


async def shutdown_langgraph_checkpointer() -> None:
    """Dispose the singleton checkpointer on shutdown."""
    global _checkpointer, _checkpointer_ctx

    if _checkpointer_ctx is not None:
        await _checkpointer_ctx.__aexit__(None, None, None)
        _checkpointer_ctx = None

    _checkpointer = None


def is_postgres_checkpointer_required() -> bool:
    return APP_ENV == "production" or LANGGRAPH_CHECKPOINTER_BACKEND == "postgres"
