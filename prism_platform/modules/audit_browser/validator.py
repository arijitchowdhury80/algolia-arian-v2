"""Audit Browser validator -- quality checks for browser test output.

Validation checks (9 total):
1. At least 10 queries executed
2. At least 1 competitor tested
3. All 10 dimensions scored
4. Screenshots captured (at least 1)
5. search_bar_found is True
6. total_queries_executed > 0
7. No more than 50% queries failed/timed out
8. detected_search_provider is not None (warning only)
9. response_time_ms average < 5000ms (warning only)
"""

from __future__ import annotations

import structlog

from prism_platform.core.types import ValidationResult
from prism_platform.modules.audit_browser.schemas import SEARCH_DIMENSIONS, BrowserOutput

logger = structlog.get_logger(__name__)


def validate_output(output: BrowserOutput) -> ValidationResult:
    """Validate a BrowserOutput against quality standards.

    Args:
        output: The BrowserOutput to validate.

    Returns:
        ValidationResult with pass/fail and diagnostic details.
    """
    logger.info("[BrowserValidator] validation started", domain=output.domain)

    errors: list[str] = []
    warnings: list[str] = []
    checks_run = 0
    checks_passed = 0

    try:
        # Check 1: At least 10 queries executed on prospect
        checks_run += 1
        prospect_count = len(output.prospect_query_results)
        if prospect_count < 10:
            errors.append(
                f"Only {prospect_count} prospect queries executed -- expected at least 10"
            )
        else:
            checks_passed += 1

        # Check 2: At least 1 competitor tested
        checks_run += 1
        comp_count = len(output.competitor_results)
        if comp_count < 1:
            errors.append("No competitors tested -- expected at least 1 competitor")
        else:
            checks_passed += 1

        # Check 3: All 10 dimensions scored
        checks_run += 1
        scored_dimensions = {ds.dimension for ds in output.dimension_scores}
        missing_dimensions = set(SEARCH_DIMENSIONS) - scored_dimensions
        if missing_dimensions:
            errors.append(f"Missing dimension scores: {', '.join(sorted(missing_dimensions))}")
        else:
            checks_passed += 1

        # Check 4: At least 1 screenshot captured
        checks_run += 1
        if output.total_screenshots < 1:
            errors.append("No screenshots captured -- expected at least 1")
        else:
            checks_passed += 1

        # Check 5: search_bar_found is True
        checks_run += 1
        if not output.search_bar_found:
            errors.append(
                "Search bar not found on the prospect's site -- "
                "browser test could not execute queries"
            )
        else:
            checks_passed += 1

        # Check 6: total_queries_executed > 0
        checks_run += 1
        if output.total_queries_executed <= 0:
            errors.append("No queries were executed -- total_queries_executed is 0")
        else:
            checks_passed += 1

        # Check 7: No more than 50% queries failed/timed out
        checks_run += 1
        if output.prospect_query_results:
            failed_queries = sum(
                1
                for qr in output.prospect_query_results
                if qr.has_zero_result_page and qr.result_count == 0 and qr.response_time_ms == 0
            )
            fail_ratio = failed_queries / len(output.prospect_query_results)
            if fail_ratio > 0.5:
                errors.append(
                    f"{failed_queries}/{len(output.prospect_query_results)} queries "
                    f"failed or timed out ({fail_ratio:.0%}) -- exceeds 50% threshold"
                )
            else:
                checks_passed += 1
        else:
            checks_passed += 1  # No queries to fail

        # Check 8: detected_search_provider (warning only)
        checks_run += 1
        if output.detected_search_provider is None:
            warnings.append(
                "No search provider detected via network interception -- "
                "may be server-side or custom implementation"
            )
        else:
            checks_passed += 1

        # Check 9: Average response time < 5000ms (warning only)
        checks_run += 1
        if output.prospect_query_results:
            times = [
                qr.response_time_ms
                for qr in output.prospect_query_results
                if qr.response_time_ms > 0
            ]
            if times:
                avg_time = sum(times) / len(times)
                if avg_time > 5000:
                    warnings.append(
                        f"Average response time is {avg_time:.0f}ms -- "
                        f"exceeds 5000ms threshold, indicating very slow search"
                    )
                else:
                    checks_passed += 1
            else:
                checks_passed += 1  # No timed queries
        else:
            checks_passed += 1  # No queries

    except Exception as error:
        logger.error(
            "[BrowserValidator] validation failed unexpectedly",
            error=str(error),
        )
        errors.append(f"Validation error: {error}")

    passed = len(errors) == 0

    logger.info(
        "[BrowserValidator] validation completed",
        domain=output.domain,
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
