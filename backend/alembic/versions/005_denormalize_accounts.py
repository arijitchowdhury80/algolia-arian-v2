"""Denormalize accounts table — proper columns replacing intelligence JSONB.

Adds proper columns for every field from CompanyProfileOutput. Migrates existing
data from intelligence JSONB and vertical column. Drops intelligence and vertical
after migration.

Revision ID: 005
Revises: 004
Create Date: 2026-04-02
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "005"
down_revision: str = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new proper columns
    op.add_column("accounts", sa.Column("legal_name", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("headquarters", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("employee_count", sa.Integer(), nullable=True))
    op.add_column("accounts", sa.Column("employee_count_source", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("year_founded", sa.Integer(), nullable=True))
    op.add_column("accounts", sa.Column("business_model", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("motto", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("industry", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("sub_vertical", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("parent_company", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("revenue_estimate", sa.Numeric(15, 2), nullable=True))
    op.add_column("accounts", sa.Column("revenue_source", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("has_search_bar", sa.Boolean(), nullable=True))
    op.add_column("accounts", sa.Column("product_categories", JSONB(), server_default="[]"))
    op.add_column("accounts", sa.Column("executives", JSONB(), server_default="[]"))
    op.add_column("accounts", sa.Column("competitors", JSONB(), server_default="[]"))
    op.add_column("accounts", sa.Column("recent_news", JSONB(), server_default="[]"))
    op.add_column("accounts", sa.Column("recent_blog_posts", JSONB(), server_default="[]"))
    op.add_column("accounts", sa.Column("sources", JSONB(), server_default="[]"))

    # Migrate existing data from intelligence JSONB + vertical column
    op.execute("""
        UPDATE accounts SET
            legal_name = intelligence->>'legal_name',
            headquarters = intelligence->>'headquarters',
            employee_count = CASE
                WHEN intelligence->>'employee_count' ~ '^[0-9]+$'
                THEN (intelligence->>'employee_count')::integer
                ELSE NULL
            END,
            industry = COALESCE(intelligence->>'industry', vertical),
            sub_vertical = intelligence->>'sub_vertical',
            business_model = intelligence->>'business_model',
            revenue_estimate = CASE
                WHEN intelligence->>'revenue_estimate' ~ '^[0-9.]+$'
                THEN (intelligence->>'revenue_estimate')::numeric
                ELSE NULL
            END
        WHERE intelligence IS NOT NULL AND intelligence != '{}'::jsonb
    """)

    # Copy vertical to industry for rows where intelligence was empty
    op.execute("""
        UPDATE accounts SET industry = vertical
        WHERE industry IS NULL AND vertical IS NOT NULL
    """)

    # Drop old columns
    op.drop_column("accounts", "intelligence")
    op.drop_column("accounts", "vertical")


def downgrade() -> None:
    op.add_column("accounts", sa.Column("intelligence", JSONB(), server_default="{}"))
    op.add_column("accounts", sa.Column("vertical", sa.Text(), nullable=True))

    # Best-effort reverse: copy industry back to vertical
    op.execute("UPDATE accounts SET vertical = industry")

    op.drop_column("accounts", "sources")
    op.drop_column("accounts", "recent_blog_posts")
    op.drop_column("accounts", "recent_news")
    op.drop_column("accounts", "competitors")
    op.drop_column("accounts", "executives")
    op.drop_column("accounts", "product_categories")
    op.drop_column("accounts", "has_search_bar")
    op.drop_column("accounts", "revenue_source")
    op.drop_column("accounts", "revenue_estimate")
    op.drop_column("accounts", "parent_company")
    op.drop_column("accounts", "sub_vertical")
    op.drop_column("accounts", "industry")
    op.drop_column("accounts", "motto")
    op.drop_column("accounts", "business_model")
    op.drop_column("accounts", "year_founded")
    op.drop_column("accounts", "employee_count_source")
    op.drop_column("accounts", "employee_count")
    op.drop_column("accounts", "headquarters")
    op.drop_column("accounts", "legal_name")
