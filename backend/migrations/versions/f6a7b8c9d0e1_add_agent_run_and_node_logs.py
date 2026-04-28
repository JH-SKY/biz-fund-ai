"""add agent run and node observability logs

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-04-28 20:40:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_run_logs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
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
            "user_message_log_id",
            UUID(as_uuid=True),
            sa.ForeignKey("chat_logs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "assistant_message_log_id",
            UUID(as_uuid=True),
            sa.ForeignKey("chat_logs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("route_intent", sa.String(length=50), nullable=True),
        sa.Column("final_agent", sa.String(length=50), nullable=True),
        sa.Column("prompt_version", sa.String(length=100), nullable=True),
        sa.Column("graph_version", sa.String(length=100), nullable=True),
        sa.Column("rag_strategy_version", sa.String(length=100), nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'SUCCESS'"),
        ),
        sa.Column("fallback_mode", sa.String(length=50), nullable=True),
        sa.Column("fallback_reason", sa.Text(), nullable=True),
        sa.Column("question_preview", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("total_latency_ms", sa.Integer(), nullable=True),
        sa.Column("first_token_latency_ms", sa.Integer(), nullable=True),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        sa.Column("total_cost_usd", sa.Numeric(12, 8), nullable=True),
        sa.Column("rag_hit_count", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("extra", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_agent_run_logs_created_at", "agent_run_logs", ["created_at"])
    op.create_index("ix_agent_run_logs_room_id", "agent_run_logs", ["room_id"])
    op.create_index("ix_agent_run_logs_route_intent", "agent_run_logs", ["route_intent"])
    op.create_index("ix_agent_run_logs_final_agent", "agent_run_logs", ["final_agent"])
    op.create_index("ix_agent_run_logs_status", "agent_run_logs", ["status"])

    op.create_table(
        "agent_node_logs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("agent_run_logs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("node_name", sa.String(length=100), nullable=False),
        sa.Column(
            "sequence",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'SUCCESS'"),
        ),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(12, 8), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_agent_node_logs_run_id", "agent_node_logs", ["run_id"])
    op.create_index("ix_agent_node_logs_node_name", "agent_node_logs", ["node_name"])
    op.create_index("ix_agent_node_logs_status", "agent_node_logs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_agent_node_logs_status", table_name="agent_node_logs")
    op.drop_index("ix_agent_node_logs_node_name", table_name="agent_node_logs")
    op.drop_index("ix_agent_node_logs_run_id", table_name="agent_node_logs")
    op.drop_table("agent_node_logs")

    op.drop_index("ix_agent_run_logs_status", table_name="agent_run_logs")
    op.drop_index("ix_agent_run_logs_final_agent", table_name="agent_run_logs")
    op.drop_index("ix_agent_run_logs_route_intent", table_name="agent_run_logs")
    op.drop_index("ix_agent_run_logs_room_id", table_name="agent_run_logs")
    op.drop_index("ix_agent_run_logs_created_at", table_name="agent_run_logs")
    op.drop_table("agent_run_logs")
