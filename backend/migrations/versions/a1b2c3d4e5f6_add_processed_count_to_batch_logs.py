"""add processed_count to batch_logs

Revision ID: a1b2c3d4e5f6
Revises: c7143fb55e37
Create Date: 2026-04-25 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "c7143fb55e37"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "batch_logs",
        sa.Column(
            "processed_count",
            sa.Integer(),
            nullable=True,
            comment="현재까지 처리 완료된 건수 (실행 중 주기적 갱신)",
        ),
    )


def downgrade() -> None:
    op.drop_column("batch_logs", "processed_count")
