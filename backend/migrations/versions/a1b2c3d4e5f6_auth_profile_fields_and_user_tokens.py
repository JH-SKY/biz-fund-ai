"""users profile fields + user_tokens table

Revision ID: a1b2c3d4e5f6
Revises: c3e4f5a6b7c8
Create Date: 2026-04-02

변경 내용
- users: interest_sectors(JSONB), military_service(VARCHAR), is_non_major(BOOLEAN), tech_stack(JSONB) 추가
- user_tokens: Refresh Token 무효화를 위한 신규 테이블 생성
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "c3e4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users 프로필 확장 컬럼
    op.add_column(
        "users",
        sa.Column(
            "interest_sectors",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="관심 업종/분야 리스트 (JSONB array)",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "military_service",
            sa.String(length=30),
            nullable=True,
            comment="군필 여부 (COMPLETED / EXEMPTED / IN_PROGRESS / NA)",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "is_non_major",
            sa.Boolean(),
            nullable=True,
            comment="비전공 창업자 여부",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "tech_stack",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="기술 스택 리스트 (JSONB array)",
        ),
    )

    # 2. user_tokens (Refresh Token 저장·무효화)
    op.create_table(
        "user_tokens",
        sa.Column("id", sa.UUID(), nullable=False, comment="토큰 레코드 식별자"),
        sa.Column("user_id", sa.UUID(), nullable=False, comment="소유 사용자 ID (users.id)"),
        sa.Column(
            "token",
            sa.Text(),
            nullable=False,
            comment="opaque Refresh Token 값 (SHA-256 다이제스트 저장)",
        ),
        sa.Column(
            "expires_at",
            sa.TIMESTAMP(),
            nullable=False,
            comment="토큰 만료 일시",
        ),
        sa.Column(
            "is_revoked",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment="로그아웃 등으로 무효화 여부",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="발급 일시",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )


def downgrade() -> None:
    op.drop_table("user_tokens")
    op.drop_column("users", "tech_stack")
    op.drop_column("users", "is_non_major")
    op.drop_column("users", "military_service")
    op.drop_column("users", "interest_sectors")
