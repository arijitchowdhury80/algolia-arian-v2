"""Tests for the deterministic bot-wall / anti-bot vendor detector."""

from __future__ import annotations

import dataclasses

import pytest

from server.pipeline.block_detector import (
    BlockVerdict,
    PageEvidence,
    detect_block,
)

# ---------------------------------------------------------------------------
# Hard-block fixtures — one per vendor, page content is unambiguously a
# challenge/interstitial/denial page.
# ---------------------------------------------------------------------------


def test_datadome_captcha_page_is_blocked() -> None:
    evidence = PageEvidence(
        url="https://example.com/",
        status=200,
        headers={"X-DataDome": "abc123"},
        cookies=["datadome"],
        body=(
            "<html><body><script src='https://geo.captcha-delivery.com/captcha/"
            "?initialCid=abc'></script>DataDome protects this site</body></html>"
        ),
    )

    verdict = detect_block(evidence)

    assert verdict.verdict == "BLOCKED"
    assert verdict.vendor == "datadome"
    assert "header:x-datadome" in verdict.signals
    assert "cookie:datadome" in verdict.signals
    assert "body:geo.captcha-delivery.com" in verdict.signals
    assert "body:DataDome" in verdict.signals


def test_akamai_pardon_our_interruption_is_blocked() -> None:
    evidence = PageEvidence(
        url="https://example.com/",
        status=200,
        headers={},
        cookies=["_abck"],
        body="<html><title>Pardon Our Interruption</title><body>...</body></html>",
    )

    verdict = detect_block(evidence)

    assert verdict.verdict == "BLOCKED"
    assert verdict.vendor == "akamai"
    assert "body:Pardon Our Interruption" in verdict.signals
    assert "cookie:_abck" in verdict.signals


def test_akamai_access_denied_with_edgesuite_reference_is_blocked() -> None:
    evidence = PageEvidence(
        url="https://example.com/",
        status=403,
        headers={},
        cookies=[],
        body=(
            "Access Denied\nYou don't have permission to access this resource. "
            "Reference #18.4abc1234.1234567890.deadbeef "
            "https://errors.edgesuite.net/18.4abc1234.1234567890.deadbeef"
        ),
    )

    verdict = detect_block(evidence)

    assert verdict.verdict == "BLOCKED"
    assert verdict.vendor == "akamai"
    assert "body:Access Denied" in verdict.signals


def test_cloudflare_just_a_moment_challenge_is_blocked() -> None:
    evidence = PageEvidence(
        url="https://example.com/",
        status=403,
        headers={"cf-ray": "abcd1234-SEA", "cf-mitigated": "challenge"},
        cookies=[],
        body="<html><title>Just a moment...</title><div id='challenge-running'></div></html>",
    )

    verdict = detect_block(evidence)

    assert verdict.verdict == "BLOCKED"
    assert verdict.vendor == "cloudflare"
    assert "header:cf-mitigated=challenge" in verdict.signals
    assert "body:Just a moment" in verdict.signals
    assert "body:cf-challenge-marker" in verdict.signals


def test_imperva_incapsula_incident_page_is_blocked() -> None:
    evidence = PageEvidence(
        url="https://example.com/",
        status=403,
        headers={"X-Iinfo": "5-123456-0 0NNN RT(1234 0) q(0 0 0 0) r(0 0)"},
        cookies=["incap_ses_123_456789"],
        body="Request unsuccessful. Incapsula incident ID: 123-456789012345",
    )

    verdict = detect_block(evidence)

    assert verdict.verdict == "BLOCKED"
    assert verdict.vendor == "imperva"
    assert "body:Incapsula incident ID" in verdict.signals
    assert "body:Request unsuccessful" in verdict.signals


# ---------------------------------------------------------------------------
# Soft-block fixtures — vendor fingerprint present but the page content is
# healthy (status 200, no challenge/deny markers).
# ---------------------------------------------------------------------------

_CLEAN_ECOMMERCE_BODY = (
    "<html><head><title>Acme Store</title></head><body>"
    "<h1>Welcome to Acme Store</h1><div class='product-grid'>"
    "<div class='product'>Running Shoes - $89.99</div></div></body></html>"
)


def test_datadome_cookie_only_on_healthy_page_is_soft_block() -> None:
    evidence = PageEvidence(
        url="https://example.com/",
        status=200,
        headers={},
        cookies=["datadome"],
        body=_CLEAN_ECOMMERCE_BODY,
    )

    verdict = detect_block(evidence)

    assert verdict.verdict == "SOFT_BLOCK"
    assert verdict.vendor == "datadome"
    assert verdict.signals == ("cookie:datadome",)


