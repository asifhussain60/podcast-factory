#!/usr/bin/env python3
"""Tests for the standardized per-book folder skeleton (_paths.BOOK_SUBDIRS).

Contract: ONE registry drives every creation path (intake flat, intake volume,
intake_launch, scaffold) so layouts can never drift again; ensure_book_skeleton
is idempotent and drops .gitkeep only in empty dirs so the skeleton survives git.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from _paths import BOOK_SUBDIRS, ensure_book_skeleton  # noqa: E402


class SkeletonTests(unittest.TestCase):
    def test_creates_full_standard_set(self) -> None:
        d = Path(tempfile.mkdtemp()) / "book"
        ensure_book_skeleton(d)
        for sub in BOOK_SUBDIRS:
            self.assertTrue((d / sub).is_dir(), f"missing {sub}")

    def test_required_pipeline_surfaces_present(self) -> None:
        # The folders Asif's directive names explicitly + the PDF-route surfaces.
        for required in ("m4a", "slide-decks", "slide-decks/_manifests",
                         "book", "chapters", "episodes", "transcripts",
                         "_source", "_system/episode-drafts"):
            self.assertIn(required, BOOK_SUBDIRS)

    def test_gitkeep_in_empty_leaves_only(self) -> None:
        d = Path(tempfile.mkdtemp()) / "book"
        ensure_book_skeleton(d)
        self.assertTrue((d / "m4a" / ".gitkeep").exists())
        # Parent dirs that contain subdirs may or may not carry a keep — but a
        # dir with real content must NOT get one on a re-run.
        (d / "chapters" / "ch01-x.txt").write_text("x", encoding="utf-8")
        (d / "chapters" / ".gitkeep").unlink()
        ensure_book_skeleton(d)
        self.assertFalse((d / "chapters" / ".gitkeep").exists())

    def test_idempotent(self) -> None:
        d = Path(tempfile.mkdtemp()) / "book"
        ensure_book_skeleton(d)
        before = sorted(p.relative_to(d).as_posix() for p in d.rglob("*"))
        ensure_book_skeleton(d)
        after = sorted(p.relative_to(d).as_posix() for p in d.rglob("*"))
        self.assertEqual(before, after)

    def test_no_other_skeleton_lists_survive(self) -> None:
        # Drift guard: no module may define its own folder list again.
        for mod in ("intake_book.py", "intake_launch.py", "scaffold_book.py"):
            text = (SCRIPTS_PODCAST / mod).read_text(encoding="utf-8")
            self.assertNotIn("SKELETON_DIRS", text, f"{mod} re-grew a folder list")
            self.assertIn("ensure_book_skeleton", text, f"{mod} bypasses the registry")


if __name__ == "__main__":
    unittest.main()
