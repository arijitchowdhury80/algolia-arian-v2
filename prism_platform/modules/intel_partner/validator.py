"""Intel Partner validator -- quality checks on partner intelligence output."""

from __future__ import annotations

import structlog

from prism_platform.core.types import Source, ValidationResult
from prism_platform.modules.intel_partner.schemas import PartnerOutput

logger = structlog.get_logger(__name__)


def validate_output(output: PartnerOutput, sources: list[Source]) -> ValidationResult:
    """Validate a PartnerOutput against quality standards.

    Checks:
        1. domain not empty
        2. partner_summary not empty
        3. at least 1 source provenance
        4. all partner_overlaps have non-empty partner_name
        5. all co_sell_opportunities have non-empty partner_name
        6. all si_relationships have non-empty si_name
        7. partner_play is not None
        8. crossbeam_available flag is consistent

    Args:
        output: The PartnerOutput to validate.
        sources: The list of Source provenance records.

    Returns:
        ValidationResult with pass/fail and diagnostic details.
    """
    logger.info("[PartnerValidator] validation started")

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

        # Check 2: partner_summary not empty
        checks_run += 1
        if not output.partner_summary.strip():
            warnings.append("partner_summary is empty -- may indicate enrichment failure")
        else:
            checks_passed += 1

        # Check 3: at least 1 source provenance
        checks_run += 1
        if len(sources) < 1:
            errors.append("No sources recorded -- provenance chain is broken")
        else:
            checks_passed += 1

        # Check 4: all partner_overlaps have non-empty partner_name
        checks_run += 1
        bad_overlaps = [
            i for i, o in enumerate(output.partner_overlaps) if not o.partner_name.strip()
        ]
        if bad_overlaps:
            errors.append(f"Partner overlaps at indices {bad_overlaps} have empty partner_name")
        else:
            checks_passed += 1

        # Check 5: all co_sell_opportunities have non-empty partner_name
        checks_run += 1
        bad_cosell = [
            i for i, c in enumerate(output.co_sell_opportunities) if not c.partner_name.strip()
        ]
        if bad_cosell:
            errors.append(f"Co-sell opportunities at indices {bad_cosell} have empty partner_name")
        else:
            checks_passed += 1

        # Check 6: all si_relationships have non-empty si_name
        checks_run += 1
        bad_si = [i for i, s in enumerate(output.si_relationships) if not s.si_name.strip()]
        if bad_si:
            errors.append(f"SI relationships at indices {bad_si} have empty si_name")
        else:
            checks_passed += 1

        # Check 7: partner_play is not None
        checks_run += 1
        if output.partner_play is None:
            warnings.append("partner_play is None -- may indicate enrichment failure")
        else:
            checks_passed += 1

        # Check 8: crossbeam_available flag consistency
        checks_run += 1
        if output.crossbeam_available and not output.partner_overlaps:
            warnings.append(
                "crossbeam_available is True but partner_overlaps is empty -- "
                "Crossbeam data may not have been processed correctly"
            )
        else:
            checks_passed += 1

    except Exception as error:
        logger.error(
            "[PartnerValidator] validation failed unexpectedly",
            error=str(error),
        )
        errors.append(f"Validation error: {error}")

    passed = len(errors) == 0

    logger.info(
        "[PartnerValidator] validation completed",
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
