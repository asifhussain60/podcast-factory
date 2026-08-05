"""phases/audio_ingest_driver.py — drive_audio_ingest (NotebookLM audio loop).

The self-correcting INPUT side of the NotebookLM audio round-trip. Runs at the
top of publish_driver._drive_publish_through_done (after the finalize halt is
cleared, before the PDF book branch), so the manually-downloaded NotebookLM
audio is normalized + transcribed automatically on --resume instead of by a
hand-run CLI ritual.

Contract (mirrors the proven 0book-slide-import halt):
  - PURE-API / ElevenLabs book  -> no-op `skipped` (no NotebookLM episodes).
  - Audio not dropped yet        -> clean `halted` (rc 3); --resume re-enters.
  - Drift in dropped filenames   -> deterministically repaired (normalize_m4a).
  - Every NotebookLM episode now  -> `ingested` (completed) and git-committed.
    has audio + transcript
  - Anything still missing        -> `halted` (rc 3) with the precise gaps.

Idempotent: a second pass with everything present transcribes nothing new and
finds no rename actions, so it completes immediately. Engine routing reuses the
SAME `notebooklm_episode_filter` the finalize halt uses, so the halt card and
this phase can never disagree about which episodes need the ritual.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _progress import read_state, update_phase
from _subprocess import err as _err
from _subprocess import info as _info


def _episode_mapping(book_dir: Path) -> list[dict]:
    """The episode↔chapter mapping, via the finalize-halt discovery (one source)."""
    from phases.chapter_driver import _discover_episode_mapping

    return _discover_episode_mapping(book_dir)


def _canonical_stems_by_num(book_dir: Path) -> dict[int, str]:
    """Map chapter number -> canonical stem (ch19c-...) from the chapter files,

    so the completeness check targets the SAME canonical names normalize_m4a /
    transcribe_notebooklm write (letter suffixes included).
    """
    from normalize_m4a import load_chapters

    return {c.num: c.stem for c in load_chapters(book_dir)}


def drive_audio_ingest(book_dir: Path) -> tuple[str, int]:
    """Normalize + transcribe dropped NotebookLM audio; gate on completeness.

    Returns (outcome, rc): ("skipped",0) | ("ingested",0) | ("halted",3) |
    ("failed",2). publish_driver maps halted/failed to its own return.
    """
    state = read_state(book_dir) or {}
    book_slug = state.get("book_slug") or book_dir.name

    # Already done on a prior resume — stay idempotent, don't re-commit.
    block = (state.get("phases") or {}).get("audio-ingest") or {}
    if block.get("status") in ("completed", "skipped"):
        return "skipped", 0

    # ── Resolve which episodes need the NotebookLM ritual ────────────────────
    try:
        from _audio_engines import notebooklm_episode_filter

        mapping = _episode_mapping(book_dir)
        all_eps = [e["episode"] for e in mapping]
        nlm_filter = notebooklm_episode_filter(book_dir, all_eps)
    except Exception as exc:
        _err(f"audio-ingest: could not resolve audio engine — {exc}")
        update_phase(book_dir, phase="audio-ingest", status="failed", error=str(exc))
        return "failed", 2

    # Pure-autonomous book (empty set): no manual audio at all.
    if nlm_filter == set():
        update_phase(
            book_dir,
            phase="audio-ingest",
            status="skipped",
            extras={"reason": "no NotebookLM episodes (autonomous engine)"},
        )
        _info("phase: audio-ingest · skipped (autonomous audio engine — no manual drop).")
        return "skipped", 0

    # nlm_filter is None (pure NotebookLM → all) or a non-empty subset (mixed).
    nlm_entries = mapping if nlm_filter is None else [e for e in mapping if e["episode"] in nlm_filter]
    if not nlm_entries:
        update_phase(book_dir, phase="audio-ingest", status="skipped", extras={"reason": "no episodes to ingest"})
        return "skipped", 0

    _info("phase: audio-ingest · normalize + transcribe dropped NotebookLM audio")
    update_phase(book_dir, phase="audio-ingest", status="running")

    m4a_dir = book_dir / "m4a"
    tx_dir = m4a_dir / "transcripts"
    stem_by_num = _canonical_stems_by_num(book_dir)
    expected = [(e["episode"], stem_by_num.get(e["n"]) or e["chapter"]) for e in nlm_entries]

    worklist = book_dir / "_system" / "notebooklm-worklist.md"
    worklist_hint = (
        f"  See the worklist: {worklist.relative_to(book_dir.parents[2])}"
        if worklist.exists()
        else "  Re-run after dropping the generated .m4a files under m4a/."
    )

    # ── Presence gate: has the operator dropped anything yet? ────────────────
    try:
        from normalize_m4a import apply_plan, plan_book
    except Exception as exc:
        update_phase(book_dir, phase="audio-ingest", status="failed", error=str(exc))
        _err(f"audio-ingest: normalize_m4a unavailable — {exc}")
        return "failed", 2

    present_canonical = [s for _, s in expected if (m4a_dir / f"{s}.m4a").exists()]
    plan = plan_book(book_dir)
    loose_audio = [e for e in plan if e.get("kind") == "audio"]

    if not present_canonical and not loose_audio:
        update_phase(
            book_dir, phase="audio-ingest", status="halted", extras={"reason": "awaiting NotebookLM audio drop"}
        )
        _info("audio-ingest halted — no audio dropped yet.")
        _info(worklist_hint)
        return "halted", 3

    # ── Normalize: deterministically repair filename drift (SWAP/MATCH only) ──
    if plan:
        try:
            renamed = apply_plan(book_dir, plan, log=_info)
            if renamed:
                _info(f"  normalized {renamed} dropped file(s) to canonical order.")
        except Exception as exc:
            update_phase(book_dir, phase="audio-ingest", status="failed", error=str(exc))
            _err(f"audio-ingest: normalize failed — {exc}")
            return "failed", 2
        ambiguous = [e for e in plan if e.get("verdict") in ("AMBIGUOUS", "COLLISION")]
        for e in ambiguous:
            _info(f"  UNRESOLVED {e.get('kind')}: {e.get('file')} — {e.get('note', 'resolve by hand')}")

    # ── Transcribe every canonical m4a still missing its transcript ──────────
    try:
        from transcribe_notebooklm import transcribe_book

        transcribe_book(book_dir, log=_info)
    except Exception as exc:
        update_phase(book_dir, phase="audio-ingest", status="failed", error=str(exc))
        _err(f"audio-ingest: transcription failed — {exc}")
        return "failed", 2

    # ── Completeness gate: every NotebookLM episode has audio + transcript ───
    missing: list[str] = []
    for ep, stem in expected:
        if not (m4a_dir / f"{stem}.m4a").exists():
            missing.append(f"{ep}: m4a/{stem}.m4a")
        elif not (tx_dir / f"{stem}.transcript.txt").exists():
            missing.append(f"{ep}: m4a/transcripts/{stem}.transcript.txt")

    if missing:
        update_phase(book_dir, phase="audio-ingest", status="halted", extras={"missing": missing})
        _info(f"audio-ingest halted — {len(missing)} episode(s) still missing audio/transcript:")
        for m in missing:
            _info(f"    · {m}")
        _info(worklist_hint)
        return "halted", 3

    update_phase(book_dir, phase="audio-ingest", status="completed", extras={"episodes_ingested": len(expected)})
    try:
        from phases.scaffold import phase_git_commit

        phase_git_commit(
            book_dir,
            f"podcast({book_slug}): phase audio-ingest "
            f"({len(expected)} NotebookLM episode(s) normalized + transcribed)",
        )
    except Exception as exc:
        _info(f"  [audio-ingest commit skipped: {exc}]")
    _info(f"phase audio-ingest complete · {len(expected)} episode(s) have audio + transcript.")
    return "ingested", 0
