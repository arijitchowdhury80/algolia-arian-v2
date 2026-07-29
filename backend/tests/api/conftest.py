"""Shared fake-session helpers for tests/api/* -- FastAPI TestClient + a
fake DB session, no real Postgres needed for router-level ACL wiring
tests. Real-DB (@pytest.mark.db) join/window-function correctness tests
live in tests/auth/test_queries.py.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from prism_platform.db.models import Audit


class FakeScalars:
    def __init__(self, values: list) -> None:
        self._values = list(values)

    def all(self) -> list:
        return list(self._values)

    def first(self):
        return self._values[0] if self._values else None

    def unique(self) -> FakeScalars:
        return self


class FakeScalarResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value

    def scalar_one(self) -> object:
        if self._value is None:
            raise LookupError("no row")
        return self._value

    def scalars(self) -> FakeScalars:
        if isinstance(self._value, list):
            return FakeScalars(self._value)
        return FakeScalars([self._value] if self._value is not None else [])

    def one(self) -> object:
        return self._value


class FakeQueueSession:
    """Returns queued results (in call order) for `select()` statements,
    and simulates ORM Python-side default application on add()/flush()
    for Account/Audit -- just enough fidelity for router-level ACL wiring
    tests, without a real Postgres."""

    def __init__(self, results: list) -> None:
        self._results = list(results)
        self._added: list = []
        # Objects that have been through add()+flush() at least once --
        # kept around (unlike _added) so tests can inspect what was
        # written after the request completes.
        self.flushed: list = []

    async def execute(self, stmt: object) -> FakeScalarResult:
        return FakeScalarResult(self._results.pop(0))

    def add(self, obj: object) -> None:
        self._added.append(obj)

    async def flush(self) -> None:
        for obj in self._added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()
            if isinstance(obj, Audit):
                if obj.created_at is None:
                    obj.created_at = datetime.now(UTC)
                if obj.status is None:
                    obj.status = "pending"
        self.flushed.extend(self._added)
        self._added.clear()
