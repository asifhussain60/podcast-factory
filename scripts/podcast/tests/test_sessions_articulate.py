#!/usr/bin/env python3
"""`sessions-articulate` was a step name with nothing behind it.

It sat in `LANE_STEPS` and in the phase vocabulary as "Refining the language", and
because `_write_state` marked every step at or before the one it finished, running
the ingest through the preface marked it complete purely by POSITION. Both Sessions
books reported that pass as done for weeks. No code had ever run it.

The tests here cover the two halves of the fix: the state file stops claiming it,
and there is now a driver that actually does it. The driver's model calls are
injected — nothing here spends anything — because what is worth pinning is the
bookkeeping around them: which chapters are selected, what is skipped on a resume,
and that an interrupted run does not re-pay for the chapters it finished.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sessions import articulate as art  # noqa: E402
from sessions.ingest import ARTICULATE_STEP, LANE_STEPS  # noqa: E402

BOOK = """# A Series

## Introduction to the Book

Apparatus, authored under the articulation register already.

## Love Based Religion

He spoke about love, and you should notice how the word turns.

## Need For Messengers

In the last session I talked about mercy.
"""


def envelope(status: str) -> dict:
    """What `rearticulate` ACTUALLY returns — the status envelope it writes to
    `rearticulate-status.json`, with the pass verdict NESTED under `record`.

    Every fake in this file returns this shape rather than a bare
    `{"status": ...}`, because a bare one is what let the first live run report
    five successful chapters as reverted: the driver read `.get("status")` off the
    envelope, got `None` for all five, and the tests agreed with it because they
    were asserting against the same wrong shape. `test_the_fake_matches_what_the_real_function_returns`
    is what stops that happening again.
    """
    return {
        "chapter_key": "k",
        "state": "done",
        "started_at": "2026-08-11T00:00:00+00:00",
        "finished_at": "2026-08-11T00:01:00+00:00",
        "record": {"title": "t", "status": status, "windows": 1, "windows_kept": 1},
    }


@pytest.fixture()
def book_dir(tmp_path: Path) -> Path:
    (tmp_path / "book").mkdir()
    (tmp_path / "_system").mkdir()
    (tmp_path / "book" / "book.md").write_text(BOOK, encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# What the pass is asked to do
# ---------------------------------------------------------------------------


def test_the_introduction_is_not_a_chapter(book_dir: Path) -> None:
    """It is apparatus: authored in the register already, with no source to be
    faithful to. The pass engine skips it, and the lane must not report touching
    what the engine passed through."""
    keys = art.chapter_keys(book_dir / "book" / "book.md")
    assert [title for _, title in keys] == ["Love Based Religion", "Need For Messengers"]


def test_the_introduction_key_comes_from_the_engine_not_a_second_copy(book_dir: Path) -> None:
    """Two answers to "which section is apparatus" would drift the first time
    either changed, and this module would claim work the engine never did."""
    from _book_voice import _INTRODUCTION_KEY
    from sessions.articulate import _INTRODUCTION_KEY as imported

    assert imported is _INTRODUCTION_KEY


def test_the_fake_matches_what_the_real_function_returns() -> None:
    """The fakes above stand in for `rearticulate`. If its return SHAPE changes,
    every test here goes on passing against a shape that no longer exists — which
    is not hypothetical: reading the verdict off the wrong level of this envelope
    counted five articulated chapters as reverted on the first live run, and the
    suite was green throughout. Pinned against the real function's own writer."""
    import inspect

    from rearticulate_chapter import rearticulate

    source = inspect.getsource(rearticulate)
    real_keys = {"chapter_key", "state", "started_at", "finished_at", "record"}
    for key in real_keys:
        assert f'"{key}"' in source, f"rearticulate no longer returns {key!r}"
    assert set(envelope("adapted")) == real_keys
    # And the verdict is nested, not top-level — the exact confusion that failed.
    assert "status" not in envelope("adapted")
    assert envelope("adapted")["record"]["status"] == "adapted"


