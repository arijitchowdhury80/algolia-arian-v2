"""Audit Report validator -- 10 quality checks for the final audit report.

Validation checks:
1. domain not empty
2. dimension_scores has exactly 10 entries
3. all 10 dimensions represented
4. overall_score between 0-10
5. pre_call_brief is not None
6. leave_behind is not None
7. leave_behind.top_3_recommendations has exactly 3 entries
8. audit_summary not empty
9. at least 1 source provenance
10. full_audit_data is not empty
"""

from __future__ import annotations

import structlog

from prism_platform.core.types import Source, ValidationResult
from prism_platform.modules.audit_report.schemas import ALL_DIMENSIONS, AuditReportOutput

logger = structlog.get_logger(__name__)


def validate_output(
    output: AuditReportOutput,
    sources: list[Source],
) -> ValidationResult:
    """Validate an AuditReportOutput against quality standards.

    Args:
        output: The AuditReportOutput to validate.
        sources: The list of Source provenance records.

    Returns:
        ValidationResult with pass/fail, error/warning counts.
    """
    logger.info("[AuditReportValidator] validation started", domain=output.domain)

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

        # Check 2: dimension_scores has exactly 10 entries
        checks_run += 1
        dim_count = len(output.dimension_scores)
        if dim_count != 10:
            errors.append(f"dimension_scores has {dim_count} entries -- expected exactly 10")
        else:
            checks_passed += 1

        # Check 3: all 10 dimensions represented
        checks_run += 1
        scored_dims = {ds.dimension for ds in output.dimension_scores}
        missing_dims = set(ALL_DIMENSIONS) - scored_dims
        if missing_dims:
            errors.append(f"Missing dimensions: {', '.join(sorted(missing_dims))}")
        else:
            checks_passed += 1

        # Check 4: overall_score between 0-10
        checks_run += 1
        if output.overall_score is None:
            errors.append("overall_score is None -- must be a float between 0-10")
        elif not (0 <= output.overall_score <= 10):
            errors.append(f"overall_score is {output.overall_score} -- must be between 0 and 10")
        else:
            checks_passed += 1

        # Check 5: pre_call_brief is not None
        checks_run += 1
        if output.pre_call_brief is None:
            errors.append("pre_call_brief is None -- AE brief is required")
        else:
            checks_passed += 1

        # Check 6: leave_behind is not None
        checks_run += 1
        if output.leave_behind is None:
            errors.append("leave_behind is None -- prospect leave-behind is required")
        else:
            checks_passed += 1

        # Check 7: leave_behind.top_3_recommendations has exactly 3 entries
        checks_run += 1
        if output.leave_behind is not None:
            rec_count = len(output.leave_behind.top_3_recommendations)
            if rec_count != 3:
                errors.append(
                    f"leave_behind.top_3_recommendations has {rec_count} entries -- "
                    "expected exactly 3"
                )
            else:
                checks_passed += 1
        else:
            errors.append("Cannot check top_3_recommendations -- leave_behind is None")

        # Check 8: audit_summary not empty
        checks_run += 1
        if not output.audit_summary.strip():
            errors.append("audit_summary is empty -- executive summary is required")
        else:
            checks_passed += 1

        # Check 9: at least 1 source provenance
        checks_run += 1
        if len(sources) < 1:
            errors.append("No source provenance records -- at least 1 required")
        else:
            checks_passed += 1

        # Check 10: full_audit_data is not empty
        checks_run += 1
        if not output.full_audit_data:
            errors.append("full_audit_data is empty -- must contain assembled module outputs")
        else:
            checks_passed += 1

    except Exception as error:
        logger.error(
            "[AuditReportValidator] validation failed unexpectedly",
            error=str(error),
        )
        errors.append(f"Validation error: {error}")

    passed = len(errors) == 0

    logger.info(
        "[AuditReportValidator] validation completed",
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
