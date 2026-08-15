"""The progress number has to be reproducible, or it is worse than no number.

These tests pin the three judgment calls in it: long phases dominate, a phase the
book will never run leaves the denominator, and a step that is underway counts as
underway rather than as nothing.
"""

from __future__ import annotations

import json
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


# ─── chunked phases (0b, 0d) read real on-disk progress ──────────────────────
def test_a_chunked_phase_reads_real_chunk_progress_not_a_flat_guess(tmp_path: Path) -> None:
    """0d checkpoints on disk per source chunk even though the state file just
    says "running" the whole time. 2 of 5 chunks done must read as 0.4, not the
    flat 0.5 guess used when there is nothing else to go on."""
    chunks_dir = tmp_path / "_system" / "source" / "text" / "_chunks" / "0d"
    chunks_dir.mkdir(parents=True)
    (chunks_dir / "source-toc.json").write_text('{"source_chapters": [{}, {}, {}, {}, {}]}', encoding="utf-8")
    (chunks_dir / "sc-001.done").write_text("", encoding="utf-8")
    (chunks_dir / "sc-002.done").write_text("", encoding="utf-8")

    progress = compute_progress(state(**{"0a": "completed", "0d": "running"}), tmp_path)
    row = next(r for r in progress["phases"] if r["phase"] == "0d")
    assert row["fraction"] == 0.4


def test_a_chunked_phase_without_book_dir_falls_back_to_the_flat_guess() -> None:
    """Every existing pure-state caller must see the old behavior unchanged —
    book_dir is optional precisely so this stays true."""
    progress = compute_progress(state(**{"0a": "completed", "0d": "running"}))
    row = next(r for r in progress["phases"] if r["phase"] == "0d")
    assert row["fraction"] == 0.5


def test_a_running_phase_with_no_chunk_directory_yet_falls_back_to_the_flat_guess(tmp_path: Path) -> None:
    """0c and 0e do not chunk this way today — book_dir is known but there is no
    _chunks/0c directory to read, so the honest flat guess still applies."""
    (tmp_path / "_system").mkdir(parents=True)
    progress = compute_progress(state(**{"0c": "running"}), tmp_path)
    row = next(r for r in progress["phases"] if r["phase"] == "0c")
    assert row["fraction"] == 0.5


def test_a_windowed_phase_reads_real_window_progress(tmp_path: Path) -> None:
    """0b writes win-NNN.in.md / win-NNN.out.md pairs — a window counts as done
    once its .out.md exists (see _chunking.py). 3 of 4 windows done reads as 0.75."""
    chunks_dir = tmp_path / "_system" / "source" / "text" / "_chunks" / "0b"
    chunks_dir.mkdir(parents=True)
    for i in range(1, 5):
        (chunks_dir / f"win-{i:03d}.in.md").write_text("", encoding="utf-8")
    for i in range(1, 4):
        (chunks_dir / f"win-{i:03d}.out.md").write_text("", encoding="utf-8")

    progress = compute_progress(state(**{"0b": "running"}), tmp_path)
    row = next(r for r in progress["phases"] if r["phase"] == "0b")
    assert row["fraction"] == 0.75


def test_the_card_reflects_real_chunk_progress_end_to_end(tmp_path: Path) -> None:
    """build_card must pass book_dir through so a live run's ETA has a real
    signal instead of a flat half-guess frozen for the whole phase."""
    bd = tmp_path / "slug"
    (bd / "_system").mkdir(parents=True)
    (bd / "_system" / "orchestrator-state.json").write_text(
        '{"book_slug": "slug", "phase": "0d", "phase_status": "running",'
        ' "phases": {"0a": {"status": "completed"}, "0d": {"status": "running"}}}',
        encoding="utf-8",
    )
    chunks_dir = bd / "_system" / "source" / "text" / "_chunks" / "0d"
    chunks_dir.mkdir(parents=True)
    (chunks_dir / "source-toc.json").write_text('{"source_chapters": [{}, {}, {}, {}, {}]}', encoding="utf-8")
    (chunks_dir / "sc-001.done").write_text("", encoding="utf-8")
    (chunks_dir / "sc-002.done").write_text("", encoding="utf-8")

    card = build_card(bd)
    row = next(r for r in card["phases"] if r["phase"] == "0d")
    assert row["fraction"] == 0.4


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


