#!/usr/bin/env python3
"""augment_fiction_sidecar.py — Phase 0e fiction augmentation (sidecar-only).

For fiction books (content_profile="fiction"), Phase 0e must NEVER modify
the narrative chapter prose. Instead, this augmenter produces a companion
glossary + host-aside file per chapter, which the framing author can consult
when building the episode framing/customize prompt.

CONSTRAINT (enforced by design):
  - Reads: BOOK_DIR/chapters/ch*.txt  (READ ONLY, never writes)
  - Writes: BOOK_DIR/_system/fiction-companion/ch*.companion.md ONLY

Uses the need-detector from _augment_registry to skip chapters with no
culture-dense content (no LLM spend on sparse chapters).

Engine: Claude Max (TASK_AUGMENT, ENGINE_CLAUDE_MAX) via `claude -p`.

USAGE
    python3 scripts/podcast/augment_fiction_sidecar.py \\
        --slug journey-to-the-west-vol-1

OUTPUTS (per chapter that passes the need-detector)
    BOOK_DIR/_system/fiction-companion/ch-001.companion.md
    BOOK_DIR/_system/fiction-sidecar-log.md
"""
from __future__ import annotations

import argparse
import datetime as _dt
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from _engine import engine_guard, TASK_AUGMENT, ENGINE_CLAUDE_MAX  # noqa: E402
from _paths import resolve_content  # noqa: E402
from _augment_registry import needs_augmentation  # noqa: E402
from _authoring._core import (  # noqa: E402
    AuthoringError,
    PHASE_0E_CHAPTER_TIMEOUT,
    _run_claude_p_with_retry,
    _compute_sc_timeout,
)


# ─── Sidecar prompt ───────────────────────────────────────────────────────────

def _build_sidecar_prompt(chapter_file: Path, companion_path: Path) -> str:
    return (
        f"You are producing a COMPANION GLOSSARY for a fiction podcast chapter from "
        f"*Journey to the West* (Vol 1), written for Western listeners who are unfamiliar "
        f"with Chinese mythology, classical fiction, and Daoist/Buddhist cultural references.\n\n"
        f"INPUT (READ ONLY — do NOT modify this file): `{chapter_file}`\n\n"
        f"TASK:\n"
        f"  1. Read `{chapter_file}` in full.\n"
        f"  2. Identify every term, name, place, or concept that a Western listener would "
        f"     likely find confusing or culturally unfamiliar (characters, deities, kingdoms, "
        f"     mythological creatures, Daoist/Buddhist concepts, ritual objects, titles, etc.).\n"
        f"  3. Write a companion file at `{companion_path}` with TWO sections:\n\n"
        f"     ## Glossary\n\n"
        f"     One entry per term in this format:\n"
        f"     **Term** — Plain English definition in 1–3 sentences. Include:\n"
        f"       - What it is (deity / character / place / concept / creature)\n"
        f"       - Its significance in Chinese mythology or the novel\n"
        f"       - Any equivalent Western concept if useful (e.g., 'like a Chinese Olympus')\n\n"
        f"     ## Host Asides\n\n"
        f"     2–4 brief context notes for the podcast hosts to weave into the episode, "
        f"     each starting with '> Aside:'. These are conversational prompts, not prose. "
        f"     Example: '> Aside: The Jade Emperor is the supreme ruler of Heaven in Chinese "
        f"     mythology — equivalent to Zeus but with more bureaucratic paperwork.'\n\n"
        f"HARD RULES:\n"
        f"  - Do NOT modify `{chapter_file}` in any way — it is READ ONLY.\n"
        f"  - Write ONLY to `{companion_path}`. Create its parent directory if needed.\n"
        f"  - No preamble. Begin the output with `## Glossary`.\n"
        f"  - Keep each glossary entry to 1–3 sentences maximum.\n"
        f"  - If the chapter has no culturally unfamiliar content (very rare), write an "
        f"    empty glossary section with a note: 'No culture-dense terms identified.'\n\n"
        f"Exit when `{companion_path}` has been written."
    )


# ─── Per-chapter sidecar runner ───────────────────────────────────────────────

