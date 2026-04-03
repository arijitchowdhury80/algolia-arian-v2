"""Intel Hiring validator -- quality checks on hiring intelligence output."""

from __future__ import annotations

import structlog

from prism_platform.core.types import Source, ValidationResult
from prism_platform.modules.intel_hiring.schemas import HiringOutput

logger = structlog.get_logger(__name__)


def validate_output(output: HiringOutput, sources: list[Source]) -> ValidationResult:
    """Validate a HiringOutput against quality standards.

    Checks:
        1. domain not empty
        2. open_roles or hiring_summary not empty
        3. role_count_by_tier values sum equals len(open_roles) when roles present
        4. hiring_velocity is not None
        5. build_vs_buy is not None
        6. buying_committee is not None
        7. at least 1 source provenance
        8. all open_roles have non-empty title
        9. hiring_summary not empty

    Args:
        output: The HiringOutput to validate.
        sources: The list of Source provenance records.

    Returns:
        ValidationResult with pass/fail and diagnostic details.
    """
    logger.info("[HiringValidator] validation started")

    errors: list[str] = []
    warnings: list[str] = []
    checks_run = 0
    checks_passed = 0

    try:
        # Check 1: domain not empty
        checks_run += 1
        if not output.domain.strip():
            errors.append("domain is empty")
        else:
            checks_passed += 1

        # Check 2: open_roles or hiring_summary not empty
        checks_run += 1
        if not output.open_roles and not output.hiring_summary.strip():
            errors.append(
                "Both open_roles and hiring_summary are empty -- at least one must have content"
            )
        else:
            checks_passed += 1

        # Check 3: role_count_by_tier values sum equals len(open_roles)
        checks_run += 1
        if output.open_roles:
            tier_sum = sum(output.role_count_by_tier.values())
            role_count = len(output.open_roles)
            if tier_sum != role_count:
                errors.append(
                    f"role_count_by_tier sum ({tier_sum}) does not match "
                    f"open_roles count ({role_count})"
                )
            else:
                checks_passed += 1
        else:
            # No roles, check passes vacuously
            checks_passed += 1

        # Check 4: hiring_velocity is not None
        checks_run += 1
        if output.hiring_velocity is None:
            warnings.append("hiring_velocity is None -- may indicate enrichment failure")
        else:
            checks_passed += 1

        # Check 5: build_vs_buy is not None
        checks_run += 1
        if output.build_vs_buy is None:
            warnings.append("build_vs_buy is None -- may indicate enrichment failure")
        else:
            checks_passed += 1

        # Check 6: buying_committee is not None
        checks_run += 1
        if output.buying_committee is None:
            warnings.append("buying_committee is None -- may indicate enrichment failure")
        else:
            checks_passed += 1

        # Check 7: at least 1 source provenance
        checks_run += 1
        if len(sources) < 1:
            errors.append("No sources recorded -- provenance chain is broken")
        else:
            checks_passed += 1

        # Check 8: all open_roles have non-empty title
        checks_run += 1
        bad_roles = [i for i, r in enumerate(output.open_roles) if not r.title.strip()]
        if bad_roles:
            errors.append(f"Open roles at indices {bad_roles} have empty title")
        else:
            checks_passed += 1

        # Check 9: hiring_summary not empty
        checks_run += 1
        if not output.hiring_summary.strip():
            warnings.append("hiring_summary is empty -- may indicate enrichment failure")
        else:
            checks_passed += 1

    except Exception as error:
        logger.error(
            "[HiringValidator] validation failed unexpectedly",
            error=str(error),
        )
        errors.append(f"Validation error: {error}")

    passed = len(errors) == 0

    logger.info(
        "[HiringValidator] validation completed",
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
