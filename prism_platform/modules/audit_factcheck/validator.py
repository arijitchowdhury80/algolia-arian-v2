"""Audit Factcheck validator -- quality checks on factcheck output."""

from __future__ import annotations

import structlog

from prism_platform.core.types import ValidationResult
from prism_platform.modules.audit_factcheck.enricher import compute_verdict
from prism_platform.modules.audit_factcheck.schemas import (
    FactcheckOutput,
    GateVerdict,
    VerificationCategory,
)

logger = structlog.get_logger(__name__)


def validate_output(output: FactcheckOutput) -> ValidationResult:
    """Validate a FactcheckOutput against quality standards.

    Checks:
        1. verdict is a valid GateVerdict
        2. total_claims > 0
        3. All 8 categories have results
        4. contradicted_pct and unverified_pct are consistent with counts
        5. verdict matches the threshold logic (PROCEED/WARN/BLOCKED)
        6. corrections list is non-empty if contradicted_count > 0
        7. summary is non-empty
        8. Each CategoryResult claim counts are consistent

    Args:
        output: The FactcheckOutput to validate.

    Returns:
        ValidationResult with pass/fail, error/warning counts.
    """
    logger.info("[Factcheck] validation started")

    errors: list[str] = []
    warnings: list[str] = []
    checks_run = 0
    checks_passed = 0

    try:
        # Check 1: verdict is a valid GateVerdict
        checks_run += 1
        if output.verdict not in (GateVerdict.PROCEED, GateVerdict.WARN, GateVerdict.BLOCKED):
            errors.append(f"Invalid verdict: {output.verdict}")
        else:
            checks_passed += 1

        # Check 2: total_claims > 0
        checks_run += 1
        if output.total_claims <= 0:
            errors.append("total_claims is zero or negative -- no claims were evaluated")
        else:
            checks_passed += 1

        # Check 3: All 8 categories have results
        checks_run += 1
        result_categories = {cr.category for cr in output.category_results}
        all_categories = set(VerificationCategory)
        missing = all_categories - result_categories
        if missing:
            errors.append(f"Missing category results: {', '.join(m.value for m in missing)}")
        else:
            checks_passed += 1

        # Check 4: contradicted_pct and unverified_pct are consistent with counts
        checks_run += 1
        if output.total_claims > 0:
            expected_contradicted_pct = round(
                output.contradicted_count / output.total_claims * 100.0, 2
            )
            expected_unverified_pct = round(
                output.unverified_count / output.total_claims * 100.0, 2
            )
            pct_ok = (
                abs(output.contradicted_pct - expected_contradicted_pct) < 0.1
                and abs(output.unverified_pct - expected_unverified_pct) < 0.1
            )
            if not pct_ok:
                warnings.append(
                    f"Percentage inconsistency: contradicted_pct={output.contradicted_pct} "
                    f"(expected {expected_contradicted_pct}), "
                    f"unverified_pct={output.unverified_pct} "
                    f"(expected {expected_unverified_pct})"
                )
            else:
                checks_passed += 1
        else:
            checks_passed += 1  # Can't verify percentages with zero claims

        # Check 5: verdict matches the threshold logic
        checks_run += 1
        expected_verdict = compute_verdict(output.contradicted_pct, output.unverified_pct)
        if output.verdict != expected_verdict:
            errors.append(
                f"Verdict mismatch: got {output.verdict.value}, "
                f"expected {expected_verdict.value} based on "
                f"contradicted_pct={output.contradicted_pct}, "
                f"unverified_pct={output.unverified_pct}"
            )
        else:
            checks_passed += 1

        # Check 6: corrections list is non-empty if contradicted_count > 0
        checks_run += 1
        if output.contradicted_count > 0 and len(output.corrections) == 0:
            warnings.append("contradicted_count > 0 but no corrections generated")
        else:
            checks_passed += 1

        # Check 7: summary is non-empty
        checks_run += 1
        if not output.summary or not output.summary.strip():
            errors.append("summary is empty")
        else:
            checks_passed += 1

        # Check 8: Each CategoryResult claim counts are consistent
        checks_run += 1
        inconsistent_categories: list[str] = []
        for cr in output.category_results:
            expected_total = cr.verified + cr.plausible + cr.unverified + cr.contradicted
            if cr.claims_count != expected_total:
                inconsistent_categories.append(
                    f"{cr.category.value}: claims_count={cr.claims_count} but sum={expected_total}"
                )
            if cr.claims_count != len(cr.claims):
                inconsistent_categories.append(
                    f"{cr.category.value}: claims_count={cr.claims_count} "
                    f"but len(claims)={len(cr.claims)}"
                )
        if inconsistent_categories:
            errors.append(
                f"Inconsistent CategoryResult counts: {'; '.join(inconsistent_categories)}"
            )
        else:
            checks_passed += 1

    except Exception as error:
        logger.error(
            "[Factcheck] validation failed unexpectedly",
            error=str(error),
        )
        errors.append(f"Validation error: {error}")

    passed = len(errors) == 0

    logger.info(
        "[Factcheck] validation completed",
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
