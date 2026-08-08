#!/usr/bin/env python3
"""There is ONE cost ledger, and it is the one the spend ceiling reads.

Five standalone tools — augment, denoise, slide decks, reconcile, segment — each kept
a private `_system/cost-ledger.json`: a dict with its own `total_usd`, written by five
byte-identical copies of the same `_log_cost`. Nothing read it.
`cost_guard.real_spend_usd`, the status card and the cross-book dashboard all read
`cost-ledger.jsonl`, so real Gemini and metered-Anthropic spend recorded in the other
file counted toward no ceiling and appeared in no report.

No `cost-ledger.json` exists on any of the 23 books in the repo, so this closed a trap
rather than recovering lost money — and a trap is exactly what wants a test, because
the next person to add a Gemini tool will copy one of these five files.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from _tool_cost import append_precomputed_cost  # noqa: E402
from cost_guard import real_spend_usd  # noqa: E402

#: The tools that used to keep their own ledger.
STANDALONE_TOOLS = (
    "augment_book.py",
    "full_book_denoise.py",
    "generate_slide_decks.py",
    "reconcile_book.py",
    "segment_book.py",
)


class NoSecondLedgerTests(unittest.TestCase):
    def test_nothing_writes_the_dict_shaped_ledger_any_more(self) -> None:
        offenders = [
            str(py.relative_to(SCRIPTS_PODCAST))
            for py in sorted(SCRIPTS_PODCAST.rglob("*.py"))
            if "tests" not in py.relative_to(SCRIPTS_PODCAST).parts
            and '"cost-ledger.json"' in py.read_text(encoding="utf-8")
        ]
        self.assertFalse(
            offenders,
            "a second cost ledger is back; spend written there reaches no ceiling and no report: "
            + ", ".join(offenders),
        )

    def test_each_standalone_tool_routes_through_the_canonical_writer(self) -> None:
        for tool in STANDALONE_TOOLS:
            text = (SCRIPTS_PODCAST / tool).read_text(encoding="utf-8")
            self.assertIn("append_tool_cost", text, f"{tool} no longer records through _cost_ledger")

    def test_the_entry_mapping_exists_in_exactly_one_place(self) -> None:
        # Five copies of the mapping is what let the private ledger survive. The DR-005
        # line gate caught the first version of this fix duplicating the explanation
        # five times instead — the same mistake one level up.
        copies = [t for t in STANDALONE_TOOLS if 'entry.get("op")' in (SCRIPTS_PODCAST / t).read_text(encoding="utf-8")]
        self.assertFalse(copies, f"these tools map the entry dict themselves instead of delegating: {copies}")

    def test_the_five_tools_no_longer_keep_their_own_total(self) -> None:
        # `total_usd` was each copy's own running sum, and each tool's `main()` read it
        # back to print "Running total cost". Summing is the reader's job now
        # (`cost_guard.real_spend_usd`, which counts only rows billed as real money);
        # a tool keeping its own total is the split ledger returning by the back door.
        #
        # Matched on the two CODE shapes the old version used, not on the bare word:
        # the replacement docstrings explain what `total_usd` was, and augment_book
        # legitimately writes a `total_cost_usd` into its own augmentation ledger,
        # which is a different file. assertFalse, not assertNotIn — the latter prints
        # the entire source file on failure.
        offenders = [
            t
            for t in STANDALONE_TOOLS
            for src in [(SCRIPTS_PODCAST / t).read_text(encoding="utf-8")]
            if '["total_usd"]' in src or 'get("total_usd"' in src
        ]
        self.assertFalse(offenders, f"these tools still maintain their own total: {offenders}")

    def test_each_tool_reports_its_running_total_from_the_canonical_reader(self) -> None:
        for tool in STANDALONE_TOOLS:
            text = (SCRIPTS_PODCAST / tool).read_text(encoding="utf-8")
            self.assertIn("real_spend_usd", text, f"{tool} reports a total it computes itself")


class SpendReachesTheCeilingTests(unittest.TestCase):
    """The property that matters: money recorded is money the ceiling can see."""

    def test_a_recorded_row_shows_up_as_real_spend(self) -> None:
        with TemporaryDirectory() as td:
            book = Path(td) / "a-book"
            (book / "_system").mkdir(parents=True)
            append_precomputed_cost(
                book,
                phase="standalone",
                step="augment_book",
                model="gemini/gemini-2.5-flash",
                cost_usd=1.25,
                in_units=1000,
                out_units=2000,
            )
            self.assertAlmostEqual(real_spend_usd(book), 1.25, places=4)

    def test_rows_append_rather_than_replace(self) -> None:
        with TemporaryDirectory() as td:
            book = Path(td) / "a-book"
            (book / "_system").mkdir(parents=True)
            for _ in range(3):
                append_precomputed_cost(book, phase="standalone", step="denoise", model="gemini/x", cost_usd=0.5)
            lines = (book / "_system" / "cost-ledger.jsonl").read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 3)
            self.assertAlmostEqual(real_spend_usd(book), 1.5, places=4)

    def test_the_row_records_real_money_not_flat_rate(self) -> None:
        # `engine` decides whether a row is real spend or notional Max usage. These
        # tools call metered Gemini and the metered Anthropic SDK, so "api" is right —
        # defaulting to "max" would make every one of them free in the report.
        with TemporaryDirectory() as td:
            book = Path(td) / "a-book"
            (book / "_system").mkdir(parents=True)
            append_precomputed_cost(book, phase="standalone", step="s", model="m", cost_usd=2.0)
            row = json.loads((book / "_system" / "cost-ledger.jsonl").read_text(encoding="utf-8").strip())
            self.assertEqual(row["engine"], "api")
            self.assertEqual(row["cost_usd"], 2.0)


if __name__ == "__main__":
    unittest.main()
