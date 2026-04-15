"""Domain normalization — canonical home in v2.

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
    - www prefix: "www.nike.com" -> "nike.com"
    - Already clean: "shopify.com" -> "shopify.com"
    - Trailing slashes: "apple.com/" -> "apple.com"
    - Mixed case: "DELL.COM" -> "dell.com"

    Args:
        input_str: Any domain-like string.

    Returns:
        Clean lowercase domain, e.g. "dell.com".

    Raises:
        ValueError: If the input cannot be parsed into a recognisable domain.
    """
    if not input_str or not input_str.strip():
        raise ValueError("Domain input is empty")

    raw = input_str.strip().lower()

    # If it has a scheme, parse as URL
    if "://" in raw:
        parsed = urlparse(raw)
        hostname = parsed.hostname or ""
    else:
        # Treat as hostname — urlparse needs a scheme to work correctly
        parsed = urlparse(f"https://{raw}")
        hostname = parsed.hostname or ""

    # Strip www. prefix
    if hostname.startswith("www."):
        hostname = hostname[4:]

    # Strip trailing dot
    hostname = hostname.rstrip(".")

    if not hostname:
        raise ValueError(f"Could not extract a domain from: {input_str!r}")

    # Validate the result looks like a real domain
    if not _DOMAIN_PATTERN.match(hostname):
        raise ValueError(f"Normalised value {hostname!r} does not look like a domain")

    logger.debug("normalize_domain", input=input_str, output=hostname)
    return hostname
