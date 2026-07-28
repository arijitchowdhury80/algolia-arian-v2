"""Tests for Task 5's by-section chunking of Audit.audit_data.

Uses a real published audit_data fixture (docs/temp/fc/belk-audit-data.json)
so the chunker is exercised against the actual report shape, not an invented
one -- per the task-5 brief's instruction to check an existing audit's JSON
structure before writing the pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from prism_platform.pipeline.chunking import Chunk, chunk_audit_data

FIXTURE_PATH = Path(__file__).parent.parent.parent / "docs/temp/fc/belk-audit-data.json"


@pytest.fixture
def real_audit_data() -> dict:
    if not FIXTURE_PATH.exists():
        pytest.skip(f"fixture not present at {FIXTURE_PATH}")
    return json.loads(FIXTURE_PATH.read_text())


def test_chunk_audit_data_returns_one_chunk_per_top_level_section(real_audit_data: dict) -> None:
    chunks = chunk_audit_data(real_audit_data)
    section_names = {c.section_name for c in chunks}
    # Every non-empty top-level key in the real fixture should produce a chunk.
    non_empty_keys = {k for k, v in real_audit_data.items() if v not in (None, "", [], {})}
    assert section_names == non_empty_keys


def test_chunk_audit_data_chunks_are_named_and_nonempty(real_audit_data: dict) -> None:
    chunks = chunk_audit_data(real_audit_data)
    assert len(chunks) > 0
    for chunk in chunks:
        assert isinstance(chunk, Chunk)
        assert chunk.section_name
        assert chunk.text.strip()


def test_chunk_audit_data_skips_empty_sections() -> None:
    data = {
        "meta": {"company": "Acme", "domain": "acme.com"},
        "empty_list": [],
        "empty_dict": {},
        "empty_string": "",
        "none_value": None,
    }
    chunks = chunk_audit_data(data)
    assert {c.section_name for c in chunks} == {"meta"}


def test_chunk_audit_data_preserves_section_content_as_readable_text() -> None:
    data = {"score": {"overall": 3.7, "verdict": "MODERATE"}}
    chunks = chunk_audit_data(data)
    assert len(chunks) == 1
    assert "3.7" in chunks[0].text
    assert "MODERATE" in chunks[0].text


def test_chunk_audit_data_empty_input_returns_no_chunks() -> None:
    assert chunk_audit_data({}) == []


def test_chunk_audit_data_is_deterministic(real_audit_data: dict) -> None:
    first = chunk_audit_data(real_audit_data)
    second = chunk_audit_data(real_audit_data)
    assert [(c.section_name, c.text) for c in first] == [(c.section_name, c.text) for c in second]
