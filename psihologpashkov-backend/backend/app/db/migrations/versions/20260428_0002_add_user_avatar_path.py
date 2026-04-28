"""add user avatar path

Revision ID: 20260428_0002
Revises: 20260428_0001
Create Date: 2026-04-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260428_0002"
down_revision: str | None = "20260428_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("avatar_path", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "avatar_path")
