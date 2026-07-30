"""Backend test suite for intel-company — 5 groups covering the full pipeline.

Group 1: BrowserClient tier escalation (mock httpx/jina)
Group 2: PipelineHealthLog event capture + markdown render
Group 3: SynthesisClient mock Gemini, reconciliation assertions
Group 4: Full 3-track pipeline integration (mock all external calls)
Group 5: CompanySeedOutput contract — schema stability
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from core.browser.client import BrowserClient
from core.browser.types import FetchOptions, FetchResult, FetchTier
from core.pipeline_health import (
    PipelineHealthLog,
)
from core.synthesis import SynthesisClient, SynthesisResult
from core.types import ExecutionContextV2
from prism_platform.v2.modules.intel_company.schemas import CompanySeedOutput
from server.orchestrator.activities import _run_intel_company_pipeline
from server.orchestrator.workflows import RunModuleInput

# ── Helpers ────────────────────────────────────────────────────────────────────

_DOMAIN = "dell.com"
_COMPANY = "Dell Technologies"
_SYNTHESIS_PLAYBOOK = (
    Path(__file__).resolve().parents[2]
    / "prism_platform"
    / "v2"
    / "modules"
    / "intel_company"
    / "playbook_synthesis.md"
)


def _make_fetch_result(
    *,
    success: bool = True,
    text: str = "CEO John Smith leads the team",
    tier: FetchTier = FetchTier.HTTPX,
    error: str | None = None,
) -> FetchResult:
    return FetchResult(
        url=f"https://{_DOMAIN}/about",
        text=text if success else "",
        status_code=200 if success else 0,
        tier_used=tier,
        fetch_duration_ms=100,
        error=error if not success else None,
        is_bot_blocked=False,
    )


def _make_company_output(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "legal_name": "Dell Technologies Inc.",
        "common_name": "Dell",
        "domain": "dell.com",
        "headquarters": "Round Rock, Texas, USA",
        "employee_count": 133000,
        "employee_count_source": "FY2025 10-K",
        "year_founded": 1984,
        "business_model": (
            "Dell Technologies designs and sells enterprise hardware, servers, "
            "storage solutions, and IT services to businesses and consumers worldwide."
        ),
        "industry": "Enterprise Technology",
        "sub_vertical": "Hardware & Infrastructure",
        "is_public": True,
        "ticker": "DELL",
        "parent_company": None,
        "revenue_estimate": 88400000000.0,
        "revenue_source": "SEC 10-K FY2025",
        "executives": [
            {
                "full_name": "Michael Dell",
                "title": "Chairman & CEO",
                "role_classification": "economic_buyer",
                "linkedin_url": None,
                "tenure_description": "Since 1984",
                "previous_company": None,
            }
        ],
        "competitors": [
            {
                "company_name": "HP Inc",
                "domain": "hp.com",
                "why_competitor": "Competes in PCs and enterprise hardware",
                "linkedin_url": None,
            }
        ],
        "product_categories": ["Servers", "Laptops", "Storage"],
        "company_linkedin_url": None,
        "twitter_handle": None,
        "youtube_url": None,
        "recent_headline": "Dell reports strong Q4 driven by AI server demand",
    }
    base.update(overrides)
    return base


# ══════════════════════════════════════════════════════════════════════════════
# Group 1: BrowserClient Tier Escalation
# ══════════════════════════════════════════════════════════════════════════════


class TestBrowserClientTierEscalation:
    """BrowserClient escalates through tiers correctly."""

    @pytest.mark.asyncio
    async def test_httpx_success_returns_without_escalation(self) -> None:
        """When httpx succeeds, no further tiers are called."""
        success_result = _make_fetch_result(tier=FetchTier.HTTPX)

        with (
            patch(
                "core.browser.client.fetch_direct",
                new=AsyncMock(return_value=success_result),
            ) as mock_httpx,
            patch(
                "core.browser.client.fetch_jina",
                new=AsyncMock(),
            ) as mock_jina,
        ):
            client = BrowserClient()
            result = await client.fetch(f"https://{_DOMAIN}/about")

        assert result.success is True
        assert result.tier_used == FetchTier.HTTPX
        mock_httpx.assert_called_once()
        mock_jina.assert_not_called()

    @pytest.mark.asyncio
    async def test_httpx_failure_escalates_to_jina(self) -> None:
        """When httpx fails, BrowserClient tries Jina."""
        httpx_fail = _make_fetch_result(success=False, tier=FetchTier.HTTPX, error="connection_refused")
        jina_success = _make_fetch_result(tier=FetchTier.JINA)

        with (
            patch(
                "core.browser.client.fetch_direct",
                new=AsyncMock(return_value=httpx_fail),
            ),
            patch(
                "core.browser.client.fetch_jina",
                new=AsyncMock(return_value=jina_success),
            ) as mock_jina,
        ):
            client = BrowserClient()
            result = await client.fetch(f"https://{_DOMAIN}/about")

        assert result.success is True
        assert result.tier_used == FetchTier.JINA
        mock_jina.assert_called_once()

    @pytest.mark.asyncio
    async def test_both_tier1_fail_escalates_to_tier2(self) -> None:
        """When httpx AND Jina fail, BrowserClient tries Playwright (Tier 2)."""
        httpx_fail = _make_fetch_result(success=False, tier=FetchTier.HTTPX, error="blocked")
        jina_fail = _make_fetch_result(success=False, tier=FetchTier.JINA, error="blocked")
        playwright_success = _make_fetch_result(tier=FetchTier.PLAYWRIGHT)

        with (
            patch(
                "core.browser.client.fetch_direct",
                new=AsyncMock(return_value=httpx_fail),
            ),
            patch(
                "core.browser.client.fetch_jina",
                new=AsyncMock(return_value=jina_fail),
            ),
            patch(
                "core.browser.client.fetch_stealth",
                new=AsyncMock(return_value=playwright_success),
            ) as mock_t2,
        ):
            client = BrowserClient()
            result = await client.fetch(f"https://{_DOMAIN}/about")

        assert result.success is True
        assert result.tier_used == FetchTier.PLAYWRIGHT
        mock_t2.assert_called_once()

    @pytest.mark.asyncio
    async def test_max_tier_1_prevents_escalation_to_tier2_stealth(self) -> None:
        """With max_tier=1, Tier 1 failure does NOT escalate to Tier 2 stealth browser."""
        httpx_fail = _make_fetch_result(success=False, tier=FetchTier.HTTPX, error="blocked")
        jina_fail = _make_fetch_result(success=False, tier=FetchTier.JINA, error="blocked")

        with (
            patch(
                "core.browser.client.fetch_direct",
                new=AsyncMock(return_value=httpx_fail),
            ),
            patch(
                "core.browser.client.fetch_jina",
                new=AsyncMock(return_value=jina_fail),
            ),
            patch(
                "core.browser.client.fetch_stealth",
                new=AsyncMock(),
            ) as mock_t2,
        ):
            client = BrowserClient()
            result = await client.fetch(
                f"https://{_DOMAIN}/about",
                FetchOptions(max_tier=1),
            )

        # Tier 2 stealth must NOT be called when max_tier=1
        mock_t2.assert_not_called()
        assert result.success is False  # Both Tier 1 attempts failed

    @pytest.mark.asyncio
    async def test_fetch_multiple_returns_results_in_order(self) -> None:
        """fetch_multiple returns results in the same order as input URLs."""
        urls = [
            f"https://{_DOMAIN}/about",
            f"https://{_DOMAIN}/leadership",
            f"https://{_DOMAIN}/ir",
        ]
        results_in_order = [
            _make_fetch_result(text=f"page {i}", tier=FetchTier.HTTPX)
            for i in range(3)
        ]

        with patch(
            "core.browser.client.fetch_direct",
            new=AsyncMock(side_effect=results_in_order),
        ):
            client = BrowserClient()
            results = await client.fetch_multiple(urls)

        assert len(results) == 3
        for i, result in enumerate(results):
            assert f"page {i}" in result.text


# ══════════════════════════════════════════════════════════════════════════════
# Group 2: PipelineHealthLog
# ══════════════════════════════════════════════════════════════════════════════


class TestPipelineHealthLog:
    """PipelineHealthLog captures events and renders correct summaries."""

    def test_empty_log_is_healthy(self) -> None:
        health = PipelineHealthLog(module_name="intel-company", domain=_DOMAIN)
        assert health.overall_status == "HEALTHY"
        assert health.has_errors is False
        assert health.has_warnings is False

    def test_info_events_do_not_degrade_status(self) -> None:
        health = PipelineHealthLog(module_name="intel-company", domain=_DOMAIN)
        health.info("track1_webfetch", "Fetched leadership page", url="https://dell.com/about")
        health.info("track2_perplexity", "API call succeeded", citations=3)
        assert health.overall_status == "HEALTHY"

    def test_warning_degrades_to_degraded(self) -> None:
        health = PipelineHealthLog(module_name="intel-company", domain=_DOMAIN)
        health.warning("track1_webfetch", "Leadership page not found")
        assert health.overall_status == "DEGRADED"
        assert health.has_warnings is True
        assert health.has_errors is False

    def test_error_degrades_to_degraded(self) -> None:
        health = PipelineHealthLog(module_name="intel-company", domain=_DOMAIN)
        health.error("track2_perplexity", "API timeout")
        assert health.overall_status == "DEGRADED"
        assert health.has_errors is True

    def test_critical_becomes_failed(self) -> None:
        health = PipelineHealthLog(module_name="intel-company", domain=_DOMAIN)
        health.critical("track3_synthesis", "Synthesis completely failed")
        assert health.overall_status == "FAILED"

    def test_events_by_category_filters_correctly(self) -> None:
        health = PipelineHealthLog(module_name="intel-company", domain=_DOMAIN)
        health.info("track1_webfetch", "T1 event")
        health.warning("track2_perplexity", "T2 warning")
        health.info("track3_synthesis", "T3 event")
        health.error("track1_webfetch", "T1 error")

        t1_events = health.events_by_category("track1_webfetch")
        t2_events = health.events_by_category("track2_perplexity")

        assert len(t1_events) == 2
        assert len(t2_events) == 1

    def test_summary_includes_event_counts(self) -> None:
        health = PipelineHealthLog(module_name="intel-company", domain=_DOMAIN)
        health.info("track1_webfetch", "OK")
        health.info("track1_webfetch", "OK 2")
        health.warning("track2_perplexity", "Slow")
        health.error("track3_synthesis", "Bad JSON")

        summary = health.summary()
        assert summary["module"] == "intel-company"
        assert summary["domain"] == _DOMAIN
        assert summary["event_counts"]["info"] == 2
        assert summary["event_counts"]["warning"] == 1
        assert summary["event_counts"]["error"] == 1
        assert summary["overall_status"] == "DEGRADED"

    def test_summary_excludes_info_events_from_json(self) -> None:
        """Info events are not included in the summary events list (noise reduction)."""
        health = PipelineHealthLog(module_name="intel-company", domain=_DOMAIN)
        health.info("track1_webfetch", "Just info")
        health.warning("track2_perplexity", "A warning")

        summary = health.summary()
        # Only the warning appears in summary events
        assert len(summary["events"]) == 1
        assert summary["events"][0]["severity"] == "warning"

    def test_markdown_render_contains_track_sections(self) -> None:
        health = PipelineHealthLog(module_name="intel-company", domain=_DOMAIN)
        health.info("track1_webfetch", "Fetched leadership page")
        health.warning("track2_perplexity", "Slow response", latency_ms=4500)
        health.info("track3_synthesis", "Synthesis completed")

        md = health.to_markdown()
        assert "Track 1 — WebFetch" in md
        assert "Track 2 — Perplexity" in md
        assert "Track 3 — Synthesis" in md

    def test_markdown_shows_overall_status(self) -> None:
        health = PipelineHealthLog(module_name="intel-company", domain=_DOMAIN)
        health.warning("track1_webfetch", "Leadership page not public")

        md = health.to_markdown()
        assert "DEGRADED" in md

    def test_markdown_healthy_shows_pass(self) -> None:
        health = PipelineHealthLog(module_name="intel-company", domain=_DOMAIN)
        health.info("track1_webfetch", "OK")
        health.info("track2_perplexity", "OK")

        md = health.to_markdown()
        assert "PASS" in md

    def test_detail_kwargs_captured_in_event(self) -> None:
        health = PipelineHealthLog(module_name="intel-company", domain=_DOMAIN)
        health.error("track1_webfetch", "Fetch failed", url="https://dell.com", code=403)

        event = health.events[0]
        assert event.detail["url"] == "https://dell.com"
        assert event.detail["code"] == 403


# ══════════════════════════════════════════════════════════════════════════════
# Group 3: SynthesisClient (mock Gemini)
# ══════════════════════════════════════════════════════════════════════════════


class TestSynthesisClient:
    """SynthesisClient resolves the synthesis playbook and calls Gemini correctly."""

    def _make_gemini_mock(self, response_text: str) -> tuple[MagicMock, MagicMock]:
        """Build a mock Gemini client that returns the given response text."""
        mock_response = MagicMock()
        mock_response.text = response_text

        mock_gemini_client = MagicMock()
        mock_gemini_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        mock_genai_module = MagicMock()
        mock_genai_module.Client.return_value = mock_gemini_client

        return mock_genai_module, mock_gemini_client

    def _synthesis_patches(self, mock_genai_module: MagicMock) -> tuple:
        """Return the patch context managers needed for SynthesisClient tests.

        genai is imported locally inside _call_gemini (from google import genai),
        so we must patch at the google package level, not the synthesis module level.
        """
        return (
            patch("core.synthesis.settings") ,
            patch("core.synthesis.genai", mock_genai_module),
        )

    @pytest.mark.asyncio
    async def test_synthesis_success_returns_parsed_output(self) -> None:
        """When Gemini returns valid JSON, SynthesisClient parses it."""
        valid_output = _make_company_output()
        mock_genai_module, _ = self._make_gemini_mock(json.dumps(valid_output))

        with (
            patch("core.synthesis.settings") as mock_settings,
            patch("core.synthesis.genai", mock_genai_module),
        ):
            mock_settings.get_enricher_provider.return_value = "gemini"
            mock_settings.get_enricher_model.return_value = "gemini-3.1-flash-lite-preview"
            mock_settings.gemini_api_key = "test-key"

            client = SynthesisClient()
            result = await client.synthesize(
                playbook_path=_SYNTHESIS_PLAYBOOK,
                template_vars={
                    "domain": _DOMAIN,
                    "company_name": _COMPANY,
                    "upstream_leadership_page": "CEO Michael Dell leads Dell",
                    "upstream_ir_page": "Revenue: $88.4B FY2025",
                    "upstream_newsroom_page": "Dell launches AI servers",
                    "upstream_perplexity_output": json.dumps(valid_output),
                    "upstream_perplexity_citations": "https://dell.com",
                },
                output_schema=CompanySeedOutput,
            )

        assert result.status == "success"
        assert result.output is not None
        assert result.output["legal_name"] == "Dell Technologies Inc."
        assert result.model_used == "gemini-3.1-flash-lite-preview"
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_synthesis_strips_markdown_code_fences(self) -> None:
        """If Gemini wraps the JSON in ```json ... ```, it's stripped correctly."""
        valid_output = _make_company_output()
        fenced_response = f"```json\n{json.dumps(valid_output)}\n```"
        mock_genai_module, _ = self._make_gemini_mock(fenced_response)

        with (
            patch("core.synthesis.settings") as mock_settings,
            patch("core.synthesis.genai", mock_genai_module),
        ):
            mock_settings.get_enricher_provider.return_value = "gemini"
            mock_settings.get_enricher_model.return_value = "gemini-3.1-flash-lite-preview"
            mock_settings.gemini_api_key = "test-key"

            client = SynthesisClient()
            result = await client.synthesize(
                playbook_path=_SYNTHESIS_PLAYBOOK,
                template_vars={"domain": _DOMAIN, "company_name": _COMPANY,
                                "upstream_leadership_page": "", "upstream_ir_page": "",
                                "upstream_newsroom_page": "", "upstream_perplexity_output": "{}",
                                "upstream_perplexity_citations": ""},
                output_schema=CompanySeedOutput,
            )

        assert result.status == "success"
        assert result.output["legal_name"] == "Dell Technologies Inc."

    @pytest.mark.asyncio
    async def test_synthesis_returns_failed_on_bad_json(self) -> None:
        """When Gemini returns non-JSON, synthesis returns failed status."""
        mock_genai_module, _ = self._make_gemini_mock("Sorry, I cannot help with that.")

        with (
            patch("core.synthesis.settings") as mock_settings,
            patch("core.synthesis.genai", mock_genai_module),
        ):
            mock_settings.get_enricher_provider.return_value = "gemini"
            mock_settings.get_enricher_model.return_value = "gemini-3.1-flash-lite-preview"
            mock_settings.gemini_api_key = "test-key"

            client = SynthesisClient()
            result = await client.synthesize(
                playbook_path=_SYNTHESIS_PLAYBOOK,
                template_vars={"domain": _DOMAIN, "company_name": _COMPANY,
                                "upstream_leadership_page": "", "upstream_ir_page": "",
                                "upstream_newsroom_page": "", "upstream_perplexity_output": "{}",
                                "upstream_perplexity_citations": ""},
                output_schema=CompanySeedOutput,
            )

        assert result.status == "failed"
        assert result.output is None
        assert "JSON parse error" in (result.error or "")

    @pytest.mark.asyncio
    async def test_synthesis_resolves_template_vars_into_playbook(self) -> None:
        """Template variables are substituted into the playbook before the Gemini call."""
        captured_prompt: list[str] = []

        valid_output = _make_company_output()
        mock_response = MagicMock()
        mock_response.text = json.dumps(valid_output)

        async def capture_generate(*args: Any, **kwargs: Any) -> MagicMock:
            captured_prompt.append(kwargs.get("contents", args[0] if args else ""))
            return mock_response

        mock_gemini_client = MagicMock()
        mock_gemini_client.aio.models.generate_content = capture_generate
        mock_genai_module = MagicMock()
        mock_genai_module.Client.return_value = mock_gemini_client

        with (
            patch("core.synthesis.settings") as mock_settings,
            patch("core.synthesis.genai", mock_genai_module),
        ):
            mock_settings.get_enricher_provider.return_value = "gemini"
            mock_settings.get_enricher_model.return_value = "gemini-3.1-flash-lite-preview"
            mock_settings.gemini_api_key = "test-key"

            client = SynthesisClient()
            await client.synthesize(
                playbook_path=_SYNTHESIS_PLAYBOOK,
                template_vars={
                    "domain": "nike.com",
                    "company_name": "Nike",
                    "upstream_leadership_page": "Nike leadership content here",
                    "upstream_ir_page": "",
                    "upstream_newsroom_page": "",
                    "upstream_perplexity_output": "{}",
                    "upstream_perplexity_citations": "",
                },
                output_schema=CompanySeedOutput,
            )

        assert len(captured_prompt) == 1
        prompt = captured_prompt[0]
        assert "nike.com" in prompt
        assert "Nike leadership content here" in prompt
        assert "{domain}" not in prompt  # All placeholders resolved


