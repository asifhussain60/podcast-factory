#!/usr/bin/env python3
"""Tests for _slide_replicate.py deterministic pieces (slide intelligence).

classify_value (final high/low rubric), verify_svg (exact text/digit/Arabic
survival), and inject_slides svg_overrides (inline SVG figure + raster
fallback + idempotent strip of both figure variants).
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from _slide_replicate import classify_value, verify_svg  # noqa: E402
from inject_slide_deck import inject_slides, strip_slide_figures  # noqa: E402


def _entry(**kw) -> dict:
    base = {
        "page": 3,
        "title": "Seven heavens",
        "text_blocks": ["Seven heavens", "12 mansions", "Air encompasses all"],
        "diagram_type": "hierarchy",
        "arabic_terms": ["nutaqa"],
        "value_class": "high",
        "illegible": False,
    }
    base.update(kw)
    return base


_GOOD_SVG = (
    '<svg viewBox="0 0 760 300" xmlns="http://www.w3.org/2000/svg">'
    '<text x="10" y="30">Seven heavens</text>'
    '<text x="10" y="60"><tspan>12 mansions</tspan></text>'
    '<text x="10" y="90">Air encompasses all</text>'
    '<text x="10" y="120">nutaqa</text>'
    "</svg>"
)


class ClassifyValueTests(unittest.TestCase):
    def test_clean_hierarchy_is_high(self):
        final, reasons = classify_value(_entry())
        self.assertEqual(final, "high", reasons)

    def test_cover_page_is_low(self):
        final, reasons = classify_value(_entry(diagram_type="none"))
        self.assertEqual(final, "low")
        self.assertTrue(any("not replicable" in r for r in reasons))

    def test_illegible_is_low(self):
        final, _ = classify_value(_entry(illegible=True))
        self.assertEqual(final, "low")

    def test_dense_text_is_low(self):
        # Ceiling calibrated to 1,000 chars (real decks run 470-960).
        final, reasons = classify_value(_entry(text_blocks=["x" * 1100]))
        self.assertEqual(final, "low")
        self.assertTrue(any("too dense" in r for r in reasons))

    def test_manual_override_wins(self):
        final, reasons = classify_value(
            _entry(diagram_type="none", manual_value_class="high"))
        self.assertEqual(final, "high")
        self.assertEqual(reasons, ["manual override"])

    def test_llm_advisory_is_overridden(self):
        # LLM says high, rubric says low (type "other") — Python disposes.
        final, _ = classify_value(_entry(diagram_type="other", value_class="high"))
        self.assertEqual(final, "low")


class VerifySvgTests(unittest.TestCase):
    def _write(self, svg: str) -> Path:
        f = Path(tempfile.mkdtemp()) / "page-03.svg"
        f.write_text(svg, encoding="utf-8")
        return f

    def test_exact_survival_passes(self):
        ok, why = verify_svg(self._write(_GOOD_SVG), _entry())
        self.assertTrue(ok, why)

    def test_corrupted_digit_fails(self):
        bad = _GOOD_SVG.replace("12 mansions", "13 mansions")
        ok, why = verify_svg(self._write(bad), _entry())
        self.assertFalse(ok)
        self.assertIn("12", why)

    def test_missing_arabic_term_fails(self):
        bad = _GOOD_SVG.replace("nutaqa", "speakers")
        ok, why = verify_svg(self._write(bad), _entry())
        self.assertFalse(ok)
        self.assertIn("nutaqa", why)

    def test_reworded_block_fails(self):
        bad = _GOOD_SVG.replace("Air encompasses all", "Air covers everything")
        ok, why = verify_svg(self._write(bad), _entry())
        self.assertFalse(ok)

    def test_unparseable_fails(self):
        ok, why = verify_svg(self._write("<svg><text>oops"), _entry())
        self.assertFalse(ok)
        self.assertIn("unparseable", why)


class InjectSvgOverrideTests(unittest.TestCase):
    BOOK = "Intro paragraph.\n\nThe seven heavens emerged from the smoke that day.\n\nClosing paragraph."
    ENTRIES = [{"slide_id": "ch01-s03", "page": 1003, "title": "Seven heavens",
                "anchor_text": "seven heavens emerged from the smoke"}]
    PAGES = {1003: "slide-decks/_pages/ch01/page-03.jpg"}

    def test_svg_override_inlines_svg(self):
        svg = Path(tempfile.mkdtemp()) / "page-03.svg"
        svg.write_text(_GOOD_SVG, encoding="utf-8")
        out = inject_slides(self.BOOK, self.ENTRIES, pages=self.PAGES,
                            svg_overrides={1003: svg})
        self.assertIn("book-slide-svg", out)
        self.assertIn("<svg viewBox=", out)
        self.assertNotIn("page-03.jpg", out)

    def test_no_override_uses_raster(self):
        out = inject_slides(self.BOOK, self.ENTRIES, pages=self.PAGES)
        self.assertIn('img src="slide-decks/_pages/ch01/page-03.jpg"', out)
        self.assertNotIn("book-slide-svg", out)

    def test_invalid_svg_falls_back_to_raster(self):
        bad = Path(tempfile.mkdtemp()) / "page-03.svg"
        bad.write_text("not svg at all", encoding="utf-8")
        out = inject_slides(self.BOOK, self.ENTRIES, pages=self.PAGES,
                            svg_overrides={1003: bad})
        self.assertIn("page-03.jpg", out)
        self.assertNotIn("book-slide-svg", out)

    def test_strip_removes_both_variants(self):
        svg = Path(tempfile.mkdtemp()) / "page-03.svg"
        svg.write_text(_GOOD_SVG, encoding="utf-8")
        with_svg = inject_slides(self.BOOK, self.ENTRIES, pages=self.PAGES,
                                 svg_overrides={1003: svg})
        with_raster = inject_slides(self.BOOK, self.ENTRIES, pages=self.PAGES)
        self.assertEqual(strip_slide_figures(with_svg), strip_slide_figures(with_raster))
        # Re-injecting over an already-injected doc stays idempotent.
        again = inject_slides(with_svg, self.ENTRIES, pages=self.PAGES)
        self.assertEqual(again, with_raster)


if __name__ == "__main__":
    unittest.main()
