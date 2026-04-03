"""Intel Social validator -- quality checks on social intelligence output."""

from __future__ import annotations

import structlog

from prism_platform.core.types import Source, ValidationResult
from prism_platform.modules.intel_social.schemas import SocialOutput

logger = structlog.get_logger(__name__)

# Valid literal values for runtime validation
_VALID_POST_TOPICS = {
    "digital_strategy",
    "technology_investment",
    "customer_experience",
    "search_related",
    "ai_related",
    "hiring",
    "culture",
    "product_launch",
    "competitive",
    "other",
}

_VALID_QUOTE_TOPICS = {
    "digital_strategy",
    "technology_investment",
    "customer_experience",
    "search_related",
    "ai_related",
    "competitive_positioning",
    "growth_commitment",
    "cost_optimization",
    "other",
}

_VALID_RELEVANCE = {"high", "medium", "low"}


def validate_output(output: SocialOutput, sources: list[Source]) -> ValidationResult:
    """Validate a SocialOutput against quality standards.

    Checks:
        1. domain is not empty
        2. prospect_posts or prospect_exec_quotes not both empty
        3. all posts have non-empty content_summary
        4. all exec_quotes have non-empty quote and executive_name
        5. high_relevance_count matches actual high-relevance count
        6. medium_relevance_count matches actual medium-relevance count
        7. at least 1 source provenance recorded
        8. social_summary not empty
        9. topic values are all valid Literal options

    Args:
        output: The SocialOutput to validate.
        sources: The list of Source provenance records.

    Returns:
        ValidationResult with pass/fail and diagnostic details.
    """
    logger.info("[SocialValidator] validation started")

    errors: list[str] = []
    warnings: list[str] = []
    checks_run = 0
    checks_passed = 0

    try:
        # Check 1: domain is not empty
        checks_run += 1
        if not output.domain.strip():
            errors.append("domain is empty")
        else:
            checks_passed += 1

        # Check 2: prospect_posts or prospect_exec_quotes not both empty
        checks_run += 1
        if not output.prospect_posts and not output.prospect_exec_quotes:
            warnings.append(
                "Both prospect_posts and prospect_exec_quotes are empty -- "
                "may indicate collection failure"
            )
        else:
            checks_passed += 1

        # Check 3: all posts have non-empty content_summary
        checks_run += 1
        bad_posts = [
            i for i, p in enumerate(output.prospect_posts) if not p.content_summary.strip()
        ]
        if bad_posts:
            errors.append(f"Posts at indices {bad_posts} have empty content_summary")
        else:
            checks_passed += 1

        # Check 4: all exec_quotes have non-empty quote and executive_name
        checks_run += 1
        bad_quotes = [
            i
            for i, q in enumerate(output.prospect_exec_quotes)
            if not q.quote.strip() or not q.executive_name.strip()
        ]
        if bad_quotes:
            errors.append(f"Exec quotes at indices {bad_quotes} have empty quote or executive_name")
        else:
            checks_passed += 1

        # Check 5: high_relevance_count matches actual count
        checks_run += 1
        actual_high = sum(
            1
            for item in [*output.prospect_posts, *output.prospect_exec_quotes]
            if item.algolia_relevance == "high"
        )
        if output.high_relevance_count != actual_high:
            errors.append(
                f"high_relevance_count ({output.high_relevance_count}) does not match "
                f"actual high-relevance count ({actual_high})"
            )
        else:
            checks_passed += 1

        # Check 6: medium_relevance_count matches actual count
        checks_run += 1
        actual_medium = sum(
            1
            for item in [*output.prospect_posts, *output.prospect_exec_quotes]
            if item.algolia_relevance == "medium"
        )
        if output.medium_relevance_count != actual_medium:
            errors.append(
                f"medium_relevance_count ({output.medium_relevance_count}) does not match "
                f"actual medium-relevance count ({actual_medium})"
            )
        else:
            checks_passed += 1

        # Check 7: at least 1 source provenance recorded
        checks_run += 1
        if len(sources) < 1:
            errors.append("No sources recorded -- provenance chain is broken")
        else:
            checks_passed += 1

        # Check 8: social_summary not empty
        checks_run += 1
        if not output.social_summary.strip():
            warnings.append("social_summary is empty -- may indicate enrichment failure")
        else:
            checks_passed += 1

        # Check 9: topic values are all valid Literal options
        checks_run += 1
        invalid_post_topics = [
            (i, p.topic)
            for i, p in enumerate(output.prospect_posts)
            if p.topic not in _VALID_POST_TOPICS
        ]
        invalid_quote_topics = [
            (i, q.topic)
            for i, q in enumerate(output.prospect_exec_quotes)
            if q.topic not in _VALID_QUOTE_TOPICS
        ]
        if invalid_post_topics or invalid_quote_topics:
            details: list[str] = []
            if invalid_post_topics:
                details.append(f"Invalid post topics: {invalid_post_topics}")
            if invalid_quote_topics:
                details.append(f"Invalid quote topics: {invalid_quote_topics}")
            errors.append(f"Invalid topic values: {'; '.join(details)}")
        else:
            checks_passed += 1

    except Exception as error:
        logger.error(
            "[SocialValidator] validation failed unexpectedly",
            error=str(error),
        )
        errors.append(f"Validation error: {error}")

    passed = len(errors) == 0

    logger.info(
        "[SocialValidator] validation completed",
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
