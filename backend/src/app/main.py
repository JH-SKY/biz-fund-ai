# src/app/main.py
"""FastAPI 앱 인스턴스 생성 및 전역 설정.

SQLAlchemy mapper 구성을 위해 모든 도메인 모델을 앱 시작 전에 로드한다.
relationship 문자열 참조("ClassName") 해석은 모든 모델이 메모리에 올라온 뒤 이뤄진다.
"""

from contextlib import asynccontextmanager
from typing import Annotated

import src.app.domains.auth.model  # noqa: F401
import src.app.domains.business.model  # noqa: F401
import src.app.domains.chat.model  # noqa: F401
import src.app.domains.diagnosis.model  # noqa: F401
import src.app.domains.notification.model  # noqa: F401
import src.app.domains.policy.model  # noqa: F401
import src.app.domains.system.model  # noqa: F401
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.api.v1.router import api_router
from src.app.core.config import FRONTEND_ORIGINS
from src.app.core.exceptions import (
    BaseAppException,
    base_app_exception_handler,
    request_validation_exception_handler,
)
from src.app.database.postgres.database import get_db
from src.app.worker.scheduler import shutdown_scheduler, start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 수명주기 관리.

    startup  : APScheduler 를 시작하고 일일 정책 동기화 크론 잡을 등록한다.
    shutdown : 실행 중인 배치가 완료되기를 기다리지 않고 스케줄러를 즉시 종료한다.
              (wait=False — 서버 재시작 시 응답 지연 방지)
    """
    await start_scheduler()
    yield
    await shutdown_scheduler()


app = FastAPI(
    title="Biz-Fund-AI API",
    description="소상공인 맞춤형 정책 매칭 및 AI 에이전트 서비스",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(
    RequestValidationError,
    request_validation_exception_handler,
)
app.add_exception_handler(
    BaseAppException,
    base_app_exception_handler,
)


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """500 에러에도 CORS 헤더를 포함시켜 프론트에서 오류를 확인할 수 있게 한다."""
    origin = request.headers.get("origin", "")
    headers = {}
    if origin in FRONTEND_ORIGINS:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers=headers,
    )


app.add_exception_handler(Exception, _unhandled_exception_handler)
app.include_router(api_router)

db_session = Annotated[AsyncSession, Depends(get_db)]


@app.get("/")
async def read_root():
    return {
        "status": "online",
        "message": "Biz-Fund-AI 서버가 정상 작동 중입니다!",
        "version": "0.1.0",
    }


@app.get("/db-check")
async def check_db_connection(db: db_session):
    result = await db.execute(text("SELECT 1"))
    if result:
        return {"status": "success", "message": "Database Connection Verified"}
    return {"status": "fail", "message": "Database Connection Failed"}
