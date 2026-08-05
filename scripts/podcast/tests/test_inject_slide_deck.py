#!/usr/bin/env python3
"""Tests for scripts/podcast/inject_slide_deck.py (slide-deck import into the
reading edition).

Contract under test (no real book, no poppler — synthesized fixtures only):
  - anchor_text must match EXACTLY ONCE in the book markdown; zero or multiple
    matches fail loudly with the offending slide_id(s) in the message
    (deliberate hardening vs. _book_illustrate's soft-skip).
  - a manifest page beyond the extracted page count fails naming the slide_id.
  - injection is idempotent: re-running on its own output yields identical md.
  - cover slides (anchor_text: null) are never injected inline.
  - _page_map tolerates pdftoppm's page-number padding variants.
  - build_book_pdf prefers book-slides.md > book-illustrated.md > book.md.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import inject_slide_deck as isd
from _authoring._core import AuthoringError

BOOK_MD = """# The Test Book

## Chapter One

The seeker walks toward the mirage expecting water at its edge.

More prose follows in a second paragraph that says something else.

## Chapter Two

True comportment is the mechanism of self-surrender in every act.

Closing synthesis paragraph unifying the levels of transmission.
"""


def _entry(slide_id: str, page: int, anchor: str | None, title: str = "T") -> dict:
    return {"slide_id": slide_id, "page": page, "title": title, "anchor_text": anchor}


def _pages(n: int, prefix: str = "slide-decks/_pages/book") -> dict[int, str]:
    return {i: f"{prefix}/page-{i:02d}.jpg" for i in range(1, n + 1)}


class InjectSlidesTests(unittest.TestCase):
    def test_happy_path_inserts_after_anchor_paragraph(self) -> None:
        entries = [_entry("ch01-s02", 2, "expecting water at its edge")]
        out = isd.inject_slides(BOOK_MD, entries, pages=_pages(2))
        self.assertIn('<figure class="book-diagram book-slide">', out)
        # Default position="before": figure precedes the anchor paragraph.
        fig_pos = out.find("book-slide")
        self.assertLess(fig_pos, out.find("expecting water"))
        self.assertGreater(fig_pos, out.find("## Chapter One"))
        self.assertIn('src="slide-decks/_pages/book/page-02.jpg"', out)

    def test_after_position_still_supported(self) -> None:
        entries = [_entry("ch01-s02", 2, "expecting water at its edge")]
        out = isd.inject_slides(BOOK_MD, entries, pages=_pages(2), position="after")
        fig_pos = out.find("book-slide")
        self.assertGreater(fig_pos, out.find("expecting water"))
        self.assertLess(fig_pos, out.find("More prose follows"))

    def test_anchor_in_first_paragraph_inserts_at_start(self) -> None:
        md = "First paragraph with the anchor phrase inside.\n\nSecond paragraph."
        entries = [_entry("ch01-s02", 1, "anchor phrase inside")]
        out = isd.inject_slides(md, entries, pages=_pages(1))
        self.assertTrue(out.startswith('<figure class="book-diagram book-slide">'))

    def test_multi_deck_combined_injection(self) -> None:
        # Two chapters' decks combined: re-keyed pages, per-chapter src paths.
        pages = {1002: "slide-decks/_pages/ch01/page-02.jpg", 2003: "slide-decks/_pages/ch02/page-03.jpg"}
        entries = [
            _entry("ch01-s02", 1002, "expecting water at its edge"),
            _entry("ch02-s03", 2003, "mechanism of self-surrender"),
        ]
        out = isd.inject_slides(BOOK_MD, entries, pages=pages)
        self.assertIn('src="slide-decks/_pages/ch01/page-02.jpg"', out)
        self.assertIn('src="slide-decks/_pages/ch02/page-03.jpg"', out)

    def test_cover_with_null_anchor_is_not_injected(self) -> None:
        entries = [_entry("ch01-s01", 1, None, title="Cover")]
        out = isd.inject_slides(BOOK_MD, entries, pages=_pages(1))
        self.assertNotIn("book-slide", out)

    def test_anchor_not_found_fails_with_slide_id(self) -> None:
        entries = [_entry("ch01-s03", 2, "this text appears nowhere at all")]
        with self.assertRaises(AuthoringError) as ctx:
            isd.inject_slides(BOOK_MD, entries, pages=_pages(2))
        self.assertIn("ch01-s03", str(ctx.exception))

    def test_ambiguous_anchor_fails_with_slide_id(self) -> None:
        entries = [_entry("ch02-s04", 2, "paragraph")]  # appears twice
        with self.assertRaises(AuthoringError) as ctx:
            isd.inject_slides(BOOK_MD, entries, pages=_pages(2))
        self.assertIn("ch02-s04", str(ctx.exception))

    def test_all_bad_anchors_reported_together(self) -> None:
        entries = [
            _entry("ch01-s05", 2, "appears nowhere"),
            _entry("ch02-s06", 2, "paragraph"),
        ]
        with self.assertRaises(AuthoringError) as ctx:
            isd.inject_slides(BOOK_MD, entries, pages=_pages(2))
        msg = str(ctx.exception)
        self.assertIn("ch01-s05", msg)
        self.assertIn("ch02-s06", msg)

    def test_page_beyond_extracted_count_fails_with_slide_id(self) -> None:
        entries = [_entry("ch02-s09", 9, "mechanism of self-surrender")]
        with self.assertRaises(AuthoringError) as ctx:
            isd.inject_slides(BOOK_MD, entries, pages=_pages(3))
        self.assertIn("ch02-s09", str(ctx.exception))

    def test_idempotent_rerun_identical(self) -> None:
        entries = [
            _entry("ch01-s02", 2, "expecting water at its edge"),
            _entry("ch02-s03", 3, "mechanism of self-surrender"),
        ]
        once = isd.inject_slides(BOOK_MD, entries, pages=_pages(3))
        twice = isd.inject_slides(once, entries, pages=_pages(3))
        self.assertEqual(once, twice)

    def test_strip_removes_previous_slide_figures_only(self) -> None:
        entries = [_entry("ch01-s02", 2, "expecting water at its edge")]
        injected = isd.inject_slides(BOOK_MD, entries, pages=_pages(2))
        with_diagram = injected.replace(
            "## Chapter Two",
            '<figure class="book-diagram">\n<svg></svg>\n<figcaption>d</figcaption>\n</figure>\n\n## Chapter Two',
        )
        stripped = isd.strip_slide_figures(with_diagram)
        self.assertNotIn("book-slide", stripped)
        self.assertIn('<figure class="book-diagram">', stripped)  # plain diagram survives


class PageMapTests(unittest.TestCase):
    def _make(self, names: list[str]) -> Path:
        d = Path(tempfile.mkdtemp())
        for n in names:
            (d / n).write_bytes(b"\x89PNG")
        return d

    def test_zero_padded_names(self) -> None:
        d = self._make(["page-01.jpg", "page-02.jpg", "page-14.png"])
        m = isd._page_map(d)
        self.assertEqual(sorted(m), [1, 2, 14])

    def test_unpadded_names(self) -> None:
        d = self._make(["page-1.png", "page-2.png", "page-3.png"])
        self.assertEqual(sorted(isd._page_map(d)), [1, 2, 3])


class ManifestValidationTests(unittest.TestCase):
    def test_duplicate_slide_id_rejected(self) -> None:
        d = Path(tempfile.mkdtemp())
        mf = d / "slide-manifest.json"
        mf.write_text(
            json.dumps(
                [
                    _entry("ch01-s02", 2, "a" * 30),
                    _entry("ch01-s02", 3, "b" * 30),
                ]
            ),
            encoding="utf-8",
        )
        with self.assertRaises(AuthoringError) as ctx:
            isd.load_manifest(mf)
        self.assertIn("ch01-s02", str(ctx.exception))

    def test_missing_required_key_rejected(self) -> None:
        d = Path(tempfile.mkdtemp())
        mf = d / "slide-manifest.json"
        mf.write_text(json.dumps([{"slide_id": "x", "page": 1}]), encoding="utf-8")
        with self.assertRaises(AuthoringError):
            isd.load_manifest(mf)


class RenderPriorityTests(unittest.TestCase):
    def test_render_input_is_always_book_md(self) -> None:
        # Visuals are decoupled (curated via visual-layout.json), so the render
        # input is always the diagram-free book.md — legacy *-illustrated/-slides
        # markdown is neither produced nor consumed.
        import build_book_pdf as bbp

        d = Path(tempfile.mkdtemp())
        (d / "book").mkdir()
        (d / "book" / "book.md").write_text("# t", encoding="utf-8")
        self.assertEqual(bbp._pick_book_md(d).name, "book.md")
        (d / "book" / "book-illustrated.md").write_text("# t", encoding="utf-8")
        (d / "book" / "book-slides.md").write_text("# t", encoding="utf-8")
        self.assertEqual(bbp._pick_book_md(d).name, "book.md")


if __name__ == "__main__":
    unittest.main()
