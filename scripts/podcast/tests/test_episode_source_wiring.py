#!/usr/bin/env python3
"""Regression: the NotebookLM SOURCE is ALWAYS the author-voice chapter
(chapters/<slug>.txt), never the Branch-B revoice (chapters/literary/<slug>.txt).

Guards the 2026-06-04 wiring fix in build_episode_txt.build() that dropped the
`chapters/literary` preference — podcast path (author voice) feeds NotebookLM; the
revoice is a separate deliverable (the companion book, PDF path).
"""
from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build_episode_txt as bld  # noqa: E402


class EpisodeSourceWiringTests(unittest.TestCase):
    def test_source_is_author_voice_never_literary(self):
        captured: list[str] = []

        def fake_find(d, slug, required=True):
            captured.append(str(d))
            return Path(d) / f"ch01-{slug}.txt"

        with tempfile.TemporaryDirectory() as tmp:
            book = Path(tmp) / "bucket" / "the-book"
            draft = book / "_system" / "episode-drafts" / "EP01-foo"
            draft.mkdir(parents=True)
            (draft / "00-framing.md").write_text("framing\n")
            (book / "chapters").mkdir(parents=True)
            (book / "chapters" / "literary").mkdir(parents=True)  # decoy — must be ignored

            with mock.patch.object(bld, "find_chapter_by_slug", side_effect=fake_find), \
                 mock.patch.object(bld, "load_book_meta_prose_tells", lambda *a, **k: []), \
                 mock.patch.object(bld, "assert_chapters_populated", lambda *a, **k: None), \
                 mock.patch.object(bld, "validate_chapter", lambda *a, **k: 1200), \
                 mock.patch.object(bld, "is_islamic_scholarly", lambda *a, **k: False), \
                 mock.patch.object(bld, "build_framing_episode_txt", lambda *a, **k: 500):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    bld.build(book, "EP01-foo", check_only=True)

        self.assertTrue(captured, "find_chapter_by_slug was never called")
        self.assertTrue(any(c.rstrip("/").endswith("chapters") for c in captured),
                        f"expected the source lookup in <book>/chapters: {captured}")
        self.assertFalse(any("literary" in c for c in captured),
                         f"NotebookLM source must NEVER resolve from chapters/literary/: {captured}")


if __name__ == "__main__":
    unittest.main()
