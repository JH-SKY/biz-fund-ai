"""business_financial_snapshots: operating_profit, capital, is_active 추가 +
(business_id, snapshot_year) UniqueConstraint 추가.
documents: ocr_result(JSONB), is_active 추가.

DB가 비어있는 초기 상태이므로 모든 신규 컬럼을 NOT NULL + server_default 로 엄격하게 설정.

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-04-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── business_financial_snapshots ──────────────────────────────────────

    op.add_column(
        "business_financial_snapshots",
        sa.Column(
            "operating_profit",
            sa.BigInteger(),
            nullable=True,
            comment="영업이익 (원, 음수 가능) — API 명세서 #4·#5 대응",
        ),
    )
    op.add_column(
        "business_financial_snapshots",
        sa.Column(
            "capital",
            sa.BigInteger(),
            nullable=True,
            comment="자본금 (원) — API 명세서 #4·#5 대응",
        ),
    )
    op.add_column(
        "business_financial_snapshots",
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
            comment="[Soft Delete] 활성 여부 — False 이면 삭제 처리된 레코드",
        ),
    )
    # (business_id, snapshot_year) 복합 유니크 — Service 레이어 중복 체크와 이중 보호
    op.create_unique_constraint(
        "uq_biz_financial_snapshot_year",
        "business_financial_snapshots",
        ["business_id", "snapshot_year"],
    )

    # ── documents ─────────────────────────────────────────────────────────

    op.add_column(
        "documents",
        sa.Column(
            "ocr_result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="OCR 추출 원본 데이터 (COMPLETED 상태일 때 채워짐) — API 명세서 #11",
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
            comment="[Soft Delete] 활성 여부 — False 이면 삭제 처리된 레코드",
        ),
    )


def downgrade() -> None:
    op.drop_column("documents", "is_active")
    op.drop_column("documents", "ocr_result")

    op.drop_constraint(
        "uq_biz_financial_snapshot_year",
        "business_financial_snapshots",
        type_="unique",
    )
    op.drop_column("business_financial_snapshots", "is_active")
    op.drop_column("business_financial_snapshots", "capital")
    op.drop_column("business_financial_snapshots", "operating_profit")
