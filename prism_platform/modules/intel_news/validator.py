"""Intel News validator -- quality checks on news intelligence output."""

from __future__ import annotations

import structlog

from prism_platform.core.types import Source, ValidationResult
from prism_platform.modules.intel_news.schemas import NewsOutput

logger = structlog.get_logger(__name__)


def validate_output(output: NewsOutput, sources: list[Source]) -> ValidationResult:
    """Validate a NewsOutput against quality standards.

    Checks:
        1. prospect_articles has at least 1 article
        2. domain matches expected format (non-empty)
        3. all articles have non-empty headline and source
        4. all exec quotes have non-empty quote and executive_name
        5. sell_signal_count matches actual is_sell_signal count
        6. high_value_quote_count matches actual is_high_value count
        7. at least 1 source provenance recorded
        8. news_summary not empty
        9. urgency_signals each have valid urgency_level

    Args:
        output: The NewsOutput to validate.
        sources: The list of Source provenance records.

    Returns:
        ValidationResult with pass/fail and diagnostic details.
    """
    logger.info("[NewsValidator] validation started")

    errors: list[str] = []
    warnings: list[str] = []
    checks_run = 0
    checks_passed = 0

    try:
        # Check 1: at least 1 prospect article
        checks_run += 1
        if len(output.prospect_articles) < 1:
            errors.append("No prospect articles found -- expected at least 1 article")
        else:
            checks_passed += 1

        # Check 2: domain is non-empty
        checks_run += 1
        if not output.domain.strip():
            errors.append("domain is empty")
        else:
            checks_passed += 1

        # Check 3: all articles have non-empty headline and source
        checks_run += 1
        bad_articles = [
            i
            for i, a in enumerate(output.prospect_articles)
            if not a.headline.strip() or not a.source.strip()
        ]
        if bad_articles:
            errors.append(f"Articles at indices {bad_articles} have empty headline or source")
        else:
            checks_passed += 1

        # Check 4: all exec quotes have non-empty quote and executive_name
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

        # Check 5: sell_signal_count matches actual count
        checks_run += 1
        actual_sell_signals = sum(1 for a in output.prospect_articles if a.is_sell_signal)
        if output.sell_signal_count != actual_sell_signals:
            errors.append(
                f"sell_signal_count ({output.sell_signal_count}) does not match "
                f"actual is_sell_signal count ({actual_sell_signals})"
            )
        else:
            checks_passed += 1

        # Check 6: high_value_quote_count matches actual count
        checks_run += 1
        actual_high_value = sum(1 for q in output.prospect_exec_quotes if q.is_high_value)
        if output.high_value_quote_count != actual_high_value:
            errors.append(
                f"high_value_quote_count ({output.high_value_quote_count}) does not match "
                f"actual is_high_value count ({actual_high_value})"
            )
        else:
            checks_passed += 1

        # Check 7: at least 1 source provenance
        checks_run += 1
        if len(sources) < 1:
            errors.append("No sources recorded -- provenance chain is broken")
        else:
            checks_passed += 1

        # Check 8: news_summary not empty
        checks_run += 1
        if not output.news_summary.strip():
            warnings.append("news_summary is empty -- may indicate enrichment failure")
        else:
            checks_passed += 1

        # Check 9: urgency_signals have valid urgency_level
        checks_run += 1
        bad_signals = [
            i
            for i, s in enumerate(output.urgency_signals)
            if s.urgency_level not in ("high", "medium", "low")
        ]
        if bad_signals:
            errors.append(f"Urgency signals at indices {bad_signals} have invalid urgency_level")
        else:
            checks_passed += 1

    except Exception as error:
        logger.error(
            "[NewsValidator] validation failed unexpectedly",
            error=str(error),
        )
        errors.append(f"Validation error: {error}")

    passed = len(errors) == 0

    logger.info(
        "[NewsValidator] validation completed",
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