def author_fiction_sidecar(
    book_dir: Path,
    timeout: int = PHASE_0E_CHAPTER_TIMEOUT,
    log=print,
) -> str:
    """Run the fiction sidecar augmenter for all chapters in book_dir.

    Idempotent: skips chapters whose companion file already exists.
    Uses the need-detector to skip culture-sparse chapters without LLM spend.
    Returns a status summary string (same contract as author_phase_0e).
    """
    engine_guard(TASK_AUGMENT, ENGINE_CLAUDE_MAX)

    chapters_dir = book_dir / "chapters"
    companion_dir = book_dir / "_system" / "fiction-companion"
    log_path = book_dir / "_system" / "fiction-sidecar-log.md"

    chapter_files = sorted(chapters_dir.glob("ch*.txt"))
    if not chapter_files:
        raise AuthoringError(
            phase="0e-fiction-sidecar",
            message=f"no chapters found under {chapters_dir} (Phase 0d should have produced them)",
            manual_fallback="Run Phase 0d first.",
        )

    companion_dir.mkdir(parents=True, exist_ok=True)
    if not log_path.exists():
        log_path.write_text(
            f"# Fiction sidecar log — {book_dir.name}\n\n"
            f"Per-chapter companion status. Rows with COMPANION mark idempotent checkpoints.\n\n",
            encoding="utf-8",
        )

    existing_log = log_path.read_text(encoding="utf-8")
    already_done: set[str] = set()
    for line in existing_log.splitlines():
        s = line.strip()
        if s.startswith("- ") and ": COMPANION" in s:
            stem = s[2:].split(":", 1)[0].strip()
            already_done.add(stem)

    log(f"  phase 0e-fiction · sidecar loop ({len(chapter_files)} chapters, "
        f"{len(already_done)} already done)")

    skipped_no_need = 0
    done = 0
    failures: list[tuple[str, str]] = []

    for chapter_file in chapter_files:
        stem = chapter_file.stem
        companion_path = companion_dir / f"{stem}.companion.md"

        if stem in already_done:
            log(f"    {stem} · skip (companion already written)")
            continue

        # Need-detector gate — cheap heuristic, zero LLM spend
        chapter_text = chapter_file.read_text(encoding="utf-8")
        if not needs_augmentation(chapter_text, content_profile="fiction"):
            log(f"    {stem} · skip (need-detector: no culture-dense content)")
            skipped_no_need += 1
            ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with log_path.open("a", encoding="utf-8") as f:
                f.write(f"- {stem}: COMPANION SKIPPED (no culture-dense content) at {ts}\n")
            continue

        chapter_words = len(chapter_text.split())
        per_chapter_timeout = _compute_sc_timeout(chapter_words)
        log(f"    {stem} · generating companion ({chapter_words} words, timeout={per_chapter_timeout}s)")

        prompt = _build_sidecar_prompt(chapter_file, companion_path)
        try:
            rc, stdout, stderr = _run_claude_p_with_retry(
                prompt, timeout=per_chapter_timeout,
                book_dir=book_dir, phase="0e-fiction-sidecar", step=stem,
                log=log,
            )
        except AuthoringError as e:
            if "BOTH attempts timed out" in str(e):
                raise
            raise

        if rc != 0:
            failures.append((stem, f"rc={rc}: {(stderr or '').strip()[:200]}"))
            log(f"    {stem} · FAILED rc={rc}")
            continue

        if not companion_path.exists() or companion_path.stat().st_size == 0:
            raise AuthoringError(
                phase="0e-fiction-sidecar",
                message=(
                    f"{stem} returned rc=0 but no companion file at {companion_path}. "
                    f"claude -p exited without writing."
                ),
                manual_fallback="Check stdout/stderr. If a permission issue, use --permission-mode acceptEdits.",
                stdout=stdout or "",
                stderr=stderr or "",
            )

        done += 1
        ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with log_path.open("a", encoding="utf-8") as f:
            f.write(f"- {stem}: COMPANION written at {ts}\n")
        log(f"    {stem} · OK → {companion_path.relative_to(book_dir)}")

    if failures:
        raise AuthoringError(
            phase="0e-fiction-sidecar",
            message=(
                f"{len(failures)} of {len(chapter_files)} chapters failed: "
                + "; ".join(f"{s}: {m}" for s, m in failures[:3])
            ),
            manual_fallback=(
                "Check chapter files. Each chapter must be writable and non-empty. "
                "Add '- <stem>: COMPANION ...' rows to fiction-sidecar-log.md to skip "
                "already-handled chapters and re-invoke orchestrate-book --resume."
            ),
        )

    return (
        f"0e-fiction-sidecar: {len(chapter_files)} chapters scanned, "
        f"{done} companion(s) written, {skipped_no_need} skipped (no culture-density), "
        f"{len(already_done)} skipped (already done)"
    )


# ─── CLI entry point ──────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Fiction sidecar augmenter — companion glossary for podcast hosts.",
    )
    ap.add_argument("--slug", required=True, help="Book slug, e.g. journey-to-the-west-vol-1")
    ap.add_argument("--force", action="store_true", help="Re-run even for chapters with existing companion files")
    args = ap.parse_args()

    book_dir = resolve_content(args.slug)
    if not book_dir.exists():
        raise SystemExit(f"ERROR: book directory not found for slug '{args.slug}'")

    if args.force:
        # Wipe the log so idempotency check passes nothing as done
        log_path = book_dir / "_system" / "fiction-sidecar-log.md"
        if log_path.exists():
            log_path.unlink()
        print(f"  --force: cleared sidecar log, will re-generate all companion files")

    print(f"Fiction sidecar augmenter — {args.slug}")
    result = author_fiction_sidecar(book_dir)
    print(f"\n{result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
