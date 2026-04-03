"""Intel TechStack validator -- quality checks on tech stack output."""

from __future__ import annotations

import structlog

from prism_platform.core.types import Source, ValidationResult
from prism_platform.modules.intel_techstack.schemas import TechStackOutput

logger = structlog.get_logger(__name__)


def validate_output(output: TechStackOutput, sources: list[Source]) -> ValidationResult:
    """Validate a TechStackOutput against quality standards.

    Checks:
        - search_vendor is not None (warning if missing)
        - at least 3 technologies detected (error if fewer)
        - at least 1 source in the result (error if missing)
        - tech_stack_summary is not empty (error if empty)

    Args:
        output: The TechStackOutput to validate.
        sources: The list of Source provenance records.

    Returns:
        ValidationResult with pass/fail, error/warning counts.
    """
    logger.info("[TechStack] validation started")

    errors: list[str] = []
    warnings: list[str] = []
    checks_run = 0
    checks_passed = 0

    try:
        # Check 1: search_vendor presence
        checks_run += 1
        if output.search_vendor is None:
            warnings.append("No search vendor detected -- site may use a custom or no search")
        else:
            checks_passed += 1

        # Check 2: minimum technology count
        checks_run += 1
        tech_count = len(output.all_technologies)
        if tech_count < 3:
            errors.append(
                f"Only {tech_count} technologies detected -- expected at least 3. "
                "API may have returned partial data."
            )
        else:
            checks_passed += 1

        # Check 3: at least 1 source
        checks_run += 1
        if len(sources) < 1:
            errors.append("No sources recorded -- provenance chain is broken")
        else:
            checks_passed += 1

        # Check 4: summary not empty
        checks_run += 1
        if not output.tech_stack_summary.strip():
            errors.append("tech_stack_summary is empty")
        else:
            checks_passed += 1

        # Check 5: comparative_summary not empty when competitors present
        checks_run += 1
        if output.competitor_tech_stacks and not output.comparative_summary.strip():
            errors.append("comparative_summary is empty but competitor_tech_stacks has entries")
        else:
            checks_passed += 1

        # Check 6: each competitor_tech_stack has at least 1 technology
        checks_run += 1
        empty_competitors = [
            cs.domain for cs in output.competitor_tech_stacks if len(cs.all_technologies) < 1
        ]
        if empty_competitors:
            warnings.append(
                f"Competitors with no technologies detected: {', '.join(empty_competitors)}"
            )
        else:
            checks_passed += 1

        # Check 7: golden_angle_competitors is a subset of competitor names
        checks_run += 1
        competitor_names = {cs.company_name for cs in output.competitor_tech_stacks}
        invalid_golden = [
            name for name in output.golden_angle_competitors if name not in competitor_names
        ]
        if invalid_golden:
            errors.append(
                f"golden_angle_competitors contains names not in competitor_tech_stacks: "
                f"{', '.join(invalid_golden)}"
            )
        else:
            checks_passed += 1

        # Check 8: all competitor domains are valid (contain a dot)
        checks_run += 1
        invalid_domains = [
            cs.domain for cs in output.competitor_tech_stacks if "." not in cs.domain
        ]
        if invalid_domains:
            errors.append(f"Invalid competitor domains (missing dot): {', '.join(invalid_domains)}")
        else:
            checks_passed += 1

    except Exception as error:
        logger.error(
            "[TechStack] validation failed unexpectedly",
            error=str(error),
        )
        errors.append(f"Validation error: {error}")

    passed = len(errors) == 0

    logger.info(
        "[TechStack] validation completed",
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
