"""Tests for intel-social v2 module.

Covers:
  - SocialPost and SocialIntelOutput schema validation
  - Config correctness
  - Playbook existence and metadata
  - collector.collect() graceful degradation:
      - no Apify key → returns empty lists (non-fatal)
      - no intel-company upstream → returns empty lists (non-fatal)
      - missing linkedin_url and twitter_handle → returns empty lists (non-fatal)
      - Apify HTTP failure → returns empty lists (non-fatal)
      - happy path → posts shaped and returned correctly
  - Registration in V2_MODULE_REGISTRY
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from prism_platform.v2.modules.intel_social.config import INTEL_SOCIAL_CONFIG
from prism_platform.v2.modules.intel_social.schemas import SocialIntelOutput, SocialPost
from prism_platform.v2.playbook import PlaybookLoader
from prism_platform.v2.types import ExecutionContextV2

PLAYBOOK_PATH = (
    Path(__file__).parent.parent.parent / "prism_platform/v2/modules/intel_social/playbook.md"
)


# ── Helpers ────────────────────────────────────────────────────────────────


def _make_context(
    upstream: dict[str, Any] | None = None,
    domain: str = "algolia.com",
) -> ExecutionContextV2:
    ctx = ExecutionContextV2(
        audit_id=str(uuid4()),
        account_domain=domain,
        company_name="Algolia",
        industry="Enterprise Search",
    )
    if upstream is not None:
        ctx.upstream_results.update(upstream)
    return ctx


def _sample_linkedin_post() -> dict[str, Any]:
    return {
        "text": "We just launched our AI-powered search personalisation feature.",
        "date": "2026-06-01",
        "url": "https://linkedin.com/posts/algolia-123",
    }


def _sample_twitter_post() -> dict[str, Any]:
    return {
        "text": "Excited to share our new search relevance dashboard!",
        "created_at": "2026-06-05",
        "tweetUrl": "https://twitter.com/algolia/status/999",
    }


# ── SocialPost schema tests ────────────────────────────────────────────────


class TestSocialPost:
    def test_valid_post(self) -> None:
        p = SocialPost(
            text="We launched a new search experience.",
            platform="linkedin",
            date="2026-06-01",
            url="https://linkedin.com/posts/test",
            relevance_score=0.9,
            relevance_tags=["search_mention", "cx_focus"],
        )
        assert p.platform == "linkedin"
        assert p.relevance_score == 0.9

    def test_defaults_safe(self) -> None:
        p = SocialPost(text="hello", platform="twitter")
        assert p.relevance_score == 0.0
        assert p.relevance_tags == []
        assert p.date is None
        assert p.url is None

    def test_is_frozen(self) -> None:
        p = SocialPost(text="hello", platform="twitter")
        with pytest.raises((ValidationError, TypeError)):
            p.text = "changed"  # type: ignore[misc]

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            SocialPost(
                text="hello",
                platform="linkedin",
                extra_field="oops",  # type: ignore[call-arg]
            )


# ── SocialIntelOutput schema tests ─────────────────────────────────────────


class TestSocialIntelOutput:
    def test_valid_output(self) -> None:
        out = SocialIntelOutput(domain="algolia.com")
        assert out.domain == "algolia.com"
        assert out.linkedin_posts == []
        assert out.twitter_posts == []
        assert out.high_signal_posts == []
        assert out.signal_summary is None
        assert out.sources == []

    def test_with_posts(self) -> None:
        post = SocialPost(
            text="New search feature launched.",
            platform="linkedin",
            relevance_score=0.85,
        )
        out = SocialIntelOutput(
            domain="algolia.com",
            linkedin_posts=[post],
            high_signal_posts=[post],
            signal_summary="Algolia launched new search feature.",
            sources=["linkedin:https://linkedin.com/company/algolia"],
        )
        assert len(out.linkedin_posts) == 1
        assert len(out.high_signal_posts) == 1
        assert out.signal_summary is not None

    def test_domain_required(self) -> None:
        with pytest.raises(ValidationError):
            SocialIntelOutput()  # type: ignore[call-arg]

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            SocialIntelOutput(domain="algolia.com", unexpected="oops")  # type: ignore[call-arg]

    def test_json_schema_has_all_fields(self) -> None:
        schema = SocialIntelOutput.model_json_schema()
        props = schema["properties"]
        assert "domain" in props
        assert "linkedin_posts" in props
        assert "twitter_posts" in props
        assert "high_signal_posts" in props
        assert "signal_summary" in props
        assert "sources" in props


# ── Config tests ───────────────────────────────────────────────────────────


class TestIntelSocialConfig:
    def test_name(self) -> None:
        assert INTEL_SOCIAL_CONFIG.name == "intel-social"

    def test_version_v2(self) -> None:
        assert INTEL_SOCIAL_CONFIG.version.startswith("2.")

    def test_composes_intel_company(self) -> None:
        assert "intel-company" in INTEL_SOCIAL_CONFIG.composes

    def test_cost_tier(self) -> None:
        assert INTEL_SOCIAL_CONFIG.cost_tier == "pro-search"

    def test_api_clients_documents_apify(self) -> None:
        assert "apify" in INTEL_SOCIAL_CONFIG.api_clients

    def test_cache_ttl_days(self) -> None:
        # Social data is reasonably fresh at 7 days
        assert INTEL_SOCIAL_CONFIG.cache_ttl_days <= 14


# ── Playbook tests ─────────────────────────────────────────────────────────


class TestIntelSocialPlaybook:
    def test_playbook_exists(self) -> None:
        assert PLAYBOOK_PATH.exists(), f"Playbook not found at {PLAYBOOK_PATH}"

    def test_execution_strategy_is_prospect_only(self) -> None:
        loader = PlaybookLoader()
        meta, _ = loader.load(PLAYBOOK_PATH)
        assert meta.execution_strategy == "prospect-only"

    def test_playbook_references_upstream_posts(self) -> None:
        """Playbook must reference the upstream keys that the collector injects."""
        content = PLAYBOOK_PATH.read_text()
        assert "upstream_social_linkedin_posts" in content
        assert "upstream_social_twitter_posts" in content

    def test_playbook_has_relevance_scoring_guidance(self) -> None:
        content = PLAYBOOK_PATH.read_text()
        assert "relevance_score" in content
        assert "relevance_tags" in content


# ── Collector graceful degradation tests ──────────────────────────────────


class TestIntelSocialCollector:
    """All tests mock httpx — no real Apify calls."""

    @pytest.mark.asyncio
    async def test_no_apify_key_returns_empty(self) -> None:
        """If Apify key is not configured, collector returns empty lists immediately."""
        from prism_platform.v2.modules.intel_social.collector import collect

        ctx = _make_context(
            upstream={
                "intel-company": {
                    "company_linkedin_url": "https://linkedin.com/company/algolia",
                    "twitter_handle": "algolia",
                }
            }
        )

        mock_settings = MagicMock()
        mock_settings.apify_api_key = ""

        with patch("prism_platform.v2.modules.intel_social.collector.settings", mock_settings):
            result = await collect(ctx)

        assert result["linkedin_posts"] == []
        assert result["twitter_posts"] == []
        assert result["social_sources"] == []

    @pytest.mark.asyncio
    async def test_no_intel_company_upstream_returns_empty(self) -> None:
        """Missing intel-company upstream → graceful empty result."""
        from prism_platform.v2.modules.intel_social.collector import collect

        ctx = _make_context(upstream={})

        mock_settings = MagicMock()
        mock_settings.apify_api_key = "test-key-123"

        with patch("prism_platform.v2.modules.intel_social.collector.settings", mock_settings):
            result = await collect(ctx)

        assert result["linkedin_posts"] == []
        assert result["twitter_posts"] == []

    @pytest.mark.asyncio
    async def test_missing_linkedin_and_twitter_in_upstream_returns_empty(self) -> None:
        """intel-company upstream present but has no social URLs → no Apify calls."""
        from prism_platform.v2.modules.intel_social.collector import collect

        ctx = _make_context(
            upstream={
                "intel-company": {
                    "domain": "algolia.com",
                    "company_name": "Algolia",
                    # No linkedin URL, no twitter handle
                }
            }
        )

        mock_settings = MagicMock()
        mock_settings.apify_api_key = "test-key-123"

        with patch("prism_platform.v2.modules.intel_social.collector.settings", mock_settings):
            result = await collect(ctx)

        assert result["linkedin_posts"] == []
        assert result["twitter_posts"] == []
        assert result["social_sources"] == []

    @pytest.mark.asyncio
    async def test_apify_http_error_returns_empty(self) -> None:
        """Apify API returning an error → collector returns empty lists (non-fatal)."""
        import httpx

        from prism_platform.v2.modules.intel_social.collector import collect

        ctx = _make_context(
            upstream={
                "intel-company": {
                    "company_linkedin_url": "https://linkedin.com/company/algolia",
                    "twitter_handle": "algolia",
                }
            }
        )

        mock_settings = MagicMock()
        mock_settings.apify_api_key = "test-key-123"

        # Mock httpx.AsyncClient to raise on POST (actor start)
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("connection refused"))

        with (
            patch("prism_platform.v2.modules.intel_social.collector.settings", mock_settings),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            result = await collect(ctx)

        assert result["linkedin_posts"] == []
        assert result["twitter_posts"] == []

    @pytest.mark.asyncio
    async def test_happy_path_linkedin_and_twitter(self) -> None:
        """With valid Apify key and upstream URLs, posts are collected and shaped."""
        from prism_platform.v2.modules.intel_social.collector import collect

        ctx = _make_context(
            upstream={
                "intel-company": {
                    "company_linkedin_url": "https://linkedin.com/company/algolia",
                    "twitter_handle": "algolia",
                }
            }
        )

        mock_settings = MagicMock()
        mock_settings.apify_api_key = "test-key-abc"

        # Build a deterministic Apify mock: start → poll (SUCCEEDED) → items
        def _make_run_resp(run_id: str, dataset_id: str) -> MagicMock:
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = {
                "data": {"id": run_id, "defaultDatasetId": dataset_id, "status": "SUCCEEDED"}
            }
            return resp

        def _make_status_resp(status: str = "SUCCEEDED") -> MagicMock:
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = {"data": {"status": status}}
            return resp

        def _make_items_resp(items: list[dict[str, Any]]) -> MagicMock:
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = items
            return resp

        linkedin_items = [_sample_linkedin_post()]
        twitter_items = [_sample_twitter_post()]

        # POST (start) returns run info; GET (status) returns SUCCEEDED; GET (items) returns posts
        # Called for LinkedIn first, then Twitter — two separate actor runs
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        li_run = _make_run_resp("run-li-1", "ds-li-1")
        tw_run = _make_run_resp("run-tw-1", "ds-tw-1")
        li_status = _make_status_resp("SUCCEEDED")
        tw_status = _make_status_resp("SUCCEEDED")
        li_items_resp = _make_items_resp(linkedin_items)
        tw_items_resp = _make_items_resp(twitter_items)

        # POST calls: first = LinkedIn actor start, second = Twitter actor start
        mock_client.post = AsyncMock(side_effect=[li_run, tw_run])
        # GET calls: status polls then item fetches (LinkedIn poll, LinkedIn items, Twitter poll, Twitter items)
        mock_client.get = AsyncMock(
            side_effect=[li_status, li_items_resp, tw_status, tw_items_resp]
        )

        with (
            patch("prism_platform.v2.modules.intel_social.collector.settings", mock_settings),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            result = await collect(ctx)

        assert len(result["linkedin_posts"]) == 1
        assert len(result["twitter_posts"]) == 1

        li_post = result["linkedin_posts"][0]
        assert li_post["platform"] == "linkedin"
        assert "search" in li_post["text"].lower() or "AI" in li_post["text"]
        assert li_post["relevance_score"] == 0.0  # LLM sets this in Track 2

        tw_post = result["twitter_posts"][0]
        assert tw_post["platform"] == "twitter"

        assert "linkedin:https://linkedin.com/company/algolia" in result["social_sources"]
        assert "twitter:@algolia" in result["social_sources"]

    @pytest.mark.asyncio
    async def test_twitter_handle_normalised_from_url(self) -> None:
        """If twitter_handle is stored as a full URL, the collector normalises it."""
        from prism_platform.v2.modules.intel_social.collector import collect

        ctx = _make_context(
            upstream={
                "intel-company": {
                    # Full URL stored as handle — must be normalised to just "algolia"
                    "twitter_handle": "https://twitter.com/algolia",
                    # No LinkedIn URL
                }
            }
        )

        mock_settings = MagicMock()
        mock_settings.apify_api_key = "test-key-abc"

        def _make_run_resp() -> MagicMock:
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = {
                "data": {"id": "run-1", "defaultDatasetId": "ds-1", "status": "SUCCEEDED"}
            }
            return resp

        def _make_status_resp() -> MagicMock:
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = {"data": {"status": "SUCCEEDED"}}
            return resp

        def _make_items_resp() -> MagicMock:
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = [_sample_twitter_post()]
            return resp

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=_make_run_resp())
        mock_client.get = AsyncMock(side_effect=[_make_status_resp(), _make_items_resp()])

        with (
            patch("prism_platform.v2.modules.intel_social.collector.settings", mock_settings),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            result = await collect(ctx)

        # Check the source descriptor uses the normalised handle
        assert any("@algolia" in s for s in result["social_sources"])
        assert result["twitter_posts"][0]["platform"] == "twitter"

    @pytest.mark.asyncio
    async def test_apify_run_failed_status_returns_empty(self) -> None:
        """If the Apify run ends in FAILED status, return empty list for that platform."""
        from prism_platform.v2.modules.intel_social.collector import collect

        ctx = _make_context(
            upstream={
                "intel-company": {
                    "company_linkedin_url": "https://linkedin.com/company/algolia",
                }
            }
        )

        mock_settings = MagicMock()
        mock_settings.apify_api_key = "test-key-abc"

        run_resp = MagicMock()
        run_resp.raise_for_status = MagicMock()
        run_resp.json.return_value = {
            "data": {"id": "run-bad", "defaultDatasetId": "ds-bad", "status": "RUNNING"}
        }

        failed_status = MagicMock()
        failed_status.raise_for_status = MagicMock()
        failed_status.json.return_value = {"data": {"status": "FAILED"}}

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=run_resp)
        mock_client.get = AsyncMock(return_value=failed_status)

        with (
            patch("prism_platform.v2.modules.intel_social.collector.settings", mock_settings),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            result = await collect(ctx)

        assert result["linkedin_posts"] == []


# ── Registry integration test ──────────────────────────────────────────────


class TestIntelSocialRegistration:
    def test_registered_in_v2_registry(self) -> None:
        from prism_platform.v2.registry import V2_MODULE_REGISTRY, register_all_v2_modules

        register_all_v2_modules()
        assert "intel-social" in V2_MODULE_REGISTRY

    def test_registry_handle_has_collector(self) -> None:
        from prism_platform.v2.registry import V2_MODULE_REGISTRY, register_all_v2_modules

        register_all_v2_modules()
        handle = V2_MODULE_REGISTRY["intel-social"]
        assert handle.collector is not None

    def test_registry_handle_output_schema(self) -> None:
        from prism_platform.v2.registry import V2_MODULE_REGISTRY, register_all_v2_modules

        register_all_v2_modules()
        handle = V2_MODULE_REGISTRY["intel-social"]
        assert handle.output_schema is SocialIntelOutput

    def test_registry_handle_playbook_exists(self) -> None:
        from prism_platform.v2.registry import V2_MODULE_REGISTRY, register_all_v2_modules

        register_all_v2_modules()
        handle = V2_MODULE_REGISTRY["intel-social"]
        assert handle.playbook_path.exists()