# ---------------------------------------------------------------------------
# Resume
# ---------------------------------------------------------------------------


def test_a_composer_edit_is_not_the_resume_signal(book_dir: Path) -> None:
    """EVERY chapter of both Sessions books already carries one, written by the
    mechanical repairs (honorifics, verse cards, stray emphasis) that ran before
    this step existed. Reading edits as "already articulated" would skip all 29
    chapters and report a finished run."""
    (book_dir / "_system" / "composer-edits.json").write_text(
        json.dumps([{"chapter_key": "love based religion", "body_md": "x"}]), encoding="utf-8"
    )
    plan = art.articulate_book(book_dir, dry_run=True, log=lambda *_: None)
    assert plan["planned"] == 2


def test_a_chapter_this_lane_articulated_is_skipped(book_dir: Path) -> None:
    art._record(book_dir, "love based religion", "Love Based Religion", "adapted")
    plan = art.articulate_book(book_dir, dry_run=True, log=lambda *_: None)
    assert plan["planned"] == 1
    assert plan["skipped"] == 1


def test_force_re_runs_what_the_ledger_records(book_dir: Path) -> None:
    art._record(book_dir, "love based religion", "Love Based Religion", "adapted")
    plan = art.articulate_book(book_dir, dry_run=True, force=True, log=lambda *_: None)
    assert plan["planned"] == 2


@pytest.mark.parametrize("status", ["failed", "reverted", "unknown", "skipped"])
def test_only_a_KEPT_chapter_counts_as_done(book_dir: Path, status: str) -> None:
    """A crash is not a result, and neither is a revert: the gates threw the
    rewrite away and the base still stands, so that chapter is un-articulated
    prose in a book that would otherwise be reported complete. Anything but
    `adapted` is retried."""
    art._record(book_dir, "love based religion", "Love Based Religion", status)
    plan = art.articulate_book(book_dir, dry_run=True, log=lambda *_: None)
    assert plan["planned"] == 2


@pytest.mark.parametrize("status", ["adapted"])
def test_a_kept_chapter_is_not_paid_for_twice(book_dir: Path, status: str) -> None:
    art._record(book_dir, "love based religion", "Love Based Religion", status)
    plan = art.articulate_book(book_dir, dry_run=True, log=lambda *_: None)
    assert plan["planned"] == 1


def test_a_partial_chapter_is_retried_for_full_sessions_quality(book_dir: Path) -> None:
    """Partial means at least one stitched window fell back to source prose. That
    is safe, but it is not finished Sessions articulation."""
    art._record(book_dir, "love based religion", "Love Based Religion", "partial")
    plan = art.articulate_book(book_dir, dry_run=True, log=lambda *_: None)
    assert plan["planned"] == 2


def test_sessions_driver_does_not_install_partial_chapters(book_dir: Path, monkeypatch) -> None:
    seen: list[bool] = []

    def fake(_bd, _key, *, log=print, write_partial=True):
        seen.append(write_partial)
        return envelope("partial")

    monkeypatch.setattr(art, "rearticulate", fake)
    art.articulate_book(book_dir, limit=1, log=lambda *_: None)

    assert seen == [False]


def test_sessions_partial_leaves_book_text_untouched(book_dir: Path, monkeypatch) -> None:
    book_md = book_dir / "book" / "book.md"
    before = book_md.read_text(encoding="utf-8")
    monkeypatch.setattr(art, "rearticulate", lambda bd, key, log=print, **_kwargs: envelope("partial"))

    art.articulate_book(book_dir, limit=1, log=lambda *_: None)

    assert book_md.read_text(encoding="utf-8") == before


