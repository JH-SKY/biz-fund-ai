"""policies 테이블: category, region, support_amount_desc, required_documents, closed_at,
is_active 컬럼 추가.
policy_bookmarks 테이블 신규 생성 (business_id × policy_id N:M 북마크).

Revision ID: a4b5c6d7e8f9
Revises: f2a3b4c5d6e7
Create Date: 2026-04-03
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "a4b5c6d7e8f9"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── policies 컬럼 추가 ──────────────────────────────────────────────────

    # category — 정책 카테고리 (금융/바우처, R&D 등)
    op.add_column(
        "policies",
        sa.Column(
            "category",
            sa.String(50),
            nullable=True,
            comment="정책 카테고리 (금융/바우처, R&D 등)",
        ),
    )

    # region — 지원 대상 지역 (검색·필터용)
    op.add_column(
        "policies",
        sa.Column(
            "region",
            sa.String(100),
            nullable=True,
            comment="지원 대상 지역 (검색·필터용)",
        ),
    )

    # support_amount_desc — 지원 금액 표시 문자열 (예: 최대 400만원)
    op.add_column(
        "policies",
        sa.Column(
            "support_amount_desc",
            sa.String(100),
            nullable=True,
            comment="지원 금액 표시 문자열 (예: 최대 400만원)",
        ),
    )

    # required_documents — 신청 필수 서류 목록 (JSONB 배열)
    op.add_column(
        "policies",
        sa.Column(
            "required_documents",
            JSONB,
            nullable=True,
            comment="신청 필수 서류 목록 (문자열 배열 JSON)",
        ),
    )

    # closed_at — 접수 마감일 (상시접수는 9999-12-31)
    op.add_column(
        "policies",
        sa.Column(
            "closed_at",
            sa.Date,
            nullable=False,
            server_default="9999-12-31",
            comment="접수 마감일. 상시접수는 9999-12-31 저장",
        ),
    )

    # is_active — Soft Delete 플래그
    op.add_column(
        "policies",
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
            comment="[Soft Delete] 활성 여부 — False이면 서비스에서 노출 안 됨",
        ),
    )

    # ── policy_bookmarks 테이블 신규 생성 ─────────────────────────────────

    op.create_table(
        "policy_bookmarks",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            comment="북마크 고유 식별자",
        ),
        sa.Column(
            "business_id",
            UUID(as_uuid=True),
            sa.ForeignKey("businesses.id"),
            nullable=False,
            comment="북마크한 사업장 ID (businesses.id)",
        ),
        sa.Column(
            "policy_id",
            UUID(as_uuid=True),
            sa.ForeignKey("policies.id"),
            nullable=False,
            comment="북마크 대상 정책 ID (policies.id)",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="북마크 등록 일시",
        ),
        sa.UniqueConstraint(
            "business_id",
            "policy_id",
            name="uq_policy_bookmark_biz_policy",
        ),
    )

    op.create_index(
        "ix_policy_bookmarks_business_id",
        "policy_bookmarks",
        ["business_id"],
    )
    op.create_index(
        "ix_policy_bookmarks_policy_id",
        "policy_bookmarks",
        ["policy_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_policy_bookmarks_policy_id", table_name="policy_bookmarks")
    op.drop_index("ix_policy_bookmarks_business_id", table_name="policy_bookmarks")
    op.drop_table("policy_bookmarks")

    op.drop_column("policies", "is_active")
    op.drop_column("policies", "closed_at")
    op.drop_column("policies", "required_documents")
    op.drop_column("policies", "support_amount_desc")
    op.drop_column("policies", "region")
    op.drop_column("policies", "category")
