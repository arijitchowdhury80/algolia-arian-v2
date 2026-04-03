"""Synth Business Case validator -- quality checks on business case output."""

from __future__ import annotations

import structlog

from prism_platform.core.types import Source, ValidationResult
from prism_platform.modules.synth_business_case.schemas import BusinessCaseOutput

logger = structlog.get_logger(__name__)


def validate_output(output: BusinessCaseOutput, sources: list[Source]) -> ValidationResult:
    """Validate a BusinessCaseOutput against quality standards.

    Checks:
        1. domain is not empty
        2. said_vs_found has at least 3 rows
        3. each said_vs_found row has all 4 columns non-empty
        4. value_levers has at least 3 levers
        5. total_conservative_impact is calculated (not None when levers present)
        6. executive_summary is not empty
        7. at least 1 source provenance
        8. timing_signals has at least 1 entry
        9. one_line_pitch is not empty
        10. customer_proofs has at least 1 entry

    Args:
        output: The BusinessCaseOutput to validate.
        sources: The list of Source provenance records.

    Returns:
        ValidationResult with pass/fail, error/warning counts.
    """
    logger.info("[BusinessCase] validation started")

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

        # Check 2: said_vs_found has at least 3 rows
        checks_run += 1
        if len(output.said_vs_found) < 3:
            errors.append(f"said_vs_found has {len(output.said_vs_found)} rows, need at least 3")
        else:
            checks_passed += 1

        # Check 3: each said_vs_found row has all 4 columns non-empty
        checks_run += 1
        empty_cols: list[str] = []
        for i, row in enumerate(output.said_vs_found):
            if not row.exec_said or not row.exec_said.strip():
                empty_cols.append(f"row[{i}].exec_said")
            if not row.we_found or not row.we_found.strip():
                empty_cols.append(f"row[{i}].we_found")
            if not row.competitors_doing or not row.competitors_doing.strip():
                empty_cols.append(f"row[{i}].competitors_doing")
            if not row.your_move or not row.your_move.strip():
                empty_cols.append(f"row[{i}].your_move")
        if empty_cols:
            errors.append(f"said_vs_found has empty columns: {', '.join(empty_cols)}")
        else:
            checks_passed += 1

        # Check 4: value_levers has at least 3 levers
        checks_run += 1
        if len(output.value_levers) < 3:
            errors.append(f"value_levers has {len(output.value_levers)} entries, need at least 3")
        else:
            checks_passed += 1

        # Check 5: total_conservative_impact is calculated when levers present
        checks_run += 1
        has_levers_with_estimates = any(
            lv.conservative_estimate is not None for lv in output.value_levers
        )
        if has_levers_with_estimates and output.total_conservative_impact is None:
            errors.append("total_conservative_impact is None but value levers have estimates")
        elif not has_levers_with_estimates and not output.value_levers:
            # No levers at all -- already flagged in check 4, just pass this check
            warnings.append("total_conservative_impact cannot be calculated without value levers")
        else:
            checks_passed += 1

        # Check 6: executive_summary is not empty
        checks_run += 1
        if not output.executive_summary or not output.executive_summary.strip():
            errors.append("executive_summary is empty")
        else:
            checks_passed += 1

        # Check 7: at least 1 source provenance
        checks_run += 1
        if len(sources) < 1:
            errors.append("No sources recorded -- provenance chain is broken")
        else:
            checks_passed += 1

        # Check 8: timing_signals has at least 1 entry
        checks_run += 1
        if len(output.timing_signals) < 1:
            errors.append("timing_signals is empty -- need at least 1 signal")
        else:
            checks_passed += 1

        # Check 9: one_line_pitch is not empty
        checks_run += 1
        if not output.one_line_pitch or not output.one_line_pitch.strip():
            errors.append("one_line_pitch is empty")
        else:
            checks_passed += 1

        # Check 10: customer_proofs has at least 1 entry
        checks_run += 1
        if len(output.customer_proofs) < 1:
            errors.append("customer_proofs is empty -- need at least 1 proof")
        else:
            checks_passed += 1

    except Exception as error:
        logger.error(
            "[BusinessCase] validation failed unexpectedly",
            error=str(error),
        )
        errors.append(f"Validation error: {error}")

    passed = len(errors) == 0

    logger.info(
        "[BusinessCase] validation completed",
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
