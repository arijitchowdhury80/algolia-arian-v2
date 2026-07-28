"""Deterministic bot-wall / anti-bot vendor detector.

Classifies fetched page evidence into OK / SOFT_BLOCK / BLOCKED before any
downstream screenshot or extracted content is trusted. Detects known
signatures from DataDome, Akamai, Cloudflare, and Imperva/Incapsula in
response headers, cookies, and body markup.

Classification rules:
  - Any hard-block content signal (challenge page, denial page, captcha
    delivery marker) -> BLOCKED, regardless of HTTP status.
  - A blocking HTTP status (403/405/429) combined with any vendor
    fingerprint (even a header/cookie alone) -> BLOCKED.
  - A vendor fingerprint present but the page is otherwise healthy (no hard
    signal, non-blocking status) -> SOFT_BLOCK: the vendor is active on this
    site and a later request may still get walled, but this response wasn't.
  - No signals at all -> OK.
  - When multiple vendors match, BLOCKED wins over SOFT_BLOCK. Ties within a
    verdict are broken by matched-signal count, then by vendor priority
    order (datadome, akamai, cloudflare, imperva).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

Vendor = Literal["datadome", "akamai", "cloudflare", "imperva"]
Verdict = Literal["OK", "BLOCKED", "SOFT_BLOCK"]

_BLOCKING_STATUSES = frozenset({403, 405, 429})

# Rough prevalence order, used only to break ties when two+ vendors match
# with an equal signal count.
_VENDOR_PRIORITY: tuple[Vendor, ...] = ("datadome", "akamai", "cloudflare", "imperva")


@dataclass(frozen=True)
class PageEvidence:
    """Raw evidence gathered about a single fetched page."""

    url: str
    status: int | None = None
    headers: Mapping[str, str] = field(default_factory=dict)
    cookies: Sequence[str] = ()
    body: str = ""


@dataclass(frozen=True)
class BlockVerdict:
    """Classification result for a `PageEvidence`."""

    verdict: Verdict
    vendor: Vendor | None
    signals: tuple[str, ...]


def _lower_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {key.lower(): value for key, value in headers.items()}


def _lower_cookies(cookies: Sequence[str]) -> list[str]:
    return [cookie.lower() for cookie in cookies]


def _detect_datadome(
    headers: Mapping[str, str], cookies: Sequence[str], body: str
) -> tuple[list[str], list[str]]:
    hard: list[str] = []
    soft: list[str] = []
    if "x-datadome" in headers:
        soft.append("header:x-datadome")
    if "datadome" in cookies:
        soft.append("cookie:datadome")
    if "geo.captcha-delivery.com" in body:
        hard.append("body:geo.captcha-delivery.com")
    if "datadome" in body:
        hard.append("body:DataDome")
    return hard, soft


def _detect_akamai(
    headers: Mapping[str, str], cookies: Sequence[str], body: str
) -> tuple[list[str], list[str]]:
    hard: list[str] = []
    soft: list[str] = []
    if "_abck" in cookies:
        soft.append("cookie:_abck")
    if "pardon our interruption" in body:
        hard.append("body:Pardon Our Interruption")
    if "access denied" in body and ("errors.edgesuite.net" in body or "reference #" in body):
        hard.append("body:Access Denied")
    return hard, soft


def _detect_cloudflare(headers: Mapping[str, str], body: str) -> tuple[list[str], list[str]]:
    hard: list[str] = []
    soft: list[str] = []
    if headers.get("cf-mitigated", "").strip().lower() == "challenge":
        hard.append("header:cf-mitigated=challenge")
    if "just a moment" in body:
        hard.append("body:Just a moment")
    if "challenge-running" in body or "cf-challenge" in body:
        hard.append("body:cf-challenge-marker")
    if "cf-ray" in headers:
        soft.append("header:cf-ray")
    return hard, soft


def _detect_imperva(
    headers: Mapping[str, str], cookies: Sequence[str], body: str
) -> tuple[list[str], list[str]]:
    hard: list[str] = []
    soft: list[str] = []
    if "x-iinfo" in headers:
        soft.append("header:x-iinfo")
    if any(cookie.startswith(("incap_ses_", "visid_incap_")) for cookie in cookies):
        soft.append("cookie:incap_ses/visid_incap")
    if "incapsula incident id" in body:
        hard.append("body:Incapsula incident ID")
    if "request unsuccessful" in body:
        hard.append("body:Request unsuccessful")
    return hard, soft


def detect_block(evidence: PageEvidence) -> BlockVerdict:
    """Classify page evidence as OK, SOFT_BLOCK, or BLOCKED.

    Header, cookie, and body matching are all case-insensitive.
    """
    headers = _lower_headers(evidence.headers)
    cookies = _lower_cookies(evidence.cookies)
    body = evidence.body.lower()

    per_vendor: dict[Vendor, tuple[list[str], list[str]]] = {
        "datadome": _detect_datadome(headers, cookies, body),
        "akamai": _detect_akamai(headers, cookies, body),
        "cloudflare": _detect_cloudflare(headers, body),
        "imperva": _detect_imperva(headers, cookies, body),
    }

    is_blocking_status = evidence.status in _BLOCKING_STATUSES

    all_signals: list[str] = []
    blocked_candidates: list[tuple[Vendor, int]] = []
    soft_candidates: list[tuple[Vendor, int]] = []

    for vendor in _VENDOR_PRIORITY:
        hard, soft = per_vendor[vendor]
        all_signals.extend(hard)
        all_signals.extend(soft)

        if hard:
            blocked_candidates.append((vendor, len(hard)))
        elif is_blocking_status and soft:
            blocked_candidates.append((vendor, len(soft)))
        elif soft:
            soft_candidates.append((vendor, len(soft)))

    if blocked_candidates:
        blocked_candidates.sort(key=lambda candidate: -candidate[1])
        return BlockVerdict(
            verdict="BLOCKED", vendor=blocked_candidates[0][0], signals=tuple(all_signals)
        )

    if soft_candidates:
        soft_candidates.sort(key=lambda candidate: -candidate[1])
        return BlockVerdict(
            verdict="SOFT_BLOCK", vendor=soft_candidates[0][0], signals=tuple(all_signals)
        )

    return BlockVerdict(verdict="OK", vendor=None, signals=())
