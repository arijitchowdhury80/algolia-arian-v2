"""Add users, audit_shares, seen_assertions tables + ACL indexes.

Per-user-to-company authorization (run-2026-07-14-001). See
.development-loop/run-2026-07-14-001/04-spec.md §1 and §9 step 1
(Additive) -- no existing data touched. Reversible: downgrade() drops all
three new tables and the one new index.

Revision ID: 011
Revises: 010
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "012"
down_revision: str = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("email", sa.Text, nullable=False),
        sa.Column("name", sa.Text, nullable=True),
        # Dormant until Clerk Orgs is explicitly turned on -- never read by
        # prism_platform.auth.acl.can_user_see() while off [C3].
        sa.Column("org_id", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "audit_shares",
        sa.Column(
            "audit_id",
            UUID(as_uuid=True),
            sa.ForeignKey("audits.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "shared_with_user_id",
            sa.Text,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        # Locked to 'view' only this slice -- see the CHECK constraint below.
        sa.Column("permission", sa.Text, nullable=False, server_default="view"),
        # Must equal the audit's owner; enforced at write time by the shares
        # endpoint, not just by convention.
        sa.Column("created_by", sa.Text, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("permission = 'view'", name="ck_audit_shares_permission_view_only"),
    )
    # The PK's non-leading column -- /acl/visible's core query scans by
    # this [I-3].
    op.create_index("idx_audit_shares_shared_with", "audit_shares", ["shared_with_user_id"])

    # jti replay-defense store for the signed trust-assertion channel
    # (§4). A table (not an in-memory LRU) -- survives a process restart,
    # correct under >1 uvicorn worker (06-plan.md §4 design note).
    op.create_table(
        "seen_assertions",
        sa.Column("jti", sa.Text, primary_key=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Every ACL check and the /acl/visible lookup filters by this column;
    # no index existed on it before this slice.
    op.create_index("idx_audits_user", "audits", ["user_id"])


def downgrade() -> None:
    op.drop_index("idx_audits_user", table_name="audits")
    op.drop_table("seen_assertions")
    op.drop_index("idx_audit_shares_shared_with", table_name="audit_shares")
    op.drop_table("audit_shares")
    op.drop_table("users")
