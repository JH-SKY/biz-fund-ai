"""add ai metrics to chat_logs and correction_notes table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-26 21:00:00.000000

변경 내용:
  1. chat_logs에 AI 운영 메트릭 컬럼 4개 추가
     - tokens_in:        입력 토큰 수
     - tokens_out:       출력 토큰 수
     - model_name:       사용된 LLM 모델명
     - response_time_ms: 응답 소요시간 (ms)
  2. correction_notes 테이블 신규 생성
     - 관리자가 피드백에 대해 작성하는 정정 노트를 영속화
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. chat_logs AI 메트릭 컬럼 추가 ────────────────────────────────────
    op.add_column(
        "chat_logs",
        sa.Column("tokens_in", sa.Integer(), nullable=True, comment="입력 토큰 수"),
    )
    op.add_column(
        "chat_logs",
        sa.Column("tokens_out", sa.Integer(), nullable=True, comment="출력 토큰 수"),
    )
    op.add_column(
        "chat_logs",
        sa.Column(
            "model_name",
            sa.String(100),
            nullable=True,
            comment="사용된 LLM 모델명 (gpt-4o, gpt-4o-mini 등)",
        ),
    )
    op.add_column(
        "chat_logs",
        sa.Column(
            "response_time_ms",
            sa.Integer(),
            nullable=True,
            comment="응답 소요시간 (ms)",
        ),
    )

    # ── 2. correction_notes 테이블 생성 ─────────────────────────────────────
    op.create_table(
        "correction_notes",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="정정 노트 고유 식별자",
        ),
        sa.Column(
            "feedback_id",
            UUID(as_uuid=True),
            sa.ForeignKey("chat_logs.id", ondelete="CASCADE"),
            nullable=False,
            comment="대상 피드백 ChatLog ID",
        ),
        sa.Column(
            "created_by_admin_id",
            UUID(as_uuid=True),
            sa.ForeignKey("admins.id", ondelete="SET NULL"),
            nullable=True,
            comment="작성 관리자 ID",
        ),
        sa.Column(
            "question_pattern",
            sa.Text(),
            nullable=True,
            comment="정정이 필요한 질문 패턴",
        ),
        sa.Column(
            "expected_answer",
            sa.Text(),
            nullable=True,
            comment="기대하는 정답/답변",
        ),
        sa.Column(
            "applies_to_agent",
            sa.String(50),
            nullable=True,
            comment="적용 대상 에이전트 (rag / diagnosis / simulator 등)",
        ),
        sa.Column(
            "extra",
            JSONB,
            nullable=True,
            comment="추가 메타데이터 (JSON)",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="활성 여부 (비활성화된 정정 노트는 에이전트 적용 제외)",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="작성 일시",
        ),
    )
    op.create_index(
        "ix_correction_notes_feedback_id",
        "correction_notes",
        ["feedback_id"],
    )
    op.create_index(
        "ix_correction_notes_created_by",
        "correction_notes",
        ["created_by_admin_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_correction_notes_created_by", table_name="correction_notes")
    op.drop_index("ix_correction_notes_feedback_id", table_name="correction_notes")
    op.drop_table("correction_notes")
    op.drop_column("chat_logs", "response_time_ms")
    op.drop_column("chat_logs", "model_name")
    op.drop_column("chat_logs", "tokens_out")
    op.drop_column("chat_logs", "tokens_in")
