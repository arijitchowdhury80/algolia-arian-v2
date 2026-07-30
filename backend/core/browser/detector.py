"""Bot-block detection — identifies Cloudflare, WAF, CAPTCHA challenge pages.

Used by all tiers to distinguish "I got a page" from "I got a challenge page."
Without this, a Cloudflare challenge page would be silently treated as
real content, corrupting downstream module output.
"""

from __future__ import annotations

import re

import structlog

logger = structlog.get_logger(__name__)

# --- Cloudflare-specific signals ---
_CLOUDFLARE_PATTERNS = [
    "checking your browser",
    "just a moment",
    "cf-challenge",
    "cf-browser-verification",
    "cloudflare ray id",
    "attention required! | cloudflare",
    "enable javascript and cookies to continue",
    "performing browser check",
    "ddos protection by cloudflare",
]

# --- Generic WAF / bot-block signals ---
_WAF_PATTERNS = [
    "access denied",
    "403 forbidden",
    "verify you are human",
    "verify you are not a robot",
    "captcha",
    "recaptcha",
    "hcaptcha",
    "please enable javascript",
    "bot detection",
    "automated access",
    "pardon our interruption",
    "please verify you are a human",
    "we need to verify",
    "security check",
    "blocked by",
    "request blocked",
]

# --- Login wall signals (LinkedIn, etc.) ---
_LOGIN_WALL_PATTERNS = [
    "sign in to continue",
    "log in to continue",
    "join now to see",
    "sign up to view",
    "authwall",
]

# Compiled pattern for efficiency (case-insensitive)
_ALL_PATTERNS = _CLOUDFLARE_PATTERNS + _WAF_PATTERNS + _LOGIN_WALL_PATTERNS
_BLOCK_RE = re.compile("|".join(re.escape(p) for p in _ALL_PATTERNS), re.IGNORECASE)


def detect_bot_block(text: str, status_code: int = 200) -> bool:
    """Check if response content is a bot-block page rather than real content.

    Args:
        text: Extracted text content (HTML stripped or raw).
        status_code: HTTP status code.

    Returns:
        True if the page appears to be a bot challenge, WAF block,
        CAPTCHA, or login wall rather than real content.
    """
    # Obvious HTTP-level blocks
    if status_code in (403, 429, 503):
        # 503 with short content is almost always a Cloudflare challenge
        if status_code == 503 and len(text) < 5000:
            return True
        # 403 could be legitimate (auth required) — check content
        if status_code == 403:
            return True

    # Empty or very short responses
    if len(text.strip()) < 100:
        return False  # Too little to detect — let min_content_length handle it

    # Pattern matching on content
    text_lower = text[:5000].lower()  # Only scan first 5KB for efficiency
    if _BLOCK_RE.search(text_lower):
        logger.info(
            "Bot block detected in page content",
            content_preview=text_lower[:200],
        )
        return True

    return False


def detect_content_quality(text: str, min_length: int = 200) -> bool:
    """Check if page content looks like real, substantive content.

    Catches cases where we got a 200 OK but the page is essentially
    empty (JS app that didn't render) or a soft block.

    Args:
        text: Extracted text content.
        min_length: Minimum length for real content.

    Returns:
        True if content passes quality checks.
    """
    stripped = text.strip()

    if len(stripped) < min_length:
        return False

    # JS-app shells: lots of script/noscript tags but no actual text
    # After HTML stripping, these show up as very short or repetitive
    words = stripped.split()
    if len(words) < 20:
        return False

    return True
