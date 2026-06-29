"""Add Algolia knowledge store: algolia_knowledge + algolia_gaps tables.

Also retrofits GENERATED tsvector FTS columns onto existing Algolia evidence
tables (algolia_knowledge, algolia_case_studies, algolia_proofpoints,
algolia_quotes) so retrieve/ can UNION across all four with ts_rank.

Note: GENERATED ALWAYS AS STORED columns and GIN indexes cannot be expressed
cleanly via op.add_column — we use op.execute() raw SQL for these operations.

Revision ID: 008
Revises: 007
Create Date: 2026-06-29
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "008"
down_revision: str = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── algolia_knowledge ────────────────────────────────────────────────────
    op.create_table(
        "algolia_knowledge",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("topic", sa.Text, nullable=False),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("question_hash", sa.Text, nullable=False),
        sa.Column("answer", sa.Text, nullable=False),
        sa.Column("sources", JSONB, nullable=False, server_default="[]"),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=True),
        sa.Column("judge_score", sa.Numeric(3, 2), nullable=True),
        sa.Column("origin", sa.Text, nullable=False, server_default="learned"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.UniqueConstraint("question_hash", name="uq_algolia_knowledge_question_hash"),
    )
    op.create_index("idx_algolia_knowledge_topic", "algolia_knowledge", ["topic"])
    op.create_index("idx_algolia_knowledge_origin", "algolia_knowledge", ["origin"])

    # ── algolia_gaps ─────────────────────────────────────────────────────────
    op.create_table(
        "algolia_gaps",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("question_hash", sa.Text, nullable=False),
        sa.Column("topic", sa.Text, nullable=True),
        sa.Column("conversation_id", sa.Text, nullable=True),
        sa.Column("why", sa.Text, nullable=False, server_default="kb_miss"),
        sa.Column("status", sa.Text, nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_algolia_gaps_status", "algolia_gaps", ["status"])
    op.create_index("idx_algolia_gaps_question_hash", "algolia_gaps", ["question_hash"])

    # ── FTS: algolia_knowledge ────────────────────────────────────────────────
    # GENERATED ALWAYS AS STORED requires raw SQL — alembic op.add_column cannot express it.
    op.execute(
        """
        ALTER TABLE algolia_knowledge
        ADD COLUMN search_tsv tsvector
        GENERATED ALWAYS AS (
            to_tsvector('english',
                coalesce(topic, '') || ' ' ||
                coalesce(question, '') || ' ' ||
                coalesce(answer, ''))
        ) STORED
        """
    )
    op.execute(
        "CREATE INDEX idx_algolia_knowledge_search_fts ON algolia_knowledge USING GIN(search_tsv)"
    )

    # ── FTS: existing evidence tables ─────────────────────────────────────────
    # Drop the old single-column expression indexes added in migration 004
    # before adding the new multi-column generated-column GIN indexes.
    op.execute("DROP INDEX IF EXISTS idx_algolia_quotes_text_fts")
    op.execute("DROP INDEX IF EXISTS idx_algolia_proofpoints_text_fts")

    # algolia_case_studies — customer_name + use_case + key_results + competitor_takeout
    op.execute(
        """
        ALTER TABLE algolia_case_studies
        ADD COLUMN search_tsv tsvector
        GENERATED ALWAYS AS (
            to_tsvector('english',
                coalesce(customer_name, '') || ' ' ||
                coalesce(use_case, '') || ' ' ||
                coalesce(key_results, '') || ' ' ||
                coalesce(competitor_takeout, ''))
        ) STORED
        """
    )
    op.execute(
        "CREATE INDEX idx_algolia_case_studies_search_fts"
        " ON algolia_case_studies USING GIN(search_tsv)"
    )

    # algolia_proofpoints — result_text + customer_or_theme
    op.execute(
        """
        ALTER TABLE algolia_proofpoints
        ADD COLUMN search_tsv tsvector
        GENERATED ALWAYS AS (
            to_tsvector('english',
                coalesce(result_text, '') || ' ' ||
                coalesce(customer_or_theme, ''))
        ) STORED
        """
    )
    op.execute(
        "CREATE INDEX idx_algolia_proofpoints_search_fts"
        " ON algolia_proofpoints USING GIN(search_tsv)"
    )

    # algolia_quotes — quote_text + person_title + customer_name
    op.execute(
        """
        ALTER TABLE algolia_quotes
        ADD COLUMN search_tsv tsvector
        GENERATED ALWAYS AS (
            to_tsvector('english',
                coalesce(quote_text, '') || ' ' ||
                coalesce(person_title, '') || ' ' ||
                coalesce(customer_name, ''))
        ) STORED
        """
    )
    op.execute("CREATE INDEX idx_algolia_quotes_search_fts ON algolia_quotes USING GIN(search_tsv)")


def downgrade() -> None:
    # ── Existing-table FTS rollback ───────────────────────────────────────────
    op.execute("DROP INDEX IF EXISTS idx_algolia_quotes_search_fts")
    op.execute("ALTER TABLE algolia_quotes DROP COLUMN IF EXISTS search_tsv")
    # Restore the simple single-column expression index from migration 004
    op.execute(
        "CREATE INDEX idx_algolia_quotes_text_fts"
        " ON algolia_quotes USING gin(to_tsvector('english', quote_text))"
    )

    op.execute("DROP INDEX IF EXISTS idx_algolia_proofpoints_search_fts")
    op.execute("ALTER TABLE algolia_proofpoints DROP COLUMN IF EXISTS search_tsv")
    op.execute(
        "CREATE INDEX idx_algolia_proofpoints_text_fts"
        " ON algolia_proofpoints USING gin(to_tsvector('english', result_text))"
    )

    op.execute("DROP INDEX IF EXISTS idx_algolia_case_studies_search_fts")
    op.execute("ALTER TABLE algolia_case_studies DROP COLUMN IF EXISTS search_tsv")

    # ── algolia_knowledge FTS rollback ────────────────────────────────────────
    op.execute("DROP INDEX IF EXISTS idx_algolia_knowledge_search_fts")
    op.execute("ALTER TABLE algolia_knowledge DROP COLUMN IF EXISTS search_tsv")

    # ── Drop new tables ───────────────────────────────────────────────────────
    op.drop_table("algolia_gaps")
    op.drop_table("algolia_knowledge")
