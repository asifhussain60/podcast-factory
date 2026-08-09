#!/usr/bin/env python3
"""Every review gate must be able to FAIL, and the review must never raise.

This repo has been bitten repeatedly by gates that reported clean over a rule they
never ran — three separate instances in the 2026-08-06 audit alone. A review layer
whose gates all pass on every book is worse than none, because it manufactures
confidence. So each gate here is driven to BOTH outcomes against a synthetic book,
and the cross-phase recheck tier is tested for the property that is its whole
point: a defect introduced by an earlier phase is caught at a LATER phase's
checkpoint.

Also pinned: the blocking policy. Gates are advisory unless declared in
`BLOCKING_GATES`, because a new review layer that can halt a run is a layer that
can strand a finished book.
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

import _phase_review as pr
from _step_ledger import record_step


class _BookFixture(unittest.TestCase):
    """A synthetic book that starts SOUND, so each test breaks exactly one thing."""

    SOURCE_WORDS = 1000

    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self.book = Path(self._td.name) / "book"
        self.text = self.book / "_system" / "source" / "text"
        self.text.mkdir(parents=True)
        (self.book / "book").mkdir(parents=True)
        (self.book / "chapter-contracts").mkdir(parents=True)

        (self.text / "raw-extract.md").write_text(" ".join(["word"] * self.SOURCE_WORDS), encoding="utf-8")
        (self.text / "refined-english.md").write_text(" ".join(["word"] * self.SOURCE_WORDS), encoding="utf-8")
        cache = self.text / "_chunks" / "0b"
        cache.mkdir(parents=True)
        (cache / "win-001.out.md").write_text("refined window", encoding="utf-8")
        (self.book / "chapter-contracts" / "ch01.yml").write_text("title: One\n", encoding="utf-8")
        (self.book / "book" / "book-toc.json").write_text(
            json.dumps({"book_title": "T", "chapters": [{"bk_index": 1, "title": "One"}]}), encoding="utf-8"
        )
        (self.book / "book" / "book.md").write_text("# T\n\n## One\n\nProse.\n", encoding="utf-8")

    def tearDown(self) -> None:
        self._td.cleanup()


class OwnGateTests(_BookFixture):
    def test_source_text_gate_passes_then_fails(self):
        self.assertTrue(pr.gate_source_text_present(self.book)[0])
        (self.text / "raw-extract.md").unlink()
        ok, note = pr.gate_source_text_present(self.book)
        self.assertFalse(ok)
        self.assertIn("missing", note)

    def test_refined_text_gate_passes_then_fails(self):
        self.assertTrue(pr.gate_refined_text_present(self.book)[0])
        (self.text / "refined-english.md").write_text("", encoding="utf-8")
        self.assertFalse(pr.gate_refined_text_present(self.book)[0])

    def test_coverage_gate_catches_a_truncated_refinement(self):
        self.assertTrue(pr.gate_refined_covers_source(self.book)[0])
        # Half the source: below the 60% floor, the shape of a windowed run that
        # stitched only some of its windows.
        (self.text / "refined-english.md").write_text(" ".join(["word"] * 400), encoding="utf-8")
        ok, note = pr.gate_refined_covers_source(self.book)
        self.assertFalse(ok)
        self.assertIn("truncated", note)

    def test_coverage_gate_tolerates_a_slightly_longer_refinement(self):
        # Refinement legitimately expands some prose; 102% is normal (measured on
        # the-master-and-the-disciple). A strict ratio would cry wolf.
        (self.text / "refined-english.md").write_text(" ".join(["word"] * 1020), encoding="utf-8")
        self.assertTrue(pr.gate_refined_covers_source(self.book)[0])

    def test_chapter_contracts_gate_passes_then_fails(self):
        self.assertTrue(pr.gate_chapter_contracts_exist(self.book)[0])
        (self.book / "chapter-contracts" / "ch01.yml").unlink()
        self.assertFalse(pr.gate_chapter_contracts_exist(self.book)[0])

    def test_toc_gate_fails_on_unparseable_json(self):
        self.assertTrue(pr.gate_book_toc_parses(self.book)[0])
        (self.book / "book" / "book-toc.json").write_text("{ not json", encoding="utf-8")
        ok, note = pr.gate_book_toc_parses(self.book)
        self.assertFalse(ok)
        self.assertIn("does not parse", note)

    def test_toc_gate_fails_when_it_declares_no_chapters(self):
        (self.book / "book" / "book-toc.json").write_text(json.dumps({"chapters": []}), encoding="utf-8")
        ok, note = pr.gate_book_toc_parses(self.book)
        self.assertFalse(ok)
        self.assertIn("no chapters", note)

    def test_book_md_gate_passes_then_fails(self):
        self.assertTrue(pr.gate_book_md_present(self.book)[0])
        (self.book / "book" / "book.md").unlink()
        self.assertFalse(pr.gate_book_md_present(self.book)[0])

    def test_toc_coverage_gate_catches_a_missing_chapter(self):
        (self.book / "book" / "book-toc.json").write_text(
            json.dumps({"chapters": [{"title": "One"}, {"title": "Two"}, {"title": "Three"}]}), encoding="utf-8"
        )
        ok, note = pr.gate_book_md_covers_toc(self.book)
        self.assertFalse(ok, note)
        self.assertIn("heading", note)


class WindowCacheGateTests(_BookFixture):
    """The gate that would have named the $8.38 re-spend."""

    def test_passes_while_the_cache_is_present(self):
        ok, note = pr.gate_window_cache_intact(self.book)
        self.assertTrue(ok)
        self.assertIn("intact", note)

    def test_fails_when_the_cache_vanished_but_the_source_did_not(self):
        # The exact 2026-08-05 condition: refined output on disk, source unchanged,
        # window cache gone — so the next run re-pays for every window.
        import shutil

        shutil.rmtree(self.text / "_chunks" / "0b")
        ok, note = pr.gate_window_cache_intact(self.book)
        self.assertFalse(ok)
        self.assertIn("GONE", note)

    def test_does_not_fire_before_0b_has_produced_anything(self):
        import shutil

        shutil.rmtree(self.text / "_chunks" / "0b")
        (self.text / "refined-english.md").unlink()
        ok, note = pr.gate_window_cache_intact(self.book)
        self.assertTrue(ok, "a book that has not run 0b yet must not be reported as having lost its cache")


class LedgerBackedGateTests(_BookFixture):
    def test_apparatus_gate_reports_missing_steps(self):
        # One step recorded out of twenty-five.
        record_step(self.book, phase="0book-compose", step="translit", outcome="ok")
        ok, note = pr.gate_apparatus_steps_all_ran(self.book)
        self.assertFalse(ok)
        self.assertIn("left no record", note)

    def test_apparatus_gate_passes_when_every_step_recorded(self):
        from _book_apparatus import APPARATUS_STEPS

        for name in APPARATUS_STEPS:
            record_step(self.book, phase="0book-compose", step=name, outcome="ok")
        ok, note = pr.gate_apparatus_steps_all_ran(self.book)
        self.assertTrue(ok, note)

    def test_apparatus_gate_is_quiet_before_compose_has_run(self):
        # No records at all is "compose has not run", not "every step is missing".
        ok, _ = pr.gate_apparatus_steps_all_ran(self.book)
        self.assertTrue(ok)

    def test_failed_step_gate_passes_then_fails(self):
        record_step(self.book, phase="0b", step="win-001", outcome="ok")
        self.assertTrue(pr.gate_no_step_failed(self.book)[0])
        record_step(self.book, phase="0b", step="win-002", outcome="failed", error="empty")
        ok, note = pr.gate_no_step_failed(self.book)
        self.assertFalse(ok)
        self.assertIn("win-002", note)

    def test_a_deliberate_skip_is_not_a_failure(self):
        # `skipped` means a config knob turned the step off, which most books do for
        # most optional steps. It must stay invisible to this gate or the gate is noise.
        record_step(self.book, phase="per-chapter", step="augment", outcome="skipped", evidence={"why": "gate off"})
        self.assertTrue(pr.gate_no_step_failed(self.book)[0])

    def test_a_step_that_crashed_reaches_this_gate(self):
        """The payoff of recording a crash as `failed` rather than `skipped`.

        The per-chapter augment stage caught every exception and recorded `skipped` —
        the same value a book records for having the feature switched off — so this
        gate, which filters on `failed`, never saw it. An augmenter broken for months
        was indistinguishable from one nobody had enabled.
        """
        record_step(self.book, phase="per-chapter", step="augment", outcome="failed", error="DB unavailable")
        ok, note = pr.gate_no_step_failed(self.book)
        self.assertFalse(ok, "a crashing step must reach the review gate")
        self.assertIn("augment", note)

    def test_a_per_chapter_failure_is_reported_even_when_later_chapters_pass(self):
        # The gate scans every row rather than the per-step summary, so it was never
        # subject to the collapse `last_by_step` had — pinned here because the two read
        # the same records and a future consolidation must not lose this property.
        record_step(self.book, phase="per-chapter", step="build", outcome="failed", evidence={"chapter": "ch03"})
        for n in range(4, 21):
            record_step(self.book, phase="per-chapter", step="build", outcome="ok", evidence={"chapter": f"ch{n:02d}"})
        ok, note = pr.gate_no_step_failed(self.book)
        self.assertFalse(ok)
        self.assertIn("build", note)

    def test_repaid_windows_gate_distinguishes_cache_from_recompute(self):
        record_step(self.book, phase="0b", step="win-001", outcome="noop", evidence={"why": "cache hit"})
        record_step(self.book, phase="0b", step="win-002", outcome="ok", evidence={"why": "computed"})
        ok, note = pr.gate_windows_not_repaid(self.book)
        self.assertTrue(ok)
        self.assertIn("from cache", note)
        self.assertIn("recomputed", note)


class CrossPhaseRecheckTests(_BookFixture):
    """The point of the recheck tier: a LATER phase catches an EARLIER phase's defect."""

    def test_compose_review_rechecks_earlier_phases(self):
        report = pr.review_phase(self.book, "0book-compose")
        kinds = {g["kind"] for g in report["gates"]}
        self.assertIn("recheck", kinds)
        names = " ".join(g["name"] for g in report["gates"])
        for earlier in ("from 0a", "from 0b", "from 0d", "from 0book-design"):
            self.assertIn(earlier, names, f"compose did not re-verify {earlier}")

    def test_a_broken_0a_artifact_is_caught_at_the_compose_checkpoint(self):
        # This is the snag-list request made concrete: 0a already "passed", and its
        # work is broken later. The compose review must name it.
        (self.text / "raw-extract.md").unlink()
        report = pr.review_phase(self.book, "0book-compose")
        failed = [g for g in report["gates"] if g["passed"] is False]
        self.assertTrue(
            any("0a" in g["name"] for g in failed),
            f"compose did not report the broken 0a artifact; failures were {[g['name'] for g in failed]}",
        )
        self.assertEqual(report["verdict"], pr.VERDICT_CONCERNS)

    def test_an_early_phase_does_not_recheck_later_ones(self):
        report = pr.review_phase(self.book, "0b")
        names = " ".join(g["name"] for g in report["gates"])
        self.assertNotIn("from 0d", names, "0b must not re-verify a phase that has not run")
        self.assertNotIn("from 0book-design", names)

    def test_a_phase_does_not_recheck_itself(self):
        report = pr.review_phase(self.book, "0b")
        self.assertNotIn("from 0b", " ".join(g["name"] for g in report["gates"]))


