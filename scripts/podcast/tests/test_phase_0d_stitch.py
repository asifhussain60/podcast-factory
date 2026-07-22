"""Golden test for Phase 0d STEP 3 (deterministic stitch).

Pins the byte-for-byte output of _phase_0d_stitch — the LLM-free assembly of
per-source-chapter rationale + source-map fragments into the book-level
chapters-rationale.md and source-chapter-map.md. The expected strings below are
derived by hand from the stitch logic as it existed BEFORE the audit-Spec-2
extraction, so this test proves the extraction preserved behaviour exactly.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _authoring._chapter_design import _phase_0d_stitch


def _seed(chunks_dir: Path) -> None:
    chunks_dir.mkdir(parents=True, exist_ok=True)
    (chunks_dir / "sc-001.rationale.md").write_text("rationale one\n", encoding="utf-8")
    (chunks_dir / "sc-002.rationale.md").write_text("rationale two\n", encoding="utf-8")
    (chunks_dir / "sc-001.source-map.md").write_text("| 1 | Alpha | ch01.txt | merged |\n", encoding="utf-8")
    (chunks_dir / "sc-002.source-map.md").write_text("| 2 | Beta | ch02.txt | split |\n", encoding="utf-8")


SOURCE_CHAPTERS = [
    {"sc_index": 1, "source_title": "Alpha"},
    {"sc_index": 2, "source_title": "Beta"},
]


class Phase0dStitchGolden(unittest.TestCase):
    def test_section_mode_stitches_rationale_and_source_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chunks_dir = root / "_chunks" / "0d"
            _seed(chunks_dir)
            out_rationale = root / "chapters-rationale.md"
            out_source_map = root / "source-chapter-map.md"

            _phase_0d_stitch(
                SOURCE_CHAPTERS,
                unit_mode="section",
                chunks_dir=chunks_dir,
                out_rationale=out_rationale,
                out_source_map=out_source_map,
            )

            self.assertEqual(
                out_rationale.read_text(encoding="utf-8"),
                "## Source chapter 1 — Alpha\n\nrationale one\n\n## Source chapter 2 — Beta\n\nrationale two\n\n",
            )
            self.assertEqual(
                out_source_map.read_text(encoding="utf-8"),
                "| source chapter | source title | episode(s) | split reason |\n"
                "|---|---|---|---|\n"
                "| 1 | Alpha | ch01.txt | merged |\n"
                "| 2 | Beta | ch02.txt | split |\n",
            )

    def test_chapter_mode_skips_source_map(self):
        # unit_mode == "chapter": rationale written, source-map NOT written.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chunks_dir = root / "_chunks" / "0d"
            _seed(chunks_dir)
            out_rationale = root / "chapters-rationale.md"
            out_source_map = root / "source-chapter-map.md"

            _phase_0d_stitch(
                SOURCE_CHAPTERS,
                unit_mode="chapter",
                chunks_dir=chunks_dir,
                out_rationale=out_rationale,
                out_source_map=out_source_map,
            )

            self.assertTrue(out_rationale.exists())
            self.assertFalse(out_source_map.exists())

    def test_missing_and_empty_fragments_are_skipped(self):
        # A source chapter with no rationale fragment (or an empty one) is
        # omitted from the stitched output — never crashes, never blank-injects.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chunks_dir = root / "_chunks" / "0d"
            chunks_dir.mkdir(parents=True, exist_ok=True)
            (chunks_dir / "sc-001.rationale.md").write_text("only one\n", encoding="utf-8")
            (chunks_dir / "sc-002.rationale.md").write_text("", encoding="utf-8")  # empty
            out_rationale = root / "chapters-rationale.md"
            out_source_map = root / "source-chapter-map.md"

            _phase_0d_stitch(
                SOURCE_CHAPTERS,
                unit_mode="chapter",
                chunks_dir=chunks_dir,
                out_rationale=out_rationale,
                out_source_map=out_source_map,
            )

            self.assertEqual(
                out_rationale.read_text(encoding="utf-8"),
                "## Source chapter 1 — Alpha\n\nonly one\n\n",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
