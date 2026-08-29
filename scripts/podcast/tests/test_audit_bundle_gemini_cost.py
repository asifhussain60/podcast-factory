"""Tests for audit_bundle_gemini.py's cost-ledger wiring.

Regression coverage for a repo-surgeon AU-S3 finding: this script's Gemini
call (the per-chapter "two-model audit gate") never reached the orchestrator
state's cost dict, unlike every other direct Gemini caller in the repo.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest import mock

_SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_PODCAST) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_PODCAST))

import audit_bundle_gemini as abg  # noqa: E402


class TestBookDirFromBundle:
    def test_resolves_book_dir_from_real_bundle_layout(self, tmp_path):
        book_dir = tmp_path / "some-book"
        bundle_dir = book_dir / "_system" / "episode-drafts" / "EP01-opening"
        bundle_dir.mkdir(parents=True)
        assert abg._book_dir_from_bundle(bundle_dir) == book_dir

    def test_returns_none_for_none_input(self):
        assert abg._book_dir_from_bundle(None) is None

    def test_returns_none_when_layout_does_not_match(self, tmp_path):
        # A --packed invocation has no bundle_dir at all, and an arbitrary
        # directory three levels up with no _system/ isn't a book either.
        loose = tmp_path / "a" / "b" / "c"
        loose.mkdir(parents=True)
        assert abg._book_dir_from_bundle(loose) is None


class TestRecordCost:
    def test_appends_to_the_real_cost_ledger(self, tmp_path):
        book_dir = tmp_path / "some-book"
        (book_dir / "_system").mkdir(parents=True)
        abg._record_cost(book_dir, model="gemini-2.5-pro", in_chars=1000, out_chars=200)
        ledger = book_dir / "_system" / "cost-ledger.jsonl"
        assert ledger.exists()
        row = json.loads(ledger.read_text(encoding="utf-8").strip())
        assert row["model"] == "gemini-2.5-pro"
        assert row["input_tokens"] == 1000
        assert row["output_tokens"] == 200
        assert row["cost_usd"] > 0

    def test_none_book_dir_is_a_noop(self, tmp_path):
        # --packed with no resolvable book_dir: cost tracking is skipped,
        # never an error that would lose a finished audit.
        abg._record_cost(None, model="gemini-2.5-pro", in_chars=1000, out_chars=200)

    def test_ledger_failure_never_raises(self, tmp_path, capsys):
        book_dir = tmp_path / "some-book"
        (book_dir / "_system").mkdir(parents=True)
        with mock.patch("_cost_ledger.append_gemini_cost", side_effect=RuntimeError("disk full")):
            abg._record_cost(book_dir, model="gemini-2.5-pro", in_chars=1000, out_chars=200)
        assert "WARN" in capsys.readouterr().err
