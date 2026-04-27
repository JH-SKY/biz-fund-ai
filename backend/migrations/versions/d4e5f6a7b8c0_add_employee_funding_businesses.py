"""add employee_count and funding_purpose to businesses

Revision ID: d4e5f6a7b8c0
Revises: c3d4e5f6a8b9
Create Date: 2026-04-27 15:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c0"
down_revision: Union[str, None] = "c3d4e5f6a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "businesses",
        sa.Column(
            "employee_count",
            sa.Integer(),
            nullable=True,
            comment="온보딩/프로필의 상시 근로자 수(대략)",
        ),
    )
    op.add_column(
        "businesses",
        sa.Column(
            "funding_purpose",
            sa.String(length=32),
            nullable=True,
            comment="자금 용도: FACILITY|OPERATING|WORKING|MIXED|UNSURE",
        ),
    )


def downgrade() -> None:
    op.drop_column("businesses", "funding_purpose")
    op.drop_column("businesses", "employee_count")
