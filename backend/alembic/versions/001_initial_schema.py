"""Initial schema -- accounts, audits, module_executions, deliverables.

Revision ID: 001
Revises:
Create Date: 2026-03-30
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("company_name", sa.Text(), nullable=False),
        sa.Column("domain", sa.Text(), unique=True, nullable=False),
        sa.Column("vertical", sa.Text(), nullable=True),
        sa.Column("is_public", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("ticker", sa.Text(), nullable=True),
        sa.Column("intelligence", JSONB(), server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "audits",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "account_id",
            UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Text(), nullable=False, server_default=sa.text("'system'")),
        sa.Column("status", sa.Text(), server_default=sa.text("'pending'")),
        sa.Column("score", sa.Numeric(3, 1), nullable=True),
        sa.Column("factcheck_score", sa.Numeric(3, 1), nullable=True),
        sa.Column("factcheck_action", sa.Text(), nullable=True),
        sa.Column("config", JSONB(), server_default=sa.text("'{}'")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_audits_account", "audits", ["account_id"])
    op.create_index("idx_audits_status", "audits", ["status"])

    op.create_table(
        "module_executions",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "audit_id",
            UUID(as_uuid=True),
            sa.ForeignKey("audits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("module_name", sa.Text(), nullable=False),
        sa.Column("module_version", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'pending'")),
        sa.Column("wave", sa.Integer(), nullable=True),
        sa.Column("output_json", JSONB(), nullable=True),
        sa.Column("sources_json", JSONB(), nullable=True),
        sa.Column("validation_json", JSONB(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("llm_calls", sa.Integer(), server_default=sa.text("0")),
        sa.Column("llm_cost_usd", sa.Numeric(8, 4), server_default=sa.text("0")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("audit_id", "module_name"),
    )
    op.create_index("idx_module_exec_audit", "module_executions", ["audit_id"])
    op.create_index("idx_module_exec_status", "module_executions", ["audit_id", "status"])

    op.create_table(
        "deliverables",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "audit_id",
            UUID(as_uuid=True),
            sa.ForeignKey("audits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("file_key", sa.Text(), nullable=True),
        sa.Column("file_url", sa.Text(), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("deliverables")
    op.drop_table("module_executions")
    op.drop_table("audits")
    op.drop_table("accounts")
