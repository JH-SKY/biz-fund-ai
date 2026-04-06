# src/app/database/postgres/database.py
import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# 1. 환경 변수 로드 (준비물):
# - .env 파일의 DATABASE_URL(보안 정보)을 시스템 환경 변수로 등록
load_dotenv()
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# 2. 비동기 엔진 생성 (고속도로):
# - asyncpg 드라이버를 사용한 PostgreSQL 비동기 연결 수행
# - echo=True: 실행되는 SQL 쿼리를 터미널에 실시간 기록 (디버깅 용도)
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)

# 3. 세션 팩토리 설정 (대화권):
# - AsyncSession 기반의 비동기 세션 생성기 정의
# - autoflush/autocommit 비활성화로 데이터 무결성 제어권 확보
SessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,  #  커밋 후에도 객체 데이터를 유지합니다.
    class_=AsyncSession,
)


# 4. 의존성 주입 함수 (설계 의도):
# - 각 API 요청 시 독립적인 DB 세션을 할당하고 작업 종료 후 자동 회수
# - FastAPI의 Depends() 구문과 결합하여 리소스 누수 방지
async def get_db():
    async with SessionLocal() as session:
        yield session