# ══════════════════════════════════════════════════════════════════════════════
# Group 4: Full 3-Track Pipeline Integration
# ══════════════════════════════════════════════════════════════════════════════


def _make_run_module_input(domain: str = _DOMAIN) -> RunModuleInput:
    return RunModuleInput(
        audit_id=str(uuid4()),
        account_id=str(uuid4()),
        module_name="intel-company",
        domain=domain,
        company_name=_COMPANY,
        ticker="DELL",
        is_private=False,
        wave=1,
    )


def _make_executor_result(status: str = "success", output: dict | None = None) -> Any:
    """Build a ModuleExecutorResult-like mock for the executor."""
    from core.executor import ModuleExecutorResult
    from core.types import ClaimRegistryEntry

    if output is None:
        output = _make_company_output()

    claims = [
        ClaimRegistryEntry(
            statement="legal_name = Dell Technologies Inc.",
            source_url="https://dell.com",
            evidence_tier="WEBSEARCH",
            module_origin="intel-company",
            field_path="legal_name",
        )
    ]

    return ModuleExecutorResult(
        module_name="intel-company",
        module_version="2.0.0",
        status=status,
        output=output if status == "success" else {},
        claims=claims if status == "success" else [],
        citations=["https://dell.com", "https://investors.dell.com"],
        llm_calls=1,
        input_tokens=300,
        output_tokens=900,
        errors=[] if status == "success" else ["API timeout"],
    )


