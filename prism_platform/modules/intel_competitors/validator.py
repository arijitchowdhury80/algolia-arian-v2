"""Intel Competitors validator -- quality checks on competitive intelligence output."""

from __future__ import annotations

import structlog

from prism_platform.core.types import Source, ValidationResult
from prism_platform.modules.intel_competitors.schemas import CompetitorsOutput

logger = structlog.get_logger(__name__)


def validate_output(output: CompetitorsOutput, sources: list[Source]) -> ValidationResult:
    """Validate a CompetitorsOutput against quality standards.

    Checks:
        1. domain is not empty
        2. at least 1 comparison type populated (tech, traffic, financial, or hiring)
        3. competitive_position is not "unknown" (warning, not error)
        4. competitive_scenario is not None (warning)
        5. competitive_summary is not empty
        6. top_competitive_angles has at least 1 entry
        7. at least 1 source provenance
        8. all comparison entries have non-empty company_name
        9. golden_angle_competitors is a subset of tech_comparison company names

    Args:
        output: The CompetitorsOutput to validate.
        sources: The list of Source provenance records.

    Returns:
        ValidationResult with pass/fail, error/warning counts.
    """
    logger.info("[Competitors] validation started")

    errors: list[str] = []
    warnings: list[str] = []
    checks_run = 0
    checks_passed = 0

    try:
        # Check 1: domain not empty
        checks_run += 1
        if not output.domain or not output.domain.strip():
            errors.append("domain is empty")
        else:
            checks_passed += 1

        # Check 2: at least 1 comparison type populated
        checks_run += 1
        has_tech = len(output.tech_comparisons) > 0
        has_traffic = len(output.traffic_comparisons) > 0
        has_financial = len(output.financial_comparisons) > 0
        has_hiring = len(output.hiring_comparisons) > 0
        if not (has_tech or has_traffic or has_financial or has_hiring):
            errors.append(
                "No comparison data populated -- need at least tech, traffic, financial, or hiring"
            )
        else:
            checks_passed += 1

        # Check 3: competitive_position is not "unknown" (warning)
        checks_run += 1
        if output.competitive_position == "unknown":
            warnings.append(
                "competitive_position is 'unknown' -- insufficient data for positioning"
            )
        else:
            checks_passed += 1

        # Check 4: competitive_scenario is not None (warning)
        checks_run += 1
        if output.competitive_scenario is None:
            warnings.append("competitive_scenario is None -- no scenario could be determined")
        else:
            checks_passed += 1

        # Check 5: competitive_summary not empty
        checks_run += 1
        if not output.competitive_summary or not output.competitive_summary.strip():
            errors.append("competitive_summary is empty")
        else:
            checks_passed += 1

        # Check 6: top_competitive_angles has at least 1 entry
        checks_run += 1
        if len(output.top_competitive_angles) < 1:
            errors.append("top_competitive_angles is empty -- need at least 1 angle")
        else:
            checks_passed += 1

        # Check 7: at least 1 source provenance
        checks_run += 1
        if len(sources) < 1:
            errors.append("No sources recorded -- provenance chain is broken")
        else:
            checks_passed += 1

        # Check 8: all comparison entries have non-empty company_name
        checks_run += 1
        empty_names: list[str] = []
        for tc in output.tech_comparisons:
            if not tc.company_name or not tc.company_name.strip():
                empty_names.append(f"tech:{tc.domain}")
        for tc in output.traffic_comparisons:
            if not tc.company_name or not tc.company_name.strip():
                empty_names.append(f"traffic:{tc.domain}")
        for fc in output.financial_comparisons:
            if not fc.company_name or not fc.company_name.strip():
                empty_names.append(f"financial:{fc.domain}")
        for hc in output.hiring_comparisons:
            if not hc.company_name or not hc.company_name.strip():
                empty_names.append(f"hiring:{hc.domain}")
        if empty_names:
            errors.append(f"Comparison entries with empty company_name: {', '.join(empty_names)}")
        else:
            checks_passed += 1

        # Check 9: golden_angle_competitors is a subset of tech_comparison company names
        checks_run += 1
        tech_company_names = {tc.company_name for tc in output.tech_comparisons}
        invalid_golden = [
            name for name in output.golden_angle_competitors if name not in tech_company_names
        ]
        if invalid_golden:
            errors.append(
                f"golden_angle_competitors contains names not in tech_comparisons: "
                f"{', '.join(invalid_golden)}"
            )
        else:
            checks_passed += 1

    except Exception as error:
        logger.error(
            "[Competitors] validation failed unexpectedly",
            error=str(error),
        )
        errors.append(f"Validation error: {error}")

    passed = len(errors) == 0

    logger.info(
        "[Competitors] validation completed",
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
