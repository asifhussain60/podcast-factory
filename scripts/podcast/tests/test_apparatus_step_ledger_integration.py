#!/usr/bin/env python3
"""Every apparatus step leaves a ledger record in a REAL `apply_book_apparatus` run.

`test_step_ledger.py` pins the ledger's mechanics and proves, by reading the
source, that each step has both an `_ok` and a `_record_skip` site. That is a
placement check: it cannot tell whether a record is actually written when the
function runs, which is the property a review gate depends on.

This test runs the real sequence over a synthetic book and asserts that all
twenty-five declared steps appear in the ledger. Steps are allowed to FAIL here —
a synthetic book has no glossary, no source scan and no OCR — because the
assertion is about the RECORD existing, not about the step succeeding. A step
that silently wrote nothing is exactly what this catches.

WHY THE PATCHES

  Six steps either call a model or shell out to one, so an unpatched run costs
  real money and can hang: the glossary fill subprocess carries `timeout=900`,
  and an unstubbed run of this sequence hit that during development. Each is
  replaced by a stub that does nothing, so the sequence still executes end to end
  while spending nothing. They are patched in their DEFINING modules because
  `_book_apparatus` imports them inside the function body, so a patch on the
  apparatus module's namespace would never be seen.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from _book_apparatus import APPARATUS_STEPS, apply_book_apparatus
from _step_ledger import last_by_step, outcome_counts, read_steps

#: (module, attribute) pairs replaced with no-ops for the duration of the run.
#: Everything here either invokes a model directly or spawns something that does.
PAID_OR_SLOW = (
    ("_book_frontmatter", "apply_introduction"),  # one claude -p per book
    ("_annotation_policy", "propose_annotation_policy"),  # model judgment
    ("_etymology", "build_etymology_atoms"),  # two claude -p calls
    ("vowel_glossary", "vowel_glossary"),  # Gemini
    ("vowel_book", "vowel_book"),  # Gemini
    ("harvest_gloss_terms", "apply"),  # its result gates a subprocess model call
)


class ApparatusLedgerIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self.book = Path(self._td.name) / "synthetic-book"
        (self.book / "_system").mkdir(parents=True)
        (self.book / "book").mkdir(parents=True)
        (self.book / "book" / "book.md").write_text(
            "# Synthetic Book\n\n## Chapter One\n\nSome prose about the ranks (hudud).\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self._td.cleanup()

    def _run_apparatus(self) -> None:
        with ExitStack() as stack:
            for mod_name, attr in PAID_OR_SLOW:
                mod = __import__(mod_name)
                stack.enter_context(mock.patch.object(mod, attr, lambda *a, **k: None))
            # The harvest itself is deterministic and free, but its RESULT gates a
            # subprocess model call, so force it to report nothing added.
            import harvest_gloss_terms as hgt

            stack.enter_context(
                mock.patch.object(hgt, "harvest", lambda *a, **k: {"candidates": 0, "known": 0, "terms": []})
            )
            try:
                apply_book_apparatus(self.book, log=lambda m: None)
            except Exception:
                # A synthetic book legitimately breaks steps that need real inputs.
                # The sequence is instrumented per step, so records survive either
                # way — and that is what is under test.
                pass

    def test_every_declared_step_leaves_a_record(self):
        self._run_apparatus()
        recorded = set(last_by_step(read_steps(self.book)))
        missing = [s for s in APPARATUS_STEPS if s not in recorded]
        self.assertEqual(
            missing,
            [],
            f"these steps ran without leaving any ledger record: {missing} — a review "
            f"gate cannot distinguish them from steps that were never reached",
        )

    def test_records_carry_a_phase_and_an_outcome(self):
        self._run_apparatus()
        rows = read_steps(self.book)
        self.assertTrue(rows, "the apparatus recorded nothing at all")
        for row in rows:
            self.assertEqual(row.get("phase"), "0book-compose")
            self.assertIn(row.get("outcome"), {"ok", "noop", "skipped", "failed"})

    def test_a_failing_step_records_its_error(self):
        # The failure is INJECTED rather than assumed. A synthetic book turned out
        # to break nothing — every apparatus step degrades cleanly on missing
        # inputs, which is worth knowing but leaves the failure path unexercised.
        # Forcing one step to raise tests the path deterministically instead of
        # depending on a fixture staying broken.
        import _book_inline_arabic as bia

        with mock.patch.object(bia, "apply_inline_arabic", side_effect=RuntimeError("injected overlay failure")):
            self._run_apparatus()

        rows = read_steps(self.book)
        failed = [r for r in rows if r.get("outcome") == "failed"]
        self.assertEqual(
            [r["step"] for r in failed],
            ["inline-arabic"],
            "the injected failure should be the only one recorded",
        )
        self.assertIn("injected overlay failure", failed[0]["error"])

    def test_a_failing_step_does_not_stop_the_steps_after_it(self):
        # The apparatus is non-blocking by design — a broken overlay must never cost
        # a finished translation. So the ledger must still show the later steps.
        import _book_inline_arabic as bia

        with mock.patch.object(bia, "apply_inline_arabic", side_effect=RuntimeError("boom")):
            self._run_apparatus()

        recorded = set(last_by_step(read_steps(self.book)))
        later = APPARATUS_STEPS[APPARATUS_STEPS.index("inline-arabic") + 1 :]
        self.assertEqual(
            [s for s in later if s not in recorded],
            [],
            "a failure in one step suppressed the records of the steps after it",
        )

    def test_no_step_is_recorded_twice_in_one_run(self):
        self._run_apparatus()
        rows = read_steps(self.book)
        names = [r["step"] for r in rows]
        dupes = {n for n in names if names.count(n) > 1}
        self.assertEqual(
            dupes,
            set(),
            f"these steps recorded more than once in a single run: {dupes} — a gate "
            f"counting outcomes would double-count them",
        )

    def test_the_run_spent_nothing(self):
        # The cost ledger is the repo's own record of real money. A run of this test
        # must never create one: if it does, a paid step escaped PAID_OR_SLOW.
        self._run_apparatus()
        self.assertFalse(
            (self.book / "_system" / "cost-ledger.jsonl").exists(),
            "a paid step ran during this test — add it to PAID_OR_SLOW",
        )

    def test_outcome_counts_summarise_the_run(self):
        self._run_apparatus()
        counts = outcome_counts(read_steps(self.book))
        self.assertEqual(sum(counts.values()), len(read_steps(self.book)))


if __name__ == "__main__":
    unittest.main()
