"""Add audits.audit_data JSONB + widen score precision to Numeric(3,2).

Surfaced by the historical-audit migration dry-run (2026-07-02):
- audits.score / factcheck_score were Numeric(3,1) → silently rounded real
  two-decimal scores (jbl 1.93→1.9, nike 4.32→4.3). Widen to Numeric(3,2).
- audits had no dedicated column for the full audit-data JSON blob (the airtight
  plan §1.4 makes Postgres the source of truth for the whole audit). Add
  audit_data JSONB so the report data lives in its own column, not overloaded
  into config (which stays for run-config).

Revision ID: 009
Revises: 008
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "009"
down_revision: str = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "audits",
        sa.Column("audit_data", JSONB(), nullable=True),
    )
    op.alter_column(
        "audits",
        "score",
        type_=sa.Numeric(3, 2),
        existing_type=sa.Numeric(3, 1),
        existing_nullable=True,
    )
    op.alter_column(
        "audits",
        "factcheck_score",
        type_=sa.Numeric(3, 2),
        existing_type=sa.Numeric(3, 1),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "audits",
        "factcheck_score",
        type_=sa.Numeric(3, 1),
        existing_type=sa.Numeric(3, 2),
        existing_nullable=True,
    )
    op.alter_column(
        "audits",
        "score",
        type_=sa.Numeric(3, 1),
        existing_type=sa.Numeric(3, 2),
        existing_nullable=True,
    )
    op.drop_column("audits", "audit_data")
