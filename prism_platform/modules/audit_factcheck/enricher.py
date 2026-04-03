"""Audit Factcheck enricher -- Claude-powered claim verification (8 batched calls).

Uses Instructor + Claude Sonnet to verify claims. Makes exactly 8 calls --
one per VerificationCategory. Each call sends all claims in that category plus
their evidence for evaluation.

Gate verdict logic:
- PROCEED: <5% CONTRADICTED and <15% UNVERIFIED
- WARN: 5-15% CONTRADICTED or 15-30% UNVERIFIED
- BLOCKED: >15% CONTRADICTED
"""

from __future__ import annotations

import time

import structlog
from pydantic import BaseModel, ConfigDict, Field

from prism_platform.core.llm import create_completion
from prism_platform.modules.audit_factcheck.schemas import (
    CategoryResult,
    Claim,
    ClaimStatus,
    Correction,
    FactcheckOutput,
    GateVerdict,
    VerificationCategory,
    VerifiedClaim,
)

logger = structlog.get_logger(__name__)


class VerifiedClaimBatch(BaseModel):
    """Instructor response model for a batch of verified claims."""

    model_config = ConfigDict(extra="forbid")

    verified_claims: list[VerifiedClaim] = Field(
        default_factory=list,
        description="List of claims with verification status and notes.",
    )