def test_a_claude_row_never_counts_as_spend_even_with_a_genuine_cost(tmp_path: Path) -> None:
    """Asif, 2026-08-12: no Claude figure on this card, full stop — not merely
    "no Claude figure under the current flat-rate billing engine." Excluded by
    model name so the guarantee survives even a row that carries a real,
    nonzero cost_usd (a hypothetical metered Claude call), not just today's
    always-zero Max rows."""
    bd = tmp_path / "slug"
    (bd / "_system").mkdir(parents=True)
    (bd / "_system" / "orchestrator-state.json").write_text(
        '{"book_slug": "slug", "phase": "0a", "phase_status": "running", "phases": {"0a": {"status": "running"}}}',
        encoding="utf-8",
    )
    (bd / "_system" / "cost-ledger.jsonl").write_text(
        '{"model": "claude-sonnet-4-6", "cost_usd": 9.99}\n'
        '{"model": "gemini-2.5-pro", "cost_usd": 0.03}\n'
        '{"model": "azure-speech-stt-fast", "cost_usd": 2.20}\n',
        encoding="utf-8",
    )

    card = build_card(bd)

    assert card["spend_usd"] == 2.23, "the Claude row must be excluded, the other two kept"


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
    # Emoji count as one character but occupy two columns, so a per-step icon
    # row is one character shorter than a plain row by design (same accounting
    # the verbose step list has always used — now also true by default, since
    # the remaining steps are itemized on every card, not just --verbose).
    assert {len(line) for line in lines} <= {51, 52}, "every row must be at most one frame wide"
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

    assert {len(line) for line in lines} <= {51, 52}


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


# ─── the Sessions lane (its own sequence, not the orchestrator's PHASES) ─────
#
# `sessions-articulate` checkpoints per chapter in `_system/sessions-articulation
# .json`, exactly like 0b/0d checkpoint per chunk on disk — same reason for the
# same kind of helper. Found 2026-08-12: `book_status_card.py` reported Surah
# Al-Fateha as 92% complete, one step from done, while 21 of 23 chapters still
# read exactly as the lecture transcript left them. Two independent bugs
# produced that number, and both are pinned below.


def _sessions_book(tmp_path: Path, *, headings: list[str], kept: dict[str, str]) -> Path:
    bd = tmp_path / "surah-al-fateha"
    (bd / "book").mkdir(parents=True)
    (bd / "_system").mkdir()
    body = "\n\n".join(f"## {h}\n\nSome prose.\n" for h in headings)
    (bd / "book" / "book.md").write_text(f"# A Series\n\n{body}\n", encoding="utf-8")
    from _book_edits import anchor_key

    ledger = {"chapters": {anchor_key(h): {"title": h, "status": s} for h, s in kept.items()}}
    (bd / "_system" / "sessions-articulation.json").write_text(json.dumps(ledger), encoding="utf-8")
    return bd


def test_a_stale_completed_flag_does_not_grant_full_credit(tmp_path: Path) -> None:
    """The bug as it actually shipped: the driver wrote `completed` after
    keeping 2 of 23 chapters, and the flag alone earned this phase its FULL
    weight. Real per-chapter progress must be read even when status claims done,
    or a stale flag from before a correctness fix keeps lying forever."""
    bd = _sessions_book(
        tmp_path,
        headings=["Introduction to the Book", "A", "B"],
        kept={"A": "adapted"},
    )
    state_dict = {
        "phases": {
            "sessions-ingest": {"status": "completed"},
            "sessions-articulate": {"status": "completed", "chapters_kept": 1},
            "sessions-preface": {"status": "completed"},
        }
    }
    progress = compute_progress(state_dict, bd)
    row = next(r for r in progress["phases"] if r["phase"] == "sessions-articulate")
    assert row["fraction"] == 0.5  # 1 of 2 real chapters, not 1.0 from the flag


