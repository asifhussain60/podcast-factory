"""Tests for the no-teaching-lost guardrail in _literary.teaching_loss_findings."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from _literary import teaching_loss_findings


SOURCE = """# Ayyuhal Walad

## Section 1 — The Problem of Knowledge

Know, beloved son, that the verse 2:255 (Ayat al-Kursi) teaches the living,
self-subsisting nature of the divine. Hatim al-Asamm gave eight benefits. The
prophetic hadith warns against knowledge that does not benefit. Consider the
parable of the man who memorized a hundred sciences yet faltered at the grave.

## Section 2 — The Disciplines of the Path

Four things must be acquired and four abandoned, as 17:36 makes plain.
"""


class TeachingLossGuardrailTests(unittest.TestCase):
    def test_faithful_revoice_is_clean(self):
        # Same headings, similar length, both citations present → no findings.
        out = SOURCE.replace("Know, beloved son", "Listen closely, my child")
        self.assertEqual(teaching_loss_findings(SOURCE, out), [])

    def test_dropped_section_heading_flagged(self):
        out = SOURCE.replace("## Section 2 — The Disciplines of the Path", "")
        findings = teaching_loss_findings(SOURCE, out)
        self.assertTrue(any("missing section heading" in f for f in findings))

    def test_large_length_drop_flagged(self):
        # Length check only fires for substantial chapters (>=200 source words).
        long_src = "## Section 1 — Foundations\n" + ("the teaching unfolds carefully here. " * 60)
        out = "## Section 1 — Foundations\nA terse summary."
        findings = teaching_loss_findings(long_src, out)
        self.assertTrue(any("length drop" in f for f in findings))

    def test_dropped_citations_flagged(self):
        # Keep headings + length but strip the verse refs.
        out = SOURCE.replace("2:255", "the throne verse").replace("17:36", "the verse")
        findings = teaching_loss_findings(SOURCE, out)
        self.assertTrue(any("citation refs dropped" in f for f in findings))

    def test_headings_deduped_no_noise(self):
        # A repeated heading in source must not produce duplicate findings.
        src = "## A\ntext\n## A\nmore"
        out = "nothing"
        findings = [f for f in teaching_loss_findings(src, out) if "heading" in f]
        self.assertEqual(len(findings), 1)


if __name__ == "__main__":
    unittest.main()