class FactcheckEnricher:
    """Verifies claims using Instructor + Claude Sonnet."""

    def __init__(self) -> None:
        """Initialize the Claude Instructor client."""
        pass

    async def enrich(
        self,
        domain: str,
        categorized_claims: dict[VerificationCategory, list[Claim]],
    ) -> tuple[FactcheckOutput, int, float]:
        """Verify all claims via 8 batched Claude calls and produce FactcheckOutput.

        Args:
            domain: The domain being fact-checked.
            categorized_claims: Dict mapping category to list of claims.

        Returns:
            Tuple of (FactcheckOutput, llm_calls, llm_cost_usd).
        """
        logger.info(
            "[FactcheckEnricher] enrich started",
            domain=domain,
            categories=len(categorized_claims),
        )

        llm_calls = 0
        total_input_chars = 0
        total_output_chars = 0
        category_results: list[CategoryResult] = []
        all_corrections: list[Correction] = []

        # Make exactly 8 calls -- one per category
        for category in VerificationCategory:
            claims = categorized_claims.get(category, [])

            if not claims:
                # Empty category -- still include in results with zero counts
                category_results.append(
                    CategoryResult(
                        category=category,
                        claims_count=0,
                        verified=0,
                        plausible=0,
                        unverified=0,
                        contradicted=0,
                        claims=[],
                    )
                )
                continue

            try:
                logger.info(
                    "[FactcheckEnricher] verifying category",
                    category=category.value,
                    claims_count=len(claims),
                )
                cat_start = time.monotonic()
                verified_batch = await self._verify_category(domain, category, claims)
                cat_duration_ms = round((time.monotonic() - cat_start) * 1000)
                llm_calls += 1

                prompt_text = self._build_verification_prompt(domain, category, claims)
                input_chars = len(prompt_text)
                output_chars = len(verified_batch.model_dump_json())
                total_input_chars += input_chars
                total_output_chars += output_chars
                cat_cost = (input_chars * 0.10 / 1_000_000) + (output_chars * 0.40 / 1_000_000)

                # Build category result from verified claims
                cat_result = self._build_category_result(category, verified_batch.verified_claims)
                category_results.append(cat_result)

                # Extract corrections for contradicted claims
                for vc in verified_batch.verified_claims:
                    if vc.status == ClaimStatus.CONTRADICTED and vc.corrected_value:
                        all_corrections.append(
                            Correction(
                                claim_text=vc.claim.claim_text,
                                source_module=vc.claim.source_module,
                                incorrect_value=vc.claim.claim_text,
                                corrected_value=vc.corrected_value,
                                correction_reason=vc.verification_notes,
                            )
                        )

                logger.info(
                    "[FactcheckEnricher] category verified",
                    category=category.value,
                    claims_count=len(claims),
                    verified=cat_result.verified,
                    plausible=cat_result.plausible,
                    unverified=cat_result.unverified,
                    contradicted=cat_result.contradicted,
                    duration_ms=cat_duration_ms,
                    est_input_tokens=input_chars // 4,
                    est_output_tokens=output_chars // 4,
                    est_cost_usd=round(cat_cost, 6),
                )
            except Exception as exc:
                logger.error(
                    "[FactcheckEnricher] category verification failed, marking all UNVERIFIED",
                    category=category.value,
                    error=str(exc),
                )
                # Fallback: mark all claims as UNVERIFIED
                fallback_claims = [
                    VerifiedClaim(
                        claim=claim,
                        status=ClaimStatus.UNVERIFIED,
                        verification_notes=f"Verification failed: {exc}",
                        corrected_value=None,
                    )
                    for claim in claims
                ]
                cat_result = self._build_category_result(category, fallback_claims)
                category_results.append(cat_result)

        # Aggregate totals
        total_claims = sum(cr.claims_count for cr in category_results)
        verified_count = sum(cr.verified for cr in category_results)
        plausible_count = sum(cr.plausible for cr in category_results)
        unverified_count = sum(cr.unverified for cr in category_results)
        contradicted_count = sum(cr.contradicted for cr in category_results)

        contradicted_pct = (contradicted_count / total_claims * 100.0) if total_claims > 0 else 0.0
        unverified_pct = (unverified_count / total_claims * 100.0) if total_claims > 0 else 0.0

        # Determine gate verdict
        verdict = compute_verdict(contradicted_pct, unverified_pct)
        logger.info(
            "[FactcheckEnricher] verdict computed",
            domain=domain,
            verdict=verdict.value,
            contradicted_pct=round(contradicted_pct, 2),
            unverified_pct=round(unverified_pct, 2),
            total_claims=total_claims,
            verified_count=verified_count,
            plausible_count=plausible_count,
            unverified_count=unverified_count,
            contradicted_count=contradicted_count,
        )

        # Build summary
        summary = self._build_summary(
            domain,
            verdict,
            total_claims,
            verified_count,
            plausible_count,
            unverified_count,
            contradicted_count,
            contradicted_pct,
            unverified_pct,
        )

        # Estimate cost (Claude Sonnet pricing: ~$0.10/1M input, ~$0.40/1M output chars)
        estimated_cost = (total_input_chars * 0.10 / 1_000_000) + (
            total_output_chars * 0.40 / 1_000_000
        )

        output = FactcheckOutput(
            domain=domain,
            verdict=verdict,
            category_results=category_results,
            total_claims=total_claims,
            verified_count=verified_count,
            plausible_count=plausible_count,
            unverified_count=unverified_count,
            contradicted_count=contradicted_count,
            contradicted_pct=round(contradicted_pct, 2),
            unverified_pct=round(unverified_pct, 2),
            corrections=all_corrections,
            summary=summary,
        )

        logger.info(
            "[FactcheckEnricher] enrich completed",
            domain=domain,
            verdict=verdict.value,
            total_claims=total_claims,
            contradicted_pct=round(contradicted_pct, 2),
            unverified_pct=round(unverified_pct, 2),
            corrections_count=len(all_corrections),
            llm_calls=llm_calls,
            est_total_cost_usd=round(estimated_cost, 4),
            total_input_chars=total_input_chars,
            total_output_chars=total_output_chars,
        )

        return output, llm_calls, estimated_cost

    async def _verify_category(
        self,
        domain: str,
        category: VerificationCategory,
        claims: list[Claim],
    ) -> VerifiedClaimBatch:
        """Verify all claims in a single category via one Claude call.

        Args:
            domain: The domain being fact-checked.
            category: The verification category.
            claims: All claims in this category.

        Returns:
            VerifiedClaimBatch with verification results.

        Raises:
            Exception: If the Claude call fails after retries.
        """
        prompt = self._build_verification_prompt(domain, category, claims)

        try:
            result = create_completion(
                response_model=VerifiedClaimBatch,
                max_retries=3,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
            )
            return result
        except Exception as exc:
            logger.error(
                "[FactcheckEnricher] Claude call failed",
                category=category.value,
                domain=domain,
                error=str(exc),
            )
            raise

    def _build_verification_prompt(
        self,
        domain: str,
        category: VerificationCategory,
        claims: list[Claim],
    ) -> str:
        """Build the verification prompt for a category of claims.

        Args:
            domain: The domain being fact-checked.
            category: The verification category.
            claims: Claims to verify.

        Returns:
            The prompt string.
        """
        claims_text = ""
        for i, claim in enumerate(claims, 1):
            claims_text += f"\n{i}. Claim: {claim.claim_text}"
            claims_text += f"\n   Source module: {claim.source_module}"
            if claim.evidence_text:
                claims_text += f"\n   Evidence: {claim.evidence_text}"
            if claim.evidence_source_url:
                claims_text += f"\n   Source URL: {claim.evidence_source_url}"
            claims_text += "\n"

        return f"""You are a fact-checker for a sales intelligence platform. Verify each claim below
about the company at domain '{domain}'. Category: {category.value}.

For each claim, assign one of these statuses:
- VERIFIED: The claim is factually correct based on the evidence and your knowledge.
- PLAUSIBLE: The claim is reasonable and consistent with available information but cannot be independently confirmed.
- UNVERIFIED: There is insufficient evidence to evaluate the claim.
- CONTRADICTED: The claim is factually incorrect based on available evidence.

For CONTRADICTED claims, provide the corrected_value with the accurate information.

Claims to verify:
{claims_text}

Return exactly {len(claims)} verified claims in the same order as the input.
Each must include the original claim object, a status, verification_notes explaining your reasoning,
and corrected_value (only for CONTRADICTED claims, None otherwise)."""

    def _build_category_result(
        self,
        category: VerificationCategory,
        verified_claims: list[VerifiedClaim],
    ) -> CategoryResult:
        """Build a CategoryResult from a list of verified claims.

        Args:
            category: The verification category.
            verified_claims: List of verified claims.

        Returns:
            CategoryResult with aggregated counts.
        """
        verified = sum(1 for vc in verified_claims if vc.status == ClaimStatus.VERIFIED)
        plausible = sum(1 for vc in verified_claims if vc.status == ClaimStatus.PLAUSIBLE)
        unverified = sum(1 for vc in verified_claims if vc.status == ClaimStatus.UNVERIFIED)
        contradicted = sum(1 for vc in verified_claims if vc.status == ClaimStatus.CONTRADICTED)

        return CategoryResult(
            category=category,
            claims_count=len(verified_claims),
            verified=verified,
            plausible=plausible,
            unverified=unverified,
            contradicted=contradicted,
            claims=verified_claims,
        )

    def _build_summary(
        self,
        domain: str,
        verdict: GateVerdict,
        total_claims: int,
        verified_count: int,
        plausible_count: int,
        unverified_count: int,
        contradicted_count: int,
        contradicted_pct: float,
        unverified_pct: float,
    ) -> str:
        """Build a human-readable summary of fact-check results.

        Args:
            domain: The domain that was checked.
            verdict: The gate verdict.
            total_claims: Total claims evaluated.
            verified_count: Count of VERIFIED claims.
            plausible_count: Count of PLAUSIBLE claims.
            unverified_count: Count of UNVERIFIED claims.
            contradicted_count: Count of CONTRADICTED claims.
            contradicted_pct: Percentage of contradicted claims.
            unverified_pct: Percentage of unverified claims.

        Returns:
            Summary string.
        """
        verdict_text = {
            GateVerdict.PROCEED: "PROCEED -- data quality sufficient for delivery",
            GateVerdict.WARN: "WARN -- some claims need attention before delivery",
            GateVerdict.BLOCKED: "BLOCKED -- too many contradictions, manual review required",
        }

        return (
            f"Factcheck for {domain}: {verdict_text[verdict]}. "
            f"Evaluated {total_claims} claims: "
            f"{verified_count} verified, {plausible_count} plausible, "
            f"{unverified_count} unverified ({unverified_pct:.1f}%), "
            f"{contradicted_count} contradicted ({contradicted_pct:.1f}%)."
        )


def compute_verdict(contradicted_pct: float, unverified_pct: float) -> GateVerdict:
    """Compute the gate verdict based on contradiction and unverified percentages.

    Threshold logic:
    - BLOCKED: >15% CONTRADICTED
    - WARN: 5-15% CONTRADICTED or 15-30% UNVERIFIED
    - PROCEED: <5% CONTRADICTED and <15% UNVERIFIED

    Args:
        contradicted_pct: Percentage of contradicted claims (0-100).
        unverified_pct: Percentage of unverified claims (0-100).

    Returns:
        GateVerdict.
    """
    if contradicted_pct > 15.0:
        return GateVerdict.BLOCKED
    if contradicted_pct >= 5.0 or unverified_pct >= 15.0:
        return GateVerdict.WARN
    return GateVerdict.PROCEED
