# src/app/main.py
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# SQLAlchemy mapper 구성을 위해 모든 도메인 모델을 앱 시작 전에 로드한다.
# relationship 문자열 참조("ClassName") 해석은 모든 모델이 메모리에 올라온 뒤 이뤄진다.
import src.app.domains.auth.model  # noqa: F401
import src.app.domains.business.model  # noqa: F401
import src.app.domains.policy.model  # noqa: F401
import src.app.domains.diagnosis.model  # noqa: F401
import src.app.domains.chat.model  # noqa: F401
import src.app.domains.notification.model  # noqa: F401
import src.app.domains.system.model  # noqa: F401

from src.app.api.v1.router import api_router
from src.app.core.exceptions import request_validation_exception_handler
from src.app.database.postgres.database import get_db

app = FastAPI(
    title="Biz-Fund-AI API",
    description="소상공인 맞춤형 정책 매칭 및 AI 에이전트 서비스",
    version="0.1.0",
)
app.add_exception_handler(
    RequestValidationError,
    request_validation_exception_handler,
)
app.include_router(api_router)

db_session = Annotated[AsyncSession, Depends(get_db)]


# 1. 앱 초기화 및 메타데이터 설정:
@app.get("/")
async def read_root():
    return {
        "status": "online",
        "message": "Biz-Fund-AI 서버가 정상 작동 중입니다!",
        "version": "0.1.0",
    }


# 2. DB 연결 상태 점검 (흐름 파악)
@app.get("/db-check")
async def check_db_connection(db: db_session):
    # 3. 테스트 쿼리 실행 (흐름 파악)
    result = await db.execute(text("SELECT 1"))

    # 4. 응답 처리 (설계 의도):
    if result:
        return {"status": "success", "message": "Database Connection Verified"}
    return {"status": "fail", "message": "Database Connection Failed"}
