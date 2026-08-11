#!/usr/bin/env python3
"""The one repair in `pf-compose-fix` that spends money must say what it spent.

The defect this pins was found on 2026-08-11, by reading Love Of The Prophet's own
ledgers after the book finished rather than by any failure. `vowel_chapters` called
`vowel_book.vowel_text` directly and never called `vowel_book.record_spend`, which sits
one import away and exists precisely because the same omission had already been fixed
once on the whole-book path. The result: a pass making metered Gemini calls was absent
from `cost-ledger.jsonl` and `model-provenance.jsonl` both, and wrote no
`book-vowelling.json`, so neither what it cost nor what it refused could be read back.

Two properties, and the second is the one that bites:

  THE LEDGERS ARE WRITTEN BEFORE THE NO-CHANGE CHECK. A chapter whose runs the gate
  refuses outright leaves the prose byte-identical — and it still cost a model call, and
  its refusals are the ones a person most needs to see. Recording after the check would
  make exactly the interesting case invisible.

  THE REPORT SAYS WHAT IT COVERED. This writes the same file the whole-book pass writes,
  so `scope` is what tells a reader the difference between "these two chapters" and "the
  book".
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts" / "podcast"))

import vowel_book  # noqa: E402
from _compose_fix_vowel import vowel_chapters  # noqa: E402

BOOK = "# Title\n\n## 1. One\n\nBody one.\n\n## 2. Two\n\nBody two.\n"


def _book(tmp_path: Path) -> Path:
    (tmp_path / "book").mkdir()
    (tmp_path / "_system").mkdir()
    (tmp_path / "book" / "book.md").write_text(BOOK, encoding="utf-8")
    return tmp_path


def _section_text(md: str, heading: str) -> tuple[int, int]:
    start = md.index(f"## {heading}")
    nxt = md.find("\n## ", start + 1)
    return start, len(md) if nxt == -1 else nxt + 1


SELECTION = [
    {"number": 1, "heading": "1. One", "key": "one"},
    {"number": 2, "heading": "2. Two", "key": "two"},
]


def _refuses_everything(text, **_kwargs):
    """What the engine returns when the gate turns every run away: the prose comes
    back untouched, and the stats carry the spend and the reasons."""
    return text, {
        "vowelled": 0,
        "refused": 1,
        "in_chars": 40,
        "out_chars": 60,
        "refusals": [{"run": "الطور", "reason": "skeleton changed"}],
    }


def test_a_chapter_that_changed_nothing_still_records_its_spend(tmp_path, monkeypatch) -> None:
    """The regression. Both chapters come back byte-identical, and both cost money."""
    book_dir = _book(tmp_path)
    monkeypatch.setattr(vowel_book, "vowel_text", _refuses_everything)

    result = vowel_chapters(book_dir, SELECTION, section_text=_section_text, log=lambda *_: None)

    assert result["chapters_changed"] == 0
    rows = [
        json.loads(line)
        for line in (book_dir / "_system" / "cost-ledger.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert [r["step"] for r in rows] == ["vowel/01", "vowel/02"]
    assert all(r["phase"] == "compose-fix" for r in rows)


def test_the_model_that_answered_is_named_in_the_provenance_ledger(tmp_path, monkeypatch) -> None:
    book_dir = _book(tmp_path)
    monkeypatch.setattr(vowel_book, "vowel_text", _refuses_everything)

    vowel_chapters(book_dir, SELECTION, section_text=_section_text, log=lambda *_: None)

    rows = [
        json.loads(line)
        for line in (book_dir / "_system" / "model-provenance.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 2
    assert all(r["model"] == vowel_book.MODEL for r in rows)


def test_the_refusals_are_written_where_the_whole_book_pass_writes_them(tmp_path, monkeypatch) -> None:
    """`book-vowelling.json` is what the plan's vowelling probe reads for a rejection
    rate. Absent, the probe cannot be satisfied however many books are run."""
    book_dir = _book(tmp_path)
    monkeypatch.setattr(vowel_book, "vowel_text", _refuses_everything)

    vowel_chapters(book_dir, SELECTION, section_text=_section_text, log=lambda *_: None)

    report = json.loads((book_dir / "_system" / "book-vowelling.json").read_text(encoding="utf-8"))
    assert report["refused"] == 2, "counters accumulate across the chapters touched"
    assert len(report["refusals"]) == 2, "every refusal is kept, not just the last chapter's"
    assert report["in_chars"] == 80


def test_the_report_names_the_chapters_it_covered(tmp_path, monkeypatch) -> None:
    """The whole-book pass writes this same file. `scope` is the only thing that says
    whether the numbers describe two chapters or twenty."""
    book_dir = _book(tmp_path)
    monkeypatch.setattr(vowel_book, "vowel_text", _refuses_everything)

    vowel_chapters(book_dir, SELECTION[:1], section_text=_section_text, log=lambda *_: None)

    report = json.loads((book_dir / "_system" / "book-vowelling.json").read_text(encoding="utf-8"))
    assert report["scope"] == ["1. One"]


def test_nothing_is_written_when_no_chapter_was_selected(tmp_path, monkeypatch) -> None:
    """An empty run must not overwrite a real report with zeroes."""
    book_dir = _book(tmp_path)
    prior = {"scope": [], "refused": 7}
    (book_dir / "_system" / "book-vowelling.json").write_text(json.dumps(prior), encoding="utf-8")
    monkeypatch.setattr(vowel_book, "vowel_text", _refuses_everything)

    vowel_chapters(book_dir, [], section_text=_section_text, log=lambda *_: None)

    kept = json.loads((book_dir / "_system" / "book-vowelling.json").read_text(encoding="utf-8"))
    assert kept == prior


@pytest.mark.parametrize("key", ["in_chars", "out_chars", "refused", "vowelled"])
def test_every_counter_the_engine_reports_survives_the_accumulation(tmp_path, monkeypatch, key) -> None:
    """`_COUNTERS` is a hand-written list beside a dict the engine owns. If the engine
    grows a counter and the list does not, the number silently stops being reported."""
    book_dir = _book(tmp_path)
    monkeypatch.setattr(vowel_book, "vowel_text", _refuses_everything)

    vowel_chapters(book_dir, SELECTION[:1], section_text=_section_text, log=lambda *_: None)

    report = json.loads((book_dir / "_system" / "book-vowelling.json").read_text(encoding="utf-8"))
    assert key in report