class CalibrationTests(_BookFixture):
    """The two rules that took the 2026-08-08 sweep from 162 failures to 8.

    Both exist because a review nobody can read is worse than none: of 162 raw gate
    failures across 23 books, 4 were real. 95 were rechecks of phases the book never
    ran (every route skips something — a `source-ready` book never does OCR), and 22
    were volumes of a nested series being asked for a scan they are not supposed to own.
    """

    def _with_state(self, **phase_status: str) -> None:
        from _progress import initial_state, write_state

        state = initial_state("test-book", "books")
        for phase, status in phase_status.items():
            state["phases"][phase] = {"status": status}
        write_state(self.book, state)

    def test_a_recheck_is_skipped_when_its_phase_never_completed(self):
        self._with_state(**{"0a": "skipped", "0b": "completed"})
        (self.text / "raw-extract.md").unlink()  # 0a's artifact, but 0a never ran
        report = pr.review_phase(self.book, "0d")
        names = " ".join(g["name"] for g in report["gates"])
        self.assertNotIn(
            "from 0a",
            names,
            "a phase that never completed was re-verified — this is the 95-failure noise",
        )

    def test_a_recheck_still_runs_for_a_phase_that_did_complete(self):
        self._with_state(**{"0a": "completed", "0b": "completed"})
        (self.text / "raw-extract.md").unlink()
        report = pr.review_phase(self.book, "0d")
        failed = [g for g in report["gates"] if g["passed"] is False]
        self.assertTrue(
            any("from 0a" in g["name"] for g in failed),
            "a completed phase's broken artifact must still be caught — the filter must "
            "not have suppressed real findings along with the noise",
        )

    def test_no_state_file_means_check_everything(self):
        # "Cannot tell" must never be the quiet path: a standalone review over a book
        # with no orchestrator state must still report rather than silently pass.
        (self.text / "raw-extract.md").unlink()
        report = pr.review_phase(self.book, "0book-compose")
        self.assertTrue(
            any("from 0a" in g["name"] for g in report["gates"]),
            "with no state file every recheck should run",
        )

    def test_an_unreadable_state_file_means_check_everything(self):
        (self.book / "_system" / "orchestrator-state.json").write_text("{ not json", encoding="utf-8")
        (self.text / "raw-extract.md").unlink()
        report = pr.review_phase(self.book, "0book-compose")
        self.assertTrue(any("from 0a" in g["name"] for g in report["gates"]))

    def test_a_volume_declaring_a_content_range_is_not_asked_for_its_own_scan(self):
        # asaas-al-taveel/vol-0N: all six carry content-range.md.
        (self.text / "raw-extract.md").unlink()
        (self.text / "content-range.md").write_text("body_starts_at_page: 76\n", encoding="utf-8")
        ok, note = pr.gate_source_text_present(self.book)
        self.assertTrue(ok, note)
        self.assertIn("container", note)

    def test_a_volume_with_sibling_volumes_is_not_asked_for_its_own_scan(self):
        # al-anwaar-al-lateefah/vol-0N: NO content-range.md, so the structural signal is
        # what catches them. Missing this is why the first calibration attempt only
        # fixed half the volumes.
        series = Path(self._td.name) / "series"
        for n in (1, 2, 3):
            (series / f"vol-{n:02d}" / "_system" / "source" / "text").mkdir(parents=True)
        vol = series / "vol-01"
        (vol / "_system" / "source" / "text" / "refined-english.md").write_text("prose", encoding="utf-8")
        ok, note = pr.gate_source_text_present(vol)
        self.assertTrue(ok, note)
        self.assertIn("container", note)

    def test_a_lone_vol_directory_is_still_asked_for_its_scan(self):
        # Requiring SIBLINGS is what stops the structural signal firing on a
        # coincidentally-named folder and excusing a genuinely missing scan.
        lone = Path(self._td.name) / "solo" / "vol-01"
        (lone / "_system" / "source" / "text").mkdir(parents=True)
        ok, note = pr.gate_source_text_present(lone)
        self.assertFalse(ok, note)

    def test_a_normal_book_missing_its_scan_still_fails(self):
        # The calibration must not have turned the gate off for ordinary books.
        (self.text / "raw-extract.md").unlink()
        ok, note = pr.gate_source_text_present(self.book)
        self.assertFalse(ok, note)
        self.assertIn("missing", note)


