"""Add users table — Clerk-mirrored tenant identity.

Revision ID: 009
Revises: 008
Create Date: 2026-06-30
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "009"
down_revision: str = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("email", sa.Text, nullable=True),
        sa.Column("name", sa.Text, nullable=True),
        sa.Column("org_id", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("idx_users_org", "users", ["org_id"])


def downgrade() -> None:
    op.drop_index("idx_users_org", table_name="users")
    op.drop_table("users")
