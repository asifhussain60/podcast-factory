"""ETA: an estimate from observed velocity, never from a fixed start time.

Asif: "Show me an ETA in the status update card. Update the base template."
These tests pin the property that makes the number trustworthy rather than
decorative — it comes from checkpoints this module recorded itself, and it
degrades to "no estimate" instead of guessing when it doesn't have enough.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from book_status_card import build_card, estimate_eta, render_card  # noqa: E402

T0 = datetime(2026, 7, 19, 12, 0, 0, tzinfo=timezone.utc)


def test_the_first_call_on_any_run_has_nothing_to_compare_against() -> None:
    """One sample is not a rate. A fabricated ETA from a single point is worse
    than admitting there isn't one yet."""
    assert estimate_eta(Path("/tmp/does-not-matter-1"), 10.0, now=T0) is None


def test_a_second_call_with_real_progress_produces_an_estimate(tmp_path: Path) -> None:
    estimate_eta(tmp_path, 10.0, now=T0)
    eta = estimate_eta(tmp_path, 20.0, now=T0 + timedelta(minutes=10))
    assert eta is not None
    # 10% in 10 minutes -> 80% remaining at the same rate -> 80 minutes from now.
    assert abs((eta - (T0 + timedelta(minutes=90))).total_seconds()) < 1


def test_no_progress_since_the_last_checkpoint_yields_no_fresh_estimate(tmp_path: Path) -> None:
    """Flat percent between calls means no NEW rate to compute from — the
    module must not invent one."""
    estimate_eta(tmp_path, 10.0, now=T0)
    assert estimate_eta(tmp_path, 10.0, now=T0 + timedelta(minutes=5)) is None


def test_the_estimate_recedes_on_its_own_when_a_run_stalls(tmp_path: Path) -> None:
    """Self-correction, not a reset: real progress at 12:00 and 12:10 sets a rate.
    Every later call re-projects from THAT rate using the CURRENT time as the
    reference point — so as wall-clock time passes with no new checkpoint, the
    implied rate quietly falls (same gain, growing elapsed) and the predicted
    completion date slides later on its own. No stall flag needed."""
    estimate_eta(tmp_path, 10.0, now=T0)
    estimate_eta(tmp_path, 20.0, now=T0 + timedelta(minutes=10))

    soon = estimate_eta(tmp_path, 20.0, now=T0 + timedelta(minutes=15))
    later = estimate_eta(tmp_path, 20.0, now=T0 + timedelta(hours=5))

    assert soon is not None and later is not None
    assert later > soon, "silence must push the estimate further out, not hold it fixed"


def test_a_completed_run_needs_no_estimate(tmp_path: Path) -> None:
    estimate_eta(tmp_path, 90.0, now=T0)
    assert estimate_eta(tmp_path, 100.0, now=T0 + timedelta(minutes=5)) is None


def test_an_absurd_extrapolation_is_suppressed_not_shown(tmp_path: Path) -> None:
    """A hair of progress over a long span implies a wildly distant completion —
    reporting it as a number would look precise while being noise."""
    estimate_eta(tmp_path, 1.0, now=T0)
    eta = estimate_eta(tmp_path, 1.001, now=T0 + timedelta(hours=1))
    assert eta is None


def test_a_corrupt_velocity_file_never_crashes_the_card(tmp_path: Path) -> None:
    (tmp_path / "_system").mkdir(parents=True)
    (tmp_path / "_system" / "status-velocity.json").write_text("{not json", encoding="utf-8")
    assert estimate_eta(tmp_path, 50.0, now=T0) is None


def test_the_checkpoint_window_does_not_grow_without_bound(tmp_path: Path) -> None:
    for i in range(20):
        estimate_eta(tmp_path, float(i + 1), now=T0 + timedelta(minutes=i))
    import json

    stored = json.loads((tmp_path / "_system" / "status-velocity.json").read_text(encoding="utf-8"))
    assert len(stored) <= 5


# ─── the card ─────────────────────────────────────────────────────────────────
def test_the_card_shows_an_eta_row_inside_the_frame(tmp_path: Path) -> None:
    bd = tmp_path / "slug"
    (bd / "_system").mkdir(parents=True)
    (bd / "_system" / "orchestrator-state.json").write_text(
        '{"book_slug": "slug", "phase": "0a", "phase_status": "running", "phases": {"0a": {"status": "running"}}}',
        encoding="utf-8",
    )

    text = render_card(build_card(bd))
    lines = text.split("\n")

    assert "ETA" in text
    assert {len(line) for line in lines} == {52}


def test_a_fresh_run_shows_it_is_estimating_rather_than_a_wrong_number(tmp_path: Path) -> None:
    bd = tmp_path / "slug"
    (bd / "_system").mkdir(parents=True)
    (bd / "_system" / "orchestrator-state.json").write_text(
        '{"book_slug": "slug", "phase": "0a", "phase_status": "running", "phases": {"0a": {"status": "running"}}}',
        encoding="utf-8",
    )

    assert "estimating" in render_card(build_card(bd))
