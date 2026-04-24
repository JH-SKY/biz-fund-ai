"""pgvector 익스텐션 활성화 및 policy_chunks 테이블 생성.

이전 두 HEAD(b5c6d7e8f9a0, e07de3ca211b)를 c1d2e3f4a5b6으로 이미 병합했으므로
이 마이그레이션은 c1d2e3f4a5b6을 단일 부모로 가집니다.

변경 사항:
  1. CREATE EXTENSION IF NOT EXISTS vector  — pgvector 익스텐션 활성화
  2. policies.content_hash 컬럼 추가         — 임베딩 변경 감지용 SHA-256 해시
  3. policy_chunks 테이블 생성               — 청크 텍스트 + 1536차원 임베딩 벡터

Revision ID: d1e2f3a4b5c6
Revises: c1d2e3f4a5b6
Create Date: 2026-04-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # [1] pgvector PostgreSQL 익스텐션 — 벡터 타입 및 연산자 활성화
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # [2] policies 테이블에 content_hash 컬럼 추가
    op.add_column(
        "policies",
        sa.Column(
            "content_hash",
            sa.String(64),
            nullable=True,
            comment="content_raw의 SHA-256 해시 (임베딩 변경 감지용)",
        ),
    )
    op.create_index("ix_policies_content_hash", "policies", ["content_hash"])

    # [3] policy_chunks 테이블 생성 — 청크 텍스트 + 벡터
    op.create_table(
        "policy_chunks",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            comment="청크 고유 식별자",
        ),
        sa.Column(
            "policy_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("policies.id", ondelete="CASCADE"),
            nullable=False,
            comment="원본 정책 ID (policies.id 참조)",
        ),
        sa.Column(
            "chunk_index",
            sa.Integer(),
            nullable=False,
            comment="정책 내 청크 순서 (0-based)",
        ),
        sa.Column(
            "chunk_type",
            sa.String(100),
            nullable=False,
            comment="섹션 종류 (지원대상/지원내용/신청방법 등 또는 본문_N)",
        ),
        sa.Column(
            "chunk_text",
            sa.Text(),
            nullable=False,
            comment="청크 원문 텍스트",
        ),
        sa.Column(
            "embedding",
            Vector(1536),
            nullable=True,
            comment="OpenAI text-embedding-3-small 벡터 (1536차원)",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="청크 생성 시점",
        ),
    )
    op.create_index("ix_policy_chunks_policy_id", "policy_chunks", ["policy_id"])


def downgrade() -> None:
    op.drop_index("ix_policy_chunks_policy_id", table_name="policy_chunks")
    op.drop_table("policy_chunks")
    op.drop_index("ix_policies_content_hash", table_name="policies")
    op.drop_column("policies", "content_hash")
    # 익스텐션은 다른 데이터에 영향을 줄 수 있으므로 downgrade에서 제거하지 않습니다.
