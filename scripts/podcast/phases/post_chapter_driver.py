"""phases/post_chapter_driver.py — everything after the per-chapter loop.

Phase 0g (register + dual-auditor bundle sweep) -> the slide-deck cohort -> the Audio
Engine phases -> the finalize halt.

Split out of `phases/chapter_driver` on 2026-08-08, when parallelising the chapter loop
pushed that module past its DR-005 ceiling. It is a real seam rather than a convenient
cut: `_drive_per_chapter_and_after` was doing two unrelated jobs, and this half needs
only four things from the first (the slug, which chapters completed, their outcomes, and
whether the human cleared the audio-render spend halt) — so it takes them as arguments
and shares no mutable state with the loop at all.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _convergence import ChapterOutcome
from _paths import REPO_ROOT
from _progress import read_state, update_phase
from _subprocess import err as _err
from _subprocess import info as _info
from _subprocess import run as _run

from phases.bundle_audit import phase_0g_audit_bundles
from phases.scaffold import phase_git_commit
from phases.series_plan import _series_flag, phase_0g_register
from phases.slide_cohort import run_slide_cohort


def _phase_boundary_gate(book_dir: Path, boundary_name: str, projected_cost_usd: float | None = None) -> None:
    """Log a phase boundary crossing for the phased_rollout audit trail.

    A copy of the one in `chapter_driver` rather than an import, deliberately: importing
    it back would make these two modules mutually dependent for a four-line log helper,
    and the split exists so the post-chapter chain owes the loop nothing.
    """
    _info(
        f"[phased_rollout] phase boundary: {boundary_name}"
        + (f" (projected cost: ${projected_cost_usd:.2f})" if projected_cost_usd else "")
    )


def drive_post_chapter(
    book_dir: Path,
    *,
    book_slug: str,
    completed_chapter_slugs: set[str],
    outcomes: list[ChapterOutcome],
    approve_audio_render: bool = False,
) -> int:
    """Drive 0g -> slides -> audio -> finalize. Returns the phase exit code."""
    # Phase 0g — register + dual-auditor bundle sweep.
    _0g_done = (read_state(book_dir) or {}).get("phases", {}).get("0g", {}).get("status") == "completed"
    if _0g_done:
        _info("phase: 0g · already completed, skipping")
    else:
        _info("phase: 0g · register series + dual-auditor bundle sweep")
        update_phase(book_dir, phase="0g", status="running")
        try:
            phase_0g_register(book_dir)
            _info("phase: 0g · register done; starting per-chapter audit sweep")
            audit_outcomes = phase_0g_audit_bundles(book_dir, sorted(completed_chapter_slugs))
        except RuntimeError as e:
            update_phase(book_dir, phase="0g", status="failed", error=str(e))
            _err(str(e))
            return 2
        update_phase(
            book_dir,
            phase="0g",
            status="completed",
            extras={"audit_outcomes": audit_outcomes},
        )
        phase_git_commit(
            book_dir,
            f"podcast({book_slug}): phase 0g register series + dual-auditor bundle sweep",
        )

    # Phase 11b — slide-deck cohort.
    enable_slide_decks = _series_flag(book_dir, "enable_slide_decks", default=True)
    _slides_already_done = (read_state(book_dir) or {}).get("phases", {}).get("per-chapter-slides", {}).get(
        "status"
    ) in ("completed", "skipped")
    if _slides_already_done:
        _info("phase: per-chapter-slides · already completed/skipped, advancing to finalize")
    elif enable_slide_decks:
        run_slide_cohort(book_dir, completed_chapter_slugs)
        phase_git_commit(book_dir, f"podcast({book_slug}): phase 11b slide-deck cohort")
    else:
        update_phase(
            book_dir, phase="per-chapter-slides", status="skipped", extras={"reason": "enable_slide_decks=false"}
        )

    # Audio Engine v2 phases — autonomous (API) engines author + gate dialogue
    # scripts, halt ONCE at H1 with the exact credit estimate, then render
    # into the canonical m4a layout. NotebookLM books mark both phases
    # skipped and continue to the manual finalize halt unchanged.
    from phases.audio_driver import drive_audio_phases

    _audio_outcome, _audio_rc = drive_audio_phases(book_dir, approve_render=approve_audio_render)
    if _audio_outcome == "halted":
        return 0  # clean stop at the H1 spend gate; --resume approves
    if _audio_outcome == "failed":
        return _audio_rc

    # Finalize phase — run G1-G7 gates, halt for human review before publish.
    # NOTE: the PDF companion-book path (0book-*) runs AFTER this halt, inside
    # publish_driver._drive_publish_through_done, so that any issues caught at
    # the podcast review gate are fixed before the book branch is generated.
    _phase_boundary_gate(book_dir, "per-chapter→finalize")
    _info("phase: finalize · run G1-G7 gates via validate_ship_ready.py")
    update_phase(book_dir, phase="finalize", status="running")

    # P3 (Stage 4): auto-run the zero-LLM Arabic-script restoration for
    # audio-sourced Islamic books before the gate. repair_glossary is idempotent
    # and free — it recovers any misassigned Arabic into arabic_script so the
    # reader "Show Arabic" toggle has content. The deterministic canonical/passage
    # restoration (steps 2b/3) and the reader-rendering feature are deferred;
    # until they land the G13 ship-gate only REPORTS coverage, it does not block.
    try:
        import json as _json

        from _content_profile import is_islamic_scholarly

        _state_p = book_dir / "_system" / "orchestrator-state.json"
        _st = _json.loads(_state_p.read_text()) if _state_p.exists() else {}
        if _st.get("source_kind") == "audio" and is_islamic_scholarly(book_dir):
            from restore_arabic import repair_glossary

            _rep = repair_glossary(book_dir)
            _info(f"phase: finalize · auto Arabic-restore (audio Islamic): {_rep}")
    except Exception as _e:  # never block finalize on a best-effort restore
        _err(f"finalize: Arabic auto-restore skipped (non-fatal): {_e}")

    validate_script = Path(__file__).resolve().parents[1] / "validate_ship_ready.py"
    rc, vout, verr = _run([sys.executable, str(validate_script), book_slug])
    print(vout)
    if rc != 0:
        update_phase(
            book_dir,
            phase="finalize",
            status="failed",
            error="G1-G7 gates failed; see stdout for the failing gate",
            extras={"validator_stdout": vout[-2000:], "validator_stderr": verr[-1000:]},
        )
        _err(
            "finalize halt — at least one G1-G7 gate failed. "
            "Fix the cause, then re-invoke `orchestrate_book.py --resume`."
        )
        return 2
    update_phase(book_dir, phase="finalize", status="halted", extras={"verdict": "SHIP-READY"})

    # The reading edition, built HERE rather than only after publish. Its input is
    # _system/source/text/refined-english.md, which has existed since 0b — it never
    # depended on the audio, only sat after it in the phase order. Building it now
    # means the articulated book.md and its PDF are in the Composer at the same
    # stopping point as the chapters and the slide-deck prompts, which is what a
    # human actually reviews. Self-skips unless the book lane can complete without
    # a human artifact; the publish-time call remains the path for the rest.
    from _book_preview import maybe_build_reading_edition_early

    maybe_build_reading_edition_early(book_dir, log=_info)

    # Non-blocking advisories. Emitters live in `_halt_advisories` so this file
    # (grandfathered by the line-count gate) stays their caller, not their home.
    from _halt_advisories import emit_decision_ledger, emit_transcription_advisories

    emit_transcription_advisories(book_dir, _info)
    emit_decision_ledger(book_dir, _info)

    _info("")
    _info("─" * 72)
    _info("Phase finalize complete · halted for human review (SHIP-READY).")
    _info("")
    _info("Review the clean version in the Podcast Factory Astro Site:")
    _info("  cd plan-dashboard && npm run dev")
    _info("  open http://localhost:4321/develop/" + book_slug + "/")
    _info("")
    # Engine-aware halt card. Per-episode routing: a book may be autonomous
    # (ElevenLabs) yet flip individual episodes to NotebookLM via
    # episode_engine_overrides — so the card may show BOTH an "already rendered"
    # note (for the API episodes) AND the NotebookLM upload ritual (for the
    # overridden ones). The no-overrides path is byte-identical to before (the
    # golden-test latch): pure-NotebookLM books print the full unfiltered table,
    # pure-ElevenLabs books print only the rendered note.
    # Shared filter: the SAME `notebooklm_episode_filter` the audio-ingest phase
    # uses, so the halt card and the phase agree on which episodes need the ritual.
    # None = pure-NotebookLM (all episodes); empty set = pure-API (none); a subset
    # = mixed-engine book.
    try:
        from _audio_engines import notebooklm_episode_filter

        _all_eps = [e["episode"] for e in _discover_episode_mapping(book_dir)]
        _nlm_filter: set[str] | None = notebooklm_episode_filter(book_dir, _all_eps)
    except Exception:
        _all_eps, _nlm_filter = [], None

    if _nlm_filter is None:
        _has_api = False
    elif not _nlm_filter:
        _has_api = True
    else:
        _has_api = any(ep not in _nlm_filter for ep in _all_eps)

    if _has_api:
        _info("Audio engine: elevenlabs — those episodes are ALREADY rendered into")
        _info("m4a/ with script-derived transcripts (no NotebookLM step, no")
        _info("normalize/transcribe needed). Review the audio with the reader.")
        _info("")
    # NotebookLM upload ritual: for a pure-NotebookLM book (_nlm_filter is None)
    # or any episode overridden to NotebookLM (non-empty set).
    if _nlm_filter is None or _nlm_filter:
        try:
            _print_notebooklm_table(book_dir, filter_episode_ids=_nlm_filter)
        except Exception as _tbl_exc:
            _info(f"  [notebooklm table error: {_tbl_exc}]")
        _info("")
        _info("After downloading the generated .m4a files, drop them anywhere under")
        _info("m4a/ — names don't matter. The next --resume normalizes them to canonical")
        _info("chapter order and transcribes via Azure Speech automatically (the")
        _info("audio-ingest phase) — no manual CLI step needed.")
        _info("")
        # Durable worklist file — the operator works ONE checklist across sessions
        # (it survives terminal scroll); audio-ingest + 0book-slide-import consume
        # the drops automatically on --resume.
        try:
            from _notebooklm_table import build_worklist_lines
            from assemble_bundle import build_upload_rows

            _wl_rows = build_upload_rows(book_dir, _discover_episode_mapping(book_dir), filter_episode_ids=_nlm_filter)
            _resume_cmd = f"python3 scripts/podcast/orchestrate_book.py --resume {book_slug}"
            _wl_path = book_dir / "_system" / "notebooklm-worklist.md"
            _wl_path.parent.mkdir(parents=True, exist_ok=True)
            _wl_path.write_text(
                "\n".join(build_worklist_lines(book_dir, upload_rows=_wl_rows, resume_cmd=_resume_cmd)) + "\n",
                encoding="utf-8",
            )
            _info(f"Durable worklist written: {_wl_path.relative_to(REPO_ROOT)}")
            _info("")
        except Exception as _wl_exc:
            _info(f"  [worklist file skipped: {_wl_exc}]")
    # Slide-deck generation always runs through NotebookLM's Slide-deck tool,
    # independent of the audio engine — print the card on EVERY path (it
    # self-skips when no chapter has a converged deck).
    try:
        _print_slide_deck_card(book_dir)
    except Exception as _card_exc:
        _info(f"  [slide-deck card error: {_card_exc}]")
    _info("")
    _info("When satisfied, authorize publish + trainer + merge:")
    _info(f"  python3 scripts/podcast/orchestrate_book.py --resume {book_slug}")
    _info("─" * 72)
    return 0


def _print_slide_deck_card(book_dir: Path) -> None:
    """Print the slide-deck generation card at the finalize halt.

    One row per chapter with a converged deck pair in slide-decks/ — the human
    generates each deck in NotebookLM's Slide deck tool during the SAME visit
    as the episode uploads, then drops the exported PDFs at the printed paths
    so 0book-slide-import can weave them into the reading edition on --resume.
    Prints nothing when no chapter participates (deck-less books)."""
    parent = Path(__file__).resolve().parents[1]
    if str(parent) not in sys.path:
        sys.path.insert(0, str(parent))
    from _notebooklm_table import build_slide_deck_card

    lines = build_slide_deck_card(book_dir)
    if not lines:
        return
    _info("")
    for line in lines:
        _info(line)


def _discover_episode_mapping(book_dir: Path) -> list[dict]:
    """[{episode, chapter, n}] for every episode, in order.

    Prefers the Phase-0g episode map; falls back to discovering directly from
    episodes/ for books where the map isn't generated yet. Shared by the
    NotebookLM table and the per-episode engine routing at finalize so both see
    the SAME episode set.
    """
    parent = Path(__file__).resolve().parents[1]
    if str(parent) not in sys.path:
        sys.path.insert(0, str(parent))
    from assemble_bundle import _load_episode_map

    mapping = _load_episode_map(book_dir)
    if mapping:
        return mapping
    import re as _re

    ep_pat = _re.compile(r"^(EP(\d+)-(.*))\.txt$")
    ep_dir = book_dir / "episodes"
    if not ep_dir.exists():
        return []
    out: list[dict] = []
    for ep_file in sorted(ep_dir.glob("EP*.txt")):
        m = ep_pat.match(ep_file.name)
        if not m:
            continue
        ep_slug, ep_num_str, ch_slug = m.group(1), m.group(2), m.group(3)
        out.append({"episode": ep_slug, "chapter": f"ch{ep_num_str}-{ch_slug}", "n": int(ep_num_str)})
    return out


def _print_notebooklm_table(book_dir: Path, filter_episode_ids: set[str] | None = None) -> None:
    """Print the NotebookLM upload table at finalize halt.

    Reuses discovery + formatting helpers from assemble_bundle.py.
    Prints per-episode rows: EP | Title | Upload source | Customize paste |
    NotebookLM Format setting | Length setting.

    *filter_episode_ids*: when None (the default), ALL episodes are listed —
    byte-identical to the pre-override behavior (the golden-test latch). When a
    set is given (mixed-engine books), only those episode ids are listed, so the
    operator uploads exactly the per-episode NotebookLM overrides.
    """
    try:
        # Import helpers from sibling script (same scripts/podcast/ parent).
        parent = Path(__file__).resolve().parents[1]
        if str(parent) not in sys.path:
            sys.path.insert(0, str(parent))
        from _notebooklm_table import render_upload_table_lines
        from assemble_bundle import build_upload_rows
    except ImportError as exc:
        _info(f"  [notebooklm table skipped — import error: {exc}]")
        return

    mapping = _discover_episode_mapping(book_dir)
    if not mapping:
        _info("  [notebooklm table skipped — no episodes found]")
        return

    # SINGLE row constructor — shared with the durable worklist so both render
    # from identical data (byte-identical to the prior inline loop: the latch).
    rows = build_upload_rows(book_dir, mapping, filter_episode_ids=filter_episode_ids)

    _info("─" * 72)
    _info("NOTEBOOKLM UPLOAD TABLE")
    _info("")
    _info("Per row: click the CHAPTER cell to open the SOURCE to upload, and the")
    _info("EPISODE cell to open the FRAMING to paste into NotebookLM's Customize box.")
    _info("")
    for line in render_upload_table_lines(rows):
        _info(f"  {line}")
