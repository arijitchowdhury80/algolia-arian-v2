"""Tests for intel-financial-private collector -- prompt construction and waterfall logic."""

from __future__ import annotations

from prism_platform.core.types import EvidenceTier, Source
from prism_platform.modules.intel_financial_private.collector import (
    _build_prompts,
)
from prism_platform.modules.intel_financial_private.schemas import (
    FinancialPrivateOutput,
    RevenueEstimate,
    RevenueWaterfall,
)
from prism_platform.modules.intel_financial_private.validator import validate_output


class TestBuildPrompts:
    """Tests for _build_prompts helper."""

    def test_returns_six_prompts(self) -> None:
        prompts = _build_prompts("Acme Corp", "acme.com")
        assert len(prompts) == 6

    def test_all_prompts_have_label_and_prompt(self) -> None:
        prompts = _build_prompts("Acme Corp", "acme.com")
        for p in prompts:
            assert "label" in p
            assert "prompt" in p
            assert len(p["label"]) > 0
            assert len(p["prompt"]) > 0

    def test_prompts_contain_company_name(self) -> None:
        prompts = _build_prompts("Acme Corp", "acme.com")
        for p in prompts:
            assert "Acme Corp" in p["prompt"]

    def test_prompts_contain_domain(self) -> None:
        prompts = _build_prompts("Acme Corp", "acme.com")
        for p in prompts:
            assert "acme.com" in p["prompt"]

    def test_industry_context_included(self) -> None:
        prompts = _build_prompts("Acme Corp", "acme.com", industry="SaaS")
        industry_prompts = [p for p in prompts if "SaaS" in p["prompt"]]
        # At least the industry-relevant prompts should mention it
        assert len(industry_prompts) >= 2

    def test_expected_labels(self) -> None:
        prompts = _build_prompts("Test Co", "test.com")
        labels = [p["label"] for p in prompts]
        assert "Company press releases / annual reports" in labels
        assert "Industry reports" in labels
        assert "Crunchbase / PitchBook funding data" in labels
        assert "Employee count to revenue model" in labels
        assert "News mentions of revenue" in labels
        assert "Competitor comparison" in labels


class TestValidateOutput:
    """Tests for the validator with various output states."""

    def test_skipped_with_reason_passes(self) -> None:
        output = FinancialPrivateOutput(
            domain="dell.com",
            skipped=True,
            skip_reason="Company is public",
        )
        result = validate_output(output, [])
        assert result.passed is True

    def test_skipped_without_reason_fails(self) -> None:
        output = FinancialPrivateOutput(
            domain="dell.com",
            skipped=True,
            skip_reason=None,
        )
        result = validate_output(output, [])
        assert result.passed is False
        assert any("skip_reason" in e for e in result.errors)

    def test_valid_non_skipped_output_passes(self) -> None:
        output = FinancialPrivateOutput(
            domain="acme.com",
            revenue_waterfall=RevenueWaterfall(
                estimates=[
                    RevenueEstimate(
                        source_name="IDC Report",
                        methodology="Extracted from IDC 2025",
                        estimated_revenue=50_000_000.0,
                        evidence="IDC says $50M",
                        evidence_tier="WEBSEARCH",
                    ),
                    RevenueEstimate(
                        source_name="News Article",
                        methodology="TechCrunch mention",
                        estimated_revenue=60_000_000.0,
                        evidence="TechCrunch reported ~$60M",
                        evidence_tier="WEBSEARCH",
                    ),
                ],
                best_estimate=55_000_000.0,
                best_estimate_confidence="medium",
                best_estimate_methodology="Median of two sources",
                range_low=50_000_000.0,
                range_high=60_000_000.0,
            ),
        )
        sources = [
            Source(
                field="revenue_waterfall",
                value="Perplexity research",
                tier=EvidenceTier.WEBSEARCH,
                source_label="Perplexity sonar-pro",
                method="llm_extraction",
            ),
        ]
        result = validate_output(output, sources)
        assert result.passed is True

    def test_no_waterfall_fails(self) -> None:
        output = FinancialPrivateOutput(domain="acme.com")
        sources = [
            Source(
                field="test",
                value="test",
                tier=EvidenceTier.WEBSEARCH,
                source_label="test",
            ),
        ]
        result = validate_output(output, sources)
        assert result.passed is False
        assert any("revenue_waterfall is None" in e for e in result.errors)

    def test_too_few_estimates_fails(self) -> None:
        output = FinancialPrivateOutput(
            domain="acme.com",
            revenue_waterfall=RevenueWaterfall(
                estimates=[
                    RevenueEstimate(
                        source_name="Only one",
                        methodology="Single source",
                        evidence_tier="WEBSEARCH",
                    ),
                ],
            ),
        )
        sources = [
            Source(
                field="test",
                value="test",
                tier=EvidenceTier.WEBSEARCH,
                source_label="test",
            ),
        ]
        result = validate_output(output, sources)
        assert result.passed is False
        assert any("at least 2" in e for e in result.errors)

    def test_best_estimate_outside_range_fails(self) -> None:
        output = FinancialPrivateOutput(
            domain="acme.com",
            revenue_waterfall=RevenueWaterfall(
                estimates=[
                    RevenueEstimate(
                        source_name="A",
                        methodology="test",
                        estimated_revenue=50_000_000.0,
                        evidence_tier="WEBSEARCH",
                    ),
                    RevenueEstimate(
                        source_name="B",
                        methodology="test",
                        estimated_revenue=60_000_000.0,
                        evidence_tier="WEBSEARCH",
                    ),
                ],
                best_estimate=100_000_000.0,  # Outside range
                range_low=50_000_000.0,
                range_high=60_000_000.0,
            ),
        )
        sources = [
            Source(
                field="test",
                value="test",
                tier=EvidenceTier.WEBSEARCH,
                source_label="test",
            ),
        ]
        result = validate_output(output, sources)
        assert result.passed is False
        assert any("outside range" in e for e in result.errors)

    def test_no_sources_fails(self) -> None:
        output = FinancialPrivateOutput(
            domain="acme.com",
            revenue_waterfall=RevenueWaterfall(
                estimates=[
                    RevenueEstimate(
                        source_name="A",
                        methodology="test",
                        evidence_tier="WEBSEARCH",
                    ),
                    RevenueEstimate(
                        source_name="B",
                        methodology="test",
                        evidence_tier="WEBSEARCH",
                    ),
                ],
            ),
        )
        result = validate_output(output, [])
        assert result.passed is False
        assert any("No sources" in e for e in result.errors)

    def test_empty_source_name_fails(self) -> None:
        output = FinancialPrivateOutput(
            domain="acme.com",
            revenue_waterfall=RevenueWaterfall(
                estimates=[
                    RevenueEstimate(
                        source_name="",
                        methodology="test",
                        evidence_tier="WEBSEARCH",
                    ),
                    RevenueEstimate(
                        source_name="B",
                        methodology="test",
                        evidence_tier="WEBSEARCH",
                    ),
                ],
            ),
        )
        sources = [
            Source(
                field="test",
                value="test",
                tier=EvidenceTier.WEBSEARCH,
                source_label="test",
            ),
        ]
        result = validate_output(output, sources)
        assert result.passed is False
        assert any("source_name is empty" in e for e in result.errors)
