#!/usr/bin/env python3
"""A window's model call can succeed and still break the pipeline.

Surah Al-Fateha's "The Stages Of Love" (2026-08-12): a 2,663-word window asked
for a rewording came back at 39,945 words — fifteen times its source — after
ten hours of a mostly-stalled run. Two things were true and both had to be
fixed:

  1. NOTHING checked for it. `revoice_gates` had an abridgement check (too
     SHORT) and no matching check for too LONG, so an order-of-magnitude
     runaway sailed straight past every fidelity gate.
  2. Whatever ran after the gates — on that oversized text — threw an
     exception that nothing in `_adapt_chapter_body` caught. It propagated
     past `_run_pass`, past `rearticulate()`, and was caught only by
     `articulate.py`'s own broad `except Exception`, which marked the WHOLE
     CHAPTER "failed" — not the one window that produced it.

The two fixes below are independent and this file pins both, plus the
combination: a chapter must never come out "failed" from an unforeseen
exception in the post-model-call path, whatever that exception turns out to
be. The second test constructs a candidate that passes the length gate but
still throws downstream, precisely so the file cannot rely only on catching
the specific bug that shipped — it proves the STRUCTURAL guarantee, not one
instance of it.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _book_voice import _adapt_chapter_body, revoice_gates  # noqa: E402

BASE = " ".join(f"word{i}" for i in range(600))  # ~600 words, mirrors a real window


# ---------------------------------------------------------------------------
# The gate: a runaway response is caught explicitly, with a reason
# ---------------------------------------------------------------------------


def test_a_fifteen_times_runaway_is_rejected() -> None:
    """The exact shape that shipped: real prose, repeated, far past any
    legitimate expansion from rebuilding grammar."""
    runaway = (BASE + " ") * 15
    findings = revoice_gates(BASE, runaway, frame="first_person_expository")
    assert findings
    assert "runaway" in findings[0]


def test_the_finding_names_the_actual_ratio() -> None:
    """A number a human can act on, not just a red flag."""
    findings = revoice_gates(BASE, (BASE + " ") * 4, frame="first_person_expository")
    assert "4.0x source" in findings[0]


def test_ordinary_expansion_from_rebuilt_grammar_is_not_flagged() -> None:
    """REQ-BA-020 licenses splitting sentences and unpacking dense clauses,
    which legitimately runs a bit longer than the source. The gate must not
    punish normal articulation for growing at all."""
    expanded = BASE + " " + " ".join(f"extra{i}" for i in range(300))  # 1.5x
    assert revoice_gates(BASE, expanded, frame="first_person_expository") == []


def test_a_runaway_is_caught_before_the_expensive_gates_ever_run(monkeypatch) -> None:
    """Checked and returned FIRST. The oversized text must never reach the
    doctrinal scan or the frame guards — the whole point is to stop paying
    for (and risking a crash in) checks over a quarter-million characters."""
    import _book_voice_gates as bvg

    def boom(*_a, **_kw):
        raise AssertionError("an expensive gate ran over the runaway text")

    monkeypatch.setattr(bvg, "teaching_loss_findings", boom)
    monkeypatch.setattr(bvg, "run_doctrinal_checks", boom)
    findings = revoice_gates(BASE, (BASE + " ") * 15, frame="first_person_expository")
    assert findings  # rejected, and boom() was never called


def test_short_base_texts_are_exempt_same_as_the_abridgement_check() -> None:
    """A one-line editorial aside legitimately reads longer once articulated.
    Mirrors the existing `base_words >= 8` floor on the abridgement gate."""
    assert revoice_gates("Yes.", "Yes, and here is a fuller elaboration of it.", frame="first_person_expository") == []


# ---------------------------------------------------------------------------
# The structural guarantee: nothing downstream can crash a whole chapter
# ---------------------------------------------------------------------------


def _adapter_returns(text: str):
    def fn(title, window, book_dir, label, log, *, previous_tail="", frame="", narrator=""):
        return text

    return fn


def test_a_runaway_window_reverts_that_window_not_the_whole_chapter(tmp_path: Path) -> None:
    body = f"{BASE}\n\n{BASE}"  # two short "windows" via the normal split path
    new_body, record = _adapt_chapter_body(
        "T",
        body,
        tmp_path,
        "L",
        print,
        _adapter_returns((BASE + " ") * 15),
        noun="rearticulate",
        frame="first_person_expository",
    )
    assert record["status"] == "reverted"
    assert new_body.strip() == body.strip()  # exactly the original, nothing lost


def test_an_unforeseen_exception_after_a_valid_length_reverts_cleanly(tmp_path: Path, monkeypatch) -> None:
    """The general case, not just the length bug. A candidate that is a
    perfectly normal length still must not be able to crash the chapter if
    SOMETHING ELSE in the gate path throws — any future defect in any gate
    function degrades to a clean per-window revert, the same as this one did."""
    import _book_voice as bv

    def boom(*_a, **_kw):
        raise RuntimeError("simulated defect in some future gate")

    monkeypatch.setattr(bv, "revoice_gates", boom)
    new_body, record = _adapt_chapter_body(
        "T",
        BASE,
        tmp_path,
        "L",
        print,
        _adapter_returns(BASE + " a bit more."),
        noun="rearticulate",
        frame="first_person_expository",
    )
    assert record["status"] == "reverted"
    assert new_body.strip() == BASE.strip()
    assert any("gate check raised" in g for g in record["gates"])


def test_a_multi_window_chapter_survives_one_bad_window(tmp_path: Path, monkeypatch) -> None:
    """The real failure mode: chapter has several windows, one of them breaks
    downstream, the OTHERS must still be judged and kept on their own merits."""
    import _book_voice as bv

    real_gates = bv.revoice_gates
    calls = {"n": 0}

    def flaky(base, candidate, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom on the first window only")
        return real_gates(base, candidate, **kw)

    monkeypatch.setattr(bv, "revoice_gates", flaky)
    # Long enough to actually split into multiple windows (>_LONG_CHAPTER_WORDS,
    # 4,000) — two 2,700-word paragraphs, mirroring a real dense chapter.
    long_para = " ".join(f"word{i}" for i in range(2700))
    body = f"{long_para}\n\n{long_para.replace('word', 'term')}"
    kept_candidate = long_para + " a bit more, said plainly."
    new_body, record = _adapt_chapter_body(
        "T",
        body,
        tmp_path,
        "L",
        print,
        _adapter_returns(kept_candidate),
        noun="rearticulate",
        frame="first_person_expository",
    )
    assert record["windows"] >= 2
    assert record["status"] == "partial"
    assert record["windows_kept"] == record["windows"] - 1


# ---------------------------------------------------------------------------
# End to end, at the level the bug actually surfaced: articulate.py
# ---------------------------------------------------------------------------


def test_the_lane_driver_never_reports_failed_for_a_gate_side_exception(tmp_path: Path, monkeypatch) -> None:
    """The original bug, reproduced at the layer Asif actually saw it: the
    ledger read `failed` — a Python exception — for a chapter whose model
    call had succeeded. After this fix the same scenario reverts, and
    `articulate.py`'s own except-Exception path is never reached."""
    import json

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from _book_edits import anchor_key
    from sessions import articulate as art

    book_dir = tmp_path / "book"
    (book_dir / "book").mkdir(parents=True)
    (book_dir / "_system").mkdir()
    md = f"# S\n\n## Introduction to the Book\n\nApparatus.\n\n## A Chapter\n\n{BASE}\n"
    (book_dir / "book" / "book.md").write_text(md, encoding="utf-8")

    import rearticulate_chapter as rc

    monkeypatch.setattr(rc, "_adapter", _adapter_returns((BASE + " ") * 15))
    summary = art.articulate_book(book_dir, engine="claude", log=lambda *_: None)
    assert summary["failed"] == []
    assert summary["reverted"] == 1
    ledger = json.loads((book_dir / "_system" / "sessions-articulation.json").read_text())
    assert ledger["chapters"][anchor_key("A Chapter")]["status"] == "reverted"