def test_datadome_header_only_on_healthy_page_is_soft_block() -> None:
    evidence = PageEvidence(
        url="https://example.com/",
        status=200,
        headers={"x-datadome": "1"},
        cookies=[],
        body=_CLEAN_ECOMMERCE_BODY,
    )

    verdict = detect_block(evidence)

    assert verdict.verdict == "SOFT_BLOCK"
    assert verdict.vendor == "datadome"
    assert verdict.signals == ("header:x-datadome",)


def test_akamai_abck_cookie_only_on_healthy_page_is_soft_block() -> None:
    evidence = PageEvidence(
        url="https://example.com/",
        status=200,
        headers={},
        cookies=["_abck", "bm_sz"],
        body=_CLEAN_ECOMMERCE_BODY,
    )

    verdict = detect_block(evidence)

    assert verdict.verdict == "SOFT_BLOCK"
    assert verdict.vendor == "akamai"
    assert verdict.signals == ("cookie:_abck",)


def test_cloudflare_ray_header_only_on_healthy_page_is_soft_block() -> None:
    evidence = PageEvidence(
        url="https://example.com/",
        status=200,
        headers={"cf-ray": "abcd1234-SEA"},
        cookies=[],
        body=_CLEAN_ECOMMERCE_BODY,
    )

    verdict = detect_block(evidence)

    assert verdict.verdict == "SOFT_BLOCK"
    assert verdict.vendor == "cloudflare"
    assert verdict.signals == ("header:cf-ray",)


def test_imperva_iinfo_header_only_on_healthy_page_is_soft_block() -> None:
    evidence = PageEvidence(
        url="https://example.com/",
        status=200,
        headers={"x-iinfo": "5-123456-0"},
        cookies=[],
        body=_CLEAN_ECOMMERCE_BODY,
    )

    verdict = detect_block(evidence)

    assert verdict.verdict == "SOFT_BLOCK"
    assert verdict.vendor == "imperva"
    assert verdict.signals == ("header:x-iinfo",)


def test_imperva_incap_ses_cookie_only_is_soft_block() -> None:
    evidence = PageEvidence(
        url="https://example.com/",
        status=200,
        headers={},
        cookies=["incap_ses_512_987654321"],
        body=_CLEAN_ECOMMERCE_BODY,
    )

    verdict = detect_block(evidence)

    assert verdict.verdict == "SOFT_BLOCK"
    assert verdict.vendor == "imperva"
    assert verdict.signals == ("cookie:incap_ses/visid_incap",)


def test_imperva_visid_incap_cookie_only_is_soft_block() -> None:
    evidence = PageEvidence(
        url="https://example.com/",
        status=200,
        headers={},
        cookies=["visid_incap_987654"],
        body=_CLEAN_ECOMMERCE_BODY,
    )

    verdict = detect_block(evidence)

    assert verdict.verdict == "SOFT_BLOCK"
    assert verdict.vendor == "imperva"


# ---------------------------------------------------------------------------
# Clean page / no signals.
# ---------------------------------------------------------------------------


def test_clean_ecommerce_page_is_ok() -> None:
    evidence = PageEvidence(
        url="https://example.com/",
        status=200,
        headers={"content-type": "text/html", "server": "nginx"},
        cookies=["session_id", "cart_token"],
        body=_CLEAN_ECOMMERCE_BODY,
    )

    verdict = detect_block(evidence)

    assert verdict == BlockVerdict(verdict="OK", vendor=None, signals=())


def test_empty_evidence_is_ok() -> None:
    evidence = PageEvidence(url="https://example.com/")

    verdict = detect_block(evidence)

    assert verdict == BlockVerdict(verdict="OK", vendor=None, signals=())


def test_status_none_with_clean_body_is_ok() -> None:
    evidence = PageEvidence(
        url="https://example.com/",
        status=None,
        headers={},
        cookies=[],
        body=_CLEAN_ECOMMERCE_BODY,
    )

    verdict = detect_block(evidence)

    assert verdict.verdict == "OK"


# ---------------------------------------------------------------------------
# Case-insensitivity.
# ---------------------------------------------------------------------------


def test_mixed_case_header_name_matches() -> None:
    evidence = PageEvidence(
        url="https://example.com/",
        status=200,
        headers={"X-DATADOME": "1"},
        cookies=[],
        body=_CLEAN_ECOMMERCE_BODY,
    )

    verdict = detect_block(evidence)

    assert verdict.verdict == "SOFT_BLOCK"
    assert verdict.vendor == "datadome"
    assert verdict.signals == ("header:x-datadome",)


def test_mixed_case_cookie_name_matches() -> None:
    evidence = PageEvidence(
        url="https://example.com/",
        status=200,
        headers={},
        cookies=["DataDome"],
        body=_CLEAN_ECOMMERCE_BODY,
    )

    verdict = detect_block(evidence)

    assert verdict.verdict == "SOFT_BLOCK"
    assert verdict.vendor == "datadome"


