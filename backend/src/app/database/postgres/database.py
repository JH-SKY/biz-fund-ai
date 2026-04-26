# src/app/database/postgres/database.py
import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# 1. 환경 변수 로드 (준비물):
# - .env 파일의 DATABASE_URL(보안 정보)을 시스템 환경 변수로 등록
load_dotenv()
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() == "true"

# 2. 비동기 엔진 생성 (고속도로):
# - asyncpg 드라이버를 사용한 PostgreSQL 비동기 연결 수행
# - echo=True: 실행되는 SQL 쿼리를 터미널에 실시간 기록 (디버깅 용도)
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=SQL_ECHO,
    pool_pre_ping=True,
    pool_recycle=300,      # Supabase pooler 기본 idle 타임아웃(5분) 이내로 재생성
    pool_size=5,
    max_overflow=10,
    connect_args={
        # pgbouncer(Supabase pooler) 환경에서 prepared statement 충돌 방지
        "prepared_statement_cache_size": 0,
        "server_settings": {"application_name": "biz-fund-ai"},
    },
)

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
# - Supabase pgbouncer 환경에서 idle timeout으로 커넥션이 끊긴 채 pool에
#   남아있을 수 있다. pool_pre_ping이 대부분을 잡지만, ping 직후 연결이
#   끊기는 race condition이 남는다. close/rollback 실패는 이미 버려진
#   커넥션에 대한 정리 실패이므로 suppress 처리한다.
async def get_db():
    session = SessionLocal()
    try:
        yield session
    except Exception:
        try:
            await session.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            await session.close()
        except Exception:
            pass
