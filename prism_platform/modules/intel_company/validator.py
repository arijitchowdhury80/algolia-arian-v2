"""Intel Company validator -- 8 quality checks per spec Section 2.5.

Validation checks:
1. company_name (legal_name) not empty
2. domain matches input
3. headquarters not empty
4. at least 3 executives found
5. at least 3 competitors found
6. at least 1 executive has linkedin_url
7. business_model at least 50 characters
8. at least 1 news item (warning if missing, not error)
"""

from __future__ import annotations

import structlog

from prism_platform.core.types import Source, ValidationResult
from prism_platform.modules.intel_company.schemas import CompanyProfileOutput

logger = structlog.get_logger(__name__)


def validate_output(
    output: CompanyProfileOutput,
    sources: list[Source],
    expected_domain: str | None = None,
) -> ValidationResult:
    """Validate a CompanyProfileOutput against quality standards.

    Args:
        output: The CompanyProfileOutput to validate.
        sources: The list of Source provenance records.
        expected_domain: If provided, check that output.domain matches.

    Returns:
        ValidationResult with pass/fail, error/warning counts.
    """
    logger.info("[CompanyValidator] validation started", domain=output.domain)

    errors: list[str] = []
    warnings: list[str] = []
    checks_run = 0
    checks_passed = 0

    try:
        # Check 1: legal_name not empty
        checks_run += 1
        if not output.legal_name.strip():
            errors.append("legal_name is empty -- company identity is missing")
        else:
            checks_passed += 1

        # Check 2: domain matches input
        checks_run += 1
        if expected_domain and output.domain.lower().strip() != expected_domain.lower().strip():
            errors.append(
                f"domain mismatch: output has '{output.domain}' but expected '{expected_domain}'"
            )
        elif not output.domain.strip():
            errors.append("domain is empty")
        else:
            checks_passed += 1

        # Check 3: headquarters not empty
        checks_run += 1
        if not output.headquarters.strip():
            errors.append("headquarters is empty -- company location is missing")
        else:
            checks_passed += 1

        # Check 4: at least 3 executives
        checks_run += 1
        exec_count = len(output.executives)
        if exec_count < 3:
            errors.append(
                f"Only {exec_count} executives found -- expected at least 3. "
                "Perplexity may have returned incomplete data."
            )
        else:
            checks_passed += 1

        # Check 5: at least 3 competitors
        checks_run += 1
        comp_count = len(output.competitors)
        if comp_count < 3:
            errors.append(
                f"Only {comp_count} competitors found -- expected at least 3. "
                "Competitive landscape is incomplete."
            )
        else:
            checks_passed += 1

        # Check 6: at least 1 executive has linkedin_url
        checks_run += 1
        has_linkedin = any(e.linkedin_url for e in output.executives)
        if not has_linkedin and output.executives:
            warnings.append(
                "No executives have LinkedIn URLs -- limits downstream social intelligence"
            )
        elif has_linkedin:
            checks_passed += 1
        else:
            # No executives at all -- already caught by check 4
            checks_passed += 0

        # Check 7: business_model at least 50 characters
        checks_run += 1
        bm_len = len(output.business_model.strip())
        if bm_len < 50:
            errors.append(
                f"business_model is only {bm_len} characters -- "
                "expected at least 50 for meaningful context"
            )
        else:
            checks_passed += 1

        # Check 8: at least 1 news item (warning, not error)
        checks_run += 1
        if len(output.recent_news) == 0:
            warnings.append(
                "No recent news items found -- company may have low media presence "
                "or Perplexity returned stale data"
            )
        else:
            checks_passed += 1

    except Exception as error:
        logger.error(
            "[CompanyValidator] validation failed unexpectedly",
            error=str(error),
        )
        errors.append(f"Validation error: {error}")

    passed = len(errors) == 0

    logger.info(
        "[CompanyValidator] validation completed",
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