def test_uppercase_body_marker_matches() -> None:
    evidence = PageEvidence(
        url="https://example.com/",
        status=200,
        headers={},
        cookies=[],
        body="<html><title>PARDON OUR INTERRUPTION</title></html>",
    )

    verdict = detect_block(evidence)

    assert verdict.verdict == "BLOCKED"
    assert verdict.vendor == "akamai"


# ---------------------------------------------------------------------------
# Truncated body.
# ---------------------------------------------------------------------------


def test_truncated_body_with_full_marker_still_matches() -> None:
    evidence = PageEvidence(
        url="https://example.com/",
        status=200,
        headers={},
        cookies=[],
        body="...page truncated before this... Pardon Our Interruption ...cut off here",
    )

    verdict = detect_block(evidence)

    assert verdict.verdict == "BLOCKED"
    assert verdict.vendor == "akamai"


def test_body_truncated_mid_marker_does_not_false_positive() -> None:
    evidence = PageEvidence(
        url="https://example.com/",
        status=200,
        headers={},
        cookies=[],
        body="<html><title>Pardon Our Interr",  # cut mid-marker
    )

    verdict = detect_block(evidence)

    assert verdict.verdict == "OK"


# ---------------------------------------------------------------------------
# Blocking status interplay.
# ---------------------------------------------------------------------------


def test_blocking_status_without_any_fingerprint_is_ok() -> None:
    evidence = PageEvidence(
        url="https://example.com/",
        status=429,
        headers={"retry-after": "30"},
        cookies=[],
        body="<html><body>Too many requests, please slow down.</body></html>",
    )

    verdict = detect_block(evidence)

    assert verdict.verdict == "OK"
    assert verdict.vendor is None


def test_blocking_status_429_with_fingerprint_only_is_blocked() -> None:
    evidence = PageEvidence(
        url="https://example.com/",
        status=429,
        headers={},
        cookies=["_abck"],
        body="<html><body>Too many requests, please slow down.</body></html>",
    )

    verdict = detect_block(evidence)

    assert verdict.verdict == "BLOCKED"
    assert verdict.vendor == "akamai"
    assert "cookie:_abck" in verdict.signals


def test_blocking_status_405_with_fingerprint_is_blocked() -> None:
    evidence = PageEvidence(
        url="https://example.com/",
        status=405,
        headers={"cf-ray": "abcd1234-SEA"},
        cookies=[],
        body="<html><body>Method not allowed.</body></html>",
    )

    verdict = detect_block(evidence)

    assert verdict.verdict == "BLOCKED"
    assert verdict.vendor == "cloudflare"


# ---------------------------------------------------------------------------
# Multi-vendor.
# ---------------------------------------------------------------------------


def test_multiple_vendors_hard_wins_over_soft() -> None:
    evidence = PageEvidence(
        url="https://example.com/",
        status=403,
        headers={"cf-ray": "abcd1234-SEA", "cf-mitigated": "challenge"},
        cookies=["datadome"],
        body="<html><title>Just a moment...</title></html>",
    )

    verdict = detect_block(evidence)

    assert verdict.verdict == "BLOCKED"
    assert verdict.vendor == "cloudflare"
    assert "cookie:datadome" in verdict.signals
    assert "header:cf-mitigated=challenge" in verdict.signals
    assert "body:Just a moment" in verdict.signals


def test_multiple_soft_only_vendors_picks_priority_order() -> None:
    evidence = PageEvidence(
        url="https://example.com/",
        status=200,
        headers={"cf-ray": "abcd1234-SEA"},
        cookies=["_abck"],
        body=_CLEAN_ECOMMERCE_BODY,
    )

    verdict = detect_block(evidence)

    assert verdict.verdict == "SOFT_BLOCK"
    # akamai precedes cloudflare in vendor priority when signal counts tie.
    assert verdict.vendor == "akamai"
    assert "cookie:_abck" in verdict.signals
    assert "header:cf-ray" in verdict.signals


# ---------------------------------------------------------------------------
# Immutability.
# ---------------------------------------------------------------------------


def test_page_evidence_is_frozen() -> None:
    evidence = PageEvidence(url="https://example.com/")

    with pytest.raises(dataclasses.FrozenInstanceError):
        evidence.status = 500  # type: ignore[misc]


def test_block_verdict_is_frozen() -> None:
    verdict = detect_block(PageEvidence(url="https://example.com/"))

    with pytest.raises(dataclasses.FrozenInstanceError):
        verdict.verdict = "BLOCKED"  # type: ignore[misc]
