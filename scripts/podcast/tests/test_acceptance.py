#!/usr/bin/env python3
"""Tests for scripts/podcast/_acceptance.py — the auto-marking helper."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _acceptance  # noqa: E402


SAMPLE = """\
# Acceptance Criteria

## Wave 1 — Foundation

### P1 — Boundary
- [ ] **P1.1** ✅ first bullet
- [ ] **P1.1** ✅ second bullet
- [x] **P3.1** ✅ already done

### P5 — Constants
- [ ] **P5.4** ✅ enum has 14 values
- [ ] **P5.4** ✅ tests pass
"""


class FindRowsTests(unittest.TestCase):
    def test_returns_all_rows(self):
        rows = _acceptance.find_rows(SAMPLE)
        self.assertEqual(len(rows), 5)

    def test_filters_by_task_id(self):
        rows = _acceptance.find_rows(SAMPLE, task_id="P1.1")
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r.task_id == "P1.1" for r in rows))

    def test_captures_check_status(self):
        rows = _acceptance.find_rows(SAMPLE, task_id="P3.1")
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0].checked)

        rows = _acceptance.find_rows(SAMPLE, task_id="P1.1")
        self.assertFalse(rows[0].checked)

    def test_returns_empty_on_unknown_id(self):
        self.assertEqual(_acceptance.find_rows(SAMPLE, task_id="P99"), [])


class CountAndCompleteTests(unittest.TestCase):
    def test_count_checked_partial(self):
        self.assertEqual(_acceptance.count_checked(SAMPLE, "P1.1"), (0, 2))
        self.assertEqual(_acceptance.count_checked(SAMPLE, "P3.1"), (1, 1))

    def test_is_complete(self):
        self.assertFalse(_acceptance.is_task_complete(SAMPLE, "P1.1"))
        self.assertTrue(_acceptance.is_task_complete(SAMPLE, "P3.1"))

    def test_is_complete_zero_rows_is_false(self):
        self.assertFalse(_acceptance.is_task_complete(SAMPLE, "P99"))


class MarkTaskRowsTests(unittest.TestCase):
    def test_marks_all_unchecked(self):
        new, n = _acceptance.mark_task_rows(SAMPLE, "P1.1")
        self.assertEqual(n, 2)
        self.assertEqual(_acceptance.count_checked(new, "P1.1"), (2, 2))

    def test_idempotent_already_checked(self):
        new, n = _acceptance.mark_task_rows(SAMPLE, "P3.1")
        self.assertEqual(n, 0)
        self.assertEqual(new, SAMPLE)

    def test_filters_by_text_contains(self):
        new, n = _acceptance.mark_task_rows(SAMPLE, "P5.4", text_contains="enum")
        self.assertEqual(n, 1)
        rows = _acceptance.find_rows(new, "P5.4")
        # First P5.4 row (enum-related) is now checked; second one is still pending.
        self.assertTrue(rows[0].checked)
        self.assertFalse(rows[1].checked)

    def test_no_match_when_text_filter_misses(self):
        new, n = _acceptance.mark_task_rows(SAMPLE, "P5.4", text_contains="nonexistent")
        self.assertEqual(n, 0)
        self.assertEqual(new, SAMPLE)

    def test_unknown_task_id_is_noop(self):
        new, n = _acceptance.mark_task_rows(SAMPLE, "P99")
        self.assertEqual(n, 0)
        self.assertEqual(new, SAMPLE)


class MarkInFileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        )
        self.tmp.write(SAMPLE)
        self.tmp.close()
        self.path = Path(self.tmp.name)

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def test_marks_and_writes_file(self):
        n = _acceptance.mark_task_rows_in_file("P1.1", acceptance_file=self.path)
        self.assertEqual(n, 2)
        self.assertEqual(_acceptance.count_checked(self.path.read_text(), "P1.1"), (2, 2))

    def test_no_write_when_nothing_to_mark(self):
        """File mtime stays put when 0 rows are newly marked (preserves
        downstream change-detection)."""
        before = self.path.stat().st_mtime_ns
        n = _acceptance.mark_task_rows_in_file("P3.1", acceptance_file=self.path)
        after = self.path.stat().st_mtime_ns
        self.assertEqual(n, 0)
        self.assertEqual(before, after)


class AppendEvidenceTests(unittest.TestCase):
    def test_appends_to_matching_row(self):
        new = _acceptance.append_evidence(
            SAMPLE, "P1.1", text_contains="first bullet",
            evidence="verified by test_x",
        )
        self.assertIn("first bullet — verified by test_x", new)

    def test_idempotent_already_appended(self):
        once = _acceptance.append_evidence(
            SAMPLE, "P1.1", text_contains="first bullet", evidence="verified-X",
        )
        twice = _acceptance.append_evidence(
            once, "P1.1", text_contains="first bullet", evidence="verified-X",
        )
        self.assertEqual(once, twice)


if __name__ == "__main__":
    unittest.main()
