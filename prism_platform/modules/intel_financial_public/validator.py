"""Intel Financial Public validator -- 9 quality checks for public company financials.

Validation checks:
1. If skipped=True, validate that skip_reason is set, return passed=True
2. annual_financials has at least 2 years
3. market_data is not None
4. market_data.market_cap > 0
5. at least 1 SEC insight present
6. domain matches input
7. ticker matches input
8. at least 1 source provenance
9. comparative_summary not empty when competitors present
"""

from __future__ import annotations

import structlog

from prism_platform.core.types import Source, ValidationResult
from prism_platform.modules.intel_financial_public.schemas import FinancialPublicOutput

logger = structlog.get_logger(__name__)


def validate_output(
    output: FinancialPublicOutput,
    sources: list[Source],
    expected_domain: str | None = None,
    expected_ticker: str | None = None,
) -> ValidationResult:
    """Validate a FinancialPublicOutput against quality standards.

    Args:
        output: The FinancialPublicOutput to validate.
        sources: The list of Source provenance records.
        expected_domain: If provided, check that output.domain matches.
        expected_ticker: If provided, check that output.ticker matches.

    Returns:
        ValidationResult with pass/fail, error/warning counts.
    """
    logger.info(
        "[FinancialPublicValidator] validation started",
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
                    "[FinancialPublicValidator] module was skipped (valid)",
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

        # Check 2: annual_financials has at least 2 years
        checks_run += 1
        years_count = len(output.annual_financials)
        if years_count < 2:
            errors.append(f"Only {years_count} years of annual financials -- expected at least 2")
        else:
            checks_passed += 1

        # Check 3: market_data is not None
        checks_run += 1
        if output.market_data is None:
            errors.append("market_data is None -- Yahoo Finance may have failed")
        else:
            checks_passed += 1

        # Check 4: market_data.market_cap > 0
        checks_run += 1
        if output.market_data is not None and output.market_data.market_cap is not None:
            if output.market_data.market_cap > 0:
                checks_passed += 1
            else:
                errors.append(f"market_cap is {output.market_data.market_cap} -- expected > 0")
        elif output.market_data is not None:
            warnings.append("market_cap is None within market_data")
            checks_passed += 0  # Soft fail for missing market cap
        else:
            # market_data itself is None -- already caught by check 3
            pass

        # Check 5: at least 1 SEC insight
        checks_run += 1
        if len(output.sec_insights) < 1:
            warnings.append(
                "No SEC insights found -- SEC EDGAR search may have returned no results"
            )
        else:
            checks_passed += 1

        # Check 6: domain matches input
        checks_run += 1
        if expected_domain and output.domain.lower().strip() != expected_domain.lower().strip():
            errors.append(
                f"domain mismatch: output has '{output.domain}' but expected '{expected_domain}'"
            )
        elif not output.domain.strip():
            errors.append("domain is empty")
        else:
            checks_passed += 1

        # Check 7: ticker matches input
        checks_run += 1
        if expected_ticker and output.ticker.upper().strip() != expected_ticker.upper().strip():
            errors.append(
                f"ticker mismatch: output has '{output.ticker}' but expected '{expected_ticker}'"
            )
        elif not output.ticker.strip():
            errors.append("ticker is empty")
        else:
            checks_passed += 1

        # Check 8: at least 1 source provenance
        checks_run += 1
        if len(sources) < 1:
            warnings.append("No source provenance records attached")
        else:
            checks_passed += 1

        # Check 9: comparative_summary not empty when competitors present
        checks_run += 1
        if output.competitor_financials and not output.comparative_summary.strip():
            warnings.append("competitor_financials present but comparative_summary is empty")
        else:
            checks_passed += 1

    except Exception as error:
        logger.error(
            "[FinancialPublicValidator] validation failed unexpectedly",
            error=str(error),
        )
        errors.append(f"Validation error: {error}")

    passed = len(errors) == 0

    logger.info(
        "[FinancialPublicValidator] validation completed",
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
