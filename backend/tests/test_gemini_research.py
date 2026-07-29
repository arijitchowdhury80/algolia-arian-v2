"""Tests for GeminiResearchClient — the Gemini + Google-Search research backend.

Pure-logic tests: request-payload building and response parsing against the
verified generateContent grounding wire shape. No network, no key.

Read receipt (Google docs, 2026-06-29 — generate-content/google-search):
  request:  "tools": [ { "google_search": {} } ]   (snake_case)
  response: candidates[0].content.parts[].text                 -> answer
            candidates[0].groundingMetadata.groundingChunks[].web.uri/.title -> citations
            candidates[0].groundingMetadata.webSearchQueries    -> queries
"""

from __future__ import annotations

from prism_platform.v2.agent_api import AgentAPIResponse
from prism_platform.v2.gemini_api import GeminiResearchClient

# ---------------------------------------------------------------------------
# _build_payload — request shape
# ---------------------------------------------------------------------------


def test_payload_enables_google_search_tool_snake_case():
    payload = GeminiResearchClient._build_payload(
        system_prompt="be precise", user_prompt="research", temperature=0.1, max_tokens=4096
    )
    # snake_case google_search, per the read receipt
    assert payload["tools"] == [{"google_search": {}}]


def test_payload_carries_system_instruction_and_user_contents():
    payload = GeminiResearchClient._build_payload(
        system_prompt="SYS", user_prompt="USER", temperature=0.2, max_tokens=100
    )
    assert payload["system_instruction"]["parts"][0]["text"] == "SYS"
    assert payload["contents"][0]["role"] == "user"
    assert payload["contents"][0]["parts"][0]["text"] == "USER"
    assert payload["generationConfig"]["temperature"] == 0.2
    assert payload["generationConfig"]["maxOutputTokens"] == 100


# ---------------------------------------------------------------------------
# _parse_response — response shape
# ---------------------------------------------------------------------------


_SAMPLE = {
    "candidates": [
        {
            "content": {"parts": [{"text": '{"revenue": "x"}'}]},
            "groundingMetadata": {
                "webSearchQueries": ["petsmart revenue"],
                "groundingChunks": [
                    {"web": {"uri": "https://a.com/1", "title": "a.com"}},
                    {"web": {"uri": "https://b.com/2", "title": "b.com"}},
                ],
            },
        }
    ]
}


def test_parse_extracts_text_and_citations():
    resp = GeminiResearchClient._parse_response(_SAMPLE)
    assert isinstance(resp, AgentAPIResponse)
    assert resp.content == '{"revenue": "x"}'
    assert resp.citations == ["https://a.com/1", "https://b.com/2"]


def test_parse_joins_multiple_text_parts():
    data = {"candidates": [{"content": {"parts": [{"text": "a"}, {"text": "b"}]}}]}
    resp = GeminiResearchClient._parse_response(data)
    assert resp.content == "ab"


def test_parse_strips_json_code_fences():
    data = {"candidates": [{"content": {"parts": [{"text": '```json\n{"k": 1}\n```'}]}}]}
    resp = GeminiResearchClient._parse_response(data)
    assert resp.content == '{"k": 1}'


def test_parse_no_grounding_chunks_yields_empty_citations():
    data = {"candidates": [{"content": {"parts": [{"text": "{}"}]}}]}
    resp = GeminiResearchClient._parse_response(data)
    assert resp.citations == []


def test_parse_raises_on_no_candidates():
    import pytest

    with pytest.raises(ValueError, match=r"[Nn]o candidates"):
        GeminiResearchClient._parse_response({"candidates": []})


# ---------------------------------------------------------------------------
# model resolution — non-gemini model names fall back to the client default
# ---------------------------------------------------------------------------


def test_resolve_model_passes_gemini_through():
    c = GeminiResearchClient(api_key="x", model="gemini-2.5-flash")
    assert c._resolve_model("gemini-2.5-pro") == "gemini-2.5-pro"


def test_resolve_model_maps_perplexity_name_to_default():
    # The executor passes Perplexity model names (sonar-pro); the Gemini client
    # must not forward those — it falls back to its configured default.
    c = GeminiResearchClient(api_key="x", model="gemini-2.5-flash")
    assert c._resolve_model("sonar-pro") == "gemini-2.5-flash"
    assert c._resolve_model("") == "gemini-2.5-flash"
