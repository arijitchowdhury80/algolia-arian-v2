"""Tests for the research-client factory — the single provider decision point.

Why this exists: every call site used to construct AgentAPIClient (Perplexity)
directly, so the provider was hardcoded in six places and `ENRICHER_PROVIDER`
had no effect on module execution. A dead Perplexity key therefore killed the
whole v2 pipeline with no way to switch. These tests pin the factory's contract:
explicit selection wins, auto-detection prefers Gemini, and an unsupported or
keyless selection fails loudly instead of silently falling back to Perplexity.
"""

from __future__ import annotations

import pytest

from core.agent_api import AgentAPIClient
from core.gemini_api import GeminiResearchClient
from core.research_client import (
    ResearchProviderError,
    make_research_client,
    resolve_research_provider,
)


class _FakeSettings:
    """Minimal stand-in for Settings — only the fields the factory reads."""

    def __init__(
        self,
        research_provider: str = "",
        gemini_api_key: str = "",
        perplexity_api_key: str = "",
        gemini_model: str = "gemini-2.5-flash",
    ) -> None:
        self.research_provider = research_provider
        self.gemini_api_key = gemini_api_key
        self.perplexity_api_key = perplexity_api_key
        self.gemini_model = gemini_model


# --- resolve_research_provider ---


def test_explicit_gemini_wins_even_when_perplexity_key_present() -> None:
    s = _FakeSettings(research_provider="gemini", gemini_api_key="g", perplexity_api_key="p")
    assert resolve_research_provider(s) == "gemini"


def test_explicit_perplexity_is_honoured() -> None:
    s = _FakeSettings(research_provider="perplexity", gemini_api_key="g", perplexity_api_key="p")
    assert resolve_research_provider(s) == "perplexity"


def test_explicit_selection_is_case_and_whitespace_insensitive() -> None:
    s = _FakeSettings(research_provider="  Gemini ", gemini_api_key="g")
    assert resolve_research_provider(s) == "gemini"


def test_autodetect_prefers_gemini_when_both_keys_present() -> None:
    s = _FakeSettings(gemini_api_key="g", perplexity_api_key="p")
    assert resolve_research_provider(s) == "gemini"


def test_autodetect_falls_back_to_perplexity_when_only_that_key_is_set() -> None:
    s = _FakeSettings(perplexity_api_key="p")
    assert resolve_research_provider(s) == "perplexity"


def test_no_keys_raises_rather_than_guessing() -> None:
    with pytest.raises(ResearchProviderError, match="no research provider"):
        resolve_research_provider(_FakeSettings())


def test_unsupported_provider_raises_and_never_silently_uses_perplexity() -> None:
    """This is the original bug: ENRICHER_PROVIDER=anthropic silently ran Perplexity."""
    s = _FakeSettings(research_provider="anthropic", perplexity_api_key="p")
    with pytest.raises(ResearchProviderError, match="anthropic"):
        resolve_research_provider(s)


def test_explicit_provider_without_its_key_raises() -> None:
    s = _FakeSettings(research_provider="gemini", perplexity_api_key="p")
    with pytest.raises(ResearchProviderError, match="GEMINI_API_KEY"):
        resolve_research_provider(s)


# --- make_research_client ---


def test_factory_builds_gemini_client() -> None:
    s = _FakeSettings(research_provider="gemini", gemini_api_key="g")
    client = make_research_client(timeout=30.0, settings_obj=s)
    assert isinstance(client, GeminiResearchClient)


def test_factory_builds_perplexity_client() -> None:
    s = _FakeSettings(research_provider="perplexity", perplexity_api_key="p")
    client = make_research_client(timeout=30.0, settings_obj=s)
    assert isinstance(client, AgentAPIClient)


def test_both_backends_expose_a_provider_label() -> None:
    """Call sites log ``client.provider``; re-deriving it from settings can raise."""
    assert AgentAPIClient.provider == "perplexity"
    assert GeminiResearchClient.provider == "gemini"


def test_factory_output_satisfies_the_research_contract() -> None:
    """Both backends must be drop-in for ModuleExecutor."""
    for s in (
        _FakeSettings(research_provider="gemini", gemini_api_key="g"),
        _FakeSettings(research_provider="perplexity", perplexity_api_key="p"),
    ):
        client = make_research_client(timeout=30.0, settings_obj=s)
        assert callable(client.research)
        assert callable(client.close)