def test_the_ledger_is_written_per_chapter_not_at_the_end(book_dir: Path, monkeypatch) -> None:
    """A run interrupted at chapter 19 of 23 must not re-pay for the eighteen
    that succeeded, so the record lands as each one finishes."""
    seen: list[str] = []

    def fake(bd, key, log=print, **_kwargs):
        seen.append(key)
        if len(seen) == 2:
            raise RuntimeError("interrupted")
        return envelope("adapted")

    monkeypatch.setattr(art, "rearticulate", fake)
    art.articulate_book(book_dir, log=lambda *_: None)
    ledger = art.read_ledger(book_dir)["chapters"]
    assert ledger["love based religion"]["status"] == "adapted"
    assert ledger["need for messengers"]["status"] == "failed"


def test_one_bad_chapter_does_not_end_the_run(book_dir: Path, monkeypatch) -> None:
    def fake(bd, key, log=print, **_kwargs):
        if key == "love based religion":
            raise RuntimeError("model timeout")
        return envelope("adapted")

    monkeypatch.setattr(art, "rearticulate", fake)
    summary = art.articulate_book(book_dir, log=lambda *_: None)
    assert summary["adapted"] == 1
    assert [f["key"] for f in summary["failed"]] == ["love based religion"]


def test_each_chapter_records_elapsed_time_and_token_usage(book_dir: Path, monkeypatch) -> None:
    def fake(bd, key, log=print, **_kwargs):
        with (bd / "_system" / "cost-ledger.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "phase": "rearticulate",
                        "step": f"rearticulate-{key}",
                        "model": "claude-sonnet-4-6",
                        "input_tokens": 11,
                        "output_tokens": 22,
                        "cache_read": 33,
                        "cache_create": 44,
                        "cost_usd": 0.123456,
                    }
                )
                + "\n"
            )
        return envelope("adapted")

    monkeypatch.setattr(art, "rearticulate", fake)
    art.articulate_book(book_dir, limit=1, log=lambda *_: None)

    entry = art.read_ledger(book_dir)["chapters"]["love based religion"]
    assert entry["duration_seconds"] >= 0
    assert entry["started_at"]
    assert entry["finished_at"]
    assert entry["usage"]["input_tokens"] == 11
    assert entry["usage"]["output_tokens"] == 22
    assert entry["usage"]["cache_read"] == 33
    assert entry["usage"]["cache_create"] == 44
    assert entry["usage"]["total_tokens"] == 110
    assert entry["usage"]["cost_usd"] == 0.123456
    assert entry["usage"]["rows"] == 1
    assert entry["usage"]["models"] == ["claude-sonnet-4-6"]


# ---------------------------------------------------------------------------
# The state file stops lying
# ---------------------------------------------------------------------------


def test_finishing_the_preface_no_longer_marks_articulation_done() -> None:
    """The original defect, pinned: the ingest does not run this step, so
    finishing a LATER step must not complete it by sitting earlier in a tuple."""
    import tempfile

    from sessions.ingest import _write_state
    from sessions.series import SERIES

    with tempfile.TemporaryDirectory() as tmp:
        book_dir = Path(tmp)
        (book_dir / "_system").mkdir()
        series = next(iter(SERIES.values()))
        _write_state(book_dir, series, done_through="sessions-preface")
        state = json.loads((book_dir / "_system" / "orchestrator-state.json").read_text())
        assert state["phases"][ARTICULATE_STEP]["status"] == "pending"
        assert state["phases"]["sessions-preface"]["status"] == "completed"


def test_a_re_ingest_does_not_forget_that_articulation_ran(book_dir: Path, monkeypatch) -> None:
    """The carry-over is in both directions: the ingest must not claim the step,
    and must not erase it either."""
    from sessions.ingest import _write_state
    from sessions.series import SERIES

    state_path = book_dir / "_system" / "orchestrator-state.json"
    state_path.write_text(json.dumps({"phases": {ARTICULATE_STEP: {"status": "completed"}}}), encoding="utf-8")
    _write_state(book_dir, next(iter(SERIES.values())), done_through="sessions-preface")
    state = json.loads(state_path.read_text())
    assert state["phases"][ARTICULATE_STEP]["status"] == "completed"


