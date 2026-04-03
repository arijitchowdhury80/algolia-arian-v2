"""Synth Sales Plays validator -- quality checks on sales playbook output.

Runs 10 validation checks against the generated playbook to ensure
completeness and quality before marking the module as successful.
"""

from __future__ import annotations

import structlog

from prism_platform.core.types import Source, ValidationResult
from prism_platform.modules.synth_sales_plays.schemas import SalesPlaysOutput

logger = structlog.get_logger(__name__)


def validate_output(output: SalesPlaysOutput, sources: list[Source]) -> ValidationResult:
    """Validate a SalesPlaysOutput against quality standards.

    Checks:
        1. domain is not empty
        2. meddpicc has at least 5 fields populated
        3. spin_questions has at least 8 questions
        4. all 4 SPIN categories represented
        5. objection_handlers has at least 2
        6. talk_tracks has at least 3
        7. power_map has at least 1 member
        8. playbook_summary is not empty
        9. top_3_actions has exactly 3
        10. at least 1 source provenance

    Args:
        output: The SalesPlaysOutput to validate.
        sources: The list of Source provenance records.

    Returns:
        ValidationResult with pass/fail, error/warning counts.
    """
    logger.info("[SalesPlays] validation started")

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

        # Check 2: meddpicc has at least 5 fields populated
        checks_run += 1
        meddpicc_count = len(output.meddpicc)
        if meddpicc_count < 5:
            errors.append(f"meddpicc has {meddpicc_count} fields, need at least 5")
        else:
            checks_passed += 1

        # Check 3: spin_questions has at least 8 questions
        checks_run += 1
        spin_count = len(output.spin_questions)
        if spin_count < 8:
            errors.append(f"spin_questions has {spin_count} questions, need at least 8")
        else:
            checks_passed += 1

        # Check 4: all 4 SPIN categories represented
        checks_run += 1
        spin_categories = {q.category for q in output.spin_questions}
        required_categories = {"situation", "problem", "implication", "need_payoff"}
        missing_categories = required_categories - spin_categories
        if missing_categories:
            errors.append(f"SPIN categories missing: {', '.join(sorted(missing_categories))}")
        else:
            checks_passed += 1

        # Check 5: objection_handlers has at least 2
        checks_run += 1
        objection_count = len(output.objection_handlers)
        if objection_count < 2:
            errors.append(f"objection_handlers has {objection_count}, need at least 2")
        else:
            checks_passed += 1

        # Check 6: talk_tracks has at least 3
        checks_run += 1
        track_count = len(output.talk_tracks)
        if track_count < 3:
            errors.append(f"talk_tracks has {track_count}, need at least 3")
        else:
            checks_passed += 1

        # Check 7: power_map has at least 1 member
        checks_run += 1
        power_count = len(output.power_map)
        if power_count < 1:
            warnings.append("power_map is empty -- no buying committee members mapped")
        else:
            checks_passed += 1

        # Check 8: playbook_summary is not empty
        checks_run += 1
        if not output.playbook_summary or not output.playbook_summary.strip():
            errors.append("playbook_summary is empty")
        else:
            checks_passed += 1

        # Check 9: top_3_actions has exactly 3
        checks_run += 1
        actions_count = len(output.top_3_actions)
        if actions_count != 3:
            errors.append(f"top_3_actions has {actions_count} items, need exactly 3")
        else:
            checks_passed += 1

        # Check 10: at least 1 source provenance
        checks_run += 1
        if len(sources) < 1:
            errors.append("No sources recorded -- provenance chain is broken")
        else:
            checks_passed += 1

    except Exception as error:
        logger.error(
            "[SalesPlays] validation failed unexpectedly",
            error=str(error),
        )
        errors.append(f"Validation error: {error}")

    passed = len(errors) == 0

    logger.info(
        "[SalesPlays] validation completed",
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
