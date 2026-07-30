"""Unit tests for core.auth.acl -- the ACL seam (04-spec.md §2).

No live Postgres needed: can_user_see's only I/O is one `audit_shares`
lookup, faked below the same way tests/pipeline/test_chat_router.py fakes
its DB session.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
import structlog

from core.auth.acl import can_user_see, is_owner
from core.db.models import Audit, AuditShare


class _FakeScalarResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value


class _FakeSession:
    """Returns a single queued result for the one audit_shares lookup
    can_user_see performs once ownership has already been ruled out."""

    def __init__(self, share_row: object | None) -> None:
        self._share_row = share_row

    async def execute(self, stmt: object) -> _FakeScalarResult:
        return _FakeScalarResult(self._share_row)


def _audit(owner_id: str = "user_owner") -> Audit:
    return Audit(id=uuid.uuid4(), account_id=uuid.uuid4(), user_id=owner_id)


# ---------------------------------------------------------------------------
# is_owner -- real function, exported and reused (not a second inline `==`)
# ---------------------------------------------------------------------------


def test_is_owner_true_when_ids_match() -> None:
    audit = _audit(owner_id="user_a")
    assert is_owner("user_a", audit) is True


def test_is_owner_false_when_ids_differ() -> None:
    audit = _audit(owner_id="user_a")
    assert is_owner("user_b", audit) is False


def test_is_owner_false_when_user_id_none() -> None:
    audit = _audit(owner_id="user_a")
    assert is_owner(None, audit) is False


# ---------------------------------------------------------------------------
# can_user_see -- decision order (04-spec.md §2)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_owner_sees_own_audit() -> None:
    audit = _audit(owner_id="user_a")
    session = _FakeSession(share_row=None)
    assert await can_user_see("user_a", audit, session) is True  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_shared_user_sees_audit() -> None:
    audit = _audit(owner_id="user_a")
    share = AuditShare(
        audit_id=audit.id, shared_with_user_id="user_b", permission="view", created_by="user_a"
    )
    session = _FakeSession(share_row=share)
    assert await can_user_see("user_b", audit, session) is True  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_no_match_denies() -> None:
    audit = _audit(owner_id="user_a")
    session = _FakeSession(share_row=None)
    assert await can_user_see("user_c", audit, session) is False  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_none_user_denies() -> None:
    audit = _audit(owner_id="user_a")
    session = _FakeSession(share_row=None)
    assert await can_user_see(None, audit, session) is False  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_two_null_org_id_users_cannot_see_each_other() -> None:
    """The literal test named in 03-risk-assessment.md §5 hard constraint
    #3 -- two users with org_id = NULL (modelled here by users who simply
    have no `audit_shares` row and no ownership match) cannot see each
    other's audits. can_user_see never reads users.org_id at all."""
    audit_owned_by_a = _audit(owner_id="user_a")
    session = _FakeSession(share_row=None)
    # user_b has org_id=NULL (same as user_a) and no explicit share.
    assert await can_user_see("user_b", audit_owned_by_a, session) is False  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Structural absence of org_id [C3] -- contract test
# ---------------------------------------------------------------------------


def test_org_id_not_referenced_in_source() -> None:
    import core.auth.acl as acl_module

    source = Path(acl_module.__file__).read_text()
    assert ".org_id" not in source


# ---------------------------------------------------------------------------
# Observability [C7] -- require_audit_access/can_user_see log every decision
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_decision_is_logged() -> None:
    audit = _audit(owner_id="user_a")
    session = _FakeSession(share_row=None)
    with structlog.testing.capture_logs() as cap_logs:
        await can_user_see("user_a", audit, session)  # type: ignore[arg-type]
    decision_logs = [e for e in cap_logs if e.get("event") == "acl.decision"]
    assert len(decision_logs) == 1
    entry = decision_logs[0]
    assert entry["user_id"] == "user_a"
    assert entry["audit_id"] == str(audit.id)
    assert entry["decision"] == "allow"
    assert entry["reason"] == "owner"


@pytest.mark.asyncio
async def test_deny_decision_reason_is_no_match() -> None:
    audit = _audit(owner_id="user_a")
    session = _FakeSession(share_row=None)
    with structlog.testing.capture_logs() as cap_logs:
        await can_user_see("user_stranger", audit, session)  # type: ignore[arg-type]
    decision_logs = [e for e in cap_logs if e.get("event") == "acl.decision"]
    assert len(decision_logs) == 1
    assert decision_logs[0]["decision"] == "deny"
    assert decision_logs[0]["reason"] == "no_match"
