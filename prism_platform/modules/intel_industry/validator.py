"""Intel Industry validator -- quality checks on industry intelligence output."""

from __future__ import annotations

import structlog

from prism_platform.core.types import Source, ValidationResult
from prism_platform.modules.intel_industry.schemas import IndustryOutput

logger = structlog.get_logger(__name__)


def validate_output(output: IndustryOutput, sources: list[Source]) -> ValidationResult:
    """Validate an IndustryOutput against quality standards.

    Checks:
        1. domain is not empty
        2. industry is not empty
        3. vertical_benchmarks has at least 1 entry
        4. industry_trends has at least 1 entry
        5. pain_points has at least 1 entry
        6. all pain_points have non-empty algolia_capability
        7. at least 1 source provenance recorded
        8. industry_summary is not empty
        9. all benchmarks have non-empty metric_name, value, source
        10. all trends have non-empty trend_name and description

    Args:
        output: The IndustryOutput to validate.
        sources: The list of Source provenance records.

    Returns:
        ValidationResult with pass/fail and diagnostic details.
    """
    logger.info("[IndustryValidator] validation started")

    errors: list[str] = []
    warnings: list[str] = []
    checks_run = 0
    checks_passed = 0

    try:
        # Check 1: domain is not empty
        checks_run += 1
        if not output.domain.strip():
            errors.append("domain is empty")
        else:
            checks_passed += 1

        # Check 2: industry is not empty
        checks_run += 1
        if not output.industry.strip():
            errors.append("industry is empty")
        else:
            checks_passed += 1

        # Check 3: vertical_benchmarks has at least 1 entry
        checks_run += 1
        if len(output.vertical_benchmarks) < 1:
            errors.append("No vertical benchmarks found -- expected at least 1")
        else:
            checks_passed += 1

        # Check 4: industry_trends has at least 1 entry
        checks_run += 1
        if len(output.industry_trends) < 1:
            errors.append("No industry trends found -- expected at least 1")
        else:
            checks_passed += 1

        # Check 5: pain_points has at least 1 entry
        checks_run += 1
        if len(output.pain_points) < 1:
            errors.append("No pain points found -- expected at least 1")
        else:
            checks_passed += 1

        # Check 6: all pain_points have non-empty algolia_capability
        checks_run += 1
        bad_pain_points = [
            i for i, p in enumerate(output.pain_points) if not p.algolia_capability.strip()
        ]
        if bad_pain_points:
            errors.append(f"Pain points at indices {bad_pain_points} have empty algolia_capability")
        else:
            checks_passed += 1

        # Check 7: at least 1 source provenance recorded
        checks_run += 1
        if len(sources) < 1:
            errors.append("No sources recorded -- provenance chain is broken")
        else:
            checks_passed += 1

        # Check 8: industry_summary is not empty
        checks_run += 1
        if not output.industry_summary.strip():
            warnings.append("industry_summary is empty -- may indicate enrichment failure")
        else:
            checks_passed += 1

        # Check 9: all benchmarks have non-empty metric_name, value, source
        checks_run += 1
        bad_benchmarks = [
            i
            for i, b in enumerate(output.vertical_benchmarks)
            if not b.metric_name.strip() or not b.value.strip() or not b.source.strip()
        ]
        if bad_benchmarks:
            errors.append(
                f"Benchmarks at indices {bad_benchmarks} have empty metric_name, value, or source"
            )
        else:
            checks_passed += 1

        # Check 10: all trends have non-empty trend_name and description
        checks_run += 1
        bad_trends = [
            i
            for i, t in enumerate(output.industry_trends)
            if not t.trend_name.strip() or not t.description.strip()
        ]
        if bad_trends:
            errors.append(f"Trends at indices {bad_trends} have empty trend_name or description")
        else:
            checks_passed += 1

    except Exception as error:
        logger.error(
            "[IndustryValidator] validation failed unexpectedly",
            error=str(error),
        )
        errors.append(f"Validation error: {error}")

    passed = len(errors) == 0

    logger.info(
        "[IndustryValidator] validation completed",
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