class TestFullPipelineIntegration:
    """Full 3-track pipeline — mock all external calls, test the wiring logic."""

    @pytest.mark.asyncio
    async def test_happy_path_uses_synthesis_output(self) -> None:
        """When all 3 tracks succeed, the final result uses Track 3 synthesis output."""
        from core.registry import V2_MODULE_REGISTRY, ModuleHandle
        from prism_platform.v2.modules.intel_company.config import INTEL_COMPANY_CONFIG
        from prism_platform.v2.modules.intel_company.schemas import CompanySeedOutput

        handle = V2_MODULE_REGISTRY.get("intel-company") or ModuleHandle(
            config=INTEL_COMPANY_CONFIG,
            output_schema=CompanySeedOutput,
            playbook_path=Path("prism_platform/v2/modules/intel_company/playbook.md"),
        )

        t1_pages = {
            "leadership_page": "CEO Michael Dell, CFO Yvonne McGill",
            "ir_page": "FY2025 Revenue: $88.4B",
            "newsroom_page": "Dell launches AI infrastructure",
        }
        t2_result = _make_executor_result()
        synthesis_output = _make_company_output(
            legal_name="Dell Technologies Inc. [SYNTHESIZED]"
        )
        t3_result = SynthesisResult(
            status="success",
            output=synthesis_output,
            model_used="gemini-3.1-flash-lite-preview",
            duration_ms=800,
        )

        input_ = _make_run_module_input()
        context = ExecutionContextV2(
            audit_id=input_.audit_id,
            account_domain=input_.domain,
            company_name=input_.company_name or "",
        )

        with (
            patch(
                "prism_platform.v2.modules.intel_company.fetcher.fetch_all_company_pages",
                new=AsyncMock(return_value=t1_pages),
            ),
            patch(
                "core.executor.ModuleExecutor.execute",
                new=AsyncMock(return_value=t2_result),
            ),
            patch(
                "core.synthesis.SynthesisClient.synthesize",
                new=AsyncMock(return_value=t3_result),
            ),
        ):
            result, result_dict = await _run_intel_company_pipeline(
                input=input_,
                handle=handle,
                v2_context=context,
                start_time=time.monotonic(),
            )

        assert result.status == "success"
        assert result_dict["status"] == "success"
        # Output comes from synthesis (Track 3), not Track 2
        assert result_dict["output"]["legal_name"] == "Dell Technologies Inc. [SYNTHESIZED]"
        assert result_dict["llm_calls"] == 2  # T2 + T3
        assert "pipeline_health" in result_dict
        assert result_dict["pipeline_health"]["overall_status"] in ("HEALTHY", "DEGRADED")

    @pytest.mark.asyncio
    async def test_track2_failure_skips_synthesis_returns_failed(self) -> None:
        """When Track 2 (Perplexity) fails, synthesis is skipped and failed status returned."""
        from core.registry import V2_MODULE_REGISTRY, ModuleHandle
        from prism_platform.v2.modules.intel_company.config import INTEL_COMPANY_CONFIG
        from prism_platform.v2.modules.intel_company.schemas import CompanySeedOutput

        handle = V2_MODULE_REGISTRY.get("intel-company") or ModuleHandle(
            config=INTEL_COMPANY_CONFIG,
            output_schema=CompanySeedOutput,
            playbook_path=Path("prism_platform/v2/modules/intel_company/playbook.md"),
        )

        t2_failed = _make_executor_result(status="failed")

        input_ = _make_run_module_input()
        context = ExecutionContextV2(
            audit_id=input_.audit_id,
            account_domain=input_.domain,
            company_name=input_.company_name or "",
        )

        with (
            patch(
                "prism_platform.v2.modules.intel_company.fetcher.fetch_all_company_pages",
                new=AsyncMock(return_value={"leadership_page": "", "ir_page": "", "newsroom_page": ""}),
            ),
            patch(
                "core.executor.ModuleExecutor.execute",
                new=AsyncMock(return_value=t2_failed),
            ),
            patch(
                "core.synthesis.SynthesisClient.synthesize",
                new=AsyncMock(),
            ) as mock_synth,
        ):
            result, result_dict = await _run_intel_company_pipeline(
                input=input_,
                handle=handle,
                v2_context=context,
                start_time=time.monotonic(),
            )

        assert result.status == "failed"
        assert result_dict["status"] == "failed"
        mock_synth.assert_not_called()  # Synthesis skipped when T2 fails
        assert "pipeline_health" in result_dict

    @pytest.mark.asyncio
    async def test_track3_failure_falls_back_to_track2_output(self) -> None:
        """When Track 3 synthesis fails, module falls back to Track 2 output with DEGRADED health."""
        from core.registry import V2_MODULE_REGISTRY, ModuleHandle
        from prism_platform.v2.modules.intel_company.config import INTEL_COMPANY_CONFIG
        from prism_platform.v2.modules.intel_company.schemas import CompanySeedOutput

        handle = V2_MODULE_REGISTRY.get("intel-company") or ModuleHandle(
            config=INTEL_COMPANY_CONFIG,
            output_schema=CompanySeedOutput,
            playbook_path=Path("prism_platform/v2/modules/intel_company/playbook.md"),
        )

        t2_result = _make_executor_result()
        t3_failed = SynthesisResult(
            status="failed",
            output=None,
            error="Gemini API rate limit exceeded",
            model_used="gemini-3.1-flash-lite-preview",
            duration_ms=0,
        )

        input_ = _make_run_module_input()
        context = ExecutionContextV2(
            audit_id=input_.audit_id,
            account_domain=input_.domain,
            company_name=input_.company_name or "",
        )

        with (
            patch(
                "prism_platform.v2.modules.intel_company.fetcher.fetch_all_company_pages",
                new=AsyncMock(return_value={"leadership_page": "some content", "ir_page": "", "newsroom_page": ""}),
            ),
            patch(
                "core.executor.ModuleExecutor.execute",
                new=AsyncMock(return_value=t2_result),
            ),
            patch(
                "core.synthesis.SynthesisClient.synthesize",
                new=AsyncMock(return_value=t3_failed),
            ),
        ):
            result, result_dict = await _run_intel_company_pipeline(
                input=input_,
                handle=handle,
                v2_context=context,
                start_time=time.monotonic(),
            )

        # Fell back to Track 2 output — module still succeeds
        assert result.status == "success"
        assert result_dict["status"] == "success"
        assert result_dict["output"]["legal_name"] == "Dell Technologies Inc."
        # Health shows the synthesis error
        assert result_dict["pipeline_health"]["overall_status"] == "DEGRADED"

    @pytest.mark.asyncio
    async def test_track1_exception_does_not_abort_pipeline(self) -> None:
        """Even if Track 1 WebFetch raises an exception, the pipeline continues with T2+T3."""
        from core.registry import V2_MODULE_REGISTRY, ModuleHandle
        from prism_platform.v2.modules.intel_company.config import INTEL_COMPANY_CONFIG
        from prism_platform.v2.modules.intel_company.schemas import CompanySeedOutput

        handle = V2_MODULE_REGISTRY.get("intel-company") or ModuleHandle(
            config=INTEL_COMPANY_CONFIG,
            output_schema=CompanySeedOutput,
            playbook_path=Path("prism_platform/v2/modules/intel_company/playbook.md"),
        )

        t2_result = _make_executor_result()
        t3_result = SynthesisResult(
            status="success",
            output=_make_company_output(),
            model_used="gemini-3.1-flash-lite-preview",
            duration_ms=500,
        )

        input_ = _make_run_module_input()
        context = ExecutionContextV2(
            audit_id=input_.audit_id,
            account_domain=input_.domain,
            company_name=input_.company_name or "",
        )

        with (
            patch(
                "prism_platform.v2.modules.intel_company.fetcher.fetch_all_company_pages",
                new=AsyncMock(side_effect=ConnectionError("DNS resolution failed")),
            ),
            patch(
                "core.executor.ModuleExecutor.execute",
                new=AsyncMock(return_value=t2_result),
            ),
            patch(
                "core.synthesis.SynthesisClient.synthesize",
                new=AsyncMock(return_value=t3_result),
            ),
        ):
            result, result_dict = await _run_intel_company_pipeline(
                input=input_,
                handle=handle,
                v2_context=context,
                start_time=time.monotonic(),
            )

        # Pipeline completes despite Track 1 failure
        assert result.status == "success"
        assert result_dict["pipeline_health"]["overall_status"] == "DEGRADED"

    @pytest.mark.asyncio
    async def test_pipeline_health_included_in_all_outcomes(self) -> None:
        """pipeline_health key appears in result_dict regardless of success or failure."""
        from core.registry import ModuleHandle
        from prism_platform.v2.modules.intel_company.config import INTEL_COMPANY_CONFIG
        from prism_platform.v2.modules.intel_company.schemas import CompanySeedOutput

        handle = ModuleHandle(
            config=INTEL_COMPANY_CONFIG,
            output_schema=CompanySeedOutput,
            playbook_path=Path("prism_platform/v2/modules/intel_company/playbook.md"),
        )

        # Simulate complete failure — Track 2 fails
        t2_failed = _make_executor_result(status="failed")

        input_ = _make_run_module_input()
        context = ExecutionContextV2(
            audit_id=input_.audit_id,
            account_domain=input_.domain,
            company_name=input_.company_name or "",
        )

        with (
            patch(
                "prism_platform.v2.modules.intel_company.fetcher.fetch_all_company_pages",
                new=AsyncMock(return_value={"leadership_page": "", "ir_page": "", "newsroom_page": ""}),
            ),
            patch(
                "core.executor.ModuleExecutor.execute",
                new=AsyncMock(return_value=t2_failed),
            ),
        ):
            _result, result_dict = await _run_intel_company_pipeline(
                input=input_,
                handle=handle,
                v2_context=context,
                start_time=time.monotonic(),
            )

        assert "pipeline_health" in result_dict
        assert "overall_status" in result_dict["pipeline_health"]
        assert "event_counts" in result_dict["pipeline_health"]


