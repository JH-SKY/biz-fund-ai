"""add ksic_name to businesses

Revision ID: c3d4e5f6a8b9
Revises: b2c3d4e5f6a7
Create Date: 2026-04-27 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a8b9"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "businesses",
        sa.Column(
            "ksic_name",
            sa.String(length=200),
            nullable=True,
            comment="KSIC 세세분류 표시명 (예: 한식 일반 음식점업)",
        ),
    )


def downgrade() -> None:
    op.drop_column("businesses", "ksic_name")
