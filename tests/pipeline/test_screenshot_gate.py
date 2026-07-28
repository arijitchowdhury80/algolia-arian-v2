"""Tests for the content-based screenshot quality gate.

See prism_platform/pipeline/screenshot_gate.py and
docs/plans/2026-07-02-cassandra-airtight-pipeline-goal.md §3.1b/§3.1c for design intent.

Two shipped bugs drive this module:
- black / promo-modal PNGs passed a size-only gate (>50KB) → useless screenshots shipped.
- shots captured before search suggestions rendered produced FALSE "no suggestions" findings.
This gate must catch both classes by inspecting pixel content and DOM context, not file size.
"""

from __future__ import annotations

import io

import pytest
from PIL import Image, ImageDraw

from prism_platform.pipeline.screenshot_gate import (
    DEFAULT_OVERLAY_MARKERS,
    ShotReport,
    ShotVerdict,
    check_dom,
    check_image,
    gate_screenshot,
)

# ---------------------------------------------------------------------------
# Image fixtures
# ---------------------------------------------------------------------------


def _png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def solid_black_png() -> bytes:
    return _png_bytes(Image.new("RGB", (400, 300), color=(0, 0, 0)))


def solid_white_png() -> bytes:
    return _png_bytes(Image.new("RGB", (400, 300), color=(255, 255, 255)))


def noise_png() -> bytes:
    import random

    rng = random.Random(42)
    img = Image.new("RGB", (400, 300))
    pixels = [
        (rng.randrange(256), rng.randrange(256), rng.randrange(256)) for _ in range(400 * 300)
    ]
    img.putdata(pixels)
    return _png_bytes(img)


def tiny_png() -> bytes:
    return _png_bytes(Image.new("RGB", (50, 50), color=(120, 40, 200)))


def healthy_gradient_png() -> bytes:
    """A realistic-ish screenshot: gradient background + drawn text + varied pixels."""
    img = Image.new("RGB", (800, 600))
    pixels = []
    for y in range(600):
        for x in range(800):
            pixels.append((x % 256, y % 256, (x + y) % 256))
    img.putdata(pixels)
    draw = ImageDraw.Draw(img)
    for i in range(20):
        draw.rectangle([20 + i * 5, 20, 60 + i * 5, 80], fill=(255, 255, 255))
    draw.text((30, 30), "search results for: shoes", fill=(0, 0, 0))
    return _png_bytes(img)


GARBAGE_BYTES = b"not a real png file, just garbage bytes" * 50


# ---------------------------------------------------------------------------
# check_image
# ---------------------------------------------------------------------------


