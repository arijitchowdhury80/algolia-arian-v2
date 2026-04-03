"""Intel Company parser — deterministic JSON parsing + citation extraction.

Parses Perplexity JSON responses into CompanyProfileOutput. Extracts inline
citations [label](url) as field-level Source records. NO LLM involved.

Data flow:
    raw Perplexity text → extract_citations() → strip_citations() → json.loads() → Pydantic validate
"""

from __future__ import annotations

import json
import re
from typing import Any

import structlog

from prism_platform.modules.intel_company.schemas import CompanyProfileOutput

logger = structlog.get_logger(__name__)

# Matches Perplexity inline citations: [label](url)
CITATION_RE = re.compile(r'\s*\[([\w.\-]+)\]\((https?://[^\)]+)\)')

# Matches Perplexity numbered citations: [1], [2][4], etc.
NUMBERED_CITATION_RE = re.compile(r'\[(\d+)\]')


def extract_citations(raw_text: str) -> list[dict[str, str]]:
    """Extract all inline citations from raw Perplexity response.

    Perplexity annotates facts with [label](url) inline. This function
    extracts every citation as a {source_label, source_url} dict.

    Args:
        raw_text: Raw Perplexity response text (may contain JSON + citations).

    Returns:
        List of dicts with 'source_label' and 'source_url' keys.
    """
    citations: list[dict[str, str]] = []
    for match in CITATION_RE.finditer(raw_text):
        citations.append({
            "source_label": match.group(1),
            "source_url": match.group(2),
        })
    return citations


def strip_citations(raw_text: str) -> str:
    """Remove inline citations from text so JSON parses cleanly.

    Args:
        raw_text: Text with [label](url) annotations.

    Returns:
        Clean text with citations removed.
    """
    return CITATION_RE.sub("", raw_text)


def _clean_numbered_citations(data: Any) -> None:
    """Recursively strip [N] numbered citations from all string values in a dict/list.

    Perplexity sometimes uses [1], [2][4] style citations instead of [label](url).
    These leak into field values like ticker="SHOP[1][2]". This function cleans
    them in-place from all string values, recursively through nested structures.

    Args:
        data: Dict or list to clean in-place.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str):
                cleaned = NUMBERED_CITATION_RE.sub("", value).strip()
                # Also strip trailing parenthetical noise like "(ContextLogic; changing post-sale)"
                # but only if it looks like citation noise, not legitimate content
                if key in ("ticker", "domain") and "(" in cleaned:
                    cleaned = cleaned.split("(")[0].strip()
                data[key] = cleaned
            elif isinstance(value, (dict, list)):
                _clean_numbered_citations(value)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, str):
                data[i] = NUMBERED_CITATION_RE.sub("", item).strip()
            elif isinstance(item, (dict, list)):
                _clean_numbered_citations(item)


def parse_perplexity_json(
    raw_text: str,
) -> tuple[CompanyProfileOutput, list[dict[str, str]]]:
    """Parse Perplexity JSON response into validated output + field-level sources.

    Steps:
        1. Extract all [label](url) citations from raw text
        2. Strip citations so JSON is parseable
        3. json.loads() the cleaned text
        4. Pydantic model_validate() for type safety

    Args:
        raw_text: Raw Perplexity response (JSON with inline citations).

    Returns:
        Tuple of (CompanyProfileOutput, list of source dicts).

    Raises:
        json.JSONDecodeError: If the response is not valid JSON after stripping.
        pydantic.ValidationError: If the JSON doesn't match the schema.
    """
    logger.info("[Parser] parsing Perplexity JSON response", raw_length=len(raw_text))

    # Step 1: Extract citations before stripping
    citations = extract_citations(raw_text)
    logger.info("[Parser] citations extracted", citation_count=len(citations))

    # Step 2: Strip citations from JSON string
    cleaned = strip_citations(raw_text)

    # Step 3: Extract JSON object — Perplexity may add trailing commentary after the closing }
    json_start = cleaned.find("{")
    if json_start == -1:
        raise json.JSONDecodeError("No JSON object found in response", cleaned, 0)

    # Find the matching closing brace by counting braces
    depth = 0
    json_end = json_start
    for i in range(json_start, len(cleaned)):
        if cleaned[i] == "{":
            depth += 1
        elif cleaned[i] == "}":
            depth -= 1
            if depth == 0:
                json_end = i + 1
                break

    json_str = cleaned[json_start:json_end]

    # Step 4: Parse JSON
    data = json.loads(json_str)

    # Step 5: Clean numbered citations from string values (e.g. "SHOP[1][2]" → "SHOP")
    _clean_numbered_citations(data)

    # Step 6: Validate with Pydantic (extra="ignore" handles _notes, etc.)
    profile = CompanyProfileOutput.model_validate(data)

    logger.info(
        "[Parser] parsing complete",
        domain=profile.domain,
        legal_name=profile.legal_name,
        executive_count=len(profile.executives),
        competitor_count=len(profile.competitors),
        citation_count=len(citations),
    )

    return profile, citations
