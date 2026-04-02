"""biz_pick thumbnail_url and is_published

Revision ID: f8a2c1d0e9ab
Revises: da6e1e2712e6
Create Date: 2026-04-02

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f8a2c1d0e9ab"
down_revision: Union[str, Sequence[str], None] = "984ee159a4ca"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "biz_picks",
        sa.Column("thumbnail_url", sa.Text(), nullable=True, comment="썸네일 이미지 URL"),
    )
    op.add_column(
        "biz_picks",
        sa.Column(
            "is_published",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
            comment="발행(공개) 여부",
        ),
    )


def downgrade() -> None:
    op.drop_column("biz_picks", "is_published")
    op.drop_column("biz_picks", "thumbnail_url")
