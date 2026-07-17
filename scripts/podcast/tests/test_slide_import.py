#!/usr/bin/env python3
"""Tests for _slide_import.py (phase 0book-slide-import).

No poppler, no claude -p: extraction + LLM are monkeypatched; the contract
under test is the gate (framing-driven, .SKIP exemption, halt naming exact
missing files), the sig cache, the retry path, and the combined injection.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _slide_import as si  # noqa: E402
from _authoring._core import AuthoringError, AuthoringHalt  # noqa: E402


BOOK_MD = """# T

## One

The seeker walks toward the mirage expecting water at its edge.

Filler paragraph one with its own words.

## Two

True comportment is the mechanism of self-surrender in every act.
"""


def _book(framings=(), pdfs=(), skips=(), book_md=BOOK_MD) -> Path:
    d = Path(tempfile.mkdtemp()) / "mybook"
    (d / "slide-decks" / "_manifests").mkdir(parents=True)
    (d / "book").mkdir(parents=True)
    (d / "book" / "book.md").write_text(book_md, encoding="utf-8")
    for ch, slug in framings:
        (d / "slide-decks" / f"{ch}-framing-{slug}.md").write_text("# F", encoding="utf-8")
    for ch, slug in pdfs:
        (d / "slide-decks" / f"{ch}-{slug}.pdf").write_bytes(b"%PDF-1.4 fake")
    for ch, slug in skips:
        (d / "slide-decks" / f"{ch}-{slug}.SKIP").touch()
    return d


def _fake_extract(pdf, pages_dir, *, force=False, log=print):
    pages_dir.mkdir(parents=True, exist_ok=True)
    for i in (1, 2):
        (pages_dir / f"page-{i:02d}.jpg").write_bytes(b"\xff\xd8")
    return 2


def _manifest_entries(ch):
    return [
        {"slide_id": f"{ch}-s01", "page": 1, "title": "Cover", "anchor_text": None},
        {"slide_id": f"{ch}-s02", "page": 2, "title": "Mirage",
         "anchor_text": "expecting water at its edge"},
    ]


class GateTests(unittest.TestCase):
    def test_no_framings_no_bookdeck_skips(self) -> None:
        d = _book()
        out = si.author_phase_slide_import(d)
        self.assertIn("skipped", out)

    def test_missing_pdf_halts_naming_exact_file(self) -> None:
        d = _book(framings=[("ch01", "alpha"), ("ch02", "beta")],
                  pdfs=[("ch01", "alpha")])
        with self.assertRaises(AuthoringHalt) as ctx:
            si.author_phase_slide_import(d)
        msg = str(ctx.exception)
        self.assertIn("ch02-beta.pdf", msg)
        self.assertNotIn("ch01-alpha.pdf\n", msg.split("SLIDE DECK")[0])
        self.assertIn("SLIDE DECK GENERATION", msg)  # card embedded

    def test_skip_marker_exempts(self) -> None:
        d = _book(framings=[("ch01", "alpha"), ("ch02", "beta")],
                  pdfs=[("ch01", "alpha")], skips=[("ch02", "beta")])
        with mock.patch.object(si, "extract_pages", _fake_extract), \
             mock.patch.object(si, "page_titles", lambda p: ["Cover", "Mirage"]), \
             mock.patch.object(si, "_author_manifest",
                               lambda bd, ch, slug, *a, **k: _manifest_entries(ch)):
            out = si.author_phase_slide_import(d)
        self.assertEqual(out["exempt"], ["ch02"])
        self.assertEqual(out["imported"], {"ch01": 1})


class ImportTests(unittest.TestCase):
    def test_slides_emitted_as_candidates(self) -> None:
        # Slides are decoupled: extracted + watermark-cleaned, then offered as
        # candidates to book/visuals/index.json (not injected into book text).
        d = _book(framings=[("ch01", "alpha")], pdfs=[("ch01", "alpha")])
        with mock.patch.object(si, "extract_pages", _fake_extract), \
             mock.patch.object(si, "page_titles", lambda p: ["Cover", "Mirage"]), \
             mock.patch.object(si, "_author_manifest",
                               lambda bd, ch, slug, *a, **k: _manifest_entries(ch)):
            out = si.author_phase_slide_import(d)
        # book text stays diagram-free — no book-slides.md is written.
        self.assertFalse((d / "book" / "book-slides.md").exists())
        self.assertTrue(out["awaiting_layout"])
        self.assertEqual(out["imported"], {"ch01": 1})
        index = json.loads((d / "book" / "visuals" / "index.json").read_text(encoding="utf-8"))
        self.assertTrue(index)  # at least one slide candidate registered

    def test_sig_cache_hit_skips_llm(self) -> None:
        d = _book(framings=[("ch01", "alpha")], pdfs=[("ch01", "alpha")])
        mpath = d / "slide-decks" / "_manifests" / "ch01-manifest.json"
        mpath.write_text(json.dumps(_manifest_entries("ch01")), encoding="utf-8")
        sig = si._sig(d / "slide-decks" / "ch01-alpha.pdf", d / "book" / "book.md")
        si._sig_path(d, "ch01").write_text(sig, encoding="utf-8")
        boom = mock.Mock(side_effect=AssertionError("LLM must not be called on cache hit"))
        with mock.patch.object(si, "extract_pages", _fake_extract), \
             mock.patch.object(si, "_author_manifest", boom):
            out = si.author_phase_slide_import(d)
        self.assertEqual(out["imported"], {"ch01": 1})

    def test_sig_cache_miss_on_deck_change(self) -> None:
        d = _book(framings=[("ch01", "alpha")], pdfs=[("ch01", "alpha")])
        mpath = d / "slide-decks" / "_manifests" / "ch01-manifest.json"
        mpath.write_text(json.dumps(_manifest_entries("ch01")), encoding="utf-8")
        si._sig_path(d, "ch01").write_text("stale-sig", encoding="utf-8")
        called = mock.Mock(return_value=_manifest_entries("ch01"))
        with mock.patch.object(si, "extract_pages", _fake_extract), \
             mock.patch.object(si, "_author_manifest", called):
            si.author_phase_slide_import(d)
        called.assert_called_once()

    def test_book_level_deck_uses_existing_manifest(self) -> None:
        d = _book()  # no framings
        (d / "slide-decks" / "book-deck.pdf").write_bytes(b"%PDF-1.4 fake")
        (d / "slide-decks" / "_manifests" / "book-manifest.json").write_text(
            json.dumps([{"slide_id": "book-s01", "page": 2, "title": "Mirage",
                         "anchor_text": "expecting water at its edge"}]),
            encoding="utf-8")
        boom = mock.Mock(side_effect=AssertionError("no LLM for book-level manifests"))
        with mock.patch.object(si, "extract_pages", _fake_extract), \
             mock.patch.object(si, "_author_manifest", boom):
            out = si.author_phase_slide_import(d)
        self.assertEqual(out["imported"], {"book": 1})


class RetryTests(unittest.TestCase):
    def test_retry_then_fail_raises_authoring_error(self) -> None:
        d = _book(framings=[("ch01", "alpha")], pdfs=[("ch01", "alpha")])
        bad = [{"slide_id": "ch01-s01", "page": 1, "title": "X",
                "anchor_text": "phrase that is nowhere"}]

        def fake_run(prompt, **kw):
            si._manifest_path(d, "ch01").write_text(json.dumps(bad), encoding="utf-8")
            return 0, "", ""

        with mock.patch.object(si, "extract_pages", _fake_extract), \
             mock.patch.object(si, "page_titles", lambda p: ["X"]), \
             mock.patch.object(si, "_run_claude_p", fake_run):
            with self.assertRaises(AuthoringError) as ctx:
                si.author_phase_slide_import(d)
        self.assertIn("twice", str(ctx.exception))

    def test_retry_recovers_on_second_attempt(self) -> None:
        d = _book(framings=[("ch01", "alpha")], pdfs=[("ch01", "alpha")])
        bad = [{"slide_id": "ch01-s01", "page": 1, "title": "X",
                "anchor_text": "phrase that is nowhere"}]
        good = [{"slide_id": "ch01-s01", "page": 1, "title": "X",
                 "anchor_text": "expecting water at its edge"}]
        attempts = iter([bad, good])

        def fake_run(prompt, **kw):
            si._manifest_path(d, "ch01").write_text(
                json.dumps(next(attempts)), encoding="utf-8")
            return 0, "", ""

        with mock.patch.object(si, "extract_pages", _fake_extract), \
             mock.patch.object(si, "page_titles", lambda p: ["X"]), \
             mock.patch.object(si, "_run_claude_p", fake_run):
            out = si.author_phase_slide_import(d)
        self.assertEqual(out["imported"], {"ch01": 1})


if __name__ == "__main__":
    unittest.main()
