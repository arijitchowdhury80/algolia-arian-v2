"""Intel Queries validator -- 9 quality checks for query generation output.

Validation checks:
1. domain not empty
2. prospect_queries has at least 14 queries
3. all 8 query types are represented
4. each query has non-empty query string
5. each query has non-empty expected_behavior
6. difficulty_distribution counts match actual counts
7. query_count matches len(prospect_queries)
8. types_covered has all 8 types
9. at least 1 source provenance
"""

from __future__ import annotations

import structlog

from prism_platform.core.types import Source, ValidationResult
from prism_platform.modules.intel_queries.schemas import QUERY_TYPES, QueriesOutput

logger = structlog.get_logger(__name__)


def validate_output(
    output: QueriesOutput,
    sources: list[Source],
) -> ValidationResult:
    """Validate a QueriesOutput against quality standards.

    Args:
        output: The QueriesOutput to validate.
        sources: The list of Source provenance records.

    Returns:
        ValidationResult with pass/fail, error/warning counts.
    """
    logger.info("[QueriesValidator] validation started", domain=output.domain)

    errors: list[str] = []
    warnings: list[str] = []
    checks_run = 0
    checks_passed = 0

    try:
        # Check 1: domain not empty
        checks_run += 1
        if not output.domain.strip():
            errors.append("domain is empty -- cannot associate queries with a prospect")
        else:
            checks_passed += 1

        # Check 2: at least 14 prospect queries (allowing some tolerance from 16)
        checks_run += 1
        query_count = len(output.prospect_queries)
        if query_count < 14:
            errors.append(
                f"Only {query_count} prospect queries found -- expected at least 14. "
                "Query generation may have failed or returned incomplete data."
            )
        else:
            checks_passed += 1

        # Check 3: all 8 query types are represented
        checks_run += 1
        actual_types = {q.query_type for q in output.prospect_queries}
        missing_types = set(QUERY_TYPES) - actual_types
        if missing_types:
            errors.append(
                f"Missing query types: {sorted(missing_types)}. "
                "All 8 types must be represented for comprehensive coverage."
            )
        else:
            checks_passed += 1

        # Check 4: each query has non-empty query string
        checks_run += 1
        empty_queries = [i for i, q in enumerate(output.prospect_queries) if not q.query.strip()]
        if empty_queries:
            errors.append(
                f"{len(empty_queries)} queries have empty query strings at indices: {empty_queries}"
            )
        else:
            checks_passed += 1

        # Check 5: each query has non-empty expected_behavior
        checks_run += 1
        empty_behaviors = [
            i for i, q in enumerate(output.prospect_queries) if not q.expected_behavior.strip()
        ]
        if empty_behaviors:
            errors.append(
                f"{len(empty_behaviors)} queries have empty expected_behavior at indices: "
                f"{empty_behaviors}"
            )
        else:
            checks_passed += 1

        # Check 6: difficulty_distribution counts match actual counts
        checks_run += 1
        if output.difficulty_distribution is not None:
            actual_easy = sum(1 for q in output.prospect_queries if q.difficulty == "easy")
            actual_medium = sum(1 for q in output.prospect_queries if q.difficulty == "medium")
            actual_hard = sum(1 for q in output.prospect_queries if q.difficulty == "hard")
            dist = output.difficulty_distribution
            if (
                dist.easy_count != actual_easy
                or dist.medium_count != actual_medium
                or dist.hard_count != actual_hard
            ):
                errors.append(
                    f"difficulty_distribution mismatch: "
                    f"expected easy={actual_easy}/medium={actual_medium}/hard={actual_hard}, "
                    f"got easy={dist.easy_count}/medium={dist.medium_count}/hard={dist.hard_count}"
                )
            else:
                checks_passed += 1
        else:
            warnings.append("difficulty_distribution is None -- counts not verified")

        # Check 7: query_count matches len(prospect_queries)
        checks_run += 1
        if output.query_count != len(output.prospect_queries):
            errors.append(
                f"query_count mismatch: output says {output.query_count} "
                f"but prospect_queries has {len(output.prospect_queries)} items"
            )
        else:
            checks_passed += 1

        # Check 8: types_covered has all 8 types
        checks_run += 1
        if set(output.types_covered) != set(QUERY_TYPES):
            missing = sorted(set(QUERY_TYPES) - set(output.types_covered))
            extra = sorted(set(output.types_covered) - set(QUERY_TYPES))
            msg = "types_covered does not match expected types."
            if missing:
                msg += f" Missing: {missing}."
            if extra:
                msg += f" Extra: {extra}."
            errors.append(msg)
        else:
            checks_passed += 1

        # Check 9: at least 1 source provenance
        checks_run += 1
        if len(sources) < 1:
            errors.append(
                "No source provenance records. "
                "At minimum, the Claude query generation call must be documented."
            )
        else:
            checks_passed += 1

    except Exception as error:
        logger.error(
            "[QueriesValidator] validation failed unexpectedly",
            error=str(error),
        )
        errors.append(f"Validation error: {error}")

    passed = len(errors) == 0

    logger.info(
        "[QueriesValidator] validation completed",
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
