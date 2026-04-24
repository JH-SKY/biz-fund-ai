"""Refactor domains and add policy fields.

Revision ID: f273a5a15134
Revises: 1db6b0205160
Create Date: 2026-04-08 15:39:42.892641
"""

from typing import Sequence, Union


revision: str = "f273a5a15134"
down_revision: Union[str, Sequence[str], None] = "1db6b0205160"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    This revision duplicated admin table creation that already exists in
    earlier migrations, so it is intentionally a no-op.
    """


def downgrade() -> None:
    """Downgrade schema."""

