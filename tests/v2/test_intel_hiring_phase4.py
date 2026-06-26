"""Tests for intel-hiring Scout Phase 4.

Covers AC-1 through AC-12 from the PRD.

Layer split:
  - TestTier2Stealth       — unit tests for prism_platform/browser/tier2_stealth.py
  - TestHiringFetcher      — unit tests for intel_hiring/fetcher.py
  - TestHiringFetchResult  — contract tests (Pydantic model boundary)
  - TestPlaybookCareer     — contract test: upstream_results["careers_page"] resolves correctly
  - TestHiringPipeline     — integration tests for _run_intel_hiring_pipeline()
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from prism_platform.browser.types import FetchOptions, FetchTier
from prism_platform.v2.executor import ModuleExecutorResult
from prism_platform.v2.modules.intel_hiring.fetcher import (
    HiringFetchResult,
    _is_linkedin_url,
    _truncate,
    fetch_careers_page,
)
from prism_platform.v2.playbook import PlaybookLoader
from prism_platform.v2.types import ExecutionContextV2

HIRING_PLAYBOOK_PATH = (
    Path(__file__).parent.parent.parent
    / "prism_platform"
    / "v2"
    / "modules"
    / "intel_hiring"
    / "playbook.md"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _scout_response(
    *,
    success: bool = True,
    markdown: str = "job listing content " * 20,
    url: str = "https://example.com/careers",
    error: str | None = None,
    raw_html: str | None = None,
) -> MagicMock:
    """Build a mock ScrapeResponse that matches the Scout API."""
    resp = MagicMock()
    resp.success = success
    resp.markdown = markdown
    resp.raw_html = raw_html
    resp.error = error
    resp.metadata = MagicMock()
    resp.metadata.url = url
    return resp


# ---------------------------------------------------------------------------
# Layer 1 — Unit: tier2_stealth.fetch_stealth()
# ---------------------------------------------------------------------------


class TestTier2Stealth:
    """AC-1 through AC-4: fetch_stealth() maps Scout responses to FetchResult."""

    @pytest.mark.asyncio
    async def test_success_returns_playwright_tier(self) -> None:
        """AC-1: Success response → tier_used=PLAYWRIGHT."""
        from prism_platform.browser.tier2_stealth import fetch_stealth

        resp = _scout_response(markdown="x" * 500, url="https://example.com/careers")
        mock_crawler = AsyncMock()
        mock_crawler.scrape.return_value = resp

        with patch("scout.core.ScoutCrawler", return_value=mock_crawler):
            result = await fetch_stealth(
                "https://example.com/careers",
                FetchOptions(min_content_length=100),
            )

        assert result.tier_used == FetchTier.PLAYWRIGHT
        assert result.status_code == 200
        assert result.error is None

    @pytest.mark.asyncio
    async def test_exception_returns_error_result(self) -> None:
        """AC-2: ScoutCrawler raises → FetchResult with error set."""
        from prism_platform.browser.tier2_stealth import fetch_stealth

        mock_crawler = AsyncMock()
        mock_crawler.scrape.side_effect = RuntimeError("playwright crash")

        with patch("scout.core.ScoutCrawler", return_value=mock_crawler):
            result = await fetch_stealth("https://example.com", FetchOptions())

        assert result.tier_used == FetchTier.PLAYWRIGHT
        assert result.error is not None
        assert "scout_exception" in result.error
        assert "RuntimeError" in result.error

    @pytest.mark.asyncio
    async def test_short_content_sets_bot_blocked(self) -> None:
        """AC-3: Content shorter than min_content_length → is_bot_blocked=True."""
        from prism_platform.browser.tier2_stealth import fetch_stealth

        resp = _scout_response(markdown="hi", url="https://example.com/careers")
        mock_crawler = AsyncMock()
        mock_crawler.scrape.return_value = resp

        with patch("scout.core.ScoutCrawler", return_value=mock_crawler):
            result = await fetch_stealth(
                "https://example.com/careers",
                FetchOptions(min_content_length=500),
            )

        assert result.is_bot_blocked is True
        assert result.tier_used == FetchTier.PLAYWRIGHT

    @pytest.mark.asyncio
    async def test_final_url_from_metadata(self) -> None:
        """AC-4: FetchResult.url comes from resp.metadata.url (redirect tracking)."""
        from prism_platform.browser.tier2_stealth import fetch_stealth

        redirect_target = "https://example.com/careers/en-us"
        resp = _scout_response(markdown="x" * 500, url=redirect_target)
        mock_crawler = AsyncMock()
        mock_crawler.scrape.return_value = resp

        with patch("scout.core.ScoutCrawler", return_value=mock_crawler):
            result = await fetch_stealth(
                "https://example.com/careers",
                FetchOptions(min_content_length=100),
            )

        assert result.url == redirect_target


# ---------------------------------------------------------------------------
# Layer 1 — Unit: intel_hiring/fetcher.py
# ---------------------------------------------------------------------------


class TestHiringFetcher:
    """AC-5 through AC-7: fetch_careers_page() career page discovery."""

    @pytest.mark.asyncio
    async def test_returns_content_when_scout_succeeds(self) -> None:
        """AC-5: Scout finds career page → HiringFetchResult with content."""
        rich_content = "Senior Search Engineer\n" * 30  # > _MIN_CONTENT_CHARS
        resp = _scout_response(markdown=rich_content, url="https://dell.com/careers")

        mock_crawler = AsyncMock()
        mock_crawler.scrape.return_value = resp

        with patch("scout.core.ScoutCrawler", return_value=mock_crawler):
            result = await fetch_careers_page("dell.com")

        assert isinstance(result, HiringFetchResult)
        assert len(result.careers_page_content) > 0
        assert result.redirected_to_linkedin is False

    @pytest.mark.asyncio
    async def test_linkedin_redirect_detected(self) -> None:
        """AC-6: Scout final URL contains linkedin.com → redirected_to_linkedin=True."""
        resp = _scout_response(
            markdown="x" * 500,
            url="https://www.linkedin.com/jobs/company/dell",
        )
        mock_crawler = AsyncMock()
        mock_crawler.scrape.return_value = resp

        with patch("scout.core.ScoutCrawler", return_value=mock_crawler):
            result = await fetch_careers_page("dell.com")

        assert result.redirected_to_linkedin is True
        assert result.careers_page_content == ""

    @pytest.mark.asyncio
    async def test_all_attempts_fail_returns_empty(self) -> None:
        """AC-7: All Scout scrapes fail → empty HiringFetchResult (non-fatal)."""
        fail_resp = _scout_response(success=False, markdown="", url="https://dell.com/careers")
        mock_crawler = AsyncMock()
        mock_crawler.scrape.return_value = fail_resp

        with (
            patch("scout.core.ScoutCrawler", return_value=mock_crawler),
            patch(
                "prism_platform.v2.modules.intel_hiring.fetcher._quick_httpx_probe",
                new_callable=AsyncMock,
                return_value=(False, ""),
            ),
        ):
            result = await fetch_careers_page("dell.com")

        assert result.careers_page_content == ""
        assert result.careers_url == ""
        assert result.redirected_to_linkedin is False

    def test_is_linkedin_url_detects_subdomain(self) -> None:
        assert _is_linkedin_url("https://www.linkedin.com/jobs/view/123") is True
        assert _is_linkedin_url("https://careers.linkedin.com/company/dell") is True

    def test_is_linkedin_url_ignores_non_linkedin(self) -> None:
        assert _is_linkedin_url("https://dell.com/careers") is False
        assert _is_linkedin_url("https://indeed.com/jobs") is False

    def test_truncate_at_limit(self) -> None:
        long_content = "x" * 10000
        result = _truncate(long_content, max_chars=8000)
        assert len(result) == 8000

    def test_truncate_short_content_unchanged(self) -> None:
        short = "short content"
        assert _truncate(short) == short


# ---------------------------------------------------------------------------
# Layer 2 — Contract: HiringFetchResult model
# ---------------------------------------------------------------------------


class TestHiringFetchResult:
    """AC-11: HiringFetchResult is a frozen Pydantic model."""

    def test_model_is_frozen(self) -> None:
        """AC-11: Cannot mutate HiringFetchResult after creation."""
        from pydantic import ValidationError

        result = HiringFetchResult(careers_page_content="content", careers_url="https://x.com")
        with pytest.raises((ValidationError, TypeError)):
            result.careers_page_content = "mutated"  # type: ignore[misc]

    def test_defaults_are_empty(self) -> None:
        result = HiringFetchResult()
        assert result.careers_page_content == ""
        assert result.careers_url == ""
        assert result.redirected_to_linkedin is False

    def test_linkedin_redirect_clears_content(self) -> None:
        result = HiringFetchResult(redirected_to_linkedin=True)
        assert result.careers_page_content == ""


# ---------------------------------------------------------------------------
# Layer 2 — Contract: PlaybookLoader upstream_careers_page resolution
# ---------------------------------------------------------------------------


class TestPlaybookCareer:
    """AC-10: PlaybookLoader resolves {upstream_careers_page} as raw text."""

    def test_upstream_careers_page_resolves_raw_text(self) -> None:
        """AC-10: upstream_results['careers_page'] maps to {upstream_careers_page}.

        The content must appear as raw text (not JSON-encoded with escaped newlines).
        Newlines in the content prove json.dumps would break the substitution.
        """
        careers_content = "## Open Roles\n- Senior Search Engineer\n- Staff Relevance Engineer"
        ctx = ExecutionContextV2(
            audit_id=str(uuid4()),
            account_domain="dell.com",
            company_name="Dell Technologies",
            upstream_results={"careers_page": careers_content},
        )
        loader = PlaybookLoader()
        _, body = loader.load(HIRING_PLAYBOOK_PATH)
        resolved = loader.resolve(body, ctx)

        # Raw content with real newlines must appear (not JSON-escaped \\n)
        assert "## Open Roles" in resolved
        assert "Senior Search Engineer" in resolved
        assert "Staff Relevance Engineer" in resolved

    def test_upstream_careers_page_empty_string_resolves_cleanly(self) -> None:
        """Empty careers_page → {upstream_careers_page} resolves to empty (not 'null' or error)."""
        ctx = ExecutionContextV2(
            audit_id=str(uuid4()),
            account_domain="dell.com",
            upstream_results={"careers_page": ""},
        )
        loader = PlaybookLoader()
        _, body = loader.load(HIRING_PLAYBOOK_PATH)
        resolved = loader.resolve(body, ctx)

        assert "{upstream_careers_page}" not in resolved


# ---------------------------------------------------------------------------
# Layer 3 — Integration: _run_intel_hiring_pipeline()
# ---------------------------------------------------------------------------


class TestHiringPipeline:
    """AC-8 and AC-9: _run_intel_hiring_pipeline() — 2-track pipeline wiring."""

    @pytest.mark.asyncio
    async def test_track1_result_injected_into_context(self) -> None:
        """AC-8: fetch_careers_page result injected as upstream_results['careers_page']."""
        from prism_platform.orchestrator.activities import _run_intel_hiring_pipeline
        from prism_platform.orchestrator.workflows import RunModuleInput

        careers_content = "Senior Search Engineer - Open"
        fetch_result = HiringFetchResult(
            careers_page_content=careers_content,
            careers_url="https://dell.com/careers",
        )

        v2_context = ExecutionContextV2(
            audit_id=str(uuid4()),
            account_domain="dell.com",
            company_name="Dell Technologies",
        )

        mock_handle: Any = MagicMock()
        mock_handle.config.timeout_seconds = 60
        mock_handle.output_schema = MagicMock()
        mock_handle.playbook_path = HIRING_PLAYBOOK_PATH

        mock_result = ModuleExecutorResult(
            module_name="intel-hiring",
            module_version="2.0.0",
            status="success",
        )

        run_input = RunModuleInput(
            module_name="intel-hiring",
            domain="dell.com",
            company_name="Dell Technologies",
            audit_id=str(uuid4()),
            account_id=str(uuid4()),
        )

        with (
            patch(
                "prism_platform.orchestrator.activities.fetch_careers_page",
                new_callable=AsyncMock,
                return_value=fetch_result,
            ),
            patch("prism_platform.orchestrator.activities.ModuleExecutor") as mock_executor_cls,
            patch(
                "prism_platform.orchestrator.activities.AgentAPIClient",
                return_value=MagicMock(),
            ),
        ):
            mock_executor_instance = AsyncMock()
            mock_executor_instance.execute.return_value = mock_result
            mock_executor_cls.return_value = mock_executor_instance

            _result, _ = await _run_intel_hiring_pipeline(
                input=run_input,
                handle=mock_handle,
                v2_context=v2_context,
                start_time=0.0,
            )

        assert "careers_page" in v2_context.upstream_results
        assert v2_context.upstream_results["careers_page"] == careers_content

    @pytest.mark.asyncio
    async def test_track2_runs_when_track1_empty(self) -> None:
        """AC-9: Track 2 runs even when Track 1 returns empty HiringFetchResult."""
        from prism_platform.orchestrator.activities import _run_intel_hiring_pipeline
        from prism_platform.orchestrator.workflows import RunModuleInput

        empty_fetch = HiringFetchResult()  # Track 1 found nothing

        v2_context = ExecutionContextV2(
            audit_id=str(uuid4()),
            account_domain="dell.com",
            company_name="Dell Technologies",
        )

        mock_handle: Any = MagicMock()
        mock_handle.config.timeout_seconds = 60
        mock_handle.output_schema = MagicMock()
        mock_handle.playbook_path = HIRING_PLAYBOOK_PATH

        mock_result = ModuleExecutorResult(
            module_name="intel-hiring",
            module_version="2.0.0",
            status="success",
        )

        run_input = RunModuleInput(
            module_name="intel-hiring",
            domain="dell.com",
            company_name="Dell Technologies",
            audit_id=str(uuid4()),
            account_id=str(uuid4()),
        )

        with (
            patch(
                "prism_platform.orchestrator.activities.fetch_careers_page",
                new_callable=AsyncMock,
                return_value=empty_fetch,
            ),
            patch("prism_platform.orchestrator.activities.ModuleExecutor") as mock_executor_cls,
            patch(
                "prism_platform.orchestrator.activities.AgentAPIClient",
                return_value=MagicMock(),
            ),
        ):
            mock_executor_instance = AsyncMock()
            mock_executor_instance.execute.return_value = mock_result
            mock_executor_cls.return_value = mock_executor_instance

            _result, _ = await _run_intel_hiring_pipeline(
                input=run_input,
                handle=mock_handle,
                v2_context=v2_context,
                start_time=0.0,
            )

        # Track 2 must still execute
        mock_executor_instance.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_routing_calls_hiring_pipeline(self) -> None:
        """run_module() routes intel-hiring to _run_intel_hiring_pipeline, not generic path."""
        from prism_platform.orchestrator.activities import run_module
        from prism_platform.orchestrator.workflows import RunModuleInput

        run_input = RunModuleInput(
            module_name="intel-hiring",
            domain="dell.com",
            company_name="Dell Technologies",
            audit_id=str(uuid4()),
            account_id=str(uuid4()),
        )

        pipeline_return = (
            MagicMock(status="success", output={}),
            {"status": "success", "duration_ms": 100},
        )
        with (
            patch(
                "prism_platform.orchestrator.activities._run_intel_hiring_pipeline",
                new_callable=AsyncMock,
                return_value=pipeline_return,
            ) as mock_pipeline,
            patch(
                "prism_platform.orchestrator.activities.get_cached_result",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("prism_platform.orchestrator.activities.persist_result", new_callable=AsyncMock),
            patch(
                "prism_platform.orchestrator.activities.V2_MODULE_REGISTRY",
                {"intel-hiring": MagicMock()},
            ),
        ):
            await run_module(run_input)

        mock_pipeline.assert_called_once()
