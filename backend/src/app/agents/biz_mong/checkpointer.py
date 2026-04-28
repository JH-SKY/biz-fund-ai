"""LangGraph checkpointer bootstrap helpers."""

from __future__ import annotations

import logging
import os
from contextlib import AbstractAsyncContextManager
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

logger = logging.getLogger(__name__)

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
    """Initialize a singleton checkpointer for BizMong graphs.

    Production prefers postgres, but if the runtime lacks the required psycopg /
    libpq pieces we gracefully fall back to in-memory mode instead of taking the
    whole chat service down.
    """
    global _checkpointer, _checkpointer_ctx

    if _checkpointer is not None:
        return _checkpointer

    if LANGGRAPH_CHECKPOINTER_BACKEND == "memory":
        _checkpointer = InMemorySaver()
        return _checkpointer

    if LANGGRAPH_CHECKPOINTER_BACKEND != "postgres":
        logger.warning(
            "Unsupported LANGGRAPH_CHECKPOINTER_BACKEND=%s; falling back to memory.",
            LANGGRAPH_CHECKPOINTER_BACKEND,
        )
        _checkpointer = InMemorySaver()
        return _checkpointer

    if not LANGGRAPH_CHECKPOINTER_DSN:
        logger.warning(
            "LANGGRAPH_CHECKPOINTER_DSN is missing; falling back to memory checkpointer."
        )
        _checkpointer = InMemorySaver()
        return _checkpointer

    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    except Exception as exc:
        logger.warning(
            "Postgres checkpointer import failed; falling back to memory. reason=%s",
            exc,
        )
        _checkpointer = InMemorySaver()
        return _checkpointer

    try:
        _checkpointer_ctx = AsyncPostgresSaver.from_conn_string(
            LANGGRAPH_CHECKPOINTER_DSN
        )
        _checkpointer = await _checkpointer_ctx.__aenter__()

        setup = getattr(_checkpointer, "setup", None)
        if callable(setup):
            maybe_awaitable = setup()
            if maybe_awaitable is not None:
                await maybe_awaitable

        return _checkpointer
    except Exception as exc:
        logger.warning(
            "Postgres checkpointer initialization failed; falling back to memory. reason=%s",
            exc,
        )
        if _checkpointer_ctx is not None:
            try:
                await _checkpointer_ctx.__aexit__(None, None, None)
            except Exception:
                pass
            _checkpointer_ctx = None
        _checkpointer = InMemorySaver()
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