class VerdictAndBlockingTests(_BookFixture):
    def test_a_sound_book_reports_sound(self):
        self.assertEqual(pr.review_phase(self.book, "0b")["verdict"], pr.VERDICT_SOUND)

    def test_a_failing_advisory_gate_yields_concerns_not_broken(self):
        (self.text / "refined-english.md").unlink()
        report = pr.review_phase(self.book, "0b")
        self.assertEqual(report["verdict"], pr.VERDICT_CONCERNS)
        self.assertIsNone(report["blocking_fail"], "an advisory gate must never block")

    def test_a_failing_blocking_gate_yields_broken(self):
        with mock.patch.dict(pr.OWN_GATES, {"0b": [("PC3", "forced", lambda _bd: (False, "forced failure"))]}):
            report = pr.review_phase(self.book, "0b")
        self.assertEqual(report["verdict"], pr.VERDICT_BROKEN)
        self.assertIn("forced failure", report["blocking_fail"])

    def test_only_declared_gates_can_block(self):
        self.assertEqual(
            pr.BLOCKING_GATES, frozenset({"PC3"}), "widening this set is a deliberate decision, not a drift"
        )


class RobustnessTests(_BookFixture):
    def test_a_crashing_gate_is_recorded_as_neither_pass_nor_omission(self):
        def _boom(_bd):
            raise RuntimeError("gate exploded")

        with mock.patch.dict(pr.OWN_GATES, {"0b": [("PX1", "explodes", _boom)]}):
            report = pr.review_phase(self.book, "0b")
        crashed = [g for g in report["gates"] if g["passed"] is None]
        self.assertEqual(len(crashed), 1)
        self.assertIn("gate crashed", crashed[0]["note"])
        self.assertEqual(report["verdict"], pr.VERDICT_CONCERNS, "a crashed gate must not read as sound")

    def test_review_never_raises_on_an_unknown_phase(self):
        report = pr.review_phase(self.book, "not-a-real-phase")
        self.assertEqual(report["phase"], "not-a-real-phase")

    def test_the_report_is_written_to_disk(self):
        pr.review_phase(self.book, "0b")
        path = self.book / "_system" / "phase-reviews" / "0b.json"
        self.assertTrue(path.exists())
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["phase"], "0b")

    def test_review_and_record_writes_a_summary_into_state(self):
        from _progress import initial_state, read_state, write_state

        write_state(self.book, initial_state("test-book", "books"))
        pr.review_and_record(self.book, "0b")
        block = read_state(self.book)["phases"]["0b"]
        self.assertIn("review", block)
        self.assertEqual(block["review"]["verdict"], pr.VERDICT_SOUND)

    def test_review_without_state_does_not_raise(self):
        # A review can run before the state file exists (a standalone apparatus run).
        pr.review_and_record(self.book, "0b")


if __name__ == "__main__":
    unittest.main()
