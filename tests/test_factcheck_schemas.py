"""Contract tests for audit-factcheck schemas -- 25+ pure Pydantic tests, no API/DB calls."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from prism_platform.modules.audit_factcheck.schemas import (
    CategoryResult,
    Claim,
    ClaimStatus,
    Correction,
    FactcheckInput,
    FactcheckOutput,
    GateVerdict,
    VerificationCategory,
    VerifiedClaim,
)


# ---------------------------------------------------------------------------
# FactcheckInput
# ---------------------------------------------------------------------------
class TestFactcheckInput:
    def test_valid_input(self) -> None:
        inp = FactcheckInput(domain="dell.com")
        assert inp.domain == "dell.com"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            FactcheckInput(domain="dell.com", bogus="nope")  # type: ignore[call-arg]

    def test_empty_domain_allowed_by_schema(self) -> None:
        """Domain validation is handled by the validator, not the schema."""
        inp = FactcheckInput(domain="")
        assert inp.domain == ""


# ---------------------------------------------------------------------------
# ClaimStatus enum
# ---------------------------------------------------------------------------
class TestClaimStatus:
    def test_verified_value(self) -> None:
        assert ClaimStatus.VERIFIED == "VERIFIED"

    def test_plausible_value(self) -> None:
        assert ClaimStatus.PLAUSIBLE == "PLAUSIBLE"

    def test_unverified_value(self) -> None:
        assert ClaimStatus.UNVERIFIED == "UNVERIFIED"

    def test_contradicted_value(self) -> None:
        assert ClaimStatus.CONTRADICTED == "CONTRADICTED"

    def test_all_values_count(self) -> None:
        assert len(ClaimStatus) == 4


# ---------------------------------------------------------------------------
# VerificationCategory enum
# ---------------------------------------------------------------------------
class TestVerificationCategory:
    def test_all_eight_categories(self) -> None:
        assert len(VerificationCategory) == 8

    def test_company_facts(self) -> None:
        assert VerificationCategory.COMPANY_FACTS == "company_facts"

    def test_financial_claims(self) -> None:
        assert VerificationCategory.FINANCIAL_CLAIMS == "financial_claims"

    def test_technology_claims(self) -> None:
        assert VerificationCategory.TECHNOLOGY_CLAIMS == "technology_claims"

    def test_traffic_claims(self) -> None:
        assert VerificationCategory.TRAFFIC_CLAIMS == "traffic_claims"

    def test_competitive_claims(self) -> None:
        assert VerificationCategory.COMPETITIVE_CLAIMS == "competitive_claims"

    def test_synthesis_claims(self) -> None:
        assert VerificationCategory.SYNTHESIS_CLAIMS == "synthesis_claims"

    def test_hiring_claims(self) -> None:
        assert VerificationCategory.HIRING_CLAIMS == "hiring_claims"

    def test_quote_claims(self) -> None:
        assert VerificationCategory.QUOTE_CLAIMS == "quote_claims"


# ---------------------------------------------------------------------------
# GateVerdict enum
# ---------------------------------------------------------------------------
class TestGateVerdict:
    def test_proceed_value(self) -> None:
        assert GateVerdict.PROCEED == "PROCEED"

    def test_warn_value(self) -> None:
        assert GateVerdict.WARN == "WARN"

    def test_blocked_value(self) -> None:
        assert GateVerdict.BLOCKED == "BLOCKED"

    def test_all_values_count(self) -> None:
        assert len(GateVerdict) == 3


# ---------------------------------------------------------------------------
# Claim
# ---------------------------------------------------------------------------
class TestClaim:
    def test_valid_full(self) -> None:
        claim = Claim(
            claim_text="Dell has $102B annual revenue",
            source_module="intel-financial-public",
            category=VerificationCategory.FINANCIAL_CLAIMS,
            evidence_text="Yahoo Finance FY2024 data",
            evidence_source_url="https://finance.yahoo.com/quote/DELL",
        )
        assert claim.claim_text == "Dell has $102B annual revenue"
        assert claim.source_module == "intel-financial-public"
        assert claim.category == VerificationCategory.FINANCIAL_CLAIMS
        assert claim.evidence_source_url is not None

    def test_minimal_defaults(self) -> None:
        claim = Claim(
            claim_text="Dell is a public company",
            source_module="intel-company",
            category=VerificationCategory.COMPANY_FACTS,
        )
        assert claim.evidence_text is None
        assert claim.evidence_source_url is None

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            Claim(
                claim_text="test",
                source_module="test",
                category=VerificationCategory.COMPANY_FACTS,
                bogus="nope",  # type: ignore[call-arg]
            )


# ---------------------------------------------------------------------------
# VerifiedClaim
# ---------------------------------------------------------------------------
class TestVerifiedClaim:
    def _make_claim(self) -> Claim:
        return Claim(
            claim_text="Dell uses Elasticsearch",
            source_module="intel-techstack",
            category=VerificationCategory.TECHNOLOGY_CLAIMS,
        )

    def test_verified_status(self) -> None:
        vc = VerifiedClaim(
            claim=self._make_claim(),
            status=ClaimStatus.VERIFIED,
            verification_notes="Confirmed via BuiltWith API",
            corrected_value=None,
        )
        assert vc.status == ClaimStatus.VERIFIED
        assert vc.corrected_value is None

    def test_contradicted_with_correction(self) -> None:
        vc = VerifiedClaim(
            claim=self._make_claim(),
            status=ClaimStatus.CONTRADICTED,
            verification_notes="Dell uses Algolia, not Elasticsearch",
            corrected_value="Algolia",
        )
        assert vc.status == ClaimStatus.CONTRADICTED
        assert vc.corrected_value == "Algolia"

    def test_plausible_status(self) -> None:
        vc = VerifiedClaim(
            claim=self._make_claim(),
            status=ClaimStatus.PLAUSIBLE,
            verification_notes="Consistent with BuiltWith data",
        )
        assert vc.status == ClaimStatus.PLAUSIBLE

    def test_unverified_status(self) -> None:
        vc = VerifiedClaim(
            claim=self._make_claim(),
            status=ClaimStatus.UNVERIFIED,
            verification_notes="No evidence available",
        )
        assert vc.status == ClaimStatus.UNVERIFIED

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            VerifiedClaim(
                claim=self._make_claim(),
                status=ClaimStatus.VERIFIED,
                verification_notes="ok",
                bogus="nope",  # type: ignore[call-arg]
            )


# ---------------------------------------------------------------------------
# CategoryResult
# ---------------------------------------------------------------------------
class TestCategoryResult:
    def test_valid_with_consistent_counts(self) -> None:
        claim = Claim(
            claim_text="Test claim",
            source_module="intel-company",
            category=VerificationCategory.COMPANY_FACTS,
        )
        vc = VerifiedClaim(
            claim=claim,
            status=ClaimStatus.VERIFIED,
            verification_notes="ok",
        )
        cr = CategoryResult(
            category=VerificationCategory.COMPANY_FACTS,
            claims_count=1,
            verified=1,
            plausible=0,
            unverified=0,
            contradicted=0,
            claims=[vc],
        )
        assert cr.claims_count == 1
        assert cr.verified == 1
        assert len(cr.claims) == 1

    def test_empty_category(self) -> None:
        cr = CategoryResult(
            category=VerificationCategory.HIRING_CLAIMS,
            claims_count=0,
        )
        assert cr.verified == 0
        assert cr.plausible == 0
        assert cr.unverified == 0
        assert cr.contradicted == 0
        assert cr.claims == []

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            CategoryResult(
                category=VerificationCategory.COMPANY_FACTS,
                claims_count=0,
                bogus="nope",  # type: ignore[call-arg]
            )


# ---------------------------------------------------------------------------
# Correction
# ---------------------------------------------------------------------------
class TestCorrection:
    def test_valid_correction(self) -> None:
        c = Correction(
            claim_text="Dell revenue is $50B",
            source_module="intel-financial-public",
            incorrect_value="$50B",
            corrected_value="$102B",
            correction_reason="Yahoo Finance shows $102B for FY2024",
        )
        assert c.corrected_value == "$102B"
        assert c.source_module == "intel-financial-public"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            Correction(
                claim_text="test",
                source_module="test",
                incorrect_value="wrong",
                corrected_value="right",
                correction_reason="because",
                bogus="nope",  # type: ignore[call-arg]
            )


# ---------------------------------------------------------------------------
# FactcheckOutput
# ---------------------------------------------------------------------------
class TestFactcheckOutput:
    def _make_category_results(self) -> list[CategoryResult]:
        """Build all 8 category results for a valid output."""
        results: list[CategoryResult] = []
        for cat in VerificationCategory:
            results.append(
                CategoryResult(
                    category=cat,
                    claims_count=0,
                )
            )
        return results

    def test_valid_proceed_output(self) -> None:
        results = self._make_category_results()
        # Give company_facts some claims
        claim = Claim(
            claim_text="Dell is headquartered in Round Rock, TX",
            source_module="intel-company",
            category=VerificationCategory.COMPANY_FACTS,
        )
        vc = VerifiedClaim(
            claim=claim,
            status=ClaimStatus.VERIFIED,
            verification_notes="Confirmed",
        )
        results[0] = CategoryResult(
            category=VerificationCategory.COMPANY_FACTS,
            claims_count=1,
            verified=1,
            claims=[vc],
        )

        output = FactcheckOutput(
            domain="dell.com",
            verdict=GateVerdict.PROCEED,
            category_results=results,
            total_claims=1,
            verified_count=1,
            contradicted_pct=0.0,
            unverified_pct=0.0,
            summary="All claims verified.",
        )
        assert output.verdict == GateVerdict.PROCEED
        assert output.total_claims == 1
        assert len(output.category_results) == 8

    def test_warn_verdict(self) -> None:
        results = self._make_category_results()
        output = FactcheckOutput(
            domain="dell.com",
            verdict=GateVerdict.WARN,
            category_results=results,
            total_claims=20,
            verified_count=14,
            unverified_count=4,
            contradicted_count=2,
            contradicted_pct=10.0,
            unverified_pct=20.0,
            corrections=[
                Correction(
                    claim_text="test",
                    source_module="test",
                    incorrect_value="wrong",
                    corrected_value="right",
                    correction_reason="because",
                ),
            ],
            summary="Some claims need review.",
        )
        assert output.verdict == GateVerdict.WARN
        assert output.contradicted_pct == 10.0

    def test_blocked_verdict(self) -> None:
        results = self._make_category_results()
        output = FactcheckOutput(
            domain="dell.com",
            verdict=GateVerdict.BLOCKED,
            category_results=results,
            total_claims=10,
            contradicted_count=3,
            contradicted_pct=30.0,
            summary="Too many contradictions.",
        )
        assert output.verdict == GateVerdict.BLOCKED

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            FactcheckOutput(
                domain="dell.com",
                verdict=GateVerdict.PROCEED,
                summary="ok",
                bogus="nope",  # type: ignore[call-arg]
            )

    def test_missing_required_domain(self) -> None:
        with pytest.raises(ValidationError):
            FactcheckOutput(  # type: ignore[call-arg]
                verdict=GateVerdict.PROCEED,
                summary="ok",
            )

    def test_missing_required_verdict(self) -> None:
        with pytest.raises(ValidationError):
            FactcheckOutput(  # type: ignore[call-arg]
                domain="dell.com",
                summary="ok",
            )

    def test_defaults(self) -> None:
        output = FactcheckOutput(
            domain="dell.com",
            verdict=GateVerdict.PROCEED,
        )
        assert output.total_claims == 0
        assert output.verified_count == 0
        assert output.plausible_count == 0
        assert output.unverified_count == 0
        assert output.contradicted_count == 0
        assert output.contradicted_pct == 0.0
        assert output.unverified_pct == 0.0
        assert output.corrections == []
        assert output.category_results == []
        assert output.summary == ""

    def test_all_verified_zero_pct(self) -> None:
        output = FactcheckOutput(
            domain="dell.com",
            verdict=GateVerdict.PROCEED,
            total_claims=10,
            verified_count=10,
            contradicted_pct=0.0,
            unverified_pct=0.0,
            summary="All good.",
        )
        assert output.contradicted_pct == 0.0
        assert output.unverified_pct == 0.0

    def test_all_contradicted(self) -> None:
        output = FactcheckOutput(
            domain="dell.com",
            verdict=GateVerdict.BLOCKED,
            total_claims=5,
            contradicted_count=5,
            contradicted_pct=100.0,
            unverified_pct=0.0,
            summary="Everything wrong.",
        )
        assert output.contradicted_count == 5
        assert output.contradicted_pct == 100.0
