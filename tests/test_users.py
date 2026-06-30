"""Tests for the users tenant-identity table + upsert router.

Pure-logic tests run anywhere. DB tests (@pytest.mark.db) need a live Postgres
with migration 009 applied:  pytest tests/test_users.py -m 'not db' -v
"""

from __future__ import annotations

import pytest


class TestUserModel:
    def test_user_table_name(self) -> None:
        from prism_platform.db.models import User

        assert User.__tablename__ == "users"

    def test_user_has_tenant_columns(self) -> None:
        from prism_platform.db.models import User

        cols = set(User.__table__.columns.keys())
        assert {"id", "email", "name", "org_id", "created_at", "updated_at"} <= cols

    def test_user_id_is_primary_key(self) -> None:
        from prism_platform.db.models import User

        assert User.__table__.primary_key.columns.keys() == ["id"]  # type: ignore[attr-defined]


class TestUpsertModels:
    def test_request_forbids_extra(self) -> None:
        from pydantic import ValidationError

        from prism_platform.api.routers.users import UpsertUserRequest

        with pytest.raises(ValidationError):
            UpsertUserRequest(id="user_1", surprise="x")

    def test_request_minimal(self) -> None:
        from prism_platform.api.routers.users import UpsertUserRequest

        assert UpsertUserRequest(id="user_1").email is None

    def test_response_shape(self) -> None:
        from prism_platform.api.routers.users import UpsertUserResponse

        r = UpsertUserResponse(id="user_1", created=True, updated=False)
        assert r.created and not r.updated


@pytest.mark.db
@pytest.mark.asyncio
async def test_upsert_creates_then_updates() -> None:
    from sqlalchemy import delete, select

    from prism_platform.api.routers.users import UpsertUserRequest, upsert_user
    from prism_platform.db.models import User
    from prism_platform.db.session import get_session

    uid = "user_test_slice1_upsert"
    async for session in get_session():
        await session.execute(delete(User).where(User.id == uid))
        await session.commit()

    async for session in get_session():
        r1 = await upsert_user(UpsertUserRequest(id=uid, email="a@x.com", name="Rob"), session)
        await session.commit()
    assert r1.created and not r1.updated

    async for session in get_session():
        r2 = await upsert_user(
            UpsertUserRequest(id=uid, email="rob@algolia.com", name="Rob R"), session
        )
        await session.commit()
    assert not r2.created and r2.updated and r2.id == uid

    async for session in get_session():
        row = (await session.execute(select(User).where(User.id == uid))).scalar_one()
        assert row.email == "rob@algolia.com"

    async for session in get_session():
        await session.execute(delete(User).where(User.id == uid))
        await session.commit()
