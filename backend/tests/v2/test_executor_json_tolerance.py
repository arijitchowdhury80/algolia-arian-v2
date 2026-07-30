"""Executor JSON parsing must tolerate raw control characters in string values.

Found live: on a Gemini-backed dell.com run, 2 of 13 modules failed with
"Invalid control character at ..." because Gemini embeds literal newlines and
tabs inside JSON string values. Strict json.loads rejects those; the data
itself is fine. Perplexity happened to escape them, so the pipeline had never
hit this. Providers are swappable, so the parser must be tolerant.
"""

from __future__ import annotations

import json

import pytest

from core.executor import _loads_tolerant


def test_plain_json_still_parses() -> None:
    assert _loads_tolerant('{"a": 1}') == {"a": 1}


def test_literal_newline_inside_a_string_value_parses() -> None:
    raw = '{"summary": "line one\nline two"}'
    with pytest.raises(json.JSONDecodeError):  # precondition: strict parsing rejects it
        json.loads(raw)
    assert _loads_tolerant(raw) == {"summary": "line one\nline two"}


def test_literal_tab_inside_a_string_value_parses() -> None:
    assert _loads_tolerant('{"k": "a\tb"}') == {"k": "a\tb"}


def test_genuinely_malformed_json_still_raises() -> None:
    """Tolerance must not swallow real syntax errors into silent empty output."""
    with pytest.raises(json.JSONDecodeError):
        _loads_tolerant('{"a": ')


def test_nested_structures_survive() -> None:
    raw = '{"items": [{"note": "has\na break"}, {"note": "clean"}]}'
    assert _loads_tolerant(raw)["items"][0]["note"] == "has\na break"
