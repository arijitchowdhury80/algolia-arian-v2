"""Add domain column to module_executions for cache lookups.

Revision ID: 002
Revises: 001
Create Date: 2026-03-31
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "002"
down_revision: str = "001"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "module_executions",
        sa.Column("domain", sa.Text(), nullable=False, server_default=sa.text("''")),
    )
    op.alter_column("module_executions", "audit_id", nullable=True)
    op.create_index(
        "idx_module_exec_domain_module",
        "module_executions",
        ["domain", "module_name"],
    )


def downgrade() -> None:
    op.drop_index("idx_module_exec_domain_module", table_name="module_executions")
    op.alter_column("module_executions", "audit_id", nullable=False)
    op.drop_column("module_executions", "domain")
