"""The card must not assert things it cannot support.

Four defects found on 2026-07-31 while watching a live run, all of the same
shape: the card kept its frame and its confident tone while the number inside
it had stopped meaning anything.

  * a retried phase moved the book BACKWARDS and the velocity window kept the
    peak it had fallen back from, so the projection stretched by hours;
  * the ETA rendered as a bare clock time, so an estimate past midnight printed
    as a time already in the past;
  * the projection spread one compute rate across a phase that waits on a
    HUMAN, answering a question a rate cannot answer;
  * five phases skipped because the book was MISCONFIGURED scored exactly like
    phases skipped by design, so a run that produced no reading edition at all
    reported 95% complete.

Each test below fails against the code as it stood that evening.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from book_status_card import (  # noqa: E402
    _format_est_dated,
    compute_progress,
    estimate_eta,
    render_card,
)

T0 = datetime(2026, 7, 31, 16, 0, 0, tzinfo=timezone.utc)


# ── the velocity window must not keep a peak the run fell back from ──────────


def test_a_phase_retry_that_moves_percent_backwards_does_not_inflate_the_eta(tmp_path: Path) -> None:
    """The live failure: 39.6% -> 63.6% over ~4h, then a slide-phase retry reset
    the book to 56%. Recording only INCREASES left 63.6 in the window, so the
    rate was measured against progress that no longer existed."""
    estimate_eta(tmp_path, 39.6, now=T0)
    estimate_eta(tmp_path, 63.6, now=T0 + timedelta(hours=4))
    # The retry lands: the book is genuinely at 56% now.
    estimate_eta(tmp_path, 56.0, now=T0 + timedelta(hours=4, minutes=5))
    # Real progress resumes from there.
    eta = estimate_eta(tmp_path, 60.0, now=T0 + timedelta(hours=4, minutes=15))

    assert eta is not None
    # 4 points in 10 minutes -> 40 remaining -> 100 minutes. Measured forward
    # from the regression, NOT against the abandoned 63.6 peak.
    expected = T0 + timedelta(hours=4, minutes=115)
    assert abs((eta - expected).total_seconds()) < 60


def test_a_regression_discards_the_samples_that_describe_the_rewound_run(tmp_path: Path) -> None:
    """Samples taken before a rewind describe work that was undone. Keeping them
    in the window means dividing new progress by old elapsed time."""
    estimate_eta(tmp_path, 10.0, now=T0)
    estimate_eta(tmp_path, 90.0, now=T0 + timedelta(hours=10))
    estimate_eta(tmp_path, 20.0, now=T0 + timedelta(hours=10, minutes=1))
    # Only one sample survives the reset, so there is no rate yet — and saying
    # "no estimate" is the honest answer, not a number derived from a dead run.
    assert estimate_eta(tmp_path, 20.0, now=T0 + timedelta(hours=10, minutes=2)) is None


# ── an ETA on another day must say which day ─────────────────────────────────


def test_an_eta_past_midnight_is_not_rendered_as_a_past_time() -> None:
    """6:14 AM beside a 6:49 PM check stamp read as twelve hours ago. It was
    tomorrow morning."""
    now = datetime(2026, 7, 31, 22, 49, tzinfo=timezone.utc)  # 6:49 PM EDT
    tomorrow_morning = datetime(2026, 8, 1, 10, 14, tzinfo=timezone.utc)  # 6:14 AM EDT
    rendered = _format_est_dated(tomorrow_morning, relative_to=now)
    assert "tomorrow" in rendered
    assert rendered.startswith("6:14 AM EST")


def test_an_eta_later_today_stays_a_bare_clock_time() -> None:
    """The qualifier is for ambiguity only — most ETAs are same-day and adding
    'today' to every one of them is noise."""
    now = datetime(2026, 7, 31, 22, 49, tzinfo=timezone.utc)
    later = datetime(2026, 8, 1, 1, 30, tzinfo=timezone.utc)  # 9:30 PM EDT, same day
    assert _format_est_dated(later, relative_to=now) == "9:30 PM EST"


def test_an_eta_days_out_names_the_day() -> None:
    now = datetime(2026, 7, 31, 22, 49, tzinfo=timezone.utc)
    later = datetime(2026, 8, 3, 14, 0, tzinfo=timezone.utc)  # Monday
    assert "Mon" in _format_est_dated(later, relative_to=now)


# ── human-gated phases are not machine work ──────────────────────────────────


def _state(phase_statuses: dict[str, str], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    phases = {p: {"status": s} for p, s in phase_statuses.items()}
    for phase, block in (extra or {}).items():
        phases.setdefault(phase, {}).update(block)
    return {"phase": "finalize", "phase_status": "halted", "phases": phases}


def test_a_phase_waiting_on_a_person_is_excluded_from_the_machine_percentage() -> None:
    """`audio-ingest` sits until the human uploads to NotebookLM and drops the
    .m4a files back. Counting it as pending compute is what produced 'eleven
    hours left' on a book with two hours of work and then an indefinite pause."""
    progress = compute_progress(
        _state(
            {
                "pre-flight": "completed",
                "0a": "completed",
                "per-chapter": "completed",
                "finalize": "halted",
                "audio-ingest": "pending",
            }
        )
    )
    assert "audio-ingest" in progress["human_gated_remaining"]
    # The machine is further along than the raw number suggests, because the one
    # thing still outstanding is not the machine's to do.
    assert progress["machine_percent_complete"] > progress["percent_complete"]


def test_the_card_says_the_eta_only_reaches_the_next_halt() -> None:
    progress = compute_progress(
        _state(
            {
                "pre-flight": "completed",
                "per-chapter": "completed",
                "finalize": "halted",
                "audio-ingest": "pending",
            }
        )
    )
    card = {
        "title": "Test Book",
        "slug": "test-book",
        "generated_at": "8:00 PM EST",
        "eta": "9:23 PM EST",
        "spend_usd": 0.0,
        "pending": [],
        **progress,
    }
    assert "to next halt" in render_card(card)


# ── a misconfigured skip is not a skip by design ─────────────────────────────


def test_a_phase_skipped_by_misconfiguration_is_surfaced_not_silently_dropped() -> None:
    """Both kinds of skip leave the denominator — a book that will never render
    slides must still reach 100%. Only one of them means a deliverable is
    missing, and on 2026-07-31 that one reported 95% complete with an empty
    book/ directory."""
    progress = compute_progress(
        _state(
            {
                "pre-flight": "completed",
                "per-chapter": "completed",
                "audio-render": "skipped",  # by design: a NotebookLM book renders no audio
                "0book-compose": "skipped",
                "0book-render": "skipped",
            },
            extra={
                "0book-compose": {"skipped_by": "config", "reason": "enable_book_branch not set"},
                "0book-render": {"skipped_by": "config", "reason": "enable_book_branch not set"},
            },
        )
    )
    flagged = {s["phase"] for s in progress["skipped_by_config"]}
    assert flagged == {"0book-compose", "0book-render"}
    # The by-design skip is NOT flagged — that would make the signal worthless.
    assert "audio-render" not in flagged


def test_the_card_shows_what_was_never_run() -> None:
    progress = compute_progress(
        _state(
            {"pre-flight": "completed", "per-chapter": "completed", "0book-compose": "skipped"},
            extra={"0book-compose": {"skipped_by": "config", "reason": "enable_book_branch not set"}},
        )
    )
    card = {
        "title": "Test Book",
        "slug": "test-book",
        "generated_at": "8:00 PM EST",
        "eta": None,
        "spend_usd": 0.0,
        "pending": [],
        **progress,
    }
    assert "Not run" in render_card(card)
