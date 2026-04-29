# src/app/agents/biz_mong/checkpointer.py
"""LangGraph 체크포인터(Checkpointer) 초기화 및 싱글턴 관리.

[체크포인터 역할]
LangGraph 체크포인터는 각 thread_id(=room_id) 별로 대화 상태(State)를
영속 저장해 세션 간 대화 히스토리를 유지하는 역할을 한다.

[백엔드 선택 전략]
- 운영(production) 환경: PostgreSQL 체크포인터 사용 (LANGGRAPH_CHECKPOINTER_BACKEND=postgres)
- 개발(development) 환경: InMemorySaver 사용 (재시작 시 상태 초기화됨)
- PostgreSQL 연결/임포트 실패 시: 자동으로 InMemorySaver 로 폴백
  → 채팅 서비스 전체가 중단되지 않도록 graceful degradation 구현
"""

from __future__ import annotations

import logging
import os
from contextlib import AbstractAsyncContextManager
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

logger = logging.getLogger(__name__)

# 환경 변수로 체크포인터 백엔드를 결정 (기본값: 운영=postgres, 개발=memory)
APP_ENV = os.getenv("APP_ENV", "development")
LANGGRAPH_CHECKPOINTER_BACKEND = os.getenv(
    "LANGGRAPH_CHECKPOINTER_BACKEND",
    "postgres" if APP_ENV == "production" else "memory",
).strip().lower()
LANGGRAPH_CHECKPOINTER_DSN = os.getenv(
    "LANGGRAPH_CHECKPOINTER_DSN",
    os.getenv("DATABASE_URL", ""),
)

# 프로세스 전체에서 공유되는 싱글턴 체크포인터
_checkpointer: BaseCheckpointSaver | None = None
# PostgreSQL 비동기 컨텍스트 관리자 (애플리케이션 종료 시 정리용)
_checkpointer_ctx: AbstractAsyncContextManager[Any] | None = None


async def initialize_langgraph_checkpointer() -> BaseCheckpointSaver:
    """비즈몽 그래프용 싱글턴 체크포인터를 초기화한다.

    [로직 순서]
    1. 이미 초기화된 경우 바로 반환 (중복 초기화 방지)
    2. BACKEND=memory → InMemorySaver 반환
    3. BACKEND=postgres 인데 DSN 없음 → memory 폴백
    4. asyncpg/psycopg 라이브러리 임포트 실패 → memory 폴백
    5. PostgreSQL 연결/setup 실패 → memory 폴백
    """
    global _checkpointer, _checkpointer_ctx

    # [1] 중복 초기화 방지
    if _checkpointer is not None:
        return _checkpointer

    # [2] 메모리 백엔드 명시적 요청
    if LANGGRAPH_CHECKPOINTER_BACKEND == "memory":
        _checkpointer = InMemorySaver()
        return _checkpointer

    # 지원되지 않는 백엔드 값이면 메모리로 폴백
    if LANGGRAPH_CHECKPOINTER_BACKEND != "postgres":
        logger.warning(
            "Unsupported LANGGRAPH_CHECKPOINTER_BACKEND=%s; falling back to memory.",
            LANGGRAPH_CHECKPOINTER_BACKEND,
        )
        _checkpointer = InMemorySaver()
        return _checkpointer

    # [3] DSN 누락 → 폴백
    if not LANGGRAPH_CHECKPOINTER_DSN:
        logger.warning(
            "LANGGRAPH_CHECKPOINTER_DSN is missing; falling back to memory checkpointer."
        )
        _checkpointer = InMemorySaver()
        return _checkpointer

    # [4] PostgreSQL 라이브러리 임포트 시도
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    except Exception as exc:
        logger.warning(
            "Postgres checkpointer import failed; falling back to memory. reason=%s",
            exc,
        )
        _checkpointer = InMemorySaver()
        return _checkpointer

    # [5] 실제 PostgreSQL 연결 시도
    try:
        _checkpointer_ctx = AsyncPostgresSaver.from_conn_string(
            LANGGRAPH_CHECKPOINTER_DSN
        )
        _checkpointer = await _checkpointer_ctx.__aenter__()

        # 체크포인터 테이블 생성 (이미 존재하면 무시)
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
    """초기화된 싱글턴 체크포인터를 반환한다.

    initialize_langgraph_checkpointer() 호출 전에 사용하면 RuntimeError 발생.
    """
    if _checkpointer is None:
        raise RuntimeError("LangGraph checkpointer has not been initialized yet.")
    return _checkpointer


async def shutdown_langgraph_checkpointer() -> None:
    """애플리케이션 종료 시 싱글턴 체크포인터를 정리한다.

    PostgreSQL 체크포인터는 비동기 컨텍스트 매니저를 정상 종료해야
    DB 연결 풀이 제대로 반환된다.
    """
    global _checkpointer, _checkpointer_ctx

    if _checkpointer_ctx is not None:
        await _checkpointer_ctx.__aexit__(None, None, None)
        _checkpointer_ctx = None

    _checkpointer = None


def is_postgres_checkpointer_required() -> bool:
    """현재 환경에서 PostgreSQL 체크포인터가 필요한지 여부를 반환한다."""
    return APP_ENV == "production" or LANGGRAPH_CHECKPOINTER_BACKEND == "postgres"
