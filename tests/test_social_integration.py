"""Integration tests for the full intel-social module pipeline.

Tests use real Perplexity + Gemini API calls. Requires both
PERPLEXITY_API_KEY and GEMINI_API_KEY in .env.
Test domain: dell.com (Michael Dell, Jeff Clarke social activity).
"""

from __future__ import annotations

import os

import pytest

from prism_platform.core.module import ExecutionContext
from prism_platform.modules.intel_social.module import SocialModule
from prism_platform.modules.intel_social.schemas import SocialOutput
from prism_platform.modules.intel_social.validator import validate_output

# Skip all tests if required API keys are not set
pytestmark = pytest.mark.skipif(
    not (os.environ.get("PERPLEXITY_API_KEY") and os.environ.get("GEMINI_API_KEY")),
    reason="PERPLEXITY_API_KEY and GEMINI_API_KEY required",
)


def _make_dell_context() -> ExecutionContext:
    """Build an ExecutionContext for Dell Technologies."""
    return ExecutionContext(
        audit_id="test-social-001",
        account_id="acct-dell-001",
        domain="dell.com",
        company_name="Dell Technologies",
        ticker="DELL",
        is_private=False,
    )


def _make_dell_intelligence() -> dict:
    """Build a mock intelligence dict as would come from intel-company."""
    return {
        "executives": [
            {
                "full_name": "Michael Dell",
                "title": "Chairman and CEO",
                "relevance": "economic_buyer",
            },
            {
                "full_name": "Jeff Clarke",
                "title": "Vice Chairman and COO",
                "relevance": "economic_buyer",
            },
            {
                "full_name": "Yvonne McGill",
                "title": "CFO",
                "relevance": "economic_buyer",
            },
        ],
        "competitors": [
            {"company_name": "HP Inc.", "domain": "hp.com"},
            {"company_name": "Lenovo", "domain": "lenovo.com"},
        ],
    }


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


class TestSocialModuleIntegration:
    """Full pipeline integration tests for the SocialModule."""

    @pytest.mark.asyncio
    async def test_full_pipeline_dell(self) -> None:
        """SocialModule produces valid SocialOutput for dell.com."""
        module = SocialModule()
        context = _make_dell_context()
        intelligence = _make_dell_intelligence()

        result = await module.execute(context, intelligence=intelligence)

        # Basic result checks
        assert result.module_name == "intel-social"
        assert result.status in ("success", "partial")
        assert result.duration_ms > 0
        assert result.llm_calls >= 1

        # Deserialize output
        output = SocialOutput.model_validate(result.output)
        assert output.domain == "dell.com"

        # Should have at least some posts or quotes
        total_items = len(output.prospect_posts) + len(output.prospect_exec_quotes)
        assert total_items >= 1, f"Expected at least 1 post or quote, got {total_items}"

        # Validate all posts have content
        for post in output.prospect_posts:
            assert post.content_summary.strip(), "Post has empty content_summary"
            assert post.author_name.strip(), "Post has empty author_name"

        # Validate all quotes have content
        for quote in output.prospect_exec_quotes:
            assert quote.quote.strip(), "Quote has empty quote text"
            assert quote.executive_name.strip(), "Quote has empty executive_name"

        # Sources should be present
        assert len(result.sources) >= 1

    @pytest.mark.asyncio
    async def test_validation_passes(self) -> None:
        """SocialModule output passes the validator."""
        module = SocialModule()
        context = _make_dell_context()
        intelligence = _make_dell_intelligence()

        result = await module.execute(context, intelligence=intelligence)
        validation = await module.validate(result)

        assert validation.checks_run >= 8
        assert validation.checks_passed >= 6, (
            f"Expected at least 6 checks to pass, got {validation.checks_passed}. "
            f"Errors: {validation.errors}. Warnings: {validation.warnings}"
        )

    @pytest.mark.asyncio
    async def test_health_check(self) -> None:
        """SocialModule health check returns True when keys are set."""
        module = SocialModule()
        result = await module.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_no_intelligence_fallback(self) -> None:
        """SocialModule handles missing intelligence gracefully."""
        module = SocialModule()
        context = _make_dell_context()

        result = await module.execute(context, intelligence=None)

        assert result.module_name == "intel-social"
        assert result.status in ("success", "partial", "failed")
        # Should not crash even without intelligence


# ---------------------------------------------------------------------------
# Validator unit tests (no API calls)
# ---------------------------------------------------------------------------


class TestValidatorUnit:
    """Unit tests for the validator function with crafted data."""

    def test_valid_output_passes(self) -> None:
        """A well-formed output passes all checks."""
        from prism_platform.core.types import EvidenceTier, Source

        output = SocialOutput(
            domain="dell.com",
            prospect_posts=[
                {  # type: ignore[arg-type]
                    "author_name": "Michael Dell",
                    "content_summary": "Excited about AI transformation.",
                    "topic": "ai_related",
                    "algolia_relevance": "high",
                }
            ],
            prospect_exec_quotes=[
                {  # type: ignore[arg-type]
                    "executive_name": "Michael Dell",
                    "executive_title": "CEO",
                    "company_name": "Dell Technologies",
                    "quote": "We are investing in AI-powered search.",
                    "context": "CES 2026",
                }
            ],
            high_relevance_count=1,
            medium_relevance_count=0,
            social_summary="Dell execs vocal about AI investment.",
        )
        sources = [
            Source(
                field="prospect_posts",
                value="1 post",
                tier=EvidenceTier.WEBSEARCH,
                source_label="Perplexity",
            )
        ]
        result = validate_output(output, sources)
        assert result.passed is True
        assert result.checks_run >= 8

    def test_empty_domain_fails(self) -> None:
        """Empty domain triggers validation error."""
        from prism_platform.core.types import EvidenceTier, Source

        output = SocialOutput(domain="")
        sources = [
            Source(
                field="test",
                value="test",
                tier=EvidenceTier.WEBSEARCH,
                source_label="test",
            )
        ]
        result = validate_output(output, sources)
        assert result.passed is False
        assert any("domain is empty" in e for e in result.errors)

    def test_mismatched_relevance_count_fails(self) -> None:
        """Mismatched high_relevance_count triggers validation error."""
        from prism_platform.core.types import EvidenceTier, Source

        output = SocialOutput(
            domain="dell.com",
            prospect_posts=[
                {  # type: ignore[arg-type]
                    "author_name": "Test",
                    "content_summary": "Test",
                    "algolia_relevance": "high",
                }
            ],
            high_relevance_count=5,  # Wrong -- should be 1
        )
        sources = [
            Source(
                field="test",
                value="test",
                tier=EvidenceTier.WEBSEARCH,
                source_label="test",
            )
        ]
        result = validate_output(output, sources)
        assert result.passed is False
        assert any("high_relevance_count" in e for e in result.errors)

    def test_no_sources_fails(self) -> None:
        """No source provenance triggers validation error."""
        output = SocialOutput(
            domain="dell.com",
            prospect_posts=[
                {  # type: ignore[arg-type]
                    "author_name": "Test",
                    "content_summary": "Test",
                }
            ],
            social_summary="Summary text.",
        )
        result = validate_output(output, sources=[])
        assert result.passed is False
        assert any("No sources recorded" in e for e in result.errors)
