"""Add landing_pages table for the custom landing page system.

Custom Landing Page spike (docs/workspace/custom-landing-page/), plan
i-am-starting-a-ethereal-kahn.md Step 2. audit_id is a NULLABLE FK by design:
PRISM audit data is an optional pre-fill convenience for the intake wizard,
never a prerequisite -- a landing page built from fully manual/external
content (audit_id = NULL) must be a first-class, fully supported row, not a
degraded one. ondelete="SET NULL" (not CASCADE) so deleting the source audit
never silently deletes a published landing page.

Revision ID: 011
Revises: 010
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "011"
down_revision: str = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "landing_pages",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("slug", sa.Text, nullable=False, unique=True),
        sa.Column("company_name", sa.Text, nullable=False),
        sa.Column(
            "audit_id",
            UUID(as_uuid=True),
            sa.ForeignKey("audits.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("content_json", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("sections_json", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("theme_json", JSONB(), nullable=True),
        sa.Column("status", sa.Text, nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("idx_landing_pages_audit", "landing_pages", ["audit_id"])


def downgrade() -> None:
    op.drop_index("idx_landing_pages_audit", table_name="landing_pages")
    op.drop_table("landing_pages")
