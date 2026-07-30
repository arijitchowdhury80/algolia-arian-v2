"""Integration tests for core.auth.queries (04-spec.md §2b).

@pytest.mark.db -- ephemeral docker Postgres, see tests/auth/conftest.py.
NOT executed in this sandbox (no docker daemon here) -- see
.development-loop/run-2026-07-14-001/07-build-log.md.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import event, text

from core.auth.queries import (
    latest_visible_audit_for_account,
    latest_visible_audit_per_account,
    visible_audit_ids_for_user,
)
from tests.auth.conftest import skip_if_no_docker

pytestmark = pytest.mark.db


@skip_if_no_docker
@pytest.mark.asyncio
async def test_older_owned_audit_visible_despite_newer_foreign_audit(
    async_session, seed_user, seed_account_and_audit
) -> None:
    """Arch Review I-2 -- the exact correctness scenario. User A owns an
    OLDER audit for a domain; User B owns a NEWER one for the same domain
    (same account row). User A must still see their own via the
    visible-audit query -- not silently hidden because a newer, invisible
    audit exists."""
    await seed_user("user_a")
    await seed_user("user_b")

    account_id, older_audit_id = await seed_account_and_audit("user_a", domain="belk.com")
    newer_audit_id = uuid.uuid4()
    await async_session.execute(
        text(
            "INSERT INTO audits (id, account_id, user_id, status, created_at) "
            "VALUES (:id, :account_id, 'user_b', 'completed', now() + interval '1 hour')"
        ),
        {"id": newer_audit_id, "account_id": account_id},
    )
    await async_session.commit()

    visible_to_a = await visible_audit_ids_for_user("user_a", async_session)
    assert older_audit_id in visible_to_a
    assert newer_audit_id not in visible_to_a

    latest_for_a = await latest_visible_audit_for_account(account_id, "user_a", async_session)
    assert latest_for_a is not None
    assert latest_for_a.id == older_audit_id  # not hidden by the newer, invisible audit


@skip_if_no_docker
@pytest.mark.asyncio
async def test_shared_audit_is_visible_to_the_shared_user(
    async_session, seed_user, seed_account_and_audit
) -> None:
    await seed_user("user_a")
    await seed_user("user_b")
    _account_id, audit_id = await seed_account_and_audit("user_a")
    await async_session.execute(
        text(
            "INSERT INTO audit_shares (audit_id, shared_with_user_id, permission, created_by) "
            "VALUES (:audit_id, 'user_b', 'view', 'user_a')"
        ),
        {"audit_id": audit_id},
    )
    await async_session.commit()

    visible_to_b = await visible_audit_ids_for_user("user_b", async_session)
    assert audit_id in visible_to_b


@skip_if_no_docker
@pytest.mark.asyncio
async def test_none_user_sees_nothing(async_session, seed_user, seed_account_and_audit) -> None:
    await seed_user("user_a")
    await seed_account_and_audit("user_a")

    visible = await visible_audit_ids_for_user(None, async_session)
    assert visible == []


@skip_if_no_docker
@pytest.mark.asyncio
async def test_visible_audits_single_round_trip(
    async_session, seed_user, seed_account_and_audit
) -> None:
    """Arch Review I-1 -- one query per call, not a can_user_see() loop."""
    await seed_user("user_a")
    await seed_account_and_audit("user_a")

    query_count = 0

    def _count(*_args, **_kwargs) -> None:
        nonlocal query_count
        query_count += 1

    engine = async_session.bind.sync_engine
    event.listen(engine, "before_cursor_execute", _count)
    try:
        await visible_audit_ids_for_user("user_a", async_session)
    finally:
        event.remove(engine, "before_cursor_execute", _count)

    assert query_count == 1


@skip_if_no_docker
@pytest.mark.asyncio
async def test_latest_visible_audit_per_account_one_round_trip_for_all_accounts(
    async_session, seed_user, seed_account_and_audit
) -> None:
    await seed_user("user_a")
    await seed_account_and_audit("user_a", domain="belk.com", company_name="Belk")
    await seed_account_and_audit("user_a", domain="dell.com", company_name="Dell")

    query_count = 0

    def _count(*_args, **_kwargs) -> None:
        nonlocal query_count
        query_count += 1

    engine = async_session.bind.sync_engine
    event.listen(engine, "before_cursor_execute", _count)
    try:
        by_account = await latest_visible_audit_per_account("user_a", async_session)
    finally:
        event.remove(engine, "before_cursor_execute", _count)

    assert query_count == 1
    assert len(by_account) == 2


@skip_if_no_docker
@pytest.mark.asyncio
async def test_latest_visible_audit_per_account_none_user_returns_empty(
    async_session, seed_user, seed_account_and_audit
) -> None:
    await seed_user("user_a")
    await seed_account_and_audit("user_a")

    by_account = await latest_visible_audit_per_account(None, async_session)
    assert by_account == {}
