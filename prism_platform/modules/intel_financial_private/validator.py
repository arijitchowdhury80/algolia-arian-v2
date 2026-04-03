"""Intel Financial Private validator -- quality checks on private financial output."""

from __future__ import annotations

import structlog

from prism_platform.core.types import Source, ValidationResult
from prism_platform.modules.intel_financial_private.schemas import FinancialPrivateOutput

logger = structlog.get_logger(__name__)


def validate_output(
    output: FinancialPrivateOutput,
    sources: list[Source],
) -> ValidationResult:
    """Validate a FinancialPrivateOutput against quality standards.

    Checks:
        1. If skipped: skip_reason is set, return passed=True.
        2. revenue_waterfall is not None.
        3. revenue_waterfall.estimates has at least 2 sources.
        4. Each estimate has non-empty source_name and methodology.
        5. best_estimate within range_low to range_high (or all None).
        6. domain matches expected (checked by caller).
        7. At least 1 source provenance record.
        8. evidence_tier is never NO_SOURCE for any estimate.

    Args:
        output: The FinancialPrivateOutput to validate.
        sources: The list of Source provenance records.

    Returns:
        ValidationResult with pass/fail and diagnostic details.
    """
    logger.info("[FinancialPrivate] validation started")

    errors: list[str] = []
    warnings: list[str] = []
    checks_run = 0
    checks_passed = 0

    try:
        # Check 1: If skipped, only validate skip_reason
        checks_run += 1
        if output.skipped:
            if output.skip_reason:
                checks_passed += 1
                logger.info(
                    "[FinancialPrivate] skipped module, skip_reason present",
                    skip_reason=output.skip_reason,
                )
                return ValidationResult(
                    passed=True,
                    checks_run=checks_run,
                    checks_passed=checks_passed,
                    errors=[],
                    warnings=[],
                )
            errors.append("skipped=True but skip_reason is empty")
            return ValidationResult(
                passed=False,
                checks_run=checks_run,
                checks_passed=checks_passed,
                errors=errors,
                warnings=warnings,
            )
        checks_passed += 1  # Not skipped, continue with full validation

        # Check 2: revenue_waterfall is not None
        checks_run += 1
        if output.revenue_waterfall is None:
            errors.append("revenue_waterfall is None for a non-skipped result")
        else:
            checks_passed += 1

            # Check 3: at least 2 estimate sources
            checks_run += 1
            estimate_count = len(output.revenue_waterfall.estimates)
            if estimate_count < 2:
                errors.append(
                    f"Only {estimate_count} revenue estimates "
                    "-- expected at least 2 for triangulation"
                )
            else:
                checks_passed += 1

            # Check 4: each estimate has source_name and methodology
            checks_run += 1
            empty_fields = []
            for idx, est in enumerate(output.revenue_waterfall.estimates):
                if not est.source_name.strip():
                    empty_fields.append(f"estimate[{idx}].source_name is empty")
                if not est.methodology.strip():
                    empty_fields.append(f"estimate[{idx}].methodology is empty")
            if empty_fields:
                errors.extend(empty_fields)
            else:
                checks_passed += 1

            # Check 5: best_estimate within range
            checks_run += 1
            wf = output.revenue_waterfall
            range_all_set = (
                wf.best_estimate is not None
                and wf.range_low is not None
                and wf.range_high is not None
            )
            if range_all_set:
                if not (wf.range_low <= wf.best_estimate <= wf.range_high):
                    errors.append(
                        f"best_estimate ({wf.best_estimate}) outside range "
                        f"[{wf.range_low}, {wf.range_high}]"
                    )
                else:
                    checks_passed += 1
            elif wf.best_estimate is None and wf.range_low is None and wf.range_high is None:
                # All None is acceptable
                checks_passed += 1
            else:
                warnings.append(
                    "Partial range data: best_estimate, range_low, "
                    "range_high should all be set or all None"
                )
                checks_passed += 1  # Warning, not error

            # Check 8: evidence_tier never NO_SOURCE
            checks_run += 1
            no_source_estimates = [
                est.source_name
                for est in output.revenue_waterfall.estimates
                if est.evidence_tier == "NO_SOURCE"
            ]
            if no_source_estimates:
                errors.append(f"evidence_tier is NO_SOURCE for estimates: {no_source_estimates}")
            else:
                checks_passed += 1

        # Check 6: domain is not empty
        checks_run += 1
        if not output.domain.strip():
            errors.append("domain is empty")
        else:
            checks_passed += 1

        # Check 7: at least 1 source provenance
        checks_run += 1
        if len(sources) < 1:
            errors.append("No sources recorded -- provenance chain is broken")
        else:
            checks_passed += 1

    except Exception as error:
        logger.error(
            "[FinancialPrivate] validation failed unexpectedly",
            error=str(error),
        )
        errors.append(f"Validation error: {error}")

    passed = len(errors) == 0

    logger.info(
        "[FinancialPrivate] validation completed",
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
