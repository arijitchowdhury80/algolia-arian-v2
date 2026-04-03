"""Intel Traffic validator -- 9 quality checks for traffic intelligence output.

Validation checks:
1. monthly_visits has at least 3 months of data
2. traffic_sources has at least 2 source types
3. engagement is not None
4. top_countries has at least 1 entry
5. organic_keywords has at least 3 entries
6. domain in output matches input
7. all traffic_source share_pct values are 0-100
8. comparative_summary not empty when competitors present
9. at least 1 source provenance recorded
"""

from __future__ import annotations

import structlog

from prism_platform.core.types import Source, ValidationResult
from prism_platform.modules.intel_traffic.schemas import TrafficOutput

logger = structlog.get_logger(__name__)


def validate_output(
    output: TrafficOutput,
    sources: list[Source],
    expected_domain: str | None = None,
) -> ValidationResult:
    """Validate a TrafficOutput against quality standards.

    Runs 9 checks covering data completeness, consistency, and provenance.

    Args:
        output: The TrafficOutput to validate.
        sources: The list of Source provenance records.
        expected_domain: If provided, check that output.domain matches.

    Returns:
        ValidationResult with pass/fail, error/warning counts.
    """
    logger.info("[TrafficValidator] validation started", domain=output.domain)

    errors: list[str] = []
    warnings: list[str] = []
    checks_run = 0
    checks_passed = 0

    try:
        # Check 1: monthly_visits has at least 3 months of data
        checks_run += 1
        visit_count = len(output.monthly_visits)
        if visit_count < 3:
            errors.append(
                f"Only {visit_count} months of visit data -- expected at least 3. "
                "SimilarWeb may have insufficient data for this domain."
            )
        else:
            checks_passed += 1

        # Check 2: traffic_sources has at least 2 source types
        checks_run += 1
        source_count = len(output.traffic_sources)
        if source_count < 2:
            errors.append(
                f"Only {source_count} traffic source types -- expected at least 2. "
                "Traffic source breakdown is incomplete."
            )
        else:
            checks_passed += 1

        # Check 3: engagement is not None
        checks_run += 1
        if output.engagement is None:
            warnings.append(
                "Engagement metrics (bounce rate, pages/visit) are missing. "
                "SimilarWeb may not have engagement data for this domain."
            )
        else:
            checks_passed += 1

        # Check 4: top_countries has at least 1 entry
        checks_run += 1
        if len(output.top_countries) < 1:
            errors.append(
                "No geographic data -- expected at least 1 country. "
                "SimilarWeb geo endpoint may have failed."
            )
        else:
            checks_passed += 1

        # Check 5: organic_keywords has at least 3 entries
        checks_run += 1
        kw_count = len(output.organic_keywords)
        if kw_count < 3:
            warnings.append(
                f"Only {kw_count} organic keywords -- expected at least 3. "
                "Keyword data may be limited for this domain."
            )
        else:
            checks_passed += 1

        # Check 6: domain in output matches input
        checks_run += 1
        if expected_domain and output.domain.lower().strip() != expected_domain.lower().strip():
            errors.append(
                f"domain mismatch: output has '{output.domain}' but expected '{expected_domain}'"
            )
        elif not output.domain.strip():
            errors.append("domain is empty")
        else:
            checks_passed += 1

        # Check 7: all traffic_source share_pct values are 0-100
        checks_run += 1
        invalid_shares = [
            ts for ts in output.traffic_sources if ts.share_pct < 0 or ts.share_pct > 100
        ]
        if invalid_shares:
            bad_vals = [f"{ts.source_type}={ts.share_pct}" for ts in invalid_shares]
            errors.append(f"Traffic source share_pct out of range [0-100]: {', '.join(bad_vals)}")
        else:
            checks_passed += 1

        # Check 8: comparative_summary not empty when competitors present
        checks_run += 1
        if output.competitor_traffic and not output.comparative_summary.strip():
            warnings.append(
                "Competitor traffic data is present but comparative_summary is empty. "
                "Add a narrative comparison for downstream reporting."
            )
        else:
            checks_passed += 1

        # Check 9: at least 1 source provenance recorded
        checks_run += 1
        if len(sources) < 1:
            errors.append("No source provenance recorded -- every data point must have a source")
        else:
            checks_passed += 1

    except Exception as error:
        logger.error(
            "[TrafficValidator] validation failed unexpectedly",
            error=str(error),
        )
        errors.append(f"Validation error: {error}")

    passed = len(errors) == 0

    logger.info(
        "[TrafficValidator] validation completed",
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
