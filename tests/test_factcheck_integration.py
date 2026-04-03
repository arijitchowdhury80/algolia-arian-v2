"""Integration tests for audit-factcheck module.

Tests module metadata, enricher logic, validator, and verdict computation.
"""

from __future__ import annotations

from prism_platform.modules.audit_factcheck.enricher import (
    FactcheckEnricher,
    compute_verdict,
)
from prism_platform.modules.audit_factcheck.module import FactcheckModule
from prism_platform.modules.audit_factcheck.schemas import (
    CategoryResult,
    Claim,
    ClaimStatus,
    FactcheckInput,
    FactcheckOutput,
    GateVerdict,
    VerificationCategory,
    VerifiedClaim,
)
from prism_platform.modules.audit_factcheck.validator import validate_output


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_claim(
    text: str = "Test claim about the company",
    module: str = "intel-company",
    category: VerificationCategory = VerificationCategory.COMPANY_FACTS,
) -> Claim:
    return Claim(
        claim_text=text,
        source_module=module,
        category=category,
    )


def _make_verified_claim(
    status: ClaimStatus = ClaimStatus.VERIFIED,
    corrected: str | None = None,
) -> VerifiedClaim:
    return VerifiedClaim(
        claim=_make_claim(),
        status=status,
        verification_notes="Test verification",
        corrected_value=corrected,
    )


def _make_all_category_results(
    verified: int = 10,
    plausible: int = 0,
    unverified: int = 0,
    contradicted: int = 0,
) -> list[CategoryResult]:
    """Build all 8 category results with the given counts in the first category."""
    results: list[CategoryResult] = []
    for i, cat in enumerate(VerificationCategory):
        if i == 0:
            total = verified + plausible + unverified + contradicted
            claims: list[VerifiedClaim] = []
            for _ in range(verified):
                claims.append(_make_verified_claim(ClaimStatus.VERIFIED))
            for _ in range(plausible):
                claims.append(_make_verified_claim(ClaimStatus.PLAUSIBLE))
            for _ in range(unverified):
                claims.append(_make_verified_claim(ClaimStatus.UNVERIFIED))
            for _ in range(contradicted):
                claims.append(_make_verified_claim(ClaimStatus.CONTRADICTED, corrected="fixed"))
            results.append(
                CategoryResult(
                    category=cat,
                    claims_count=total,
                    verified=verified,
                    plausible=plausible,
                    unverified=unverified,
                    contradicted=contradicted,
                    claims=claims,
                )
            )
        else:
            results.append(CategoryResult(category=cat, claims_count=0))
    return results


# ---------------------------------------------------------------------------
# Module metadata tests
# ---------------------------------------------------------------------------
class TestModuleMetadata:
    def test_module_name(self) -> None:
        mod = FactcheckModule()
        assert mod.name == "audit-factcheck"

    def test_module_version(self) -> None:
        mod = FactcheckModule()
        assert mod.version == "0.1.0"

    def test_module_layer(self) -> None:
        mod = FactcheckModule()
        assert mod.layer == "quality"

    def test_module_dependencies_empty(self) -> None:
        mod = FactcheckModule()
        assert mod.dependencies == []

    def test_module_requires_llm(self) -> None:
        mod = FactcheckModule()
        assert mod.requires_llm is True

    def test_module_timeout(self) -> None:
        mod = FactcheckModule()
        assert mod.timeout_seconds == 600

    def test_module_max_retries(self) -> None:
        mod = FactcheckModule()
        assert mod.max_retries == 1

    def test_input_schema(self) -> None:
        mod = FactcheckModule()
        assert mod.input_schema is FactcheckInput

    def test_output_schema(self) -> None:
        mod = FactcheckModule()
        assert mod.output_schema is FactcheckOutput


# ---------------------------------------------------------------------------
# compute_verdict tests
# ---------------------------------------------------------------------------
class TestComputeVerdict:
    def test_proceed_low_contradicted_low_unverified(self) -> None:
        assert compute_verdict(2.0, 10.0) == GateVerdict.PROCEED

    def test_proceed_zero_both(self) -> None:
        assert compute_verdict(0.0, 0.0) == GateVerdict.PROCEED

    def test_warn_moderate_contradicted(self) -> None:
        assert compute_verdict(10.0, 5.0) == GateVerdict.WARN

    def test_warn_high_unverified(self) -> None:
        assert compute_verdict(3.0, 20.0) == GateVerdict.WARN

    def test_warn_at_5pct_contradicted_threshold(self) -> None:
        assert compute_verdict(5.0, 0.0) == GateVerdict.WARN

    def test_warn_at_15pct_unverified_threshold(self) -> None:
        assert compute_verdict(0.0, 15.0) == GateVerdict.WARN

    def test_blocked_high_contradicted(self) -> None:
        assert compute_verdict(20.0, 5.0) == GateVerdict.BLOCKED

    def test_blocked_at_threshold(self) -> None:
        assert compute_verdict(15.1, 0.0) == GateVerdict.BLOCKED

    def test_blocked_exact_boundary(self) -> None:
        # >15 is BLOCKED, 15 exactly is WARN (5-15 range)
        assert compute_verdict(15.0, 0.0) == GateVerdict.WARN


