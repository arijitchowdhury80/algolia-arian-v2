"""Content-based screenshot quality gate for the search-audit browser phase.

See docs/plans/2026-07-02-cassandra-airtight-pipeline-goal.md §3.1b / §3.1c for the
two shipped bugs this module exists to prevent from recurring:

- §3.1b: a size-only gate (>50KB) passed all-black and promo-modal-covered PNGs.
  This gate inspects pixel content (variance, darkness, dimensions) instead of size.
- §3.1c: shots captured before search suggestions rendered produced FALSE "no
  suggestions" findings and a wrong score. This gate distinguishes a genuinely
  confirmed-empty result (waited, retried) from an unconfirmed pre-render capture,
  and refuses to let a finding be written from the latter.

STANDALONE — not wired into the capture pipeline yet. Integration is gated on
Arijit (see docs/plans/2026-07-02-SAFE-AUTONOMOUS-TRACK.md).
"""

from __future__ import annotations

import io
import re
import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

try:
    from PIL import Image

    _PILLOW_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised via monkeypatch in tests
    _PILLOW_AVAILABLE = False


DEFAULT_OVERLAY_MARKERS: tuple[str, ...] = (
    "cookie-banner",
    "cookie-consent",
    "newsletter-modal",
    "promo-modal",
    "promo-dialog",
    'id="onetrust',
    "klaviyo-form",
    "age-gate",
)

_IMAGE_HARD_FAIL_REASONS = frozenset(
    {
        "image:too_small",
        "image:all_black",
        "image:flat_frame",
        "image:degenerate_dimensions",
        "image:decode_error",
    }
)

_DIALOG_ARIA_MODAL_RE = re.compile(
    r'role=["\']dialog["\'][^>]*aria-modal=["\']true["\']'
    r'|aria-modal=["\']true["\'][^>]*role=["\']dialog["\']',
)
_VALUE_ATTR_RE = re.compile(r'value=(["\'])(.*?)\1', re.IGNORECASE | re.DOTALL)

_THUMBNAIL_MAX_SIDE = 256
_MIN_DIMENSION_PX = 200


class ShotVerdict(Enum):
    """Outcome of gating a single screenshot."""

    USABLE = "usable"
    UNUSABLE = "unusable"
    UNCONFIRMED_EMPTY = "unconfirmed_empty"


@dataclass(frozen=True)
class ShotReport:
    """Verdict + provenance for one gated screenshot."""

    verdict: ShotVerdict
    reasons: tuple[str, ...]
    checks_run: tuple[str, ...]


def check_image(
    png_bytes: bytes,
    *,
    min_bytes: int = 10_000,
    variance_threshold: float = 25.0,
    dark_fraction_threshold: float = 0.985,
) -> tuple[list[str], list[str]]:
    """Content-inspect a PNG for the failure modes that a size-only gate misses.

    Returns (failed_reasons, checks_run). If Pillow is unavailable, all image
    checks are skipped and checks_run reports that explicitly — callers should
    still run check_dom.
    """
    if not _PILLOW_AVAILABLE:
        return [], ["image:pillow_unavailable"]

    failed: list[str] = []
    checks_run: list[str] = []

    checks_run.append("image:size")
    if len(png_bytes) < min_bytes:
        failed.append("image:too_small")

    checks_run.append("image:decode")
    try:
        img = Image.open(io.BytesIO(png_bytes))
        img.load()
    except Exception:
        failed.append("image:decode_error")
        return failed, checks_run

    checks_run.append("image:dimensions")
    width, height = img.size
    if width < _MIN_DIMENSION_PX or height < _MIN_DIMENSION_PX:
        failed.append("image:degenerate_dimensions")

    thumb = img.convert("L")
    thumb.thumbnail((_THUMBNAIL_MAX_SIDE, _THUMBNAIL_MAX_SIDE))
    pixels = list(thumb.getdata())

    checks_run.append("image:dark_fraction")
    if pixels:
        dark_fraction = sum(1 for p in pixels if p < 16) / len(pixels)
        if dark_fraction > dark_fraction_threshold:
            failed.append("image:all_black")

    checks_run.append("image:variance")
    stddev = statistics.pstdev(pixels) if len(pixels) > 1 else 0.0
    if stddev < variance_threshold:
        failed.append("image:flat_frame")

    return failed, checks_run


def check_dom(
    dom_html: str,
    *,
    query: str | None = None,
    result_selectors_present: bool | None = None,
    overlay_markers: Sequence[str] = DEFAULT_OVERLAY_MARKERS,
) -> tuple[list[str], list[str]]:
    """Inspect captured DOM context for interstitials and render-timing evidence.

    Returns (failed_reasons, checks_run).
    """
    failed: list[str] = []
    checks_run: list[str] = []
    html_lower = dom_html.lower()

    checks_run.append("dom:overlay")
    overlay_hit = any(marker.lower() in html_lower for marker in overlay_markers)
    if not overlay_hit and _DIALOG_ARIA_MODAL_RE.search(html_lower):
        overlay_hit = True
    if overlay_hit:
        failed.append("dom:overlay_present")

    if query is not None:
        checks_run.append("dom:query_in_input")
        query_lower = query.lower()
        value_matches = _VALUE_ATTR_RE.findall(dom_html)
        found = any(query_lower in value.lower() for _, value in value_matches)
        if not found:
            failed.append("dom:query_not_in_input")

    if result_selectors_present is not None:
        checks_run.append("dom:results_present")
        if result_selectors_present is False:
            failed.append("dom:results_not_confirmed")

    return failed, checks_run


def gate_screenshot(
    png_bytes: bytes,
    dom_html: str = "",
    *,
    query: str | None = None,
    result_selectors_present: bool | None = None,
    retry_count: int = 0,
    min_retries_before_empty: int = 1,
) -> ShotReport:
    """Gate a screenshot by content, resolving the render-timing trap explicitly.

    A screenshot with a clean image and confirmed-absent results is only trusted
    as genuine evidence ("dom:confirmed_zero_results") once retry_count has met
    min_retries_before_empty. Before that, it's UNCONFIRMED_EMPTY — the caller
    must retry capture and MUST NOT write a finding from it (§3.1c).
    """
    img_failed, img_checks = check_image(png_bytes)
    dom_failed, dom_checks = check_dom(
        dom_html, query=query, result_selectors_present=result_selectors_present
    )
    checks_run = tuple(img_checks + dom_checks)

    has_image_hard_fail = any(r in _IMAGE_HARD_FAIL_REASONS for r in img_failed)
    has_overlay = "dom:overlay_present" in dom_failed
    has_query_mismatch = "dom:query_not_in_input" in dom_failed

    if has_image_hard_fail or has_overlay or has_query_mismatch:
        return ShotReport(ShotVerdict.UNUSABLE, tuple(img_failed + dom_failed), checks_run)

    results_not_confirmed = "dom:results_not_confirmed" in dom_failed
    if query is not None and result_selectors_present is False and results_not_confirmed:
        if retry_count < min_retries_before_empty:
            return ShotReport(ShotVerdict.UNCONFIRMED_EMPTY, tuple(dom_failed), checks_run)
        return ShotReport(ShotVerdict.USABLE, ("dom:confirmed_zero_results",), checks_run)

    if img_failed or dom_failed:
        return ShotReport(ShotVerdict.UNUSABLE, tuple(img_failed + dom_failed), checks_run)

    return ShotReport(ShotVerdict.USABLE, (), checks_run)
