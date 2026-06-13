"""phases/audio_driver.py — Audio Engine v2 orchestrator phases (Step 6).

Drives the two autonomous-audio phases between per-chapter-slides and
finalize:

    audio-script   per-chapter dialogue-script authorship + pre-synthesis
                   gate convergence (Claude Max — no API spend)
    audio-render   ONE halt per book before the first paid render (H1:
                   exact deterministic credit estimate, await approval),
                   then ElevenLabs synthesis into the canonical m4a layout

NotebookLM books mark both phases "skipped" and flow to the finalize halt
exactly as before — the manual upload/download ritual is unchanged. API
books flow straight through: author script -> gate -> render -> video ->
finalize, with H1 as the ONLY stop (mirrors the Tier-2 first-launch spend
gate).

Re-entry contract (resume_dispatcher): every phase here is idempotent —
completed/skipped phases are skipped on re-entry; a halted audio-render
re-enters with approve_render=True after the human re-invokes --resume.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _progress import read_state, update_phase  # noqa: E402
from _subprocess import err as _err, info as _info  # noqa: E402
from phases.scaffold import phase_git_commit  # noqa: E402

# Sentinel return code: halted at the H1 spend gate (clean stop, not failure).
AUDIO_HALT_RC = 0


def _phase_status(book_dir: Path, phase: str) -> str:
    state = read_state(book_dir) or {}
    return state.get("phases", {}).get(phase, {}).get("status", "pending")


def drive_audio_phases(book_dir: Path, *, approve_render: bool = False) -> tuple[str, int]:
    """Run audio-script + audio-render for this book.

    Returns (outcome, rc) where outcome is one of:
      "skipped"   manual engine — both phases skipped, continue to finalize
      "halted"    H1 spend gate — stop the driver cleanly (rc 0)
      "done"      audio rendered — continue to finalize
      "failed"    a phase failed (rc 2)
    """
    from _audio_engines import audio_engine_for_book, is_autonomous
    engine = audio_engine_for_book(book_dir)

    if not is_autonomous(engine):
        for phase in ("audio-script", "audio-render"):
            if _phase_status(book_dir, phase) not in ("completed", "skipped"):
                update_phase(book_dir, phase=phase, status="skipped",
                             extras={"reason": f"audio_engine={engine.name} (manual)"})
        return "skipped", 0

    state = read_state(book_dir) or {}
    book_slug = state.get("book_slug") or book_dir.name

    # ── Phase audio-script: author + converge every chapter's script ─────────
    if _phase_status(book_dir, "audio-script") in ("completed", "skipped"):
        _info("phase: audio-script · already completed, skipping")
    else:
        rc = _drive_audio_script(book_dir, book_slug)
        if rc != 0:
            return "failed", rc

    # ── Phase audio-render: H1 halt, then render ─────────────────────────────
    if _phase_status(book_dir, "audio-render") in ("completed", "skipped"):
        _info("phase: audio-render · already completed, skipping")
        return "done", 0
    return _drive_audio_render(book_dir, book_slug, approve_render=approve_render)


def _chapter_slugs(book_dir: Path) -> list[str]:
    return sorted(p.stem for p in (book_dir / "chapter-contracts").glob("*.yml"))


def _drive_audio_script(book_dir: Path, book_slug: str) -> int:
    from _dialogue_convergence import converge_dialogue_script, read_verdict
    from _dialogue_script import script_path_for
    from _authoring._dialogue import _episode_id_for_chapter
    from _audio_engines import engine_for_episode, ENGINE_NOTEBOOKLM

    slugs = _chapter_slugs(book_dir)
    if not slugs:
        update_phase(book_dir, phase="audio-script", status="failed",
                     error="no chapter contracts — Phase 0d must run first")
        return 2

    _info(f"phase: audio-script · {len(slugs)} chapter(s) — author + gate dialogue scripts")
    update_phase(book_dir, phase="audio-script", status="running")
    verdicts: dict[str, str] = {}
    failed: list[str] = []
    for slug in slugs:
        try:
            episode_id, _ = _episode_id_for_chapter(book_dir, slug)
        except Exception as e:  # noqa: BLE001
            failed.append(slug)
            _err(f"  [audio-script] {slug}: cannot resolve episode id: {e}")
            continue
        # Per-episode NotebookLM override: dialogue-script authorship + the
        # convergence gate are wasted work for an episode rendered manually in
        # NotebookLM — skip it here (it never reaches the ElevenLabs renderer).
        if engine_for_episode(book_dir, episode_id) == ENGINE_NOTEBOOKLM:
            _info(f"  [audio-script] {slug}: engine override -> notebooklm, skipping script")
            verdicts[slug] = "skipped-notebooklm"
            continue
        prior = read_verdict(book_dir, episode_id)
        if prior in ("SHIP-READY", "SHIP-WITH-CAUTION") and \
                script_path_for(book_dir, episode_id).exists():
            _info(f"  [audio-script] {slug}: already converged ({prior}), skipping")
            verdicts[slug] = prior
            continue
        try:
            result = converge_dialogue_script(book_dir, slug, log=_info)
        except Exception as e:  # noqa: BLE001
            failed.append(slug)
            _err(f"  [audio-script] {slug}: convergence error: {e}")
            continue
        verdicts[slug] = result.verdict
        if result.verdict not in ("SHIP-READY", "SHIP-WITH-CAUTION"):
            failed.append(slug)

    if failed:
        update_phase(
            book_dir, phase="audio-script", status="failed",
            error=f"{len(failed)} script(s) failed convergence: {', '.join(failed)}",
            extras={"verdicts": verdicts})
        _err(f"audio-script: {len(failed)} chapter script(s) failed — fix and --resume.")
        return 2
    update_phase(book_dir, phase="audio-script", status="completed",
                 extras={"verdicts": verdicts})
    phase_git_commit(book_dir,
                     f"podcast({book_slug}): phase audio-script ({len(verdicts)} scripts gated)")
    return 0


def _render_plan(book_dir: Path) -> tuple[list[str], int]:
    """(episodes still needing render, total credit estimate for them)."""
    from render_dialogue_audio import episodes_with_scripts, chapter_stem_for_episode
    from _dialogue_script import parse_dialogue_script, script_path_for, script_char_count
    from _audio_engines import (
        audio_engine_for_book, credit_estimate, engine_for_episode, ENGINE_NOTEBOOKLM,
    )

    engine = audio_engine_for_book(book_dir)
    pending: list[str] = []
    estimate = 0
    for ep in episodes_with_scripts(book_dir):
        # A NotebookLM-overridden episode is never API-rendered and must not
        # contribute to the H1 credit estimate — skip before the m4a check.
        if engine_for_episode(book_dir, ep) == ENGINE_NOTEBOOKLM:
            continue
        stem = chapter_stem_for_episode(book_dir, ep)
        if (book_dir / "m4a" / f"{stem}.m4a").exists():
            continue
        pending.append(ep)
        turns = parse_dialogue_script(
            script_path_for(book_dir, ep).read_text(encoding="utf-8"))
        estimate += credit_estimate(engine, script_char_count(turns))
    return pending, estimate


def _drive_audio_render(book_dir: Path, book_slug: str,
                        *, approve_render: bool) -> tuple[str, int]:
    pending, estimate = _render_plan(book_dir)
    if not pending:
        update_phase(book_dir, phase="audio-render", status="completed",
                     extras={"note": "all episodes already rendered"})
        return "done", 0

    if not approve_render:
        # H1: the ONLY halt on the autonomous path — exact deterministic
        # credit estimate, await human approval (mirrors the Tier-2 spend gate).
        update_phase(book_dir, phase="audio-render", status="halted",
                     extras={"credit_estimate": estimate,
                             "episodes_pending": pending})
        _info("")
        _info("─" * 72)
        _info("Phase audio-render · HALTED at H1 (paid-synthesis spend gate).")
        _info("")
        _info(f"  Episodes to render : {len(pending)}")
        for ep in pending:
            _info(f"    - {ep}")
        _info(f"  Engine             : elevenlabs (eleven_v3, final quality — no Flash)")
        _info(f"  EXACT credit estimate: {estimate:,} credits (chars x registry rate)")
        try:
            from _audio_engines import credits_to_usd
            _info(f"  Notional plan value  : ~${credits_to_usd(estimate):.2f}")
        except Exception:  # noqa: BLE001
            pass
        _info("")
        _info("To approve the spend and render, re-invoke:")
        _info(f"  python3 scripts/podcast/orchestrate_book.py --resume {book_slug}")
        _info("─" * 72)
        return "halted", AUDIO_HALT_RC

    from render_dialogue_audio import render_episode
    _info(f"phase: audio-render · H1 approved — rendering {len(pending)} episode(s)")
    update_phase(book_dir, phase="audio-render", status="running",
                 extras={"credit_estimate": estimate})
    metered_total = 0
    sanity_flags: dict[str, list[str]] = {}
    for ep in pending:
        try:
            result = render_episode(book_dir, ep, approved=True,
                                    style_gate=True, log=_info)
        except Exception as e:  # noqa: BLE001
            update_phase(book_dir, phase="audio-render", status="failed",
                         error=f"[{ep}] {e}")
            _err(f"audio-render failed on {ep}: {e}")
            return "failed", 2
        if result.credits_metered:
            metered_total += result.credits_metered
        # Flag for pre-publish review: a chunk sanity failure OR a residual
        # below-threshold style score after the bounded retake.
        if result.sanity_failures or result.style_passed is False:
            sanity_flags[ep] = result.notes
    update_phase(book_dir, phase="audio-render", status="completed",
                 extras={"credits_metered": metered_total,
                         "credit_estimate": estimate,
                         "sanity_flags": sanity_flags})
    phase_git_commit(
        book_dir,
        f"podcast({book_slug}): phase audio-render "
        f"({len(pending)} episodes, {metered_total:,} credits)")
    if sanity_flags:
        _err(f"audio-render: sanity flags on {len(sanity_flags)} episode(s) — "
             f"review before publish: {sorted(sanity_flags)}")
    return "done", 0
