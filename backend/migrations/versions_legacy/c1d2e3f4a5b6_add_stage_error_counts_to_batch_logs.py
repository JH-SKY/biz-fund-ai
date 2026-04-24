"""batch_logs에 단계별 에러 카운트 컬럼 추가

두 개의 병렬 head(b5c6d7e8f9a0, e07de3ca211b)를 merge하고
api_error_count / parse_error_count / analysis_error_count / db_fail_count 컬럼을 추가한다.

Revision ID: c1d2e3f4a5b6
Revises: b5c6d7e8f9a0, e07de3ca211b
Create Date: 2026-04-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = ("b5c6d7e8f9a0", "e07de3ca211b")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "batch_logs",
        sa.Column(
            "api_error_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
            comment="API 페이지 요청 자체 실패 건수",
        ),
    )
    op.add_column(
        "batch_logs",
        sa.Column(
            "parse_error_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
            comment="첨부파일 텍스트 추출 실패 건수",
        ),
    )
    op.add_column(
        "batch_logs",
        sa.Column(
            "analysis_error_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
            comment="AI 분석·검증 실패 건수",
        ),
    )
    op.add_column(
        "batch_logs",
        sa.Column(
            "db_fail_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
            comment="DB upsert 실패 건수",
        ),
    )
    op.alter_column(
        "batch_logs",
        "fail_count",
        comment="실패 건수 (api+parse+analysis+db 합산)",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.drop_column("batch_logs", "db_fail_count")
    op.drop_column("batch_logs", "analysis_error_count")
    op.drop_column("batch_logs", "parse_error_count")
    op.drop_column("batch_logs", "api_error_count")
