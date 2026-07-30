"""ACL seam -- the single implementation of "can this user see this audit?"

Every endpoint that gates audit access imports `is_owner`/`can_user_see`
from here (04-spec.md §2 [C2]) -- no endpoint re-implements an inline
ownership check. Default-deny: every branch below is a hard `return False`
on non-match, no fallthrough that defaults True.

`org_id` [C3]: the `org_id` column on the `users` table is NOT read
anywhere in this module. Clerk Organizations support is out of scope for
this slice (04-spec.md §2 step 4) -- structurally absent, not just
behaviorally gated off. Re-added only when Clerk Orgs is explicitly turned
on, as its own future change. (A contract test,
tests/auth/test_acl.py::test_org_id_not_referenced_in_source, greps this
file's source text for the literal attribute-access pattern to guard
against regression -- note that even this docstring avoids writing that
pattern, by design.)
"""

from __future__ import annotations

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models import Audit, AuditShare

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


def is_owner(user_id: str | None, audit: Audit) -> bool:
    """True iff `user_id` is the audit's recorded owner.

    A real function, reused by `can_user_see()` (step 2 below) and the
    shares-write endpoint (`server/api/routers/audits.py::share_audit`)
    -- not a second inline `==` comparison [I-4].
    """
    if user_id is None:
        return False
    return audit.user_id == user_id


async def can_user_see(user_id: str | None, audit: Audit, session: AsyncSession) -> bool:
    """Default-deny. Returns True only on an explicit, verified allow path.

    Decision order (04-spec.md §2), each a hard `return False` on
    non-match -- no fallthrough branch that defaults True:
      1. `user_id is None` -> False.
      2. `is_owner(user_id, audit)` -> True.
      3. Row exists in `audit_shares` for `(audit.id, user_id)` -> True.
      4. `org_id` branch (org-based visibility): not implemented in this
         slice -- see module docstring [C3].
      5. Anything else (malformed input, exception) -> False. No
         try/except that swallows to True.

    Every decision is logged as a single `acl.decision` event
    (`{user_id, audit_id, decision, reason}`) -- the repudiation-coverage
    fix [C7].
    """
    audit_id_str = str(audit.id)

    if user_id is None:
        logger.info(
            "acl.decision",
            user_id=user_id,
            audit_id=audit_id_str,
            decision="deny",
            reason="no_match",
        )
        return False

    if is_owner(user_id, audit):
        logger.info(
            "acl.decision", user_id=user_id, audit_id=audit_id_str, decision="allow", reason="owner"
        )
        return True

    try:
        result = await session.execute(
            select(AuditShare).where(
                AuditShare.audit_id == audit.id,
                AuditShare.shared_with_user_id == user_id,
            )
        )
        share = result.scalar_one_or_none()
    except Exception as exc:
        logger.error("acl.decision_error", user_id=user_id, audit_id=audit_id_str, error=str(exc))
        logger.info(
            "acl.decision",
            user_id=user_id,
            audit_id=audit_id_str,
            decision="deny",
            reason="no_match",
        )
        return False

    if share is not None:
        logger.info(
            "acl.decision",
            user_id=user_id,
            audit_id=audit_id_str,
            decision="allow",
            reason="shared",
        )
        return True

    logger.info(
        "acl.decision", user_id=user_id, audit_id=audit_id_str, decision="deny", reason="no_match"
    )
    return False