def test_a_running_articulate_step_reads_real_chapter_progress(tmp_path: Path) -> None:
    bd = _sessions_book(
        tmp_path,
        headings=["Introduction to the Book", "A", "B", "C", "D"],
        kept={"A": "adapted", "B": "partial", "C": "reverted"},
    )
    progress = compute_progress({"phases": {"sessions-articulate": {"status": "running"}}}, bd)
    row = next(r for r in progress["phases"] if r["phase"] == "sessions-articulate")
    assert row["fraction"] == 0.25  # only fully adapted chapters count complete


def test_the_introduction_does_not_count_toward_the_denominator(tmp_path: Path) -> None:
    """The pass engine never touches the introduction — it is apparatus, not a
    chapter — so counting it as un-kept work would cap this phase below 100%
    even after every real chapter is articulated."""
    bd = _sessions_book(
        tmp_path,
        headings=["Introduction to the Book", "A"],
        kept={"A": "adapted"},
    )
    progress = compute_progress({"phases": {"sessions-articulate": {"status": "running"}}}, bd)
    row = next(r for r in progress["phases"] if r["phase"] == "sessions-articulate")
    assert row["fraction"] == 0.95  # capped, same convention as _chunk_fraction


def test_without_a_book_md_the_flat_guess_still_applies(tmp_path: Path) -> None:
    """Every existing caller that passes state alone, or a book_dir with no
    book.md yet, must see the prior behavior unchanged."""
    progress = compute_progress({"phases": {"sessions-articulate": {"status": "running"}}}, tmp_path)
    row = next(r for r in progress["phases"] if r["phase"] == "sessions-articulate")
    assert row["fraction"] == 0.5


# ─── "Now" for a lane that runs its own sequence ─────────────────────────────


def test_now_is_read_from_the_step_walk_not_a_frozen_top_level_field() -> None:
    """The second bug: `state["phase"]`/`phase_status` are kept live by the
    ORCHESTRATOR's own phase-transition code on every PHASES step. A lane's
    scaffold step stamps those two fields once and nothing later touches them —
    trusting them reported a book mid-articulation as "Now: Writing the
    introduction · completed", the LAST thing the scaffold did, frozen."""
    progress = compute_progress(
        {
            "phase": "sessions-preface",
            "phase_status": "completed",
            "phases": {
                "sessions-ingest": {"status": "completed"},
                "sessions-articulate": {"status": "running"},
                "sessions-preface": {"status": "completed"},
                "sessions-apparatus": {"status": "pending"},
            },
        }
    )
    assert progress["current"] == "sessions-articulate"
    assert progress["current_status"] == "running"


def test_an_orchestrator_book_still_trusts_its_own_live_phase_field() -> None:
    """The fix must not touch the case it was never broken for. An orchestrator
    book's `state["phase"]` IS kept live by its own phase-transition code, and
    the canonical PHASES sequence must keep reading it, unchanged."""
    progress = compute_progress(
        {
            "phase": "0d",
            "phase_status": "running",
            "phases": {"0a": {"status": "completed"}, "0d": {"status": "running"}},
        }
    )
    assert progress["current"] == "0d"
    assert progress["current_status"] == "running"


def test_a_fully_finished_lane_reports_its_last_step_as_now() -> None:
    progress = compute_progress(
        {
            "phases": {
                "sessions-ingest": {"status": "completed"},
                "sessions-apparatus": {"status": "completed"},
            }
        }
    )
    assert progress["current"] == "sessions-apparatus"
    assert progress["current_status"] == "completed"


