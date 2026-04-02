import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# 1. 환경 변수 로드 (준비물):
# - 프로젝트 루트의 .env 파일을 읽어 실무 보안을 강화합니다.
import os
from dotenv import load_dotenv

load_dotenv()

# 2. 메타데이터 연결 (개념 연결):
# - 우리가 앞으로 만들 모든 모델의 부모(Base)를 가져와 감시 대상으로 등록합니다.
# - 각 도메인 model.py를 명시적으로 import해야 Alembic autogenerate가 테이블을 인식한다.
from src.app.database.postgres.base import Base
from src.app.domains.auth.model import (  # noqa: F401
    Admin,
    AdminAuditLog,
    User,
    UserToken,
)
from src.app.domains.business.model import (  # noqa: F401
    Application,
    Business,
    BusinessFinancialSnapshot,
    Document,
)
from src.app.domains.chat.model import ChatLog, ChatRoom  # noqa: F401
from src.app.domains.diagnosis.model import MatchLog, SimulationLog  # noqa: F401
from src.app.domains.notification.model import Notification  # noqa: F401
from src.app.domains.policy.model import BizPick, Policy  # noqa: F401
from src.app.domains.system.model import BatchLog, LeadRequest  # noqa: F401

config = context.config
target_metadata = Base.metadata

# 3. 주소 주입 (설계 의도):
# - .env의 DATABASE_URL을 알렘빅 설정에 동적으로 주입합니다.
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# 4. 비동기 마이그레이션 실행 함수 (흐름 파악):
async def run_migrations_online():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


# 5. 실행 로직 분기 (설계 의도):
# - 오프라인/온라인 모드에 맞춰 마이그레이션을 안전하게 수행합니다.
if context.is_offline_mode():

    def run_migrations_offline():
        url = config.get_main_option("sqlalchemy.url")
        context.configure(
            url=url,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
        )
        with context.begin_transaction():
            context.run_migrations()

    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
