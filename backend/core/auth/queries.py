"""Shared joined-query helper for "which audits can this user see"
(04-spec.md §2b). One implementation, reused by
`get_audit_data_by_slug`/`list_accounts`/`get_account_results`
(server/api/routers/audits.py, accounts.py) and
`GET /api/v1/acl/visible` (server/api/routers/acl.py) -- closes
the "don't reimplement the join four times" risk (06-plan.md Wave 2, B_Q).

Shape: LEFT JOIN audit_shares ON audit_shares.audit_id = audits.id AND
audit_shares.shared_with_user_id = :user_id, filtered
WHERE audits.user_id = :user_id OR audit_shares.shared_with_user_id IS NOT
NULL. One query, no per-row can_user_see() call (Arch Review I-1).
`user_id=None` matches nothing -- default-deny, consistent with
`core.auth.acl.can_user_see`.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from core.db.models import Audit, AuditShare


def visible_audits_select(user_id: str | None) -> Select[tuple[Audit]]:
    """Base Select over every Audit visible to `user_id` -- owned or
    explicitly shared via audit_shares. One outer join, composable with
    further `.where()`/`.join()`/`.order_by()` clauses at the call site
    (e.g. account or slug filters) -- this is the one join implementation
    reused everywhere (04-spec.md §2b)."""
    base = select(Audit).outerjoin(
        AuditShare,
        (AuditShare.audit_id == Audit.id) & (AuditShare.shared_with_user_id == user_id),
    )
    if user_id is None:
        return base.where(Audit.id.is_(None))  # explicit empty-set, not a bug
    return base.where(or_(Audit.user_id == user_id, AuditShare.shared_with_user_id.isnot(None)))


async def visible_audit_ids_for_user(user_id: str | None, session: AsyncSession) -> list[uuid.UUID]:
    """Materialized audit_id list -- powers GET /acl/visible (04-spec.md
    §5) and Arch Review I-2's test scenarios."""
    stmt = visible_audits_select(user_id).with_only_columns(Audit.id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def latest_visible_audit_for_account(
    account_id: uuid.UUID, user_id: str | None, session: AsyncSession
) -> Audit | None:
    """The most-recent audit visible to `user_id` for one account --
    "latest visible, not latest overall" (04-spec.md §2b, Arch Review
    I-2). Powers get_account_results and get_audit_data_by_slug's
    per-slug resolution."""
    stmt = (
        visible_audits_select(user_id)
        .where(Audit.account_id == account_id)
        .order_by(Audit.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalars().first()


async def latest_visible_audit_per_account(
    user_id: str | None, session: AsyncSession
) -> dict[uuid.UUID, Audit]:
    """One row per account_id: the most-recent audit visible to `user_id`
    for that account, in a single round trip (window function, Arch
    Review I-1 -- not a can_user_see() call inside a per-account loop).
    Powers list_accounts (06-plan.md B6). Accounts with zero visible
    audits are simply absent from the returned dict -- callers list them
    with status "none" rather than omitting the account itself."""
    if user_id is None:
        return {}

    ranked = (
        visible_audits_select(user_id)
        .add_columns(
            func.row_number()
            .over(partition_by=Audit.account_id, order_by=Audit.created_at.desc())
            .label("_rn")
        )
        .subquery()
    )
    audit_alias = aliased(Audit, ranked)
    stmt = select(audit_alias).where(ranked.c._rn == 1)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return {audit.account_id: audit for audit in rows}
