"""Add company hierarchy fields to accounts — parent_domain and subsidiaries.

intel-company v2 now captures the full brand portfolio:
- parent_domain: domain of the parent/holding company (e.g. 'berkshirehathaway.com')
- subsidiaries: JSONB list of brands/subsidiaries this company owns
  (e.g. Nike → Jordan, Converse; Oriental Trading → MindWare, Fun Express)

Revision ID: 007
Revises: 006
Create Date: 2026-04-15
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "007"
down_revision: str = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("parent_domain", sa.Text(), nullable=True))
    op.add_column(
        "accounts",
        sa.Column("subsidiaries", JSONB, nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("accounts", "subsidiaries")
    op.drop_column("accounts", "parent_domain")
