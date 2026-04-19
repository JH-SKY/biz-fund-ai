"""businesses 테이블에 국세청 API 검증 결과 컬럼 추가

국세청 상태(계속사업자/휴업/폐업), is_biz_no_verified 플래그, tax_type,
biz_verified_at 을 추가하여 불필요한 API 재호출을 방지하고
AI 진단 시 폐업/휴업 사업자를 필터링할 수 있게 한다.

Revision ID: b5c6d7e8f9a0
Revises: 1db6b0205160
Create Date: 2026-04-19 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b5c6d7e8f9a0"
down_revision: Union[str, Sequence[str], None] = "1db6b0205160"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "businesses",
        sa.Column(
            "is_biz_no_verified",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment="국세청 API 진위 확인 완료 여부 (True 이면 재호출 불필요)",
        ),
    )
    op.add_column(
        "businesses",
        sa.Column(
            "biz_verified_status",
            sa.String(length=30),
            nullable=True,
            comment="국세청 반환 사업자 상태 (계속사업자 | 휴업자 | 폐업자 등)",
        ),
    )
    op.add_column(
        "businesses",
        sa.Column(
            "tax_type",
            sa.String(length=50),
            nullable=True,
            comment="국세청 반환 과세 유형 (부가가치세 일반과세자 등)",
        ),
    )
    op.add_column(
        "businesses",
        sa.Column(
            "biz_verified_at",
            sa.TIMESTAMP(),
            nullable=True,
            comment="국세청 API 마지막 검증 시각 (UTC)",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("businesses", "biz_verified_at")
    op.drop_column("businesses", "tax_type")
    op.drop_column("businesses", "biz_verified_status")
    op.drop_column("businesses", "is_biz_no_verified")
