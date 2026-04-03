"""users.deleted_at — 탈퇴 시각(5년 보관·물리 파기 근거)

Revision ID: b2c3d4e5f6a7
Revises: 17124055eb37
Create Date: 2026-04-03

변경 내용
- users: deleted_at(TIMESTAMP, nullable) 추가 — Soft Delete 시각 기록
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "17124055eb37"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "deleted_at",
            sa.TIMESTAMP(),
            nullable=True,
            comment="탈퇴 시각(UTC). 도메인 규칙 1.2: 최대 5년 보관 후 물리 삭제 판단 기준",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "deleted_at")
