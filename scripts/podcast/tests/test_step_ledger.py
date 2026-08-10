#!/usr/bin/env python3
"""The step ledger must record what every step did, not only what failed or cost money.

Before this ledger a step left a trace only if it spent money
(`_cost_ledger.append_cost_row`) or threw (`_compose_skips.record_skip`). A step
that ran and quietly did nothing left NOTHING — so a deterministic pass that
no-op'd because of a bug was indistinguishable from one that worked. That covers
most of the pipeline: the twenty-five apparatus steps, the vowelling, the
alignment and the paragraph mirror all spend nothing and, on success, said
nothing.

What is pinned here:

  * every outcome is recorded, `ok` and `noop` included — the whole point;
  * a recorder never raises, because it is called from every step in the pipeline
    and must never become the failure it describes;
  * `noop` stays distinct from `ok`, since "ran and changed nothing" is the shape
    most silent-failure bugs actually take;
  * the reader tolerates a corrupt line, so one bad record cannot blind a review
    gate to the rest of the run;
  * `_compose_skips.record_skip` mirrors its failure into the ledger, which is
    what lets a gate compare steps that ran against steps that should have.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from _step_ledger import (
    OUTCOME_FAILED,
    OUTCOME_NOOP,
    OUTCOME_OK,
    OUTCOME_SKIPPED,
    file_evidence,
    last_by_step,
    latest_steps,
    ledger_path,
    outcome_counts,
    read_steps,
    record_step,
    step,
)


class RecordingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self.book = Path(self._td.name) / "book"
        (self.book / "_system").mkdir(parents=True)

    def tearDown(self) -> None:
        self._td.cleanup()

    def test_records_a_successful_step(self):
        record_step(self.book, phase="0book-compose", step="inline-arabic", outcome=OUTCOME_OK)
        rows = read_steps(self.book)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["step"], "inline-arabic")
        self.assertEqual(rows[0]["outcome"], OUTCOME_OK)
        self.assertEqual(rows[0]["phase"], "0book-compose")

    def test_appends_rather_than_overwriting(self):
        for name in ("translit", "vowelling", "spelling"):
            record_step(self.book, phase="0book-compose", step=name, outcome=OUTCOME_OK)
        self.assertEqual([r["step"] for r in read_steps(self.book)], ["translit", "vowelling", "spelling"])

    def test_noop_is_distinct_from_ok(self):
        record_step(self.book, phase="p", step="vowelling", outcome=OUTCOME_NOOP)
        rows = read_steps(self.book)
        self.assertEqual(rows[0]["outcome"], OUTCOME_NOOP)
        self.assertNotEqual(rows[0]["outcome"], OUTCOME_OK)

    def test_evidence_round_trips(self):
        record_step(
            self.book,
            phase="p",
            step="inline-arabic",
            outcome=OUTCOME_OK,
            evidence={"changed": 42, "why": "annotated terms"},
        )
        self.assertEqual(read_steps(self.book)[0]["evidence"]["changed"], 42)

    def test_filters_by_phase(self):
        record_step(self.book, phase="0b", step="win-001", outcome=OUTCOME_OK)
        record_step(self.book, phase="0book-compose", step="translit", outcome=OUTCOME_OK)
        self.assertEqual(len(read_steps(self.book, phase="0b")), 1)
        self.assertEqual(read_steps(self.book, phase="0b")[0]["step"], "win-001")

    def test_reader_on_a_missing_ledger_is_empty_not_an_error(self):
        self.assertEqual(read_steps(self.book), [])

    def test_reader_skips_a_corrupt_line_and_keeps_the_rest(self):
        record_step(self.book, phase="p", step="a", outcome=OUTCOME_OK)
        with ledger_path(self.book).open("a", encoding="utf-8") as f:
            f.write("{ this is not json\n")
        record_step(self.book, phase="p", step="b", outcome=OUTCOME_OK)
        rows = read_steps(self.book)
        self.assertEqual([r["step"] for r in rows], ["a", "b"])

    def test_recorder_never_raises_on_an_unwritable_location(self):
        # A recorder must never become the failure it records. `_system` here is a
        # FILE, so mkdir/open must fail internally and be swallowed.
        broken = Path(self._td.name) / "broken"
        broken.mkdir()
        (broken / "_system").write_text("not a directory", encoding="utf-8")
        self.assertIsNone(record_step(broken, phase="p", step="s", outcome=OUTCOME_OK))

    def test_unknown_outcome_is_recorded_not_rejected(self):
        # A caller's typo should surface in the ledger as an oddity a gate can
        # flag, never crash the step it was only trying to describe.
        record_step(self.book, phase="p", step="s", outcome="whoops")
        self.assertEqual(read_steps(self.book)[0]["outcome"], "whoops")


class ContextManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self.book = Path(self._td.name) / "book"
        (self.book / "_system").mkdir(parents=True)

    def tearDown(self) -> None:
        self._td.cleanup()

    def test_success_records_ok_once(self):
        with step(self.book, "p", "thing"):
            pass
        rows = read_steps(self.book)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["outcome"], OUTCOME_OK)

    def test_noop_and_skipped_are_settable_from_inside(self):
        with step(self.book, "p", "a") as rec:
            rec.noop("no Arabic in this book")
        with step(self.book, "p", "b") as rec:
            rec.skipped("book_visuals=manual_only")
        rows = read_steps(self.book)
        self.assertEqual(rows[0]["outcome"], OUTCOME_NOOP)
        self.assertEqual(rows[0]["evidence"]["why"], "no Arabic in this book")
        self.assertEqual(rows[1]["outcome"], OUTCOME_SKIPPED)

    def test_failure_records_failed_and_re_raises(self):
        # Deliberately does NOT swallow: it is dropped around steps whose callers
        # already have their own error handling, and changing that would alter
        # behaviour rather than observe it.
        with self.assertRaises(ValueError):
            with step(self.book, "p", "boom"):
                raise ValueError("nope")
        rows = read_steps(self.book)
        self.assertEqual(rows[0]["outcome"], OUTCOME_FAILED)
        self.assertIn("nope", rows[0]["error"])

    def test_records_exactly_one_line_per_step_even_on_failure(self):
        with self.assertRaises(RuntimeError):
            with step(self.book, "p", "once"):
                raise RuntimeError("x")
        self.assertEqual(len(read_steps(self.book)), 1)

    def test_evidence_helpers_capture_sizes_and_missing_files(self):
        real = self.book / "_system" / "present.md"
        real.write_text("hello", encoding="utf-8")
        ev = file_evidence(real, self.book / "_system" / "absent.md")
        self.assertEqual(ev[0]["bytes"], 5)
        self.assertIsNone(ev[1]["bytes"], "a missing output must be recorded, not omitted")


class ReaderHelperTests(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self.book = Path(self._td.name) / "book"
        (self.book / "_system").mkdir(parents=True)

    def tearDown(self) -> None:
        self._td.cleanup()

    def test_outcome_counts(self):
        record_step(self.book, phase="p", step="a", outcome=OUTCOME_OK)
        record_step(self.book, phase="p", step="b", outcome=OUTCOME_OK)
        record_step(self.book, phase="p", step="c", outcome=OUTCOME_FAILED)
        counts = outcome_counts(read_steps(self.book))
        self.assertEqual(counts[OUTCOME_OK], 2)
        self.assertEqual(counts[OUTCOME_FAILED], 1)

    def test_last_by_step_reports_the_final_outcome_of_a_retried_step(self):
        record_step(self.book, phase="p", step="flaky", outcome=OUTCOME_FAILED)
        record_step(self.book, phase="p", step="flaky", outcome=OUTCOME_OK)
        self.assertEqual(
            last_by_step(read_steps(self.book))["flaky"]["outcome"],
            OUTCOME_OK,
            "a step that failed then succeeded must not read as a defect",
        )

    def test_latest_steps_falls_back_when_no_run_id_is_present(self):
        # Records written before run correlation carry run_id=None; the reader must
        # still report them rather than returning nothing.
        record_step(self.book, phase="p", step="a", outcome=OUTCOME_OK)
        rows = latest_steps(self.book)
        self.assertEqual(len(rows), 1)

    def test_latest_steps_scopes_to_the_most_recent_run(self):
        path = ledger_path(self.book)
        lines = [
            {"ts": "t1", "phase": "p", "step": "old", "outcome": "ok", "run_id": "run-1", "evidence": {}},
            {"ts": "t2", "phase": "p", "step": "new", "outcome": "ok", "run_id": "run-2", "evidence": {}},
        ]
        path.write_text("".join(json.dumps(x) + "\n" for x in lines), encoding="utf-8")
        self.assertEqual([r["step"] for r in latest_steps(self.book)], ["new"])


class ComposeSkipMirrorTests(unittest.TestCase):
    """A failure recorded by the compose skip-record must also reach the ledger."""

    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self.book = Path(self._td.name) / "book"
        (self.book / "_system").mkdir(parents=True)

    def tearDown(self) -> None:
        self._td.cleanup()

    def test_record_skip_mirrors_into_the_step_ledger(self):
        from _compose_skips import record_skip

        record_skip(self.book, "inline-arabic", ValueError("bad glossary"), lambda m: None)
        rows = read_steps(self.book)
        self.assertEqual(len(rows), 1, "a skipped step must leave a ledger record")
        self.assertEqual(rows[0]["step"], "inline-arabic")
        self.assertEqual(rows[0]["outcome"], OUTCOME_FAILED)
        self.assertIn("bad glossary", rows[0]["error"])

    def test_record_skip_still_writes_its_own_record(self):
        # The mirror must not have displaced the file gate B8 reads.
        from _compose_skips import record_path, record_skip

        record_skip(self.book, "vowelling", ValueError("x"), lambda m: None)
        self.assertTrue(record_path(self.book).exists())


class ApparatusDeclarationTests(unittest.TestCase):
    """Every step the apparatus records must be declared, and vice versa.

    This is the list a review gate compares against, so a step added to compose
    without being declared would be invisible to the gate — the original failure
    mode in a new place.
    """

    #: Concatenated source of every module hosting step call sites. Read from the
    #: declared list, because naming one file is what broke this test (and two others)
    #: when the report-only steps moved to `_book_reports` on 2026-08-08.
    @staticmethod
    def _hosting_source() -> str:
        from _apparatus_steps import APPARATUS_MODULES

        return "\n".join((SCRIPTS_PODCAST / name).read_text(encoding="utf-8") for name in APPARATUS_MODULES)

    def test_declared_steps_match_the_recorded_ones(self):
        import re

        import _book_apparatus as ap

        source = self._hosting_source()
        recorded = set(re.findall(r'_ok\(book_dir, "([a-z-]+)"', source))
        recorded |= set(re.findall(r'_record_skip\(book_dir, "([a-z-]+)"', source))
        declared = set(ap.APPARATUS_STEPS)
        self.assertEqual(
            recorded - declared,
            set(),
            "these steps record but are not declared in APPARATUS_STEPS — a review gate cannot see them",
        )
        self.assertEqual(
            declared - recorded,
            set(),
            "these steps are declared but never record — the gate would report them permanently missing",
        )

    def test_every_step_records_both_outcomes(self):
        import re

        source = self._hosting_source()
        ok_names = set(re.findall(r'_ok\(book_dir, "([a-z-]+)"', source))
        fail_names = set(re.findall(r'_record_skip\(book_dir, "([a-z-]+)"', source))
        self.assertEqual(
            fail_names - ok_names,
            set(),
            "these steps record a failure but never a success — the ledger would only ever show them when they break",
        )


class LedgerReadCostTests(unittest.TestCase):
    """The ledger is append-only across every run a book has ever had.

    `latest_steps` used to call `latest_run_id` — a full read and a full JSON parse of
    every line — and then `read_steps`, doing the same again, for ONE query. The
    per-chapter lane appends six rows per chapter, and the review gates call this once
    per phase.
    """

    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.book_dir = Path(self.tmp.name) / "a-book"
        (self.book_dir / "_system").mkdir(parents=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _seed(self, n: int = 40) -> None:
        for i in range(n):
            record_step(self.book_dir, phase="per-chapter", step="build", outcome="ok", evidence={"chapter": f"c{i}"})

    def test_latest_steps_reads_the_file_once(self) -> None:
        self._seed()
        real_read = Path.read_text
        reads: list[str] = []

        def _counting_read(self_path, *a, **k):
            if self_path.name == "step-ledger.jsonl":
                reads.append(str(self_path))
            return real_read(self_path, *a, **k)

        with mock.patch.object(Path, "read_text", _counting_read):
            rows = latest_steps(self.book_dir, phase="per-chapter")
        self.assertEqual(len(reads), 1, f"the ledger was read {len(reads)} times for one query")
        self.assertEqual(len(rows), 40)

    def test_latest_steps_still_returns_only_the_newest_run(self) -> None:
        # The behaviour the double read was paying for must be unchanged.
        with mock.patch("_step_ledger._run_id", return_value="run-a"):
            record_step(self.book_dir, phase="p", step="s", outcome="ok")
        with mock.patch("_step_ledger._run_id", return_value="run-b"):
            record_step(self.book_dir, phase="p", step="s2", outcome="ok")
        rows = latest_steps(self.book_dir)
        self.assertEqual([r["step"] for r in rows], ["s2"])

    def test_records_without_a_run_id_still_report_something(self) -> None:
        with mock.patch("_step_ledger._run_id", return_value=None):
            record_step(self.book_dir, phase="p", step="s", outcome="ok")
        self.assertEqual(len(latest_steps(self.book_dir)), 1)

    def test_a_malformed_line_does_not_blind_the_reader(self) -> None:
        self._seed(3)
        path = self.book_dir / "_system" / "step-ledger.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write("{not json at all\n")
        self.assertEqual(len(read_steps(self.book_dir)), 3)


if __name__ == "__main__":
    unittest.main()
