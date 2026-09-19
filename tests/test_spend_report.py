"""Spend must be visible, and an unpriced row must not pose as a free one.

The 2026-09 history showed six spend-leak fixes in eight weeks with nothing watching spend, and 91 opus-4-7 plus 6
sonnet-4-6 API rows logged at $0 because the model had no price on file. Flat-rate ("max" engine) work is
notional and is reported separately from money that was really charged.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import spend_report as sr  # noqa: E402

NOW = dt.datetime(2026, 9, 19, tzinfo=dt.timezone.utc)


def _row(**kw):
    base = {
        "ts": "2026-09-15T00:00:00Z",
        "phase": "p",
        "step": "s",
        "model": "claude-opus-4-8",
        "engine": "api",
        "input_tokens": 1000,
        "output_tokens": 500,
        "cost_usd": 1.5,
    }
    base.update(kw)
    return base


def _repo(tmp_path, books):
    for slug, rows in books.items():
        d = tmp_path / "content" / "Islamic" / slug / "_system"
        d.mkdir(parents=True)
        (d / "cost-ledger.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return tmp_path


def test_real_money_and_flat_rate_work_are_reported_separately(tmp_path):
    root = _repo(tmp_path, {"a": [_row(cost_usd=2.0), _row(engine="max", cost_usd=99.0)]})
    rep = sr.summarise(root, now=NOW, days=30)
    assert rep["real_usd"] == 2.0 and rep["notional_usd"] == 99.0


def test_an_api_row_with_tokens_but_no_price_is_flagged_not_counted_as_free(tmp_path):
    root = _repo(
        tmp_path,
        {"a": [_row(model="claude-opus-4-7", cost_usd=0.0), _row(model="claude-opus-4-7", cost_usd=0.0, priced=False)]},
    )
    rep = sr.summarise(root, now=NOW, days=30)
    assert rep["unpriced_rows"] == 2
    assert rep["unpriced_models"] == {"claude-opus-4-7": 2}


def test_flat_rate_zero_cost_rows_are_not_unpriced(tmp_path):
    root = _repo(tmp_path, {"a": [_row(engine="max", cost_usd=0.0)]})
    assert sr.summarise(root, now=NOW, days=30)["unpriced_rows"] == 0


def test_only_the_requested_window_is_counted(tmp_path):
    root = _repo(
        tmp_path, {"a": [_row(ts="2026-09-18T00:00:00Z", cost_usd=1.0), _row(ts="2026-06-01T00:00:00Z", cost_usd=50.0)]}
    )
    assert sr.summarise(root, now=NOW, days=7)["real_usd"] == 1.0
    assert sr.summarise(root, now=NOW, days=365)["real_usd"] == 51.0


def test_books_are_ranked_by_real_spend(tmp_path):
    root = _repo(tmp_path, {"cheap": [_row(cost_usd=1.0)], "dear": [_row(cost_usd=9.0)]})
    assert [b for b, _ in sr.summarise(root, now=NOW, days=30)["by_book"]] == ["dear", "cheap"]


def test_archived_books_and_garbled_lines_are_ignored(tmp_path):
    root = _repo(tmp_path, {"a": [_row(cost_usd=1.0)]})
    arch = root / "content" / "_archive" / "old" / "_system"
    arch.mkdir(parents=True)
    (arch / "cost-ledger.jsonl").write_text(json.dumps(_row(cost_usd=1000.0)) + "\n")
    (root / "content" / "Islamic" / "a" / "_system" / "cost-ledger.jsonl").open("a").write("not json\n")
    assert sr.summarise(root, now=NOW, days=30)["real_usd"] == 1.0


def test_an_empty_repo_reports_zeroes_not_an_error(tmp_path):
    rep = sr.summarise(tmp_path, now=NOW, days=30)
    assert rep["real_usd"] == 0 and rep["by_book"] == []


def test_the_text_report_leads_with_the_things_that_need_attention(tmp_path):
    root = _repo(tmp_path, {"a": [_row(model="claude-opus-4-7", cost_usd=0.0)]})
    text = sr.render(sr.summarise(root, now=NOW, days=30))
    assert "UNPRICED" in text and "claude-opus-4-7" in text
