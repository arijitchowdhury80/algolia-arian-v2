"""Add pgvector extension + report_chunks table for the embedded chat agent.

Task 5 (Track C.3, plan 2026-07-12) -- grounding store for the plain
`claude -p` chat agent. Per patch #9 (locked in the task-5 brief), the
mechanism is:
  - embedding model: sentence-transformers/all-MiniLM-L6-v2 (384 dims, local,
    keyless -- see prism_platform/pipeline/embeddings.py)
  - chunking: by report section (one row per top-level audit_data key per
    audit -- see prism_platform/pipeline/chunking.py), not a token window
  - similarity: cosine via pgvector's `<=>` operator, threshold >= 0.35
    (prism_platform/pipeline/retrieval.py's SIMILARITY_THRESHOLD)

Revision ID: 010
Revises: 009
"""

from __future__ import annotations

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "010"
down_revision: str = "009"
branch_labels = None
depends_on = None

EMBEDDING_DIMS = 384  # all-MiniLM-L6-v2 output size -- see embeddings.py


def upgrade() -> None:
    # pgvector must exist before any `vector(...)` column can be created.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "report_chunks",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "audit_id",
            UUID(as_uuid=True),
            sa.ForeignKey("audits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("domain", sa.Text, nullable=False),
        sa.Column("section_name", sa.Text, nullable=False),
        sa.Column("chunk_text", sa.Text, nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIMS), nullable=False),
        # Provenance for re-embedding without a fresh audit_data diff:
        # which embedding model produced this row (patch #9 names it once;
        # this lets a future model swap be detected/re-indexed, not silent).
        sa.Column(
            "embedding_model",
            sa.Text,
            nullable=False,
            server_default="sentence-transformers/all-MiniLM-L6-v2",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("audit_id", "section_name", name="uq_report_chunks_audit_section"),
    )
    op.create_index("idx_report_chunks_audit", "report_chunks", ["audit_id"])
    op.create_index("idx_report_chunks_domain", "report_chunks", ["domain"])
    # IVFFlat index for cosine similarity search (`<=>` operator). `lists` is
    # a starting default per pgvector docs for small-to-mid row counts; this
    # store is one chunk per section per audit (~15-20 rows/audit), so exact
    # scan would also be fine at current volume -- the index just keeps
    # retrieve() cheap as the audit corpus grows.
    op.execute(
        "CREATE INDEX idx_report_chunks_embedding ON report_chunks "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_report_chunks_embedding")
    op.drop_index("idx_report_chunks_domain", table_name="report_chunks")
    op.drop_index("idx_report_chunks_audit", table_name="report_chunks")
    op.drop_table("report_chunks")
    # Extension is left in place on downgrade -- other tables/migrations may
    # depend on it, and DROP EXTENSION is a separate, more destructive
    # decision than undoing this one table.
