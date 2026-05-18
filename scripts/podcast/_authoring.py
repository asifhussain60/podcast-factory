#!/usr/bin/env python3
"""_authoring.py — LLM-shellout helpers for orchestrate_book.py (Phase A stubs).

The autonomous orchestrator drives Phases 0a (Azure, deterministic) and 0f
(state-file write, deterministic) directly in Python. Phases 0b–0e (English
refinement · Arabic phonetic pass · chapter design · enrichment) and
per-chapter framing authorship are **LLM authoring** — they require Claude
Code to read the source, apply the conversational `/podcast` skill's
authoring rules, and write the artifacts.

The mechanism: shell out to `claude -p "<prompt>"` (Claude Code headless
mode) with a prompt that names the phase + the BOOK_DIR. The invoked Claude
Code session re-enters the orchestrator agent's spec via the canonical
wrapper, reads the relevant SKILL.md sections, performs the authoring, and
exits when done. The Python driver captures stdout/stderr and parses the
phase's expected output paths.

This file holds **Phase A stubs**:
- `_run_claude_p(prompt, timeout)` — the shellout primitive (real)
- `author_phase_0b(book_dir, ...)` — stub (raises NotImplementedError with a
  clear message until the LLM-call prompt template is authored)
- `author_phase_0c/0d/0e(...)`, `author_framing(...)` — same shape

When Phase B (the per-chapter convergence loop) is implemented, the framing-
authorship stub is the first one to fill in. The Azure ingest (Phase 0a) is
already production-ready via `ingest_source.py`.

USAGE (from orchestrate_book.py)

    from _authoring import (
        author_phase_0b, author_phase_0c, author_phase_0d, author_phase_0e,
        author_framing, AuthoringError,
    )
    try:
        author_phase_0b(book_dir)
    except AuthoringError as e:
        # Update state; halt cleanly.
        ...

DESIGN NOTES

- Each stub names the EXACT next-step Claude Code command in its
  NotImplementedError so the human can drive that phase manually via
  conversational `/podcast` and then `--resume` the orchestrator.
- This file does NOT contain phase prompts inline — prompts are authored
  separately under `content/podcast/.skill/_authoring-prompts/<phase>.md`
  (the directory will exist once Phase B lands). Keeping prompts out of
  Python keeps them human-editable + reviewable.
- Timeouts default to 600 seconds (10 min) per call; orchestrate_book.py
  may override per phase.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

DEFAULT_TIMEOUT = 600  # 10 minutes
CLAUDE_CMD = "claude"  # resolved via PATH


class AuthoringError(RuntimeError):
    """Raised when an LLM-authoring shellout fails or is not yet implemented."""

    def __init__(self, phase: str, message: str, manual_fallback: str = ""):
        super().__init__(message)
        self.phase = phase
        self.manual_fallback = manual_fallback


def _run_claude_p(
    prompt: str,
    *,
    cwd: Path | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[int, str, str]:
    """Run `claude -p "<prompt>"` synchronously. Return (rc, stdout, stderr).

    Phase A: implemented but unused by current orchestrate_book.py stubs.
    Phase B (when LLM authoring lands) will route through this primitive.
    """
    try:
        proc = subprocess.run(
            [CLAUDE_CMD, "-p", prompt],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError as e:
        raise AuthoringError(
            phase="(shellout)",
            message=(
                f"`{CLAUDE_CMD}` not found on PATH. Install Claude Code CLI "
                f"(https://docs.claude.com/en/docs/claude-code/quickstart) or "
                f"add the binary to PATH."
            ),
            manual_fallback="Drive the phase via conversational /podcast skill.",
        ) from e
    except subprocess.TimeoutExpired as e:
        raise AuthoringError(
            phase="(shellout)",
            message=f"LLM authoring timed out after {timeout}s.",
            manual_fallback="Resume manually via /podcast and `--resume` the orchestrator.",
        ) from e


def _not_yet_implemented(phase: str, manual_steps: str) -> "AuthoringError":
    """Return an AuthoringError naming the manual fallback for Phase B work."""
    return AuthoringError(
        phase=phase,
        message=(
            f"Phase {phase} LLM authoring is a Phase B stub (orchestrate_book.py "
            f"is currently Phase A only — autonomy stops at the end of Phase 0a). "
            f"Drive this phase manually via the conversational /podcast skill, "
            f"then re-invoke orchestrate-book with --resume to pick up at the "
            f"next deterministic checkpoint."
        ),
        manual_fallback=manual_steps,
    )


# ─── Phase 0b — English refinement ───────────────────────────────────────────
def author_phase_0b(book_dir: Path) -> None:
    """Refine the Azure-translated raw extract into clean English prose.

    Reads:  BOOK_DIR/_system/source/text/raw-extract.md
    Writes: BOOK_DIR/_system/source/text/refined-english.md
    """
    raise _not_yet_implemented(
        "0b",
        manual_steps=(
            "1. Invoke the /podcast skill; let it walk Phase 0b on this BOOK_DIR.\n"
            "2. When 0b is complete (refined-english.md exists and is non-empty),\n"
            "   re-run: orchestrate-book --resume <book-slug>\n"
            "   The orchestrator will detect the completed phase and continue."
        ),
    )


# ─── Phase 0c — Arabic phonetic transcription ───────────────────────────────
def author_phase_0c(book_dir: Path) -> None:
    """Add phonetic transcription for every Arabic / non-English term.

    Reads:  BOOK_DIR/_system/source/text/refined-english.md
    Writes: BOOK_DIR/_system/source/text/_phonetics.md
            (appended terms; consults content/_shared/arabic/ manifest first)
    """
    raise _not_yet_implemented(
        "0c",
        manual_steps=(
            "1. Run /podcast Phase 0c manually; it pulls from\n"
            "   content/_shared/arabic/03-arabic-english-manifest.md.\n"
            "2. Re-invoke orchestrate-book --resume."
        ),
    )


# ─── Phase 0d — Chapter design ───────────────────────────────────────────────
def author_phase_0d(book_dir: Path) -> None:
    """Segment the refined source into meaningful, balanced chapters.

    Reads:  BOOK_DIR/_system/source/text/refined-english.md
            BOOK_DIR/_system/source/text/_phonetics.md
    Writes: BOOK_DIR/chapters/ch01-<slug>.txt ... chNN-<slug>.txt
            BOOK_DIR/chapter-contracts/<slug>.yml (one per chapter)
            BOOK_DIR/_system/source/text/chapters-rationale.md
    """
    raise _not_yet_implemented(
        "0d",
        manual_steps=(
            "1. /podcast Phase 0d — segment into chapters with meaningful titles.\n"
            "2. Each chapter MUST land in the chosen tier's word band\n"
            "   (Extended: 5,500–9,500 words; Default: 1,800–2,800; Longer: 2,800–4,500).\n"
            "3. Re-invoke orchestrate-book --resume."
        ),
    )


# ─── Phase 0e — Chapter enrichment ──────────────────────────────────────────
def author_phase_0e(book_dir: Path) -> None:
    """Enrich each chapter with citations from the seven-tier whitelist.

    Reads:  every BOOK_DIR/chapters/ch*.txt
            content/podcast/.skill/handbook/enrichment-sources.md
            content/_shared/arabic/03-arabic-english-manifest.md
    Writes: enriched BOOK_DIR/chapters/ch*.txt (in place)
            BOOK_DIR/_system/enrichment-log.md (per-chapter status)
    """
    raise _not_yet_implemented(
        "0e",
        manual_steps=(
            "1. /podcast Phase 0e — enrich each chapter (Tier 1–6 sources only;\n"
            "   ≤ 60%% outside material; tier diversity required).\n"
            "2. Verify every chapter still passes scripts/podcast/build_episode_txt.py.\n"
            "3. Re-invoke orchestrate-book --resume."
        ),
    )


# ─── Per-chapter framing authorship ──────────────────────────────────────────
def author_framing(book_dir: Path, chapter_slug: str) -> None:
    """Author 00-framing.md from the chapter contract + Extended-tier template.

    Reads:  BOOK_DIR/chapter-contracts/<slug>.yml
            BOOK_DIR/chapters/ch##-<slug>.txt
            content/podcast/.skill/handbook/notebooklm-customize-prompt-rules.md
    Writes: BOOK_DIR/_system/episode-drafts/EP##-<slug>/00-framing.md
    """
    raise _not_yet_implemented(
        f"framing/{chapter_slug}",
        manual_steps=(
            f"1. /podcast Phase 3 — author the framing for chapter '{chapter_slug}'.\n"
            "2. Run scripts/podcast/build_episode_txt.py to validate.\n"
            "3. Re-invoke orchestrate-book --resume."
        ),
    )
