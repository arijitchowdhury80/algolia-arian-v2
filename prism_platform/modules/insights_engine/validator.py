"""Insights Engine validator -- quality checks for vertical benchmark output.

Validation checks:
1. At least 3 metrics produced
2. sample_size >= 1 for all metrics
3. vertical is non-empty
4. audit_ids_included is non-empty
5. summary is non-empty
6. No company names or domains in metric values (anonymization check)
7. total_audits_in_vertical >= 1
8. is_first_in_vertical is consistent with total_audits_in_vertical
"""

from __future__ import annotations

import json
import re

import structlog

from prism_platform.core.types import ValidationResult
from prism_platform.modules.insights_engine.schemas import InsightsOutput

logger = structlog.get_logger(__name__)

# Common domain patterns to detect in metric values
DOMAIN_PATTERN = re.compile(r"\b[a-zA-Z0-9-]+\.(com|org|net|io|co|ai)\b", re.IGNORECASE)


def validate_output(
    output: InsightsOutput,
    known_domains: list[str] | None = None,
) -> ValidationResult:
    """Validate an InsightsOutput against quality standards.

    Args:
        output: The InsightsOutput to validate.
        known_domains: Optional list of known domains to check for in metric values.

    Returns:
        ValidationResult with pass/fail and diagnostic details.
    """
    logger.info(
        "[InsightsValidator] validation started",
        domain=output.domain,
        vertical=output.vertical,
    )

    errors: list[str] = []
    warnings: list[str] = []
    checks_run = 0
    checks_passed = 0

    try:
        # Check 1: At least 3 metrics produced
        checks_run += 1
        if len(output.metrics) < 3:
            errors.append(f"Only {len(output.metrics)} metrics produced -- expected at least 3")
        else:
            checks_passed += 1

        # Check 2: sample_size >= 1 for all metrics
        checks_run += 1
        bad_samples = [m.metric_name for m in output.metrics if m.sample_size < 1]
        if bad_samples:
            errors.append(f"Metrics with sample_size < 1: {', '.join(bad_samples)}")
        else:
            checks_passed += 1

        # Check 3: vertical is non-empty
        checks_run += 1
        if not output.vertical.strip():
            errors.append("vertical is empty -- cannot benchmark without vertical classification")
        else:
            checks_passed += 1

        # Check 4: audit_ids_included is non-empty
        checks_run += 1
        if not output.audit_ids_included:
            errors.append("audit_ids_included is empty -- no audits were included")
        else:
            checks_passed += 1

        # Check 5: summary is non-empty
        checks_run += 1
        if not output.summary.strip():
            errors.append("summary is empty -- must provide vertical insights summary")
        else:
            checks_passed += 1

        # Check 6: No company names or domains in metric values (anonymization)
        checks_run += 1
        anonymization_ok = True
        domains_to_check = known_domains or []
        for metric in output.metrics:
            metric_str = json.dumps(metric.metric_value, default=str).lower()

            # Check for known domains
            for d in domains_to_check:
                if d.lower() in metric_str:
                    warnings.append(f"Metric '{metric.metric_name}' may contain domain '{d}'")
                    anonymization_ok = False

            # Check for domain-like patterns
            if DOMAIN_PATTERN.search(metric_str):
                matches = DOMAIN_PATTERN.findall(metric_str)
                # Filter out known safe patterns
                suspicious = [m for m in matches if m[0] not in ("example",)]
                if suspicious:
                    warnings.append(
                        f"Metric '{metric.metric_name}' may contain domain-like strings"
                    )
                    anonymization_ok = False

        if anonymization_ok:
            checks_passed += 1

        # Check 7: total_audits_in_vertical >= 1
        checks_run += 1
        if output.total_audits_in_vertical < 1:
            errors.append(
                f"total_audits_in_vertical is {output.total_audits_in_vertical} -- must be >= 1"
            )
        else:
            checks_passed += 1

        # Check 8: is_first_in_vertical consistency
        checks_run += 1
        if output.is_first_in_vertical and output.total_audits_in_vertical > 1:
            errors.append(
                "is_first_in_vertical is True but total_audits_in_vertical > 1 -- inconsistent"
            )
        elif not output.is_first_in_vertical and output.total_audits_in_vertical == 1:
            warnings.append(
                "is_first_in_vertical is False but "
                "total_audits_in_vertical is 1 -- may be inconsistent"
            )
        else:
            checks_passed += 1

    except Exception as error:
        logger.error(
            "[InsightsValidator] validation failed unexpectedly",
            error=str(error),
        )
        errors.append(f"Validation error: {error}")

    passed = len(errors) == 0

    logger.info(
        "[InsightsValidator] validation completed",
        domain=output.domain,
        vertical=output.vertical,
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
