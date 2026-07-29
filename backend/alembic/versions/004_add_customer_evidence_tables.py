"""Add Algolia customer evidence tables: customers, case_studies, quotes, proofpoints, advocates.

Revision ID: 004
Revises: 003
Create Date: 2026-04-02
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "004"
down_revision: str = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the 5 Algolia customer evidence tables."""
    # ── algolia_customers ──
    op.create_table(
        "algolia_customers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_name", sa.Text, nullable=False),
        sa.Column("industry", sa.Text, nullable=False, server_default="Unknown"),
        sa.Column("sub_vertical", sa.Text, nullable=True),
        sa.Column("country", sa.Text, nullable=True),
        sa.Column("website", sa.Text, nullable=True),
        sa.Column("arr_range", sa.Text, nullable=True),
        sa.Column("hierarchy_segment", sa.Text, nullable=True),
        sa.Column("features_used", JSONB, server_default="[]"),
        sa.Column("ecommerce_platform", sa.Text, nullable=True),
        sa.Column("logo_rights", sa.Boolean, server_default="false"),
        sa.Column("case_study_consent", sa.Boolean, server_default="false"),
        sa.Column("publicity_consent", sa.Boolean, server_default="false"),
        sa.Column("reference_consent", sa.Boolean, server_default="false"),
        sa.Column("signed_date", sa.Date, nullable=True),
        sa.Column("go_live_date", sa.Date, nullable=True),
        sa.Column("competitor_replaced", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_algolia_customers_company", "algolia_customers", ["company_name"])
    op.create_index("idx_algolia_customers_industry", "algolia_customers", ["industry"])

    # ── algolia_case_studies ──
    op.create_table(
        "algolia_case_studies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_name", sa.Text, nullable=False),
        sa.Column("url", sa.Text, nullable=True),
        sa.Column("industry", sa.Text, nullable=False, server_default="Unknown"),
        sa.Column("sub_vertical", sa.Text, nullable=True),
        sa.Column("country", sa.Text, nullable=True),
        sa.Column("use_case", sa.Text, nullable=True),
        sa.Column("features_used", JSONB, server_default="[]"),
        sa.Column("competitor_takeout", sa.Text, nullable=True),
        sa.Column("partner_integrations", sa.Text, nullable=True),
        sa.Column("key_results", sa.Text, nullable=True),
        sa.Column("status", sa.Text, server_default="Complete"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_algolia_case_studies_customer", "algolia_case_studies", ["customer_name"])
    op.create_index("idx_algolia_case_studies_industry", "algolia_case_studies", ["industry"])

    # ── algolia_quotes ──
    op.create_table(
        "algolia_quotes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_name", sa.Text, nullable=False),
        sa.Column("person_name", sa.Text, nullable=False),
        sa.Column("person_title", sa.Text, nullable=True),
        sa.Column("industry", sa.Text, nullable=False, server_default="Unknown"),
        sa.Column("country", sa.Text, nullable=True),
        sa.Column("quote_text", sa.Text, nullable=False),
        sa.Column("evidence_type", sa.Text, nullable=True),
        sa.Column("source", sa.Text, nullable=True),
        sa.Column("tags", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_algolia_quotes_customer", "algolia_quotes", ["customer_name"])
    op.create_index("idx_algolia_quotes_industry", "algolia_quotes", ["industry"])

    # Full-text search index on quote_text
    op.execute(
        "CREATE INDEX idx_algolia_quotes_text_fts ON algolia_quotes "
        "USING gin(to_tsvector('english', quote_text))"
    )

    # ── algolia_proofpoints ──
    op.create_table(
        "algolia_proofpoints",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("result_text", sa.Text, nullable=False),
        sa.Column("source", sa.Text, nullable=True),
        sa.Column("proof_type", sa.Text, nullable=False, server_default="Aggregated Results"),
        sa.Column("industry", sa.Text, nullable=False, server_default="Unknown"),
        sa.Column("customer_or_theme", sa.Text, nullable=True),
        sa.Column("shareable", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_algolia_proofpoints_industry", "algolia_proofpoints", ["industry"])

    # Full-text search index on result_text
    op.execute(
        "CREATE INDEX idx_algolia_proofpoints_text_fts ON algolia_proofpoints "
        "USING gin(to_tsvector('english', result_text))"
    )

    # ── algolia_advocates ──
    op.create_table(
        "algolia_advocates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("first_name", sa.Text, nullable=False),
        sa.Column("last_name", sa.Text, nullable=False),
        sa.Column("company_name", sa.Text, nullable=False),
        sa.Column("job_title", sa.Text, nullable=True),
        sa.Column("email", sa.Text, nullable=True),
        sa.Column("industry", sa.Text, nullable=True),
        sa.Column("country", sa.Text, nullable=True),
        sa.Column("willing_to", JSONB, server_default="[]"),
        sa.Column("person_source", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_algolia_advocates_company", "algolia_advocates", ["company_name"])
    op.create_index("idx_algolia_advocates_industry", "algolia_advocates", ["industry"])


def downgrade() -> None:
    """Drop all 5 Algolia customer evidence tables."""
    op.drop_table("algolia_advocates")
    op.drop_table("algolia_proofpoints")
    op.drop_table("algolia_quotes")
    op.drop_table("algolia_case_studies")
    op.drop_table("algolia_customers")
