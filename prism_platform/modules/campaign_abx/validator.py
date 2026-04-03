"""Campaign ABX validator -- 10 quality checks on campaign output.

Validation checks:
1. domain is not empty
2. emails has exactly 5
3. emails sequence_numbers are 1-5
4. all emails have non-empty subject_line and body
5. linkedin_messages has at least 2
6. loom_script is not None
7. schedule has at least 3 weeks
8. campaign_summary is not empty
9. at least 1 source provenance
10. competitor_messaging is not None
"""

from __future__ import annotations

import structlog

from prism_platform.core.types import Source, ValidationResult
from prism_platform.modules.campaign_abx.schemas import CampaignOutput

logger = structlog.get_logger(__name__)


def validate_output(output: CampaignOutput, sources: list[Source]) -> ValidationResult:
    """Validate a CampaignOutput against quality standards.

    Args:
        output: The CampaignOutput to validate.
        sources: The list of Source provenance records.

    Returns:
        ValidationResult with pass/fail, error/warning counts.
    """
    logger.info("[CampaignABX] validation started", domain=output.domain)

    errors: list[str] = []
    warnings: list[str] = []
    checks_run = 0
    checks_passed = 0

    try:
        # Check 1: domain is not empty
        checks_run += 1
        if not output.domain or not output.domain.strip():
            errors.append("domain is empty")
        else:
            checks_passed += 1

        # Check 2: emails has exactly 5
        checks_run += 1
        email_count = len(output.emails)
        if email_count != 5:
            errors.append(f"Expected exactly 5 emails, got {email_count}")
        else:
            checks_passed += 1

        # Check 3: emails sequence_numbers are 1-5
        checks_run += 1
        if output.emails:
            seq_numbers = sorted(e.sequence_number for e in output.emails)
            expected = [1, 2, 3, 4, 5]
            if seq_numbers != expected:
                errors.append(f"Email sequence_numbers should be {expected}, got {seq_numbers}")
            else:
                checks_passed += 1
        else:
            errors.append("No emails to check sequence numbers")

        # Check 4: all emails have non-empty subject_line and body
        checks_run += 1
        empty_subjects: list[int] = []
        empty_bodies: list[int] = []
        for email in output.emails:
            if not email.subject_line or not email.subject_line.strip():
                empty_subjects.append(email.sequence_number)
            if not email.body or not email.body.strip():
                empty_bodies.append(email.sequence_number)
        if empty_subjects:
            errors.append(f"Emails with empty subject_line: {empty_subjects}")
        elif empty_bodies:
            errors.append(f"Emails with empty body: {empty_bodies}")
        elif output.emails:
            checks_passed += 1
        else:
            # No emails -- already caught by check 2
            pass

        # Check 5: linkedin_messages has at least 2
        checks_run += 1
        linkedin_count = len(output.linkedin_messages)
        if linkedin_count < 2:
            errors.append(f"Expected at least 2 LinkedIn messages, got {linkedin_count}")
        else:
            checks_passed += 1

        # Check 6: loom_script is not None
        checks_run += 1
        if output.loom_script is None:
            errors.append("loom_script is None -- video script was not generated")
        else:
            checks_passed += 1

        # Check 7: schedule has at least 3 weeks
        checks_run += 1
        schedule_count = len(output.schedule)
        if schedule_count < 3:
            errors.append(f"Expected at least 3 weeks in schedule, got {schedule_count}")
        else:
            checks_passed += 1

        # Check 8: campaign_summary is not empty
        checks_run += 1
        if not output.campaign_summary or not output.campaign_summary.strip():
            errors.append("campaign_summary is empty")
        else:
            checks_passed += 1

        # Check 9: at least 1 source provenance
        checks_run += 1
        if len(sources) < 1:
            errors.append("No sources recorded -- provenance chain is broken")
        else:
            checks_passed += 1

        # Check 10: competitor_messaging is not None
        checks_run += 1
        if output.competitor_messaging is None:
            errors.append("competitor_messaging is None -- competitor messaging was not generated")
        else:
            checks_passed += 1

    except Exception as error:
        logger.error(
            "[CampaignABX] validation failed unexpectedly",
            error=str(error),
        )
        errors.append(f"Validation error: {error}")

    passed = len(errors) == 0

    logger.info(
        "[CampaignABX] validation completed",
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