# ══════════════════════════════════════════════════════════════════════════════
# Group 5: CompanySeedOutput Schema Contract
# ══════════════════════════════════════════════════════════════════════════════


class TestCompanySeedOutputContract:
    """Schema stability contract — these assertions must never break silently."""

    def test_required_top_level_fields_present(self) -> None:
        """All required fields exist in the schema."""
        schema = CompanySeedOutput.model_json_schema()
        props = schema["properties"]

        required_fields = [
            "legal_name", "common_name", "domain", "headquarters",
            "business_model", "industry", "executives", "competitors",
        ]
        for field in required_fields:
            assert field in props, f"Required field '{field}' missing from CompanySeedOutput schema"

    def test_extra_fields_forbidden(self) -> None:
        """Schema rejects unknown fields (extra='forbid' enforced)."""
        with pytest.raises(ValidationError):
            CompanySeedOutput(**_make_company_output(), unknown_extra_field="oops")

    def test_business_model_min_length_enforced(self) -> None:
        """business_model must be at least 50 characters."""
        bad = _make_company_output(business_model="Too short")
        with pytest.raises(ValidationError) as exc_info:
            CompanySeedOutput(**bad)
        assert any("business_model" in str(e) or "min_length" in str(e).lower()
                   for e in exc_info.value.errors())

    def test_executive_role_classification_validated(self) -> None:
        """ExecutiveSeed role_classification must be a valid Literal."""
        bad = _make_company_output(executives=[{
            "full_name": "Test Person",
            "title": "CTO",
            "role_classification": "inventor",  # not valid
        }])
        with pytest.raises(ValidationError):
            CompanySeedOutput(**bad)

    def test_json_schema_additional_properties_false(self) -> None:
        """JSON schema advertises no additional properties for LLM instructions."""
        schema = CompanySeedOutput.model_json_schema()
        assert schema.get("additionalProperties") is False

    def test_valid_minimal_output_accepted(self) -> None:
        """A minimal valid output with optional fields null is accepted."""
        minimal: dict[str, Any] = {
            "legal_name": "Minimal Corp",
            "common_name": "Minimal",
            "domain": "minimal.com",
            "headquarters": "San Francisco, CA, USA",
            "business_model": "Minimal Corp provides enterprise software solutions to businesses.",
            "industry": "Software",
            "executives": [],
            "competitors": [],
        }
        output = CompanySeedOutput(**minimal)
        assert output.legal_name == "Minimal Corp"
        assert output.ticker is None
        assert output.is_public is False

    def test_round_trip_serialization(self) -> None:
        """model_dump → model_validate round-trip produces identical output."""
        original = CompanySeedOutput(**_make_company_output())
        dumped = original.model_dump()
        restored = CompanySeedOutput.model_validate(dumped)
        assert original.legal_name == restored.legal_name
        assert original.domain == restored.domain
        assert len(original.executives) == len(restored.executives)
        assert len(original.competitors) == len(restored.competitors)

    def test_schema_version_stable(self) -> None:
        """The schema JSON fingerprint must include all expected top-level keys.

        This test acts as a canary — if someone adds/removes a required field,
        this test surfaces the change explicitly rather than silently.
        """
        schema = CompanySeedOutput.model_json_schema()
        props = set(schema["properties"].keys())

        expected_props = {
            "legal_name", "common_name", "domain", "headquarters",
            "employee_count", "employee_count_source", "year_founded",
            "business_model", "industry", "sub_vertical",
            "is_public", "ticker", "parent_company", "parent_domain",
            "revenue_estimate", "revenue_source",
            "executives", "competitors", "subsidiaries", "product_categories",
            "company_linkedin_url", "twitter_handle", "youtube_url",
            "recent_headline",
        }

        missing = expected_props - props
        extra = props - expected_props

        assert not missing, f"Fields removed from schema: {missing}"
        assert not extra, f"Unexpected new fields in schema: {extra}"
