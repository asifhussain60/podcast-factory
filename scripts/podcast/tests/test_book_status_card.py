"""The progress number has to be reproducible, or it is worse than no number.

These tests pin the three judgment calls in it: long phases dominate, a phase the
book will never run leaves the denominator, and a step that is underway counts as
underway rather than as nothing.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _progress import PHASES  # noqa: E402
from book_status_card import build_card, compute_progress, render_card  # noqa: E402


def state(**statuses: str) -> dict:
    return {"phases": {p: {"status": s} for p, s in statuses.items()}}


def test_a_fresh_book_is_at_zero() -> None:
    assert compute_progress({"phases": {}})["percent_complete"] == 0.0


def test_a_book_that_finished_every_phase_is_at_one_hundred() -> None:
    progress = compute_progress(state(**{p: "completed" for p in PHASES}))
    assert progress["percent_complete"] == 100.0
    assert progress["remaining"] == []


def test_long_phases_move_the_number_more_than_short_ones() -> None:
    """Finishing the per-chapter loop must outweigh finishing three bookkeeping steps."""
    loop = compute_progress(state(**{"per-chapter": "completed"}))["percent_complete"]
    bookkeeping = compute_progress(
        state(**{"pre-flight": "completed", "branch": "completed", "scaffold": "completed"})
    )["percent_complete"]
    assert loop > bookkeeping


def test_a_skipped_phase_leaves_the_denominator() -> None:
    """A book with no slide decks must still be able to reach 100%."""
    progress = compute_progress(state(**{p: ("skipped" if p == "per-chapter-slides" else "completed") for p in PHASES}))
    assert progress["percent_complete"] == 100.0
    assert "per-chapter-slides" not in progress["remaining"]


def test_a_running_phase_counts_as_underway() -> None:
    partial = compute_progress(state(**{"0a": "completed", "0b": "running"}))
    finished = compute_progress(state(**{"0a": "completed", "0b": "completed"}))
    started = compute_progress(state(**{"0a": "completed"}))
    assert started["percent_complete"] < partial["percent_complete"] < finished["percent_complete"]


def test_the_per_chapter_loop_reports_its_own_chapter_progress() -> None:
    """Halfway through the loop should read as halfway, not as nothing until it flips."""
    early = {"phases": {"per-chapter": {"status": "running", "completed_slugs": ["a"], "current_chapter": "b"}}}
    late = {
        "phases": {
            "per-chapter": {"status": "running", "completed_slugs": ["a", "b", "c", "d"], "current_chapter": "e"}
        }
    }
    assert compute_progress(early)["percent_complete"] < compute_progress(late)["percent_complete"]


def test_a_shipped_book_is_not_held_back_by_steps_its_run_never_stamped() -> None:
    """A real shipped book carries stale 'pending' phases behind a completed 'done'."""
    progress = compute_progress(
        state(
            **{
                "pre-flight": "completed",
                "0a": "completed",
                "0literary": "pending",
                "per-chapter": "failed",
                "publish": "completed",
                "done": "completed",
            }
        )
    )
    assert progress["percent_complete"] == 100.0


def test_a_failure_left_behind_the_frontier_is_surfaced_not_swallowed() -> None:
    progress = compute_progress(state(**{"per-chapter": "failed", "publish": "completed", "done": "completed"}))
    assert [b["phase"] for b in progress["bypassed_unresolved"]] == ["per-chapter"]


def test_a_pending_step_ahead_of_the_frontier_is_still_work_to_do() -> None:
    progress = compute_progress(state(**{"0a": "completed", "0b": "pending"}))
    assert "0b" in progress["remaining"]
    assert progress["percent_complete"] < 100.0


# ─── the rendered card ───────────────────────────────────────────────────────
def test_the_card_reads_a_real_book_directory(tmp_path: Path) -> None:
    bd = tmp_path / "slug"
    (bd / "_system").mkdir(parents=True)
    (bd / "_system" / "orchestrator-state.json").write_text(
        '{"book_slug": "slug", "phase": "0b", "phase_status": "running",'
        ' "phases": {"0a": {"status": "completed"}, "0b": {"status": "running"}}}',
        encoding="utf-8",
    )
    (bd / "_system" / "cost-ledger.jsonl").write_text(
        '{"cost_usd": 1.5}\n{"cost_usd": 0.25}\n{"no_cost_key": 1}\n', encoding="utf-8"
    )

    card = build_card(bd)

    assert card["slug"] == "slug"
    assert card["spend_usd"] == 1.75, "only real money is reported, never flat-rate work"
    assert 0 < card["percent_complete"] < 100
    assert "EST" in card["generated_at"]


def test_the_rendered_card_shows_the_number_and_what_is_left(tmp_path: Path) -> None:
    bd = tmp_path / "slug"
    (bd / "_system").mkdir(parents=True)
    (bd / "_system" / "orchestrator-state.json").write_text(
        '{"book_slug": "slug", "phase": "0a", "phase_status": "running", "phases": {"0a": {"status": "running"}}}',
        encoding="utf-8",
    )

    text = render_card(build_card(bd))
    lines = text.split("\n")

    assert lines[0].startswith("┌") and lines[-1].startswith("└")
    assert {len(line) for line in lines} == {52}, "every row must be exactly one frame wide"
    assert "Now" in text and "Left" in text and "Spend" in text and "Checked" in text
    assert "Scanning and translating" in text, "steps are named in plain English, never by id"
    assert "0a" not in text


def test_the_card_shows_the_books_proper_title_not_its_slug(tmp_path: Path) -> None:
    bd = tmp_path / "the-master-and-the-disciple"
    (bd / "_system").mkdir(parents=True)
    (bd / "_system" / "orchestrator-state.json").write_text(
        '{"book_slug": "the-master-and-the-disciple", "phase": "0a", "phase_status": "running",'
        ' "phases": {"0a": {"status": "running"}}}',
        encoding="utf-8",
    )
    (bd / "meta.yml").write_text("slug: the-master-and-the-disciple\ntitle: The Master and the Disciple\n", "utf-8")

    text = render_card(build_card(bd))

    assert "The Master and the Disciple" in text
    assert "THE MASTER" not in text, "a title is Proper Case, never shouted"
    assert "the-master-and-the-disciple" not in text


def test_a_long_value_is_clipped_rather_than_breaking_the_frame(tmp_path: Path) -> None:
    bd = tmp_path / "slug"
    (bd / "_system").mkdir(parents=True)
    (bd / "_system" / "orchestrator-state.json").write_text(
        '{"book_slug": "slug", "phase": "0a", "phase_status": "running",'
        ' "last_error": "' + ("a very long failure message " * 12) + '",'
        ' "phases": {"0a": {"status": "running"}}}',
        encoding="utf-8",
    )

    lines = render_card(build_card(bd)).split("\n")

    assert {len(line) for line in lines} == {52}


def test_the_verbose_step_list_stays_inside_the_frame(tmp_path: Path) -> None:
    bd = tmp_path / "slug"
    (bd / "_system").mkdir(parents=True)
    (bd / "_system" / "orchestrator-state.json").write_text(
        '{"book_slug": "slug", "phase": "0a", "phase_status": "running", "phases": {"0a": {"status": "running"}}}',
        encoding="utf-8",
    )

    lines = render_card(build_card(bd), verbose=True).split("\n")

    # Emoji count as one character but occupy two columns, so icon rows are one
    # character shorter than the plain rows by design.
    assert {len(line) for line in lines} <= {51, 52}


def test_a_missing_state_file_renders_rather_than_crashing(tmp_path: Path) -> None:
    card = build_card(tmp_path)
    assert card["percent_complete"] == 0.0
    assert render_card(card)
