"""Tests for the knowledge augmentation step wired into per_chapter_pass (step 3.5).

Verifies:
- Augmentation writes back and appends a note when the augmenter injects a context block.
- Augmentation is skipped (no file write) when the augmenter returns unchanged text.
- Augmentation failure is non-fatal: the pipeline continues with the original episode .txt.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Ensure scripts/podcast/ is importable.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_SCRIPTS_PODCAST = _REPO_ROOT / "scripts" / "podcast"
if str(_SCRIPTS_PODCAST) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_PODCAST))


# Patch targets are the names as they live in the per_chapter module's namespace.
_MOD = "scripts.podcast.phases.per_chapter"


class PerChapterAugmentStepTests(unittest.TestCase):
    """Unit tests for step 3.5 — knowledge augmentation — in per_chapter_pass."""

    def _make_book_dir(self, tmp: Path) -> Path:
        book_dir = tmp / "books" / "test-book"
        (book_dir / "chapters").mkdir(parents=True)
        (book_dir / "episodes").mkdir(parents=True)
        (book_dir / "chapters" / "ch01-intro.txt").write_text("chapter text", encoding="utf-8")
        (book_dir / "episodes" / "EP01-intro.txt").write_text("episode framing", encoding="utf-8")
        return book_dir

    def _run_pass(
        self,
        book_dir: Path,
        augment_return: str = "episode framing",
        augment_raises: Exception | None = None,
    ) -> tuple:
        """Invoke per_chapter_pass with subprocess, authoring, converge, and augmenter mocked."""
        from scripts.podcast.phases import per_chapter as _m
        from scripts.podcast._convergence import ChapterOutcome

        dummy_outcome = ChapterOutcome(
            chapter_slug="intro",
            final_verdict="SHIP-READY",
            outer_iterations=1,
            fixer_attempts=0,
            p0_remaining=0, p1_remaining=0, p2_remaining=0,
            notes=[],
        )

        def _fake_run(cmd, *, cwd=None):
            return 0, "ok", ""

        def _fake_resolve(book_dir, chapter_file, chapter_slug):
            return "EP01-intro"

        augment_fn = (
            mock.MagicMock(side_effect=augment_raises)
            if augment_raises
            else mock.MagicMock(return_value=augment_return)
        )

        fake_intel_mod = mock.MagicMock()
        fake_intel_mod.augment_episode_text = augment_fn

        with (
            mock.patch.object(_m, "_run", side_effect=_fake_run),
            mock.patch.object(_m, "_resolve_episode_id", side_effect=_fake_resolve),
            mock.patch.object(_m, "author_framing"),
            mock.patch.object(_m, "converge_chapter", return_value=dummy_outcome),
        ):
            # Inject the fake intelligence.augmenter before the lazy import fires.
            sys.modules["intelligence.augmenter"] = fake_intel_mod
            try:
                result = _m.per_chapter_pass(book_dir, "intro")
            finally:
                sys.modules.pop("intelligence.augmenter", None)

        return result, augment_fn

    def test_augment_writes_back_when_text_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = self._make_book_dir(Path(tmp))
            episode_path = book_dir / "episodes" / "EP01-intro.txt"
            enriched = "[PRIOR DOCTRINAL CONTEXT]\n---\nsome atom\n\nepisode framing"

            outcome, augment_fn = self._run_pass(book_dir, augment_return=enriched)

            augment_fn.assert_called_once()
            self.assertEqual(episode_path.read_text(encoding="utf-8"), enriched)
            self.assertIn("knowledge augmentation applied", outcome.notes)

    def test_augment_no_write_when_text_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = self._make_book_dir(Path(tmp))
            episode_path = book_dir / "episodes" / "EP01-intro.txt"

            # Augmenter returns the same text (gate disabled or no matching atoms).
            outcome, augment_fn = self._run_pass(book_dir, augment_return="episode framing")

            augment_fn.assert_called_once()
            self.assertEqual(episode_path.read_text(encoding="utf-8"), "episode framing")
            self.assertNotIn("knowledge augmentation applied", outcome.notes)

    def test_augment_failure_is_nonfatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = self._make_book_dir(Path(tmp))
            episode_path = book_dir / "episodes" / "EP01-intro.txt"

            outcome, _ = self._run_pass(
                book_dir,
                augment_raises=RuntimeError("DB unavailable"),
            )

            # Original file is untouched.
            self.assertEqual(episode_path.read_text(encoding="utf-8"), "episode framing")
            # Pipeline still succeeded.
            self.assertEqual(outcome.final_verdict, "SHIP-READY")
            # A skip note is recorded.
            self.assertTrue(any("skipped" in n for n in outcome.notes))


if __name__ == "__main__":
    unittest.main()
