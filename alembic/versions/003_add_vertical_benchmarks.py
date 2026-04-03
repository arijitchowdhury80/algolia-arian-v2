"""Add vertical_benchmarks table for insights-engine module.

Revision ID: 003
Revises: 002
Create Date: 2026-04-01
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "003"
down_revision: str = "002"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "vertical_benchmarks",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("vertical", sa.Text(), nullable=False),
        sa.Column("metric_name", sa.Text(), nullable=False),
        sa.Column("metric_value", JSONB(), server_default=sa.text("'{}'")),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("audit_ids", JSONB(), server_default=sa.text("'[]'")),
    )
    op.create_index(
        "idx_vertical_benchmarks_vertical",
        "vertical_benchmarks",
        ["vertical"],
    )


def downgrade() -> None:
    op.drop_index("idx_vertical_benchmarks_vertical", table_name="vertical_benchmarks")
    op.drop_table("vertical_benchmarks")
