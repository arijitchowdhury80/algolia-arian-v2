"""Browser infrastructure types — shared across all PRISM modules.

FetchResult is the universal return type for any web fetch operation,
regardless of which tier (httpx, Jina, Playwright, Browserless) produced it.
FetchOptions controls what the caller needs from the fetch.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FetchTier(str, Enum):
    """Which tier actually served the response."""

    HTTPX = "httpx"
    JINA = "jina"
    PLAYWRIGHT = "playwright"
    BROWSERLESS = "browserless"
    SCRAPINGBEE = "scrapingbee"


class FetchResult(BaseModel):
    """Universal result from any web fetch operation.

    Every module that needs web data gets this back — it doesn't
    care which tier produced it.
    """

    model_config = ConfigDict(frozen=True)

    url: str = Field(description="Final URL after redirects")
    text: str = Field(description="Extracted text content (HTML stripped)")
    html: str | None = Field(default=None, description="Raw HTML if available")
    status_code: int = Field(description="HTTP status code (0 if fetch failed entirely)")
    tier_used: FetchTier = Field(description="Which tier actually served this response")
    is_bot_blocked: bool = Field(
        default=False,
        description="True if we detected a bot challenge page instead of real content",
    )
    fetch_duration_ms: int = Field(description="Wall-clock time for this fetch")
    error: str | None = Field(
        default=None,
        description="Error message if fetch failed. None on success.",
    )

    @property
    def success(self) -> bool:
        """True if we got real content (not blocked, not error)."""
        return (
            self.status_code == 200
            and not self.is_bot_blocked
            and self.error is None
            and len(self.text) > 0
        )


class FetchOptions(BaseModel):
    """Controls what the caller needs from the fetch.

    Modules set these flags based on their requirements.
    The BrowserClient uses them to pick the right tier.
    """

    model_config = ConfigDict(frozen=True)

    timeout: float = Field(default=15.0, description="Per-request timeout in seconds")
    render_js: bool = Field(
        default=False,
        description="If True, skip httpx and go straight to JS-capable tier (Jina/Playwright)",
    )
    interactive: bool = Field(
        default=False,
        description="If True, need full browser (Playwright/Browserless). For search audit.",
    )
    screenshot: bool = Field(
        default=False,
        description="Take a screenshot. Requires Tier 2+.",
    )
    max_tier: Literal[1, 2, 3] = Field(
        default=3,
        description="Stop escalating at this tier. 1=httpx+Jina, 2=+Playwright, 3=+commercial",
    )
    min_content_length: int = Field(
        default=200,
        description="Minimum text length to consider a page successfully fetched",
    )
    user_agent: str | None = Field(
        default=None,
        description="Override user agent. None uses tier-appropriate default.",
    )
