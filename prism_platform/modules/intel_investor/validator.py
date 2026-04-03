"""Intel Investor validator -- 10 quality checks for investor intelligence.

Validation checks:
1. If skipped=True, validate that skip_reason is set, return passed=True
2. prospect_quotes has at least 1 quote (warning if empty for public company)
3. said_vs_found has at least 1 mapping (warning if empty)
4. commitment_count matches actual is_commitment count
5. pain_signal_count matches actual pain_signal category count
6. domain not empty
7. at least 1 source provenance
8. investor_summary not empty
9. top_sales_angles has at least 1 entry
10. all quotes have non-empty speaker_name and quote text
"""

from __future__ import annotations

import structlog

from prism_platform.core.types import Source, ValidationResult
from prism_platform.modules.intel_investor.schemas import InvestorOutput

logger = structlog.get_logger(__name__)


def validate_output(
    output: InvestorOutput,
    sources: list[Source],
    expected_domain: str | None = None,
) -> ValidationResult:
    """Validate an InvestorOutput against quality standards.

    Args:
        output: The InvestorOutput to validate.
        sources: The list of Source provenance records.
        expected_domain: If provided, check that output.domain matches.

    Returns:
        ValidationResult with pass/fail, error/warning counts.
    """
    logger.info(
        "[InvestorValidator] validation started",
        domain=output.domain,
        ticker=output.ticker,
        skipped=output.skipped,
    )

    errors: list[str] = []
    warnings: list[str] = []
    checks_run = 0
    checks_passed = 0

    try:
        # Check 1: If skipped, validate skip_reason is set
        checks_run += 1
        if output.skipped:
            if output.skip_reason:
                checks_passed += 1
                logger.info(
                    "[InvestorValidator] module was skipped (valid)",
                    skip_reason=output.skip_reason,
                )
                return ValidationResult(
                    passed=True,
                    checks_run=1,
                    checks_passed=1,
                    errors=[],
                    warnings=[],
                )
            else:
                errors.append("skipped=True but skip_reason is not set")
                return ValidationResult(
                    passed=False,
                    checks_run=1,
                    checks_passed=0,
                    errors=errors,
                    warnings=[],
                )
        else:
            checks_passed += 1

        # Check 2: prospect_quotes has at least 1 quote
        checks_run += 1
        if len(output.prospect_quotes) < 1:
            if output.ticker:
                warnings.append(
                    "No prospect quotes found for a public company -- "
                    "earnings transcripts may not have been available"
                )
            else:
                # Private companies may not have earnings calls
                checks_passed += 1
        else:
            checks_passed += 1

        # Check 3: said_vs_found has at least 1 mapping
        checks_run += 1
        if len(output.said_vs_found) < 1:
            warnings.append(
                "No Said vs Found mappings generated -- "
                "this is the core deliverable and should have at least one"
            )
        else:
            checks_passed += 1

        # Check 4: commitment_count matches actual is_commitment count
        checks_run += 1
        actual_commitments = sum(1 for q in output.prospect_quotes if q.is_commitment)
        if output.commitment_count != actual_commitments:
            errors.append(
                f"commitment_count mismatch: output says {output.commitment_count} "
                f"but actual is_commitment count is {actual_commitments}"
            )
        else:
            checks_passed += 1

        # Check 5: pain_signal_count matches actual pain_signal category count
        checks_run += 1
        actual_pain = sum(1 for q in output.prospect_quotes if q.category == "pain_signal")
        if output.pain_signal_count != actual_pain:
            errors.append(
                f"pain_signal_count mismatch: output says {output.pain_signal_count} "
                f"but actual pain_signal count is {actual_pain}"
            )
        else:
            checks_passed += 1

        # Check 6: domain not empty and matches expected
        checks_run += 1
        if not output.domain.strip():
            errors.append("domain is empty")
        elif expected_domain and output.domain.lower().strip() != expected_domain.lower().strip():
            errors.append(
                f"domain mismatch: output has '{output.domain}' but expected '{expected_domain}'"
            )
        else:
            checks_passed += 1

        # Check 7: at least 1 source provenance
        checks_run += 1
        if len(sources) < 1:
            warnings.append("No source provenance records attached")
        else:
            checks_passed += 1

        # Check 8: investor_summary not empty
        checks_run += 1
        if not output.investor_summary.strip():
            warnings.append("investor_summary is empty")
        else:
            checks_passed += 1

        # Check 9: top_sales_angles has at least 1 entry
        checks_run += 1
        if len(output.top_sales_angles) < 1:
            warnings.append("top_sales_angles is empty -- AE needs at least one angle")
        else:
            checks_passed += 1

        # Check 10: all quotes have non-empty speaker_name and quote text
        checks_run += 1
        bad_quotes = []
        for i, q in enumerate(output.prospect_quotes):
            if not q.speaker_name.strip():
                bad_quotes.append(f"Quote {i}: empty speaker_name")
            if not q.quote.strip():
                bad_quotes.append(f"Quote {i}: empty quote text")
        if bad_quotes:
            errors.append(f"Invalid quotes: {'; '.join(bad_quotes)}")
        else:
            checks_passed += 1

    except Exception as error:
        logger.error(
            "[InvestorValidator] validation failed unexpectedly",
            error=str(error),
        )
        errors.append(f"Validation error: {error}")

    passed = len(errors) == 0

    logger.info(
        "[InvestorValidator] validation completed",
        domain=output.domain,
        ticker=output.ticker,
        passed=passed,
        checks_run=checks_run,
        checks_passed=checks_passed,
        error_count=len(errors),
        warning_count=len(warnings),
    )

    return ValidationResult(
        passed=passed,
        checks_run=checks_run,
        checks_passed=checks_passed,
        errors=errors,
        warnings=warnings,
    )
