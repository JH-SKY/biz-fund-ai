"""businesses.biz_verified_at 컬럼을 TIMESTAMPTZ로 변경

timezone-aware datetime(UTC)을 삽입할 때 asyncpg가 TIMESTAMP WITHOUT TIME ZONE
컬럼을 거부하는 문제를 해결하기 위해 TIMESTAMP(timezone=True)로 변경한다.

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-04-23 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e2f3a4b5c6d7"
down_revision: Union[str, Sequence[str], None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """TIMESTAMP → TIMESTAMP WITH TIME ZONE."""
    op.alter_column(
        "businesses",
        "biz_verified_at",
        type_=sa.TIMESTAMP(timezone=True),
        existing_type=sa.TIMESTAMP(timezone=False),
        existing_nullable=True,
        postgresql_using="biz_verified_at AT TIME ZONE 'UTC'",
    )


def downgrade() -> None:
    """TIMESTAMP WITH TIME ZONE → TIMESTAMP WITHOUT TIME ZONE."""
    op.alter_column(
        "businesses",
        "biz_verified_at",
        type_=sa.TIMESTAMP(timezone=False),
        existing_type=sa.TIMESTAMP(timezone=True),
        existing_nullable=True,
        postgresql_using="biz_verified_at AT TIME ZONE 'UTC'",
    )
