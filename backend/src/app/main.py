# src/app/main.py
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database.postgres.database import get_db
from typing import Annotated

app = FastAPI(
    title="Biz-Fund-AI API",
    description="소상공인 맞춤형 정책 매칭 및 AI 에이전트 서비스",
    version="0.1.0",
)
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
