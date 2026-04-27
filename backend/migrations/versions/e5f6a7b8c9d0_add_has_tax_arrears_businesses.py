"""add has_tax_arrears to businesses

(employee_count, funding_purpose 는 d4e5f6a7b8c0 에서 이미 추가됨)

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c0
Create Date: 2026-04-28 10:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "businesses",
        sa.Column(
            "has_tax_arrears",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment="온보딩/프로필: 세금 체납(미완납) 여부 — 추천·진단 시 참고",
        ),
    )


def downgrade() -> None:
    op.drop_column("businesses", "has_tax_arrears")