class TestCheckImage:
    def test_solid_black_frame_fails_all_black(self) -> None:
        failed, checks_run = check_image(solid_black_png())
        assert "image:all_black" in failed
        assert "image:dark_fraction" in checks_run

    def test_solid_white_frame_fails_flat(self) -> None:
        failed, _ = check_image(solid_white_png())
        assert "image:flat_frame" in failed
        assert "image:all_black" not in failed

    def test_noise_image_passes_clean(self) -> None:
        failed, checks_run = check_image(noise_png())
        assert failed == []
        assert "image:variance" in checks_run
        assert "image:dark_fraction" in checks_run

    def test_healthy_gradient_with_text_passes_clean(self) -> None:
        failed, _ = check_image(healthy_gradient_png())
        assert failed == []

    def test_too_small_file_fails(self) -> None:
        tiny_bytes = tiny_png()
        failed, checks_run = check_image(tiny_bytes, min_bytes=10_000_000)
        assert "image:too_small" in failed
        assert "image:size" in checks_run

    def test_degenerate_dimensions_fails(self) -> None:
        failed, checks_run = check_image(tiny_png(), min_bytes=1)
        assert "image:degenerate_dimensions" in failed
        assert "image:dimensions" in checks_run

    def test_garbage_bytes_fail_gracefully_as_decode_error(self) -> None:
        failed, checks_run = check_image(GARBAGE_BYTES)
        assert "image:decode_error" in failed
        assert "image:decode" in checks_run
        # decode failure short-circuits — no pixel-stat checks attempted after it.
        assert "image:variance" not in checks_run

    def test_truncated_valid_png_fails_gracefully(self) -> None:
        real = noise_png()
        truncated = real[: len(real) // 2]
        failed, _ = check_image(truncated)
        assert "image:decode_error" in failed

    def test_custom_variance_threshold_is_honored(self) -> None:
        # noise image has high variance; an absurdly high threshold should flag it flat.
        failed, _ = check_image(noise_png(), variance_threshold=1_000.0)
        assert "image:flat_frame" in failed

    def test_custom_dark_fraction_threshold_is_honored(self) -> None:
        # near-white-but-not-quite frame should not trip dark_fraction at default threshold,
        # but a threshold of 0.0 should trip on any dark pixel presence.
        failed, _ = check_image(solid_white_png(), dark_fraction_threshold=0.0)
        assert "image:all_black" not in failed  # white image has zero dark pixels regardless

    def test_downsamples_large_image_before_stats(self) -> None:
        # A large healthy image should still evaluate quickly and cleanly —
        # this is a smoke test that thumbnailing doesn't break correctness.
        failed, _ = check_image(healthy_gradient_png())
        assert failed == []


class TestCheckImagePillowUnavailable:
    def test_pillow_unavailable_skips_image_checks(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import prism_platform.pipeline.screenshot_gate as gate_module

        monkeypatch.setattr(gate_module, "_PILLOW_AVAILABLE", False)
        failed, checks_run = gate_module.check_image(solid_black_png())
        assert failed == []
        assert checks_run == ["image:pillow_unavailable"]

    def test_pillow_unavailable_dom_checks_still_run(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import prism_platform.pipeline.screenshot_gate as gate_module

        monkeypatch.setattr(gate_module, "_PILLOW_AVAILABLE", False)
        report = gate_module.gate_screenshot(
            solid_black_png(),
            dom_html='<div class="cookie-banner">accept cookies</div>',
        )
        assert report.verdict == ShotVerdict.UNUSABLE
        assert "dom:overlay_present" in report.reasons
        assert "image:pillow_unavailable" in report.checks_run


# ---------------------------------------------------------------------------
# check_dom
# ---------------------------------------------------------------------------


class TestCheckDom:
    @pytest.mark.parametrize("marker", DEFAULT_OVERLAY_MARKERS)
    def test_each_default_overlay_marker_detected(self, marker: str) -> None:
        dom = f'<div class="{marker}">popup content</div>'
        failed, checks_run = check_dom(dom)
        assert "dom:overlay_present" in failed
        assert "dom:overlay" in checks_run

    def test_overlay_marker_detection_is_case_insensitive(self) -> None:
        dom = '<DIV CLASS="COOKIE-BANNER">Accept</DIV>'
        failed, _ = check_dom(dom)
        assert "dom:overlay_present" in failed

    def test_aria_modal_dialog_combo_detected(self) -> None:
        dom = '<div role="dialog" aria-modal="true">Summer Sale!</div>'
        failed, _ = check_dom(dom)
        assert "dom:overlay_present" in failed

    def test_clean_dom_no_overlay(self) -> None:
        dom = '<div class="search-results"><ul><li>Result 1</li></ul></div>'
        failed, _ = check_dom(dom)
        assert "dom:overlay_present" not in failed

    def test_query_present_in_input_value_passes(self) -> None:
        dom = '<input type="search" class="search-box" value="running shoes">'
        failed, checks_run = check_dom(dom, query="running shoes")
        assert "dom:query_not_in_input" not in failed
        assert "dom:query_in_input" in checks_run

    def test_query_missing_from_input_fails(self) -> None:
        dom = '<input type="search" class="search-box" value="">'
        failed, _ = check_dom(dom, query="running shoes")
        assert "dom:query_not_in_input" in failed

    def test_query_check_case_insensitive(self) -> None:
        dom = '<input value="Running Shoes">'
        failed, _ = check_dom(dom, query="running shoes")
        assert "dom:query_not_in_input" not in failed

    def test_query_none_skips_query_check(self) -> None:
        dom = "<div>no input at all</div>"
        failed, checks_run = check_dom(dom, query=None)
        assert "dom:query_not_in_input" not in failed
        assert "dom:query_in_input" not in checks_run

    def test_results_not_confirmed_when_false(self) -> None:
        failed, checks_run = check_dom("<div></div>", result_selectors_present=False)
        assert "dom:results_not_confirmed" in failed
        assert "dom:results_present" in checks_run

    def test_results_confirmed_when_true(self) -> None:
        failed, checks_run = check_dom("<div></div>", result_selectors_present=True)
        assert "dom:results_not_confirmed" not in failed
        assert "dom:results_present" in checks_run

    def test_results_check_skipped_when_none(self) -> None:
        failed, checks_run = check_dom("<div></div>", result_selectors_present=None)
        assert "dom:results_not_confirmed" not in failed
        assert "dom:results_present" not in checks_run

    def test_custom_overlay_markers_honored(self) -> None:
        dom = '<div class="my-custom-popup">hi</div>'
        failed, _ = check_dom(dom, overlay_markers=("my-custom-popup",))
        assert "dom:overlay_present" in failed


# ---------------------------------------------------------------------------
# gate_screenshot — verdict logic
# ---------------------------------------------------------------------------


class TestGateScreenshotVerdicts:
    def test_all_checks_pass_is_usable(self) -> None:
        report = gate_screenshot(
            healthy_gradient_png(),
            '<input value="shoes"><div class="results"><li>shoe 1</li></div>',
            query="shoes",
            result_selectors_present=True,
        )
        assert report.verdict == ShotVerdict.USABLE
        assert report.reasons == ()

    def test_black_image_is_unusable(self) -> None:
        report = gate_screenshot(solid_black_png(), "<div>anything</div>")
        assert report.verdict == ShotVerdict.UNUSABLE
        assert "image:all_black" in report.reasons

    def test_flat_image_is_unusable(self) -> None:
        report = gate_screenshot(solid_white_png(), "<div>anything</div>")
        assert report.verdict == ShotVerdict.UNUSABLE
        assert "image:flat_frame" in report.reasons

    def test_tiny_image_is_unusable_via_degenerate_dimensions(self) -> None:
        report = gate_screenshot(tiny_png(), "<div>anything</div>")
        assert report.verdict == ShotVerdict.UNUSABLE
        assert "image:degenerate_dimensions" in report.reasons

    def test_overlay_present_is_unusable_even_with_healthy_image(self) -> None:
        report = gate_screenshot(
            healthy_gradient_png(),
            '<div class="newsletter-modal">Sign up and save 15%!</div>',
        )
        assert report.verdict == ShotVerdict.UNUSABLE
        assert "dom:overlay_present" in report.reasons

    def test_decode_error_is_unusable(self) -> None:
        report = gate_screenshot(GARBAGE_BYTES, "<div></div>")
        assert report.verdict == ShotVerdict.UNUSABLE
        assert "image:decode_error" in report.reasons

    def test_query_not_in_input_is_unusable_regardless_of_retries(self) -> None:
        report = gate_screenshot(
            healthy_gradient_png(),
            '<input value=""><div class="results"></div>',
            query="running shoes",
            result_selectors_present=False,
            retry_count=5,
        )
        assert report.verdict == ShotVerdict.UNUSABLE
        assert "dom:query_not_in_input" in report.reasons

    def test_empty_results_before_min_retries_is_unconfirmed(self) -> None:
        report = gate_screenshot(
            healthy_gradient_png(),
            '<input value="asdkjhqwe">',
            query="asdkjhqwe",
            result_selectors_present=False,
            retry_count=0,
            min_retries_before_empty=2,
        )
        assert report.verdict == ShotVerdict.UNCONFIRMED_EMPTY
        assert "dom:results_not_confirmed" in report.reasons

    def test_empty_results_at_min_retries_is_confirmed_usable(self) -> None:
        report = gate_screenshot(
            healthy_gradient_png(),
            '<input value="asdkjhqwe">',
            query="asdkjhqwe",
            result_selectors_present=False,
            retry_count=2,
            min_retries_before_empty=2,
        )
        assert report.verdict == ShotVerdict.USABLE
        assert "dom:confirmed_zero_results" in report.reasons

    def test_empty_results_past_min_retries_is_still_confirmed_usable(self) -> None:
        report = gate_screenshot(
            healthy_gradient_png(),
            '<input value="zzz">',
            query="zzz",
            result_selectors_present=False,
            retry_count=99,
            min_retries_before_empty=1,
        )
        assert report.verdict == ShotVerdict.USABLE

    def test_default_min_retries_is_one(self) -> None:
        # retry_count=0 < default min_retries_before_empty=1 → still unconfirmed.
        report = gate_screenshot(
            healthy_gradient_png(),
            '<input value="q">',
            query="q",
            result_selectors_present=False,
        )
        assert report.verdict == ShotVerdict.UNCONFIRMED_EMPTY

    def test_results_present_true_overrides_no_finding_written_path(self) -> None:
        report = gate_screenshot(
            healthy_gradient_png(),
            '<input value="q"><ul class="results"><li>r1</li></ul>',
            query="q",
            result_selectors_present=True,
        )
        assert report.verdict == ShotVerdict.USABLE
        assert "dom:confirmed_zero_results" not in report.reasons

    def test_no_query_no_results_flag_defaults_usable_if_image_and_dom_clean(self) -> None:
        report = gate_screenshot(healthy_gradient_png(), "<div>plain page</div>")
        assert report.verdict == ShotVerdict.USABLE

    def test_checks_run_provenance_includes_both_image_and_dom(self) -> None:
        report = gate_screenshot(
            healthy_gradient_png(),
            '<input value="q">',
            query="q",
            result_selectors_present=True,
        )
        assert any(c.startswith("image:") for c in report.checks_run)
        assert any(c.startswith("dom:") for c in report.checks_run)

    def test_report_is_frozen_dataclass(self) -> None:
        report = gate_screenshot(healthy_gradient_png(), "<div></div>")
        assert isinstance(report, ShotReport)
        with pytest.raises(AttributeError):
            report.verdict = ShotVerdict.UNUSABLE  # type: ignore[misc]

    def test_black_image_wins_over_unconfirmed_empty(self) -> None:
        # Even in the timing-trap shape, a genuinely bad image must never be waved through.
        report = gate_screenshot(
            solid_black_png(),
            '<input value="q">',
            query="q",
            result_selectors_present=False,
            retry_count=0,
        )
        assert report.verdict == ShotVerdict.UNUSABLE
        assert "image:all_black" in report.reasons
