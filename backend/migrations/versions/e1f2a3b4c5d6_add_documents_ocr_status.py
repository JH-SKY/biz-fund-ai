"""documents 테이블에 ocr_status 컬럼 추가

기존 documents 행이 있어도 NOT NULL + server_default='PENDING' 으로
한 번에 백필되므로 nullable=True 는 불필요(앱 일관성 유지).

Revision ID: e1f2a3b4c5d6
Revises: b2c3d4e5f6a7
Create Date: 2026-04-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "ocr_status",
            sa.String(length=20),
            server_default=sa.text("'PENDING'"),
            nullable=False,
            comment="OCR 분석 진행 상태 (PENDING | COMPLETED | FAILED)",
        ),
    )


def downgrade() -> None:
    op.drop_column("documents", "ocr_status")
