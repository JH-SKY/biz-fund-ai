"""add agent cta logs

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-04-29 11:10:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_cta_logs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("agent_run_logs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "room_id",
            UUID(as_uuid=True),
            sa.ForeignKey("chat_rooms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "business_id",
            UUID(as_uuid=True),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "assistant_message_log_id",
            UUID(as_uuid=True),
            sa.ForeignKey("chat_logs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("cta_type", sa.String(length=50), nullable=False),
        sa.Column("target_path", sa.String(length=255), nullable=False),
        sa.Column(
            "ref_policy_id",
            UUID(as_uuid=True),
            sa.ForeignKey("policies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_agent_cta_logs_created_at", "agent_cta_logs", ["created_at"])
    op.create_index("ix_agent_cta_logs_run_id", "agent_cta_logs", ["run_id"])
    op.create_index("ix_agent_cta_logs_cta_type", "agent_cta_logs", ["cta_type"])


def downgrade() -> None:
    op.drop_index("ix_agent_cta_logs_cta_type", table_name="agent_cta_logs")
    op.drop_index("ix_agent_cta_logs_run_id", table_name="agent_cta_logs")
    op.drop_index("ix_agent_cta_logs_created_at", table_name="agent_cta_logs")
    op.drop_table("agent_cta_logs")
