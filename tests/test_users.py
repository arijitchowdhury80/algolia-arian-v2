"""Tests for the users tenant-identity table + upsert router.

Pure-logic tests run anywhere. DB tests (@pytest.mark.db) need a live Postgres
with migration 009 applied:  pytest tests/test_users.py -m 'not db' -v
"""

from __future__ import annotations


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