def test_the_card_end_to_end_no_longer_reports_the_frontier_lie(tmp_path: Path) -> None:
    """Both fixes together, on the exact shape that shipped wrong: a stale
    `completed` on the step actually in progress, sitting behind a genuinely
    completed LATER step. Before this fix: 92% complete, "Now: Writing the
    introduction · completed", one step left. After: the real fraction, and
    "Now" pointing at the step actually still moving."""
    bd = _sessions_book(
        tmp_path,
        headings=["Introduction to the Book"] + [f"Ch{i}" for i in range(1, 24)],
        kept={"Ch1": "adapted", "Ch2": "partial"},
    )
    (bd / "_system" / "orchestrator-state.json").write_text(
        json.dumps(
            {
                "book_slug": "surah-al-fateha",
                "phase": "sessions-preface",
                "phase_status": "completed",
                "phases": {
                    "sessions-ingest": {"status": "completed"},
                    "sessions-transcribe": {"status": "completed"},
                    "sessions-articulate": {"status": "completed", "chapters_kept": 2},
                    "sessions-preface": {"status": "completed"},
                    "sessions-apparatus": {"status": "pending"},
                },
            }
        ),
        encoding="utf-8",
    )
    card = build_card(bd)
    assert card["current"] == "sessions-articulate"
    assert card["percent_complete"] < 92.0
    assert "sessions-articulate" in card["remaining"]


# ─── read-aloud, which checkpoints per chapter in its own manifest ───────────


def _narrated_book(tmp_path: Path, headings: list[str], rendered: list[str]) -> Path:
    """A reading edition plus a narration manifest, with MP3s on disk only for
    the chapters named in `rendered` — the manifest alone must never count."""
    bd = tmp_path / "book-dir"
    (bd / "book" / "narration").mkdir(parents=True)
    (bd / "book" / "book.md").write_text(
        "\n\n".join(f"## {h}\n\nBody of {h}." for h in headings),
        encoding="utf-8",
    )
    chapters = {}
    for h in headings:
        key = h.lower().replace(" ", "-")
        chapters[key] = {"title": h, "audio": f"book/narration/{key}.mp3"}
        if h in rendered:
            (bd / "book" / "narration" / f"{key}.mp3").write_bytes(b"\x00")
    (bd / "book" / "narration" / "manifest.json").write_text(json.dumps({"chapters": chapters}), encoding="utf-8")
    return bd


def test_a_running_narration_step_reads_real_chapter_progress(tmp_path: Path) -> None:
    bd = _narrated_book(tmp_path, headings=["A", "B", "C", "D"], rendered=["A", "B"])
    progress = compute_progress({"phases": {"reader-narration": {"status": "running"}}}, bd)
    row = next(r for r in progress["phases"] if r["phase"] == "reader-narration")
    assert row["fraction"] == 0.5


def test_a_manifest_entry_without_its_audio_does_not_count(tmp_path: Path) -> None:
    """The manifest is rewritten before the next chapter starts, and it survives
    a deleted or never-uploaded MP3 — so the file on disk is the evidence, not
    the entry that claims it."""
    bd = _narrated_book(tmp_path, headings=["A", "B"], rendered=[])
    progress = compute_progress({"phases": {"reader-narration": {"status": "running"}}}, bd)
    row = next(r for r in progress["phases"] if r["phase"] == "reader-narration")
    assert row["fraction"] == 0.0


def test_a_fully_narrated_running_step_is_capped_like_every_other_subphase(tmp_path: Path) -> None:
    bd = _narrated_book(tmp_path, headings=["A", "B"], rendered=["A", "B"])
    progress = compute_progress({"phases": {"reader-narration": {"status": "running"}}}, bd)
    row = next(r for r in progress["phases"] if r["phase"] == "reader-narration")
    assert row["fraction"] == 0.95  # capped, same convention as _chunk_fraction


def test_without_a_narration_manifest_the_flat_guess_still_applies(tmp_path: Path) -> None:
    """A book whose narration has not written anything yet, and every caller that
    passes state alone, must see the prior behavior unchanged."""
    progress = compute_progress({"phases": {"reader-narration": {"status": "running"}}}, tmp_path)
    row = next(r for r in progress["phases"] if r["phase"] == "reader-narration")
    assert row["fraction"] == 0.5