def test_the_step_completes_without_dragging_the_lane_backwards(book_dir: Path, monkeypatch) -> None:
    """Articulation legitimately runs AFTER the preface — the introduction it
    writes is apparatus this pass skips. Writing `phase: sessions-articulate`
    here would report a finished book as three steps from done."""
    state_path = book_dir / "_system" / "orchestrator-state.json"
    state_path.write_text(
        json.dumps(
            {
                "phase": "sessions-preface",
                "last_completed_phase": "sessions-preface",
                "phases": {step: {"status": "pending"} for step in LANE_STEPS},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(art, "rearticulate", lambda bd, key, log=print, **_kwargs: envelope("adapted"))
    art.articulate_book(book_dir, log=lambda *_: None)
    state = json.loads(state_path.read_text())
    assert state["phase"] == "sessions-preface"
    assert state["phases"][ARTICULATE_STEP]["status"] == "completed"
    assert state["phases"][ARTICULATE_STEP]["chapters_kept"] == 2
    assert state["phases"][ARTICULATE_STEP]["chapters_total"] == 2


# ---------------------------------------------------------------------------
# An unreachable model is not a quality verdict
# ---------------------------------------------------------------------------


def dead(status: str = "reverted") -> dict:
    """A chapter whose every window returned nothing from the model."""
    e = envelope(status)
    e["record"]["gates"] = ["part-01: no candidate", "part-02: no candidate"]
    return e


def test_a_run_of_empty_responses_stops_the_run(book_dir: Path, monkeypatch) -> None:
    """Twelve calls produced output on the first surah-al-fateha run, then sixteen
    chapters in a row produced zero output tokens and the run finished claiming 21
    reverts. "The gates rejected the rewrite" and "we never got a rewrite" look
    identical in the ledger afterwards, which is the worst possible report."""
    monkeypatch.setattr(art, "rearticulate", lambda bd, key, log=print, **_kwargs: dead())
    summary = art.articulate_book(book_dir, log=lambda *_: None)
    assert summary["aborted"] is True


def test_an_aborted_run_does_not_mark_the_step_complete(book_dir: Path, monkeypatch) -> None:
    """A green tick over a half-articulated book is how it stays half-articulated.

    The step reads `running`, not the `pending` it started at — a heartbeat
    catching this book mid-abort should see that work is underway, not that
    nothing has happened yet."""
    state_path = book_dir / "_system" / "orchestrator-state.json"
    state_path.write_text(json.dumps({"phases": {ARTICULATE_STEP: {"status": "pending"}}}), encoding="utf-8")
    monkeypatch.setattr(art, "rearticulate", lambda bd, key, log=print, **_kwargs: dead())
    art.articulate_book(book_dir, log=lambda *_: None)
    assert json.loads(state_path.read_text())["phases"][ARTICULATE_STEP]["status"] == "running"


def test_the_step_reads_running_the_moment_a_run_starts(book_dir: Path, monkeypatch) -> None:
    """A heartbeat firing in the first minute of an hours-long chapter must not
    see whatever an EARLIER run's outcome happened to leave stamped — including
    a stale `completed` from before this rule existed."""
    state_path = book_dir / "_system" / "orchestrator-state.json"
    state_path.write_text(
        json.dumps({"phases": {ARTICULATE_STEP: {"status": "completed", "chapters_kept": 2}}}), encoding="utf-8"
    )

    def hangs(bd, key, log=print, **_kwargs):
        raise RuntimeError("never returns in this test")

    monkeypatch.setattr(art, "rearticulate", hangs)
    try:
        art.articulate_book(book_dir, log=lambda *_: None)
    except Exception:
        pass
    # The FIRST write, before any chapter's outcome is known, already overwrote
    # the stale `completed`.
    assert json.loads(state_path.read_text())["phases"][ARTICULATE_STEP]["status"] == "running"


def test_a_run_that_ends_with_real_reverts_left_is_not_marked_complete(book_dir: Path, monkeypatch) -> None:
    """Reaching the end of the chapter list without aborting is NOT the same as
    finishing the book. The original bug: a run that tried all 21 chapters,
    kept 2, and genuinely failed the rest on content grounds still stamped
    `completed` because it never hit the dead-streak circuit breaker."""
    (book_dir / "_system" / "orchestrator-state.json").write_text(
        json.dumps({"phases": {ARTICULATE_STEP: {"status": "pending"}}}), encoding="utf-8"
    )
    monkeypatch.setattr(art, "rearticulate", lambda bd, key, log=print, **_kwargs: envelope("reverted"))
    art.articulate_book(book_dir, log=lambda *_: None)
    state = json.loads((book_dir / "_system" / "orchestrator-state.json").read_text())
    assert state["phases"][ARTICULATE_STEP]["status"] == "running"
    assert state["phases"][ARTICULATE_STEP]["chapters_kept"] == 0
    assert state["phases"][ARTICULATE_STEP]["chapters_total"] == 2


def test_a_real_gate_rejection_is_not_mistaken_for_an_unreachable_model(book_dir: Path, monkeypatch) -> None:
    """A chapter the gates genuinely rejected has a REASON. Those runs continue —
    the pass is working, it is the prose that failed, and the next chapter may pass."""
    e = envelope("reverted")
    e["record"]["gates"] = ["part-01: Arabic runs dropped (115<117)"]
    monkeypatch.setattr(art, "rearticulate", lambda bd, key, log=print, **_kwargs: e)
    summary = art.articulate_book(book_dir, log=lambda *_: None)
    assert summary["aborted"] is False
    assert summary["reverted"] == 2


# ---------------------------------------------------------------------------
# House-style normalization after a chapter is kept
# ---------------------------------------------------------------------------


def test_a_kept_chapter_gets_its_legacy_transcript_formatting_normalized(book_dir: Path, monkeypatch) -> None:
    """`rearticulate` (faked here, per this file's own contract) writes the
    rewritten body to book.md itself before returning — carrying the source
    transcript's own bare-citation/heading-transliteration conventions
    straight through, since rewording never restructures. The driver must
    still bring that output up to house style afterward."""
    book_md = book_dir / "book" / "book.md"
    text = book_md.read_text(encoding="utf-8")
    text = text.replace(
        "## Love Based Religion\n\nHe spoke about love, and you should notice how the word turns.",
        "## Love Based Religion\n\n### Trustworthy Friend ولیجۃ\n\nWALEEJA\n\nHe spoke about love.",
    )
    book_md.write_text(text, encoding="utf-8")

    monkeypatch.setattr(art, "rearticulate", lambda bd, key, log=print, **_kwargs: envelope("adapted"))
    art.articulate_book(book_dir, log=lambda *_: None)

    final = book_md.read_text(encoding="utf-8")
    assert "### Trustworthy Friend (ولیجۃ)" in final
    assert "WALEEJA" not in final


def test_a_reverted_chapter_is_never_normalized(book_dir: Path, monkeypatch) -> None:
    """Nothing changed for a reverted chapter — normalizing it would be
    touching book.md over a rewrite that was thrown away."""
    book_md = book_dir / "book" / "book.md"
    text = book_md.read_text(encoding="utf-8")
    text = text.replace(
        "## Love Based Religion\n\nHe spoke about love, and you should notice how the word turns.",
        "## Love Based Religion\n\n### Trustworthy Friend ولیجۃ\n\nWALEEJA\n\nHe spoke about love.",
    )
    book_md.write_text(text, encoding="utf-8")

    monkeypatch.setattr(art, "rearticulate", lambda bd, key, log=print, **_kwargs: envelope("reverted"))
    art.articulate_book(book_dir, log=lambda *_: None)

    final = book_md.read_text(encoding="utf-8")
    assert "### Trustworthy Friend ولیجۃ" in final  # untouched, parens NOT added
    assert "WALEEJA" in final
