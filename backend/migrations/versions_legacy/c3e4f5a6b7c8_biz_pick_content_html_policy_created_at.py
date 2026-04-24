"""biz_picks content_md -> content_html, policies.created_at

Revision ID: c3e4f5a6b7c8
Revises: f8a2c1d0e9ab
Create Date: 2026-04-02

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3e4f5a6b7c8"
down_revision: Union[str, Sequence[str], None] = "f8a2c1d0e9ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE biz_picks RENAME COLUMN content_md TO content_html"))
    op.add_column(
        "policies",
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="등록 일시",
        ),
    )


def downgrade() -> None:
    op.drop_column("policies", "created_at")
    op.execute(sa.text("ALTER TABLE biz_picks RENAME COLUMN content_html TO content_md"))
