"""tests/test_cross_book_dashboard.py — fleet view reports what is on disk.

Regression cover for two bugs that survived the type-first content migration
(content/<Bucket>/<slug> with a `status` field, replacing content/drafts/ and
content/published/books/):

  - collect_fleet derived its column from `stage == "drafts"`, comparing the
    per-book publication status that iter_content yields against a retired
    FOLDER name. Nothing matched, so every book — draft or published — was
    labelled "published".
  - render_markdown counted the summary lines by filtering for "in-flight" and
    "shipped", labels collect_fleet has never emitted, so both totals read 0
    regardless of the fleet.

Neither showed up as a crash; the dashboard printed a confident, wrong answer.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

import cross_book_dashboard as cbd  # noqa: E402


def _make_book(root: Path, bucket: str, slug: str, *, status: str, phase: str = "0a") -> Path:
    book = root / bucket / slug
    (book / "_system").mkdir(parents=True)
    (book / "_system" / "orchestrator-state.json").write_text(
        json.dumps(
            {
                "phase": phase,
                "phase_status": "pending",
                "last_completed_phase": None,
                "status": status,
            }
        ),
        encoding="utf-8",
    )
    return book


class TestCollectFleetPublicationStatus(unittest.TestCase):
    """The publication column must echo iter_content's per-book status."""

    def _fleet_for(self, entries):
        with mock.patch.object(cbd, "iter_content", return_value=iter(entries)):
            return cbd.collect_fleet(None)

    def test_draft_and_published_are_reported_distinctly(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            draft = _make_book(root, "Islamic", "a-draft-book", status="draft")
            published = _make_book(root, "Islamic", "a-published-book", status="published")
            fleet = self._fleet_for(
                [
                    ("draft", "Islamic", draft),
                    ("published", "Islamic", published),
                ]
            )

        by_slug = {b["book"]: b for b in fleet}
        self.assertEqual(by_slug["a-draft-book"]["publication_status"], "draft")
        self.assertEqual(by_slug["a-published-book"]["publication_status"], "published")

    def test_bucket_is_carried_through(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            guide = _make_book(root, "Guides", "a-guide", status="draft")
            fleet = self._fleet_for([("draft", "Guides", guide)])

        self.assertEqual(fleet[0]["bucket"], "Guides")

    def test_a_slug_seen_twice_is_counted_once(self):
        """The legacy fallback can yield the same slug from two trees."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            book = _make_book(root, "Islamic", "dupe", status="draft")
            fleet = self._fleet_for([("draft", "Islamic", book), ("draft", "Islamic", book)])

        self.assertEqual(len(fleet), 1)


class TestRenderMarkdownSummary(unittest.TestCase):
    """The two summary lines must count the fleet they are handed."""

    FLEET = [
        {
            "book": "one",
            "bucket": "Islamic",
            "publication_status": "draft",
            "phase": "0a",
            "status": "pending",
            "last_completed": "—",
            "chapters": "0/0",
            "ch_mean_time": "—",
            "cost_usd": 1.5,
            "ledger_rows": 2,
            "last_cost_ts": None,
        },
        {
            "book": "two",
            "bucket": "Guides",
            "publication_status": "published",
            "phase": "done",
            "status": "shipped",
            "last_completed": "done",
            "chapters": "3/3",
            "ch_mean_time": "—",
            "cost_usd": 2.25,
            "ledger_rows": 4,
            "last_cost_ts": "2026-07-01T00:00:00Z",
        },
    ]

    def test_counts_are_not_always_zero(self):
        md = cbd.render_markdown(self.FLEET, "all-time")
        self.assertIn("- **Draft books**: 1 (one)", md)
        self.assertIn("- **Published books**: 1 (two)", md)

    def test_every_row_carries_bucket_and_publication_status(self):
        md = cbd.render_markdown(self.FLEET, "all-time")
        self.assertIn("| `one` | Islamic | draft |", md)
        self.assertIn("| `two` | Guides | published |", md)

    def test_header_and_rows_have_matching_column_counts(self):
        md = cbd.render_markdown(self.FLEET, "all-time")
        rows = [ln for ln in md.splitlines() if ln.startswith("|")]
        widths = {ln.count("|") for ln in rows}
        self.assertEqual(len(widths), 1, f"ragged table: column counts {widths}")

    def test_total_sums_the_cost_column(self):
        md = cbd.render_markdown(self.FLEET, "all-time")
        self.assertIn("**$3.75**", md)


if __name__ == "__main__":
    unittest.main()