# ---------------------------------------------------------------------------
# Validator tests
# ---------------------------------------------------------------------------
class TestValidator:
    def test_passes_with_good_data(self) -> None:
        results = _make_all_category_results(verified=10)
        output = FactcheckOutput(
            domain="dell.com",
            verdict=GateVerdict.PROCEED,
            category_results=results,
            total_claims=10,
            verified_count=10,
            contradicted_pct=0.0,
            unverified_pct=0.0,
            summary="All verified.",
        )
        vr = validate_output(output)
        assert vr.passed is True
        assert vr.checks_run == 8
        assert vr.checks_passed == 8

    def test_fails_with_zero_claims(self) -> None:
        results = [CategoryResult(category=cat, claims_count=0) for cat in VerificationCategory]
        output = FactcheckOutput(
            domain="dell.com",
            verdict=GateVerdict.PROCEED,
            category_results=results,
            total_claims=0,
            summary="Empty.",
        )
        vr = validate_output(output)
        assert vr.passed is False
        assert any("total_claims" in e for e in vr.errors)

    def test_fails_with_missing_categories(self) -> None:
        # Only 1 category result instead of 8
        output = FactcheckOutput(
            domain="dell.com",
            verdict=GateVerdict.PROCEED,
            category_results=[
                CategoryResult(
                    category=VerificationCategory.COMPANY_FACTS,
                    claims_count=1,
                    verified=1,
                    claims=[_make_verified_claim()],
                ),
            ],
            total_claims=1,
            verified_count=1,
            contradicted_pct=0.0,
            unverified_pct=0.0,
            summary="Partial.",
        )
        vr = validate_output(output)
        assert vr.passed is False
        assert any("Missing category" in e for e in vr.errors)

    def test_warns_on_inconsistent_percentages(self) -> None:
        results = _make_all_category_results(verified=8, contradicted=2)
        output = FactcheckOutput(
            domain="dell.com",
            verdict=GateVerdict.WARN,
            category_results=results,
            total_claims=10,
            verified_count=8,
            contradicted_count=2,
            contradicted_pct=25.0,  # Wrong -- should be 20.0
            unverified_pct=0.0,
            summary="Test.",
        )
        vr = validate_output(output)
        # Should have a warning about percentage inconsistency
        assert len(vr.warnings) > 0

    def test_fails_on_verdict_mismatch(self) -> None:
        results = _make_all_category_results(verified=10)
        output = FactcheckOutput(
            domain="dell.com",
            verdict=GateVerdict.BLOCKED,  # Should be PROCEED
            category_results=results,
            total_claims=10,
            verified_count=10,
            contradicted_pct=0.0,
            unverified_pct=0.0,
            summary="Mismatch.",
        )
        vr = validate_output(output)
        assert vr.passed is False
        assert any("Verdict mismatch" in e for e in vr.errors)

    def test_warns_on_contradicted_without_corrections(self) -> None:
        results = _make_all_category_results(verified=8, contradicted=2)
        output = FactcheckOutput(
            domain="dell.com",
            verdict=GateVerdict.WARN,
            category_results=results,
            total_claims=10,
            verified_count=8,
            contradicted_count=2,
            contradicted_pct=20.0,
            unverified_pct=0.0,
            corrections=[],  # No corrections despite contradictions
            summary="Test.",
        )
        vr = validate_output(output)
        # Should warn about missing corrections
        assert any("corrections" in w for w in vr.warnings)

    def test_fails_on_empty_summary(self) -> None:
        results = _make_all_category_results(verified=10)
        output = FactcheckOutput(
            domain="dell.com",
            verdict=GateVerdict.PROCEED,
            category_results=results,
            total_claims=10,
            verified_count=10,
            contradicted_pct=0.0,
            unverified_pct=0.0,
            summary="",
        )
        vr = validate_output(output)
        assert vr.passed is False
        assert any("summary" in e for e in vr.errors)

    def test_fails_on_inconsistent_category_counts(self) -> None:
        results = [CategoryResult(category=cat, claims_count=0) for cat in VerificationCategory]
        # Make the first category have inconsistent counts
        results[0] = CategoryResult(
            category=VerificationCategory.COMPANY_FACTS,
            claims_count=5,  # Says 5 but verified=3, sum is 3
            verified=3,
            claims=[_make_verified_claim() for _ in range(3)],  # 3 claims, not 5
        )
        output = FactcheckOutput(
            domain="dell.com",
            verdict=GateVerdict.PROCEED,
            category_results=results,
            total_claims=5,
            verified_count=3,
            contradicted_pct=0.0,
            unverified_pct=0.0,
            summary="Inconsistent.",
        )
        vr = validate_output(output)
        assert vr.passed is False
        assert any("Inconsistent" in e for e in vr.errors)


# ---------------------------------------------------------------------------
# Enricher build_category_result tests
# ---------------------------------------------------------------------------
class TestEnricherCategoryResult:
    def test_build_category_result_all_verified(self) -> None:
        enricher = FactcheckEnricher()
        verified_claims = [_make_verified_claim(ClaimStatus.VERIFIED) for _ in range(5)]
        result = enricher._build_category_result(
            VerificationCategory.COMPANY_FACTS, verified_claims
        )
        assert result.claims_count == 5
        assert result.verified == 5
        assert result.contradicted == 0

    def test_build_category_result_mixed(self) -> None:
        enricher = FactcheckEnricher()
        verified_claims = [
            _make_verified_claim(ClaimStatus.VERIFIED),
            _make_verified_claim(ClaimStatus.PLAUSIBLE),
            _make_verified_claim(ClaimStatus.UNVERIFIED),
            _make_verified_claim(ClaimStatus.CONTRADICTED, corrected="fix"),
        ]
        result = enricher._build_category_result(
            VerificationCategory.FINANCIAL_CLAIMS, verified_claims
        )
        assert result.claims_count == 4
        assert result.verified == 1
        assert result.plausible == 1
        assert result.unverified == 1
        assert result.contradicted == 1
