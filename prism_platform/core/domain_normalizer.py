"""Domain normalization utilities for the PRISM platform.

Ensures consistent domain representation across the system. Prevents
duplicate records caused by variations like "www.jewson.co.uk",
"https://www.jewson.co.uk/", and "jewson.co.uk" all referring to the
same entity.

No external dependencies — uses only the Python standard library.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

import structlog

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

# Regex for a basic domain-like pattern: at least one dot with alphanumeric segments
_DOMAIN_PATTERN = re.compile(
    r"^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)+$"
)


def normalize_domain(input_str: str) -> str:
    """Normalize any domain input to a clean domain string.

    Handles:
    - Full URLs: "https://www.dell.com/en-us" -> "dell.com"
    - With www: "www.dell.com" -> "dell.com"
    - With protocol: "http://dell.com" -> "dell.com"
    - With trailing slash: "dell.com/" -> "dell.com"
    - With port: "dell.com:443" -> "dell.com"
    - Already clean: "dell.com" -> "dell.com"
    - With path: "dell.com/products" -> "dell.com"
    - UK domains: "www.jewson.co.uk" -> "jewson.co.uk"

    Does NOT handle plain company names like "Dell" — that's the LLM's job
    in intel-company. This function only normalizes URL/domain strings.

    Args:
        input_str: Raw domain, URL, or company name string.

    Returns:
        Lowercase stripped domain, or the original string (stripped/lowered)
        if it doesn't look like a domain.
    """
    if not input_str or not input_str.strip():
        return input_str.strip() if input_str else ""

    cleaned = input_str.strip()

    # If the string contains "://", urlparse handles it well.
    # If it doesn't but looks like a domain/path, prepend a scheme so
    # urlparse can extract the netloc properly.
    parse_input = cleaned
    if "://" not in cleaned:
        # Prepend scheme so urlparse treats the first segment as netloc
        parse_input = "https://" + cleaned

    try:
        parsed = urlparse(parse_input)
        hostname = parsed.hostname  # already lowercased, port stripped
    except Exception:
        logger.debug(
            "domain_normalizer.urlparse_failed",
            input=input_str,
        )
        hostname = None

    if hostname:
        domain = hostname
    else:
        # Fallback: just lowercase and strip
        domain = cleaned.lower()

    # Strip "www." prefix
    if domain.startswith("www."):
        domain = domain[4:]

    # If the result doesn't look like a domain (no dots), return as-is
    # so the LLM layer can treat it as a company name.
    if "." not in domain:
        logger.debug(
            "domain_normalizer.not_a_domain",
            input=input_str,
            result=domain,
        )
        return cleaned  # preserve original casing for company names

    logger.debug(
        "domain_normalizer.normalized",
        input=input_str,
        result=domain,
    )
    return domain


def looks_like_domain(input_str: str) -> bool:
    """Check if the input looks like a domain or URL (has a dot and valid TLD pattern).

    Args:
        input_str: Raw string to check.

    Returns:
        True if the string appears to be a domain or URL, False otherwise.
    """
    if not input_str or not input_str.strip():
        return False

    cleaned = input_str.strip().lower()

    # If it has a protocol, it's URL-like
    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        return True

    # Strip www. for the check
    check = cleaned
    if check.startswith("www."):
        check = check[4:]

    # Strip path/query/port for the domain check
    check = check.split("/")[0].split("?")[0].split("#")[0].split(":")[0]

    return bool(_DOMAIN_PATTERN.match(check))


def extract_domain_from_url(url: str) -> str:
    """Extract just the domain from a full URL.

    This is an alias for :func:`normalize_domain` provided for semantic
    clarity at call sites that always receive full URLs.

    Args:
        url: A full URL string.

    Returns:
        The normalized domain portion of the URL.
    """
    return normalize_domain(url)
