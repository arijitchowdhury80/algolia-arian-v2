"""Add social fields to accounts — company_linkedin_url, twitter_handle, youtube_url.

Needed by intel-company v2 which now collects social presence for the prospect
and stores ticker/linkedin/twitter/youtube for each competitor in the JSONB
competitors column (no migration needed for competitors — it's already JSONB).

Revision ID: 006
Revises: 005
Create Date: 2026-04-14
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "006"
down_revision: str = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("company_linkedin_url", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("twitter_handle", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("youtube_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("accounts", "youtube_url")
    op.drop_column("accounts", "twitter_handle")
    op.drop_column("accounts", "company_linkedin_url")
