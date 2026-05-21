#!/usr/bin/env python3
"""_authoring.py — LLM-shellout helpers for orchestrate_book.py (Phases 0b–0e + framing).

Each phase function shells out to `claude -p "<prompt>"` (Claude Code headless
mode) with a phase-specific prompt that:
  · names the exact files to read + write
  · references the canonical /podcast SKILL.md section
  · names the success criterion (an artifact's existence + non-emptiness)
  · forbids touching files outside the named write paths

The orchestrator (orchestrate_book.py) checks the success criterion AFTER the
shellout returns. If the criterion is not met, the phase is marked failed and
the orchestrator halts cleanly — the human can debug via the conversational
`/podcast` skill on the same BOOK_DIR, then `--resume`.

USAGE (from orchestrate_book.py)

    from _authoring import (
        author_phase_0b, author_phase_0c, author_phase_0d, author_phase_0e,
        author_framing, invoke_challenger, invoke_fixer, invoke_trainer,
        AuthoringError,
    )

DESIGN NOTES

- `claude -p` runs Claude Code in headless mode using whatever permissions the
  invoking shell has. The orchestrator's overall budget (cost cap, time cap)
  is enforced in orchestrate_book.py, not here.
- Each shellout's stdout is captured and stored in the orchestrator's state file
  under the relevant phase entry — useful for postmortem.
- Per-phase timeout defaults are tuned to typical phase duration; raise them
  via the optional `timeout` arg if a particular phase consistently times out.
- The Agent-invocation pattern (for the challenger and trainer) uses an
  inline instruction that names the canonical subagent_type so Claude Code
  routes to the right wrapper.
"""

from __future__ import annotations

import re as _re
import subprocess
import sys
from pathlib import Path

# Local import of the chunking helper (same directory as this file).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _chunking import (  # noqa: E402
    ChunkingError,
    concat_outputs,
    run_windowed,
)

DEFAULT_TIMEOUT = 1800        # 30 min — phase 0b on a long book can take a while
FRAMING_TIMEOUT = 1500        # 25 min per framing (X9 2026-05-21: bumped from 900 after
                              # ch12 qada-and-qadar — 10,180-word chapter with many named
                              # figures — timed out at 900s; 25 min absorbs the densest cases)
CHALLENGER_TIMEOUT = 900      # 15 min per challenger pass (challenger's own cap is 5 iter)
FIXER_TIMEOUT = 600           # 10 min per fixer attempt
TRAINER_TIMEOUT = 1800        # 30 min for the trainer pass

# Windowing defaults for long-source phases (0b, 0c).
PHASE_0B_WINDOW_WORDS = 3000        # ~12 KB of refined output per window
PHASE_0B_OVERLAP_WORDS = 120        # context tail to preserve cross-window coherence
PHASE_0B_WINDOW_TIMEOUT = 600       # 10 min per window
PHASE_0C_WINDOW_WORDS = 8000        # phonetic extraction tolerates larger windows (read-mostly)
PHASE_0C_OVERLAP_WORDS = 60
PHASE_0C_WINDOW_TIMEOUT = 600

# Map-reduce defaults for Phase 0d / 0e (per-source-chapter / per-episode-chapter loops).
PHASE_0D_TOC_TIMEOUT = 600            # 10 min — TOC step processes whole refined-english.md once (read-mostly)
PHASE_0D_SC_TIMEOUT = 1200            # 20 min per source chapter — writes 1-3 episode files + contracts
PHASE_0E_CHAPTER_TIMEOUT = 900        # 15 min per chapter enrichment

CLAUDE_CMD = "claude"         # resolved via PATH


class AuthoringError(RuntimeError):
    """Raised when an LLM-authoring shellout fails to produce its declared artifact."""

    def __init__(self, phase: str, message: str, manual_fallback: str = "",
                 stdout: str = "", stderr: str = ""):
        super().__init__(message)
        self.phase = phase
        self.manual_fallback = manual_fallback
        self.stdout = stdout
        self.stderr = stderr


DEFAULT_MODEL_LABEL = "claude-opus-4-7"  # Claude Code's default on Max plan; for cost-ledger labeling


def _run_claude_p(
    prompt: str,
    *,
    cwd: Path | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    book_dir: Path | None = None,
    phase: str = "",
    step: str = "",
    model: str = DEFAULT_MODEL_LABEL,
) -> tuple[int, str, str]:
    """Run `claude -p "<prompt>"` synchronously. Return (rc, stdout, stderr).

    Raises AuthoringError if the `claude` binary is not on PATH or the call
    times out. Non-zero return codes are returned to the caller for handling.

    P6.1 cost-ledger integration: if `book_dir` is provided, also append a
    row to `<book_dir>/_system/cost-ledger.jsonl` via `_cost_ledger`. Ledger
    write failures NEVER poison the LLM call's return value — they emit a
    stderr warning and otherwise proceed silently.
    """
    try:
        proc = subprocess.run(
            [CLAUDE_CMD, "-p", "--permission-mode", "acceptEdits", prompt],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        rc, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
        if book_dir is not None:
            try:
                # Late import — module is optional in some test contexts
                from _cost_ledger import append_from_claude_p_stdout
                append_from_claude_p_stdout(
                    book_dir,
                    phase=phase or "(unspecified)",
                    step=step or "(unspecified)",
                    model=model,
                    stdout=stdout,
                )
            except Exception as e:  # noqa: BLE001 — ledger errors must not poison the call
                sys.stderr.write(
                    f"[_run_claude_p] cost-ledger append failed: {e!r}\n"
                )
        return rc, stdout, stderr
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
            message=f"LLM call timed out after {timeout}s.",
            manual_fallback="Resume manually via /podcast and `--resume` the orchestrator.",
        ) from e


def _assert_artifact(
    phase: str,
    path: Path,
    rc: int,
    stdout: str,
    stderr: str,
    manual_fallback: str,
) -> None:
    """Common post-shellout success check: artifact exists and is non-empty."""
    if rc != 0:
        raise AuthoringError(
            phase=phase,
            message=f"claude -p exited rc={rc} for Phase {phase}.",
            manual_fallback=manual_fallback,
            stdout=stdout,
            stderr=stderr,
        )
    if not path.exists():
        raise AuthoringError(
            phase=phase,
            message=f"Phase {phase} did not produce expected artifact: {path}",
            manual_fallback=manual_fallback,
            stdout=stdout,
            stderr=stderr,
        )
    if path.stat().st_size == 0:
        raise AuthoringError(
            phase=phase,
            message=f"Phase {phase} produced empty artifact: {path}",
            manual_fallback=manual_fallback,
            stdout=stdout,
            stderr=stderr,
        )


# ─── Phase 0b — English refinement (chunked) ─────────────────────────────────
def build_phase_0b_window_prompt(
    book_slug: str,
    idx: int,
    total: int,
    win_in: Path,
    win_out: Path,
) -> str:
    """Construct the per-window refinement prompt sent to ``claude -p``.

    Extracted to module level (was a closure inside :func:`author_phase_0b`) so
    it can be unit-tested in isolation. See ``tests/test_phase_0b_preserves_page_markers.py``
    (P22.markers fixture) — that test asserts the prompt contains an explicit
    instruction to preserve every ``<!-- page N -->`` HTML comment verbatim.
    Without that instruction, the LLM "tidies" the markers out during heavy
    prose passages, causing the asaas Phase 0b post-mortem 2026-05-20 defect:
    58/416 page anchors missing from refined-english.md across 7 of 49 windows.
    """
    return (
        f"You are driving Phase 0b (English Refinement) of the /podcast skill on book-slug "
        f"`{book_slug}`, **window {idx} of {total}**. Read the canonical Phase 0b procedure "
        f"from `skills-staging/podcast/SKILL.md` (search `### PHASE 0b: ENGLISH REFINEMENT`).\n\n"
        f"INPUT  (read this window only): `{win_in}`\n"
        f"OUTPUT (write the refined window here): `{win_out}`\n\n"
        f"This is one window in a sequence — DO NOT add chapter headings, intros, "
        f"summaries, or transitions that assume you have seen the whole book. Refine only "
        f"the prose in the INPUT file. If the input begins with a `<!-- context-overlap -->` "
        f"block, that is the tail of the prior window for continuity — DO NOT re-emit it "
        f"in your output; resume cleanly after it.\n\n"
        f"**Page-marker invariant (CRITICAL — P22.markers).** The INPUT contains "
        f"`<!-- page N -->` HTML comments — one before the prose extracted from each "
        f"source PDF page. You MUST preserve every `<!-- page N -->` comment verbatim "
        f"at the same relative position in the OUTPUT where it appears in the INPUT. "
        f"Do NOT collapse adjacent page markers. Do NOT renumber them. Do NOT omit any. "
        f"Do NOT invent new ones. Do NOT move them to the start or end of the output. "
        f"These markers are downstream anchors for content-range enforcement (P4.10), "
        f"per-page citation accuracy (P21), and operator navigation — refinement "
        f"without them silently breaks every downstream phase. If your refined prose "
        f"merges paragraphs across a page boundary, keep the `<!-- page N -->` comment "
        f"in place at the sentence boundary closest to where it originally sat.\n\n"
        f"Constraints (same as the whole-book Phase 0b — apply at the window scope):\n"
        f"- Do NOT modify any file other than `{win_out}`.\n"
        f"- Do NOT invent content not present in the INPUT — fidelity to the source is mandatory.\n"
        f"- Preserve every Arabic-derived term in transliteration form (al-Razi, al-Kirmani, etc.).\n"
        f"- Preserve every citation (verse references, hadith collection numbers).\n"
        f"- Preserve every `<!-- page N -->` HTML comment verbatim and in-place (see invariant above).\n"
        f"- Do NOT wrap output in code fences or add preamble like 'Here is the refined text:'.\n\n"
        f"Exit when `{win_out}` is non-empty."
    )


def author_phase_0b(
    book_dir: Path,
    timeout: int = DEFAULT_TIMEOUT,        # retained for back-compat; per-window timeout is what matters
    *,
    window_words: int = PHASE_0B_WINDOW_WORDS,
    overlap_words: int = PHASE_0B_OVERLAP_WORDS,
    window_timeout: int = PHASE_0B_WINDOW_TIMEOUT,
    log=print,
) -> str:
    """Refine the Azure-translated raw extract into clean English prose — windowed.

    For books larger than ~5,000 words, refining in a single `claude -p` call
    blows past the 30-min shellout timeout and produces no artifact. This
    implementation splits the raw extract into paragraph-aligned windows of
    ~`window_words` words, refines each window in its own `claude -p` call
    with checkpointed output, then concatenates the per-window outputs into
    the final `refined-english.md`.

    Reads:  BOOK_DIR/_system/source/text/raw-extract.md
    Writes: BOOK_DIR/_system/source/text/refined-english.md
            BOOK_DIR/_system/source/text/_chunks/0b/win-NNN.{in,out}.md  (provenance)

    Resume-safe: if some windows succeeded on a prior run and others failed,
    re-invoking only retries the failed/missing windows. Once every window's
    `.out.md` is present, `refined-english.md` is assembled and the phase
    completes.

    Returns: a short summary string for state-file logging.
    """
    book_slug = book_dir.name
    in_path = book_dir / "_system" / "source" / "text" / "raw-extract.md"
    out_path = book_dir / "_system" / "source" / "text" / "refined-english.md"
    chunks_dir = book_dir / "_system" / "source" / "text" / "_chunks" / "0b"

    if not in_path.exists():
        raise AuthoringError(
            phase="0b",
            message=f"prerequisite missing: {in_path} (Phase 0a should have produced this)",
            manual_fallback="Re-run Phase 0a or drop a manual raw-extract.md.",
        )

    raw_text = in_path.read_text(encoding="utf-8")

    def _builder(body: str, idx: int, total: int, win_out: Path) -> str:
        # Write the body to a side file so the prompt stays small and the LLM
        # reads the chunk from disk (its preferred IO pattern).
        win_in = win_out.with_suffix("").with_suffix(".in.md")  # win-NNN.in.md
        return build_phase_0b_window_prompt(book_slug, idx, total, win_in, win_out)

    log("  phase 0b · chunked refinement")
    try:
        out_paths = run_windowed(
            text=raw_text,
            chunks_dir=chunks_dir,
            prompt_builder=_builder,
            target_words=window_words,
            overlap_words=overlap_words,
            timeout_per_window=window_timeout,
            log=lambda m: log(m),
            book_dir=book_dir,
            phase="0b",
        )
    except ChunkingError as e:
        raise AuthoringError(
            phase="0b",
            message=str(e),
            manual_fallback=e.manual_fallback or (
                "1. Inspect _chunks/0b/win-*.in.md and drive failed windows via /podcast.\n"
                "2. Drop each result at _chunks/0b/win-NNN.out.md.\n"
                "3. Re-invoke orchestrate-book --resume."
            ),
        ) from e

    # Stitch the per-window outputs into the final artifact.
    try:
        merged = concat_outputs(out_paths)
    except ChunkingError as e:
        raise AuthoringError(
            phase="0b",
            message=str(e),
            manual_fallback=e.manual_fallback,
        ) from e

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(merged, encoding="utf-8")
    if out_path.stat().st_size == 0:
        raise AuthoringError(
            phase="0b",
            message=f"Phase 0b assembled artifact is empty: {out_path}",
            manual_fallback="Inspect _chunks/0b/win-*.out.md — at least one was non-empty but stitched to nothing.",
        )

    return f"0b chunked: {len(out_paths)} windows merged into {out_path.name}"


# ─── Phase 0c — Arabic phonetic transcription (chunked) ──────────────────────
def author_phase_0c(
    book_dir: Path,
    timeout: int = DEFAULT_TIMEOUT,
    *,
    window_words: int = PHASE_0C_WINDOW_WORDS,
    overlap_words: int = PHASE_0C_OVERLAP_WORDS,
    window_timeout: int = PHASE_0C_WINDOW_TIMEOUT,
    log=print,
) -> str:
    """Add phonetic transcription for every Arabic / non-English term — windowed.

    Reads:  BOOK_DIR/_system/source/text/refined-english.md
            content/_shared/arabic/03-arabic-english-manifest.md (authoritative)
    Writes: BOOK_DIR/_system/source/text/_phonetics.md
            BOOK_DIR/_system/source/text/_chunks/0c/win-NNN.{in,out}.md

    Per-window output is itself a pipe-table (one row per term). After all
    windows succeed, rows are merged and deduplicated by `term`; the merged
    table is written to `_phonetics.md`.
    """
    book_slug = book_dir.name
    in_path = book_dir / "_system" / "source" / "text" / "refined-english.md"
    out_path = book_dir / "_system" / "source" / "text" / "_phonetics.md"
    chunks_dir = book_dir / "_system" / "source" / "text" / "_chunks" / "0c"

    if not in_path.exists():
        raise AuthoringError(
            phase="0c",
            message=f"prerequisite missing: {in_path} (Phase 0b should have produced this)",
            manual_fallback="Run Phase 0b first.",
        )

    refined_text = in_path.read_text(encoding="utf-8")

    def _builder(body: str, idx: int, total: int, win_out: Path) -> str:
        win_in = win_out.with_suffix("").with_suffix(".in.md")
        return (
            f"You are driving Phase 0c (Arabic Phonetic Transcription Pass) of the /podcast skill "
            f"on book-slug `{book_slug}`, **window {idx} of {total}**. Read the canonical "
            f"procedure from `skills-staging/podcast/SKILL.md` (search `### PHASE 0c`).\n\n"
            f"INPUT  (read this window): `{win_in}`\n"
            f"AUTHORITY (consult before adding new entries):\n"
            f"  - `content/_shared/arabic/03-arabic-english-manifest.md` (canonical — WINS)\n"
            f"  - `content/_shared/arabic/01-tts-pronunciation-key.md` (TTS rules)\n"
            f"  - `content/_shared/arabic/05-name-alias-policy.md` (long-name → short alias)\n"
            f"OUTPUT (write the phonetic table for THIS window only): `{win_out}`\n\n"
            f"Output FORMAT — a markdown pipe table with EXACTLY this header:\n"
            f"```\n"
            f"| term | transliteration | phonetic | first-occurrence-snippet |\n"
            f"|---|---|---|---|\n"
            f"```\n"
            f"One row per unique Arabic-derived term in the INPUT. The shared manifest WINS — "
            f"copy its entries verbatim for any term it covers; add new rows only for terms it "
            f"doesn't carry.\n\n"
            f"Constraints:\n"
            f"- Do NOT modify any file other than `{win_out}`.\n"
            f"- Do NOT wrap output in code fences.\n"
            f"- If a term repeats within this window, emit it once.\n"
            f"- Per-window dedup only — cross-window dedup is handled by the orchestrator.\n\n"
            f"Exit when `{win_out}` contains a valid pipe table (header + at least zero rows; "
            f"emit just the header if the window has no Arabic terms)."
        )

    log("  phase 0c · chunked phonetic extraction")
    try:
        out_paths = run_windowed(
            text=refined_text,
            chunks_dir=chunks_dir,
            prompt_builder=_builder,
            target_words=window_words,
            overlap_words=overlap_words,
            timeout_per_window=window_timeout,
            log=lambda m: log(m),
            book_dir=book_dir,
            phase="0c",
        )
    except ChunkingError as e:
        raise AuthoringError(
            phase="0c",
            message=str(e),
            manual_fallback=e.manual_fallback or (
                "1. Inspect _chunks/0c/win-*.in.md and drive failed windows via /podcast.\n"
                "2. Drop each result at _chunks/0c/win-NNN.out.md.\n"
                "3. Re-invoke orchestrate-book --resume."
            ),
        ) from e

    # Merge + dedup rows across windows.
    merged = _merge_phonetic_tables(out_paths)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(merged, encoding="utf-8")
    if out_path.stat().st_size == 0:
        raise AuthoringError(
            phase="0c",
            message=f"Phase 0c assembled artifact is empty: {out_path}",
            manual_fallback="Inspect _chunks/0c/win-*.out.md and merge manually.",
        )

    return f"0c chunked: {len(out_paths)} windows merged into {out_path.name}"


def _merge_phonetic_tables(paths: list[Path]) -> str:
    """Concatenate pipe-table outputs from windowed runs; dedup on first column.

    Tolerates per-window outputs that include preambles, code fences, or extra
    blank rows. Preserves first-seen order for each unique term so the resulting
    table corresponds roughly to the book's reading order.
    """
    import re as _re

    header = "| term | transliteration | phonetic | first-occurrence-snippet |"
    divider = "|---|---|---|---|"
    seen: dict[str, str] = {}
    order: list[str] = []

    row_re = _re.compile(r"^\s*\|\s*([^|]+?)\s*\|.*\|\s*$")
    for p in paths:
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("```"):
                continue
            # Skip header / divider rows in any window's output.
            if s.startswith("| term ") or s.startswith("|---"):
                continue
            m = row_re.match(line)
            if not m:
                continue
            term = m.group(1).strip().strip("`").lower()
            if not term or term in seen:
                continue
            seen[term] = line.rstrip()
            order.append(term)

    body = "\n".join(seen[t] for t in order)
    return f"{header}\n{divider}\n{body}\n" if order else f"{header}\n{divider}\n"


# ─── Phase 0d — Chapter design (map-reduce by source chapter) ────────────────
def author_phase_0d(book_dir: Path, *, length_tier: str = "extended",
                    unit_mode: str = "auto",
                    timeout: int = DEFAULT_TIMEOUT,
                    toc_timeout: int = PHASE_0D_TOC_TIMEOUT,
                    sc_timeout: int = PHASE_0D_SC_TIMEOUT,
                    log=print) -> str:
    """Segment the refined source into meaningful, balanced **episode units**.

    Implemented as a 2-step map-reduce so the LLM never has to author the
    entire book's chapter set in a single shellout:

      Step 1 (TOC + plan, one small call):
          Read refined-english.md, identify source-chapter boundaries
          (by heading or thematic break), and emit a JSON plan to
          `_chunks/0d/source-toc.json`. Each entry pins start_line +
          end_line (1-indexed, inclusive) into refined-english.md, the
          chosen `unit_mode` for that source chapter, the episode count,
          and the kebab-case slug for each episode.

      Step 2 (per-source-chapter loop, one call each):
          For each source chapter in the plan, slice the refined text,
          pass it to a focused `claude -p` call that writes ONLY this
          source chapter's episode files + contracts (with episode
          numbers already pre-assigned from the plan, so the global
          numbering is monotonic). Per-source-chapter rationale +
          source-map rows are written to
          `_chunks/0d/sc-NNN.{rationale,source-map}.md`. A
          `_chunks/0d/sc-NNN.done` marker file makes the loop
          resume-safe — if the orchestrator crashes mid-way, re-running
          only retries the not-yet-done source chapters.

      Step 3 (stitch, deterministic):
          Concat all sc-NNN.rationale.md → chapters-rationale.md.
          Concat all sc-NNN.source-map.md (under one shared pipe-table
          header) → source-chapter-map.md (when unit_mode != chapter).

    `unit_mode` controls how source structure maps to episodes:
      - `chapter` — each source chapter becomes exactly one episode
      - `section` — each source chapter is split into multiple episodes
      - `auto` (default) — Step 1 decides per-chapter based on tier band

    Reads:  BOOK_DIR/_system/source/text/refined-english.md
            BOOK_DIR/_system/source/text/_phonetics.md
    Writes: BOOK_DIR/chapters/ch##[a-z]?-<slug>.txt
            BOOK_DIR/chapter-contracts/<slug>.yml (one per episode)
            BOOK_DIR/_system/source/text/chapters-rationale.md
            BOOK_DIR/_system/source/text/source-chapter-map.md
                (when unit_mode != 'chapter')
            BOOK_DIR/_system/source/text/_chunks/0d/source-toc.json
            BOOK_DIR/_system/source/text/_chunks/0d/sc-NNN.{rationale,source-map}.md
            BOOK_DIR/_system/source/text/_chunks/0d/sc-NNN.done
    """
    import json as _json

    book_slug = book_dir.name
    in_refined = book_dir / "_system" / "source" / "text" / "refined-english.md"
    in_phonetics = book_dir / "_system" / "source" / "text" / "_phonetics.md"
    out_rationale = book_dir / "_system" / "source" / "text" / "chapters-rationale.md"
    out_source_map = book_dir / "_system" / "source" / "text" / "source-chapter-map.md"
    chapters_dir = book_dir / "chapters"
    contracts_dir = book_dir / "chapter-contracts"
    chunks_dir = book_dir / "_system" / "source" / "text" / "_chunks" / "0d"
    toc_path = chunks_dir / "source-toc.json"

    if unit_mode not in ("chapter", "section", "auto"):
        raise AuthoringError(
            phase="0d",
            message=f"unit_mode must be one of chapter|section|auto (got {unit_mode!r})",
        )

    for p in (in_refined, in_phonetics):
        if not p.exists():
            raise AuthoringError(
                phase="0d",
                message=f"prerequisite missing: {p}",
                manual_fallback="Run prior phases (0b, 0c) first.",
            )

    chunks_dir.mkdir(parents=True, exist_ok=True)
    chapters_dir.mkdir(parents=True, exist_ok=True)
    contracts_dir.mkdir(parents=True, exist_ok=True)

    tier_band = {
        "default_deep_dive": "1,800–2,800 words per episode",
        "longer": "2,800–4,500 words per episode",
        "extended": "5,500–9,500 words per episode",
    }.get(length_tier, "5,500–9,500 words per episode (extended)")

    unit_directive = {
        "chapter": (
            "UNIT MODE: **chapter** — every source chapter MUST become exactly ONE episode "
            "(unit_mode='chapter', episode_count=1). Do NOT split any source chapter even if "
            "its word count overflows the tier band."
        ),
        "section": (
            "UNIT MODE: **section** — every source chapter MUST be split into 2 or more "
            "thematic sections (unit_mode='sections', episode_count>=2). Aim for tier-band "
            "compliance per resulting episode."
        ),
        "auto": (
            "UNIT MODE: **auto** — for each source chapter, decide individually: "
            "if its word count is within ±50% of the tier band midpoint, set "
            "unit_mode='chapter' (episode_count=1). If it exceeds 1.5× the tier band's upper "
            "bound, set unit_mode='sections' and pick episode_count so each resulting episode "
            "lands inside the band. Aim for all episodes within ~30% of each other."
        ),
    }[unit_mode]

    # ── STEP 1: TOC + plan ───────────────────────────────────────────────────
    log("  phase 0d · step 1/3 · TOC + segmentation plan")

    if toc_path.exists() and toc_path.stat().st_size > 0:
        log(f"    skip toc (already on disk: {toc_path.name})")
    else:
        toc_prompt = (
            f"You are driving Phase 0d STEP 1 (TOC + segmentation plan) of the /podcast "
            f"skill on book-slug `{book_slug}`. This is a small read-mostly call: you will "
            f"NOT write any chapter or contract files in this step — only one JSON plan.\n\n"
            f"INPUT:  `{in_refined}` (the refined English source)\n"
            f"OUTPUT: `{toc_path}` (machine-readable plan; valid JSON only, no markdown)\n\n"
            f"TASK:\n"
            f"1. Read `{in_refined}` and identify the source chapters (by heading, "
            f"thematic break, or major topic shift). Use the source author's own "
            f"chapter breaks as the starting point.\n"
            f"2. For each source chapter, compute its line range in `{in_refined}` "
            f"(1-indexed, inclusive — use `wc -l` style counting; lines are separated by "
            f"`\\n`). Also compute its word count (whitespace-split).\n"
            f"3. Apply the following segmentation directive PER SOURCE CHAPTER:\n"
            f"   {unit_directive}\n"
            f"4. Assign monotonically increasing episode numbers (`ep_num`) across the whole "
            f"book starting at 1. Each episode gets a short kebab-case `episode_slug` "
            f"(distinct across the whole book). When a source chapter splits into multiple "
            f"episodes (unit_mode='sections'), each episode's slug must reflect its OWN "
            f"theme, not the source chapter's overall theme.\n\n"
            f"Length tier: **{length_tier}** — target {tier_band}.\n\n"
            f"OUTPUT FORMAT — write to `{toc_path}`, valid JSON, no surrounding text:\n"
            f"```json\n"
            f"{{\n"
            f'  "length_tier": "{length_tier}",\n'
            f'  "unit_mode_input": "{unit_mode}",\n'
            f'  "source_chapters": [\n'
            f'    {{\n'
            f'      "sc_index": 1,\n'
            f'      "source_title": "Introduction",\n'
            f'      "start_line": 12,\n'
            f'      "end_line": 487,\n'
            f'      "word_count": 4280,\n'
            f'      "unit_mode": "chapter",\n'
            f'      "episode_count": 1,\n'
            f'      "episodes": [\n'
            f'        {{ "ep_num": 1, "episode_slug": "the-question-of-authority", '
            f'"section_index": null }}\n'
            f'      ],\n'
            f'      "split_reason": "fits tier band"\n'
            f'    }},\n'
            f'    {{\n'
            f'      "sc_index": 2,\n'
            f'      "source_title": "On the Imamate",\n'
            f'      "start_line": 488,\n'
            f'      "end_line": 1820,\n'
            f'      "word_count": 11400,\n'
            f'      "unit_mode": "sections",\n'
            f'      "episode_count": 2,\n'
            f'      "episodes": [\n'
            f'        {{ "ep_num": 2, "episode_slug": "the-claim-to-succession", '
            f'"section_index": 1 }},\n'
            f'        {{ "ep_num": 3, "episode_slug": "the-tests-of-legitimacy", '
            f'"section_index": 2 }}\n'
            f'      ],\n'
            f'      "split_reason": "1.7x upper bound; thematic seam at the legitimacy tests"\n'
            f'    }}\n'
            f'  ]\n'
            f"}}\n"
            f"```\n\n"
            f"Constraints:\n"
            f"- Write ONLY `{toc_path}`. Do NOT touch any other file.\n"
            f"- The output MUST be valid JSON (parseable by Python's json.loads).\n"
            f"- ep_num starts at 1 and is strictly monotonic across the whole array.\n"
            f"- end_line of source_chapter N must be < start_line of source_chapter N+1.\n"
            f"- episode_slug must be unique across the whole book.\n"
            f"- For unit_mode='chapter', episodes[*].section_index MUST be null.\n"
            f"- For unit_mode='sections', episodes[*].section_index is 1..episode_count.\n\n"
            f"Exit when `{toc_path}` is non-empty and valid JSON."
        )
        rc, stdout, stderr = _run_claude_p(
            toc_prompt, timeout=toc_timeout,
            book_dir=book_dir, phase="0d", step="toc",
        )
        _assert_artifact(
            phase="0d-toc",
            path=toc_path,
            rc=rc,
            stdout=stdout,
            stderr=stderr,
            manual_fallback=(
                f"Author `{toc_path}` manually (see prompt structure in _authoring.py), "
                f"then re-invoke orchestrate-book --resume."
            ),
        )

    # Validate + parse plan.
    try:
        plan = _json.loads(toc_path.read_text(encoding="utf-8"))
    except _json.JSONDecodeError as e:
        raise AuthoringError(
            phase="0d-toc",
            message=f"source-toc.json is not valid JSON: {e}",
            manual_fallback=(
                f"Fix or delete `{toc_path}` and retry Phase 0d "
                f"(--resume --retry-phase 0d)."
            ),
        ) from e

    source_chapters = plan.get("source_chapters") or []
    if not source_chapters:
        raise AuthoringError(
            phase="0d-toc",
            message="source-toc.json has no source_chapters",
            manual_fallback=f"Edit `{toc_path}` to add source_chapters then retry.",
        )

    refined_lines = in_refined.read_text(encoding="utf-8").splitlines()

    # ── STEP 2: per-source-chapter loop ──────────────────────────────────────
    log(f"  phase 0d · step 2/3 · per-source-chapter loop ({len(source_chapters)} chapters)")

    sc_failures: list[tuple[int, str]] = []
    for sc in source_chapters:
        sc_idx = int(sc["sc_index"])
        sc_title = str(sc.get("source_title", f"source chapter {sc_idx}"))
        start_line = int(sc["start_line"])
        end_line = int(sc["end_line"])
        sc_unit_mode = str(sc.get("unit_mode", "chapter"))
        episode_count = int(sc.get("episode_count", 1))
        episodes = sc.get("episodes") or []
        if len(episodes) != episode_count:
            sc_failures.append((sc_idx, f"plan inconsistent: episodes={len(episodes)} != episode_count={episode_count}"))
            continue

        done_marker = chunks_dir / f"sc-{sc_idx:03d}.done"
        rationale_path = chunks_dir / f"sc-{sc_idx:03d}.rationale.md"
        source_map_path = chunks_dir / f"sc-{sc_idx:03d}.source-map.md"
        slice_path = chunks_dir / f"sc-{sc_idx:03d}.in.md"

        if done_marker.exists():
            log(f"    sc {sc_idx:03d}/{len(source_chapters)} · skip (done)")
            continue

        # Slice the refined text for this source chapter.
        if start_line < 1 or end_line > len(refined_lines) or start_line > end_line:
            sc_failures.append((sc_idx, f"bad line range {start_line}-{end_line} (refined has {len(refined_lines)} lines)"))
            log(f"    sc {sc_idx:03d}/{len(source_chapters)} · BAD RANGE")
            continue
        slice_text = "\n".join(refined_lines[start_line - 1:end_line])
        slice_wc = len(slice_text.split())
        slice_path.write_text(slice_text, encoding="utf-8")

        # Expected output filenames for THIS source chapter's episodes.
        expected_chapter_files: list[Path] = []
        expected_contract_files: list[Path] = []
        episode_lines: list[str] = []
        for ep in episodes:
            ep_num = int(ep["ep_num"])
            ep_slug = str(ep["episode_slug"])
            section_index = ep.get("section_index")
            # Naming: chNN-<slug>.txt for whole-chapter; chNN<letter>-<slug>.txt for sections.
            if sc_unit_mode == "sections" and section_index is not None:
                # section_index 1 → 'a', 2 → 'b', etc.
                suffix = chr(ord("a") + int(section_index) - 1)
                fname_base = f"ch{ep_num:02d}{suffix}-{ep_slug}"
            else:
                fname_base = f"ch{ep_num:02d}-{ep_slug}"
            expected_chapter_files.append(chapters_dir / f"{fname_base}.txt")
            expected_contract_files.append(contracts_dir / f"{ep_slug}.yml")
            episode_lines.append(
                f"  - ep_num={ep_num}  slug={ep_slug}  "
                f"chapter_file=`chapters/{fname_base}.txt`  "
                f"contract=`chapter-contracts/{ep_slug}.yml`"
                + (f"  section_index={section_index}" if section_index is not None else "")
            )

        sc_prompt = (
            f"You are driving Phase 0d STEP 2 (per-source-chapter authoring) of the /podcast "
            f"skill on book-slug `{book_slug}`, **source chapter {sc_idx} of "
            f"{len(source_chapters)}** (`{sc_title}`). Read the canonical procedure from "
            f"`skills-staging/podcast/SKILL.md` (search `### PHASE 0d`) for episode-authoring "
            f"discipline.\n\n"
            f"INPUT (the refined English for THIS source chapter only): `{slice_path}`\n"
            f"  · word_count: {slice_wc}  ·  source_line_range: {start_line}-{end_line}\n"
            f"AUTHORITY:\n"
            f"  - `{in_phonetics}` (consult for Arabic terms appearing in this slice)\n"
            f"  - `content/_shared/arabic/03-arabic-english-manifest.md`\n"
            f"  - `skills-staging/podcast/handbook/chapter-contract.template.yml` (contract shape)\n\n"
            f"PLAN FOR THIS SOURCE CHAPTER (from `{toc_path}`):\n"
            f"  unit_mode: {sc_unit_mode}\n"
            f"  episode_count: {episode_count}\n"
            f"  length_tier: {length_tier} ({tier_band})\n"
            f"  episodes:\n" + "\n".join(episode_lines) + "\n\n"
            f"OUTPUTS (write exactly these files — DO NOT touch any other path):\n"
            + "".join(f"  - `{p}`\n" for p in expected_chapter_files)
            + "".join(f"  - `{p}`\n" for p in expected_contract_files)
            + f"  - `{rationale_path}` (one paragraph per episode in this source chapter; "
            f"each paragraph starts with the episode's filename in backticks)\n"
            + (
                f"  - `{source_map_path}` (pipe-table rows for THIS source chapter, "
                f"NO header — the orchestrator stitches headers later. Format per row: "
                f"`| {sc_idx} | {sc_title} | <comma-sep chapter filenames> | <split_reason> |`)\n"
                if unit_mode != "chapter" else ""
            )
            + f"\nConstraints:\n"
            f"- Use the EXACT episode filenames listed above. Do NOT invent slugs or "
            f"renumber. Pre-assigned ep_num + section_index come from the global plan.\n"
            f"- Each `chapter-contracts/<slug>.yml` carries: chapter_ref, slug, source_type, "
            f"book_slug=`{book_slug}`, episode_number, title, audience, angle, "
            f"episode_format, format_rationale, essential, essential_rationale, "
            f"host_dynamic, host_dynamic_rationale, length_target, key_tensions, "
            f"tone_constraints, anchor_passages, adaptation_mode=faithful, "
            f"phonetic_overrides, show_notes.\n"
            f"\n"
            f"CONTENT-AWARE FIELD ASSIGNMENTS — analyze the source-chapter's rhetorical "
            f"structure to set these fields. Do NOT default blindly.\n"
            f"\n"
            f"  episode_format — one of:\n"
            f"    * deep_dive: chapter is exposition/narrative — one position being developed.\n"
            f"      Use for: editor's introductions, foundational chapters before disputes\n"
            f"      kick in, architectural settlements where the author synthesizes without\n"
            f"      a named opponent, historical/biographical narrative.\n"
            f"    * debate: chapter contains two or more NAMED opposing voices being\n"
            f"      adjudicated by the author. Look for explicit patterns like 'X said this,\n"
            f"      Y said that, the truth is …' or 'the author of [WORK_A] held …, the author\n"
            f"      of [WORK_B] held …, we reply …'. If the chapter quotes named opponents and\n"
            f"      systematically refutes/balances them, this is debate.\n"
            f"    * interview: chapter is Q&A structured (rare in primary sources).\n"
            f"    * narrative: chapter is pure historical/biographical exposition (no\n"
            f"      doctrinal dispute, no exposition-of-position — just events).\n"
            f"  format_rationale: ONE sentence — the textual evidence that drove the choice\n"
            f"    (e.g., 'Chapter explicitly names al-Islah and al-Nusra as opponents across\n"
            f"    18/19 sub-chapters; al-Kirmani's resolution appears as the closing move').\n"
            f"\n"
            f"  essential — one of:\n"
            f"    * core: required for the doctrinal/argumentative arc; cannot be removed\n"
            f"      without breaking the listener's understanding.\n"
            f"    * optional: useful context but the listener can skip it without losing\n"
            f"      the thread (e.g., an editor's overview of who the protagonists are).\n"
            f"    * bonus: scholarly bookkeeping (manuscript history, philological notes,\n"
            f"      footnote material). Listeners gain little; keep accessible for completists.\n"
            f"    * skip: editorial side-matter with minimal listener value; recommend\n"
            f"      cutting from the main series.\n"
            f"  essential_rationale: ONE sentence — what content drives the verdict (e.g.,\n"
            f"    'Pure manuscript-history bookkeeping by the 20th-century editor; no source\n"
            f"    doctrine present').\n"
            f"\n"
            f"  host_dynamic — derive from episode_format:\n"
            f"    * deep_dive → 'curious_mind + scholar_companion' (Mentor + Student)\n"
            f"    * debate (3+ voices) → 'advocate_a + advocate_b + arbiter'\n"
            f"    * debate (2 voices) → 'advocate + arbiter'\n"
            f"    * narrative → 'narrator + companion'\n"
            f"    * interview → 'interviewer + subject'\n"
            f"  host_dynamic_rationale: ONE sentence naming who-plays-what for THIS chapter\n"
            f"    (e.g., 'advocate_a voices al-Islah's gentle/dense proportion, advocate_b\n"
            f"    voices al-Nusra's structural parallel, arbiter delivers al-Kirmani's\n"
            f"    settlement that opposites do not meet in the same place').\n"
            + (
                "  - When this episode is a section of a longer source chapter, also include "
                "`source_chapter_ref` (the sc_index) and `section_index` (1-based) in the "
                "contract.\n"
                if sc_unit_mode == "sections" else ""
            )
            + f"- Each chapter txt MUST land inside the tier band ({tier_band}).\n"
            f"- Do NOT modify any file outside the named outputs (in particular, do NOT "
            f"touch other source-chapter slices or other episodes' files).\n"
            f"- Do NOT write `{toc_path}` or `{chapters_dir.parent / '_system' / 'source' / 'text' / 'chapters-rationale.md'}` — "
            f"the orchestrator stitches those.\n\n"
            f"Exit when every output file above exists and is non-empty."
        )

        log(f"    sc {sc_idx:03d}/{len(source_chapters)} · authoring "
            f"({episode_count} ep, {slice_wc} src words) · `{sc_title[:50]}`")
        rc, stdout, stderr = _run_claude_p(
            sc_prompt, timeout=sc_timeout,
            book_dir=book_dir, phase="0d", step=f"sc-{sc_idx:03d}",
        )
        if rc != 0:
            # Transient (network/API/quota) — log + continue; resume retries.
            # P5.2: capture stdout AND stderr in the failure record.
            sc_failures.append(
                (
                    sc_idx,
                    f"rc={rc}: stderr={(stderr or '').strip()[:300]} | "
                    f"stdout={(stdout or '').strip()[:300]}",
                )
            )
            log(f"    sc {sc_idx:03d}/{len(source_chapters)} · FAILED rc={rc}")
            continue

        # Validate this source chapter's outputs.
        missing = [str(p) for p in expected_chapter_files + expected_contract_files
                   if not p.exists() or p.stat().st_size == 0]
        if not rationale_path.exists() or rationale_path.stat().st_size == 0:
            missing.append(str(rationale_path))
        if unit_mode != "chapter" and (not source_map_path.exists() or source_map_path.stat().st_size == 0):
            missing.append(str(source_map_path))
        if missing:
            # P5.2: rc=0 with missing artifacts is the P5.1 failure class —
            # LLM exited cleanly without writing. Fatal, not retryable.
            raise AuthoringError(
                phase="07-chapter-design",
                message=(
                    f"sc {sc_idx:03d}/{len(source_chapters)} ({sc_title!r}) "
                    f"returned rc=0 but produced no artifacts for: {missing[:5]}. "
                    f"P5.1 failure class — claude -p exited cleanly without "
                    f"writing the expected files. After --permission-mode "
                    f"acceptEdits, this should not recur; surfaces here "
                    f"indicate a content-filter refusal, quota hit, or prompt "
                    f"issue."
                ),
                manual_fallback=(
                    f"Inspect stdout/stderr attached to this error. If the "
                    f"prompt needs adjusting, edit and resume. If transient "
                    f"quota, retry. DO NOT silently advance."
                ),
                stdout=stdout or "",
                stderr=stderr or "",
            )

        # All good → checkpoint.
        done_marker.write_text(
            f"sc_index={sc_idx}\nsource_title={sc_title}\nepisode_count={episode_count}\n",
            encoding="utf-8",
        )
        log(f"    sc {sc_idx:03d}/{len(source_chapters)} · OK")

    if sc_failures:
        raise AuthoringError(
            phase="0d",
            message=(
                f"{len(sc_failures)} of {len(source_chapters)} source chapters failed: "
                + "; ".join(f"sc {i}: {m}" for i, m in sc_failures[:3])
            ),
            manual_fallback=(
                f"Inspect _chunks/0d/sc-NNN.in.md for failed source chapters; "
                f"drive each manually via /podcast, then re-invoke "
                f"orchestrate-book --resume (already-done source chapters are skipped via "
                f"the .done marker file)."
            ),
        )

    # ── STEP 3: stitch ────────────────────────────────────────────────────────
    log("  phase 0d · step 3/3 · stitch rationale + source-map")

    rationale_parts: list[str] = []
    for sc in source_chapters:
        sc_idx = int(sc["sc_index"])
        rp = chunks_dir / f"sc-{sc_idx:03d}.rationale.md"
        if rp.exists() and rp.stat().st_size > 0:
            sc_title = str(sc.get("source_title", f"source chapter {sc_idx}"))
            rationale_parts.append(f"## Source chapter {sc_idx} — {sc_title}\n\n{rp.read_text(encoding='utf-8').strip()}\n")
    out_rationale.write_text("\n".join(rationale_parts) + "\n", encoding="utf-8")

    if unit_mode != "chapter":
        header = (
            "| source chapter | source title | episode(s) | split reason |\n"
            "|---|---|---|---|\n"
        )
        sm_rows: list[str] = []
        for sc in source_chapters:
            sc_idx = int(sc["sc_index"])
            smp = chunks_dir / f"sc-{sc_idx:03d}.source-map.md"
            if smp.exists() and smp.stat().st_size > 0:
                sm_rows.append(smp.read_text(encoding="utf-8").strip())
        out_source_map.write_text(header + "\n".join(sm_rows) + "\n", encoding="utf-8")

    # Final sanity check — at least one chapter + contract present.
    if not list(chapters_dir.glob("ch*.txt")):
        raise AuthoringError(
            phase="0d",
            message=f"Phase 0d produced no chapter files under {chapters_dir}",
            manual_fallback="Inspect _chunks/0d/sc-NNN.done markers and chapters/ dir.",
        )
    if not list(contracts_dir.glob("*.yml")):
        raise AuthoringError(
            phase="0d",
            message=f"Phase 0d produced no contracts under {contracts_dir}",
            manual_fallback="Inspect _chunks/0d/sc-NNN.done markers and chapter-contracts/ dir.",
        )

    total_episodes = sum(int(sc.get("episode_count", 1)) for sc in source_chapters)
    return (
        f"0d map-reduce: {len(source_chapters)} source chapters → "
        f"{total_episodes} episodes (chapters + contracts written)"
    )


# ─── Phase 0e — Chapter enrichment ──────────────────────────────────────────
def author_phase_0e(book_dir: Path,
                    timeout: int = DEFAULT_TIMEOUT,
                    chapter_timeout: int = PHASE_0E_CHAPTER_TIMEOUT,
                    log=print) -> str:
    """Enrich each chapter with citations from the seven-tier whitelist.

    Implemented as a per-chapter loop so the LLM only enriches one chapter
    file per `claude -p` call. Idempotent: an enrichment-log.md row of the
    form `- <chapter-stem>: ENRICHED ...` marks a chapter as done; reruns
    skip those chapters. The first time this runs the log is created and
    receives one row per chapter as each completes.

    Reads:  every BOOK_DIR/chapters/ch*.txt
            content/podcast/.skill/handbook/enrichment-sources.md
            content/_shared/arabic/03-arabic-english-manifest.md
    Writes: enriched BOOK_DIR/chapters/ch*.txt (in place)
            BOOK_DIR/_system/enrichment-log.md (per-chapter status)
    """
    import datetime as _dt

    book_slug = book_dir.name
    chapters_dir = book_dir / "chapters"
    enrichment_log = book_dir / "_system" / "enrichment-log.md"

    chapter_files = sorted(chapters_dir.glob("ch*.txt"))
    if not chapter_files:
        raise AuthoringError(
            phase="0e",
            message=f"no chapters to enrich under {chapters_dir} (Phase 0d should have produced them)",
            manual_fallback="Run Phase 0d first.",
        )

    enrichment_log.parent.mkdir(parents=True, exist_ok=True)
    if not enrichment_log.exists():
        enrichment_log.write_text(
            f"# Enrichment log — {book_slug}\n\n"
            f"Per-chapter status. Rows with `ENRICHED` are checkpointed and skipped on resume.\n\n",
            encoding="utf-8",
        )

    existing_log = enrichment_log.read_text(encoding="utf-8")
    already_done: set[str] = set()
    for line in existing_log.splitlines():
        s = line.strip()
        if s.startswith("- ") and ": ENRICHED" in s:
            # `- ch03-foo: ENRICHED at 2025-...`
            stem = s[2:].split(":", 1)[0].strip()
            already_done.add(stem)

    log(f"  phase 0e · per-chapter loop ({len(chapter_files)} chapters, "
        f"{len(already_done)} already enriched)")

    failures: list[tuple[str, str]] = []
    for chapter_file in chapter_files:
        stem = chapter_file.stem  # e.g. ch03-foo or ch03a-foo
        if stem in already_done:
            log(f"    {stem} · skip (already enriched)")
            continue

        prompt = (
            f"You are driving Phase 0e (Chapter Enrichment from Outside Sources) of the "
            f"/podcast skill on book-slug `{book_slug}`, **chapter `{stem}` only**. Read "
            f"the canonical procedure from `skills-staging/podcast/SKILL.md` "
            f"(search `### PHASE 0e`) and apply it to THIS ONE chapter.\n\n"
            f"INPUT (the chapter file to enrich in place): `{chapter_file}`\n"
            f"AUTHORITY:\n"
            f"  - `content/podcast/.skill/handbook/enrichment-sources.md` (seven-tier "
            f"whitelist + 60% cap + tier-diversity rule)\n"
            f"  - `content/_shared/arabic/03-arabic-english-manifest.md`\n"
            f"  - `content/podcast/.skill/handbook/notebooklm-source-chapter-rules.md` "
            f"(R-rules)\n\n"
            f"OUTPUTS (write ONLY these — do NOT touch any other file):\n"
            f"  - `{chapter_file}` (enriched in place)\n\n"
            f"Constraints:\n"
            f"- Outside material ≤ 60% of THIS chapter's word count. The original author's "
            f"argument stays the spine.\n"
            f"- Tier diversity required — don't pull all enrichments from one tier.\n"
            f"- Every citation carries author, work, page or section, and translator "
            f"(for Quranic translations).\n"
            f"- Apply R-PHONETICS-OUT: no inline `*term* (PHO-NE-TIC)` parens in chapter "
            f"prose; phonetic discipline lives in the customize prompt only.\n"
            f"- Apply R-HONORIFIC-ONCE: each honorific phrase form expanded ≤ 1× in this "
            f"chapter.\n"
            f"- Do NOT modify any other chapter file, contract, or `enrichment-log.md` — "
            f"the orchestrator appends the log row after validating your output.\n\n"
            f"Exit when `{chapter_file}` has been rewritten in place with citations woven in."
        )

        log(f"    {stem} · enriching")
        # Capture pre-enrichment mtime to detect that the file was actually rewritten.
        pre_mtime = chapter_file.stat().st_mtime
        rc, stdout, stderr = _run_claude_p(
            prompt, timeout=chapter_timeout,
            book_dir=book_dir, phase="0e", step=stem,
        )
        if rc != 0:
            # Transient — log + continue; resume retries.
            # P5.2: capture stdout AND stderr in the failure record.
            failures.append(
                (
                    stem,
                    f"rc={rc}: stderr={(stderr or '').strip()[:300]} | "
                    f"stdout={(stdout or '').strip()[:300]}",
                )
            )
            log(f"    {stem} · FAILED rc={rc}")
            continue
        if not chapter_file.exists() or chapter_file.stat().st_size == 0:
            # P5.2: rc=0 with missing/empty chapter file is the P5.1 failure
            # class — claude -p exited cleanly without writing. Fatal.
            raise AuthoringError(
                phase="08-enrichment",
                message=(
                    f"{stem} returned rc=0 but produced no enriched chapter "
                    f"file at {chapter_file}. P5.1 failure class — claude -p "
                    f"exited cleanly without writing. After --permission-mode "
                    f"acceptEdits this should not recur."
                ),
                manual_fallback=(
                    f"Inspect stdout/stderr on this error. If a content-filter "
                    f"refusal or quota issue, address the cause and resume. "
                    f"DO NOT silently advance."
                ),
                stdout=stdout or "",
                stderr=stderr or "",
            )
        post_mtime = chapter_file.stat().st_mtime
        touched = " (in-place rewrite)" if post_mtime > pre_mtime else " (no mtime change — verify manually)"

        # Append checkpoint row.
        ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with enrichment_log.open("a", encoding="utf-8") as f:
            f.write(f"- {stem}: ENRICHED at {ts}{touched}\n")
        log(f"    {stem} · OK")

    if failures:
        raise AuthoringError(
            phase="0e",
            message=(
                f"{len(failures)} of {len(chapter_files)} chapters failed enrichment: "
                + "; ".join(f"{s}: {m}" for s, m in failures[:3])
            ),
            manual_fallback=(
                "Inspect the chapter files of failed chapters; enrich each manually via "
                "/podcast, then add a `- <stem>: ENRICHED ...` row to enrichment-log.md "
                "and re-invoke orchestrate-book --resume."
            ),
        )

    return (
        f"0e per-chapter loop: {len(chapter_files)} chapters enriched "
        f"({len(already_done)} skipped as already done, "
        f"{len(chapter_files) - len(already_done)} newly enriched)"
    )


# ─── Per-chapter framing authorship ──────────────────────────────────────────
def author_framing(book_dir: Path, chapter_slug: str,
                   timeout: int = FRAMING_TIMEOUT) -> str:
    """Author 00-framing.md from the chapter contract + customize-prompt template.

    Reads:  BOOK_DIR/chapter-contracts/<slug>.yml
            BOOK_DIR/chapters/ch##-<slug>.txt
            content/podcast/.skill/handbook/notebooklm-customize-prompt-rules.md
    Writes: BOOK_DIR/_system/episode-drafts/EP##-<slug>/00-framing.md
    """
    book_slug = book_dir.name

    contract = book_dir / "chapter-contracts" / f"{chapter_slug}.yml"
    if not contract.exists():
        raise AuthoringError(
            phase=f"framing/{chapter_slug}",
            message=f"chapter contract missing: {contract}",
            manual_fallback="Run Phase 0d first to produce the contracts.",
        )

    # Resolve episode number + draft folder from the chapter file glob.
    chapter_files = list((book_dir / "chapters").glob(f"ch*-{chapter_slug}.txt"))
    if not chapter_files:
        raise AuthoringError(
            phase=f"framing/{chapter_slug}",
            message=f"chapter file missing for slug {chapter_slug} under {book_dir / 'chapters'}",
            manual_fallback="Run Phase 0d to produce the chapter files.",
        )
    chapter_file = chapter_files[0]
    # X7 (2026-05-21): strip letter suffix from ch## prefix via regex so chapters
    # like `ch14b-...` produce `EP14-...` not `EP14b-...`. Mirrors the X3 fix in
    # orchestrate_book.py:720-722. Without this, framing lands in EP14b/ while
    # build_episode_txt.py validator looks at EP14/ — paths diverge and the
    # chapter halts on R-PRONUNCIATION-IMPERATIVE (empty skeleton at the
    # validator's path). Affects all letter-suffix chapters: ch01a, ch03a,
    # ch04b, ch05c, ch13a, ch14b.
    _chap_prefix = chapter_file.stem.split("-", 1)[0]              # e.g. "ch14b" or "ch10"
    _m = _re.match(r"ch(\d+)", _chap_prefix)
    chap_num = _m.group(1) if _m else _chap_prefix[2:]             # "14" or "10" — digits only
    draft_dir = book_dir / "_system" / "episode-drafts" / f"EP{chap_num}-{chapter_slug}"
    framing_path = draft_dir / "00-framing.md"

    prompt = (
        f"You are authoring the framing (NotebookLM customize prompt) for episode "
        f"`EP{chap_num}-{chapter_slug}` of book `{book_slug}`. Read the canonical "
        f"procedure from `skills-staging/podcast/SKILL.md` PHASE 3 (Structure) and "
        f"`content/podcast/.skill/handbook/notebooklm-customize-prompt-rules.md` "
        f"(the framing's authority).\n\n"
        f"INPUT:\n"
        f"  - `{contract}` (chapter contract — audience, angle, host_dynamic, tensions, anchors)\n"
        f"  - `{chapter_file}` (the enriched chapter that NotebookLM uploads as SOURCE)\n"
        f"AUTHORITY:\n"
        f"  - `content/podcast/.skill/handbook/notebooklm-customize-prompt-rules.md`\n"
        f"  - `content/podcast/.skill/handbook/two-host-framing.md` (Driver vs Color roles)\n"
        f"  - `content/_shared/arabic/05-name-alias-policy.md`\n"
        f"OUTPUT: `{framing_path}` (the customize prompt — pasted into NotebookLM's Customize box)\n\n"
        f"Constraints (per `notebooklm-customize-prompt-rules.md`):\n"
        f"- R-WELCOME, R-NOREPEAT, R-NOBACKGROUND, R-NAMEALIAS, R-NOINTERRUPT, "
        f"R-PRONUNCIATION-IMPERATIVE, R-NOMODERNIZE (+ positive analogy paragraph), "
        f"R-NOSURPRISE (DENY clause + positive companion), R-NO-READ-PROMPT, "
        f"R-SUMMARYTAIL, R-NOMETA, R-CADENCE, R-NOFORMAL, R-SURPRISE-MOVE, R-RESET.\n"
        f"- Length: Default tier 200–500 words; Extended tier 1,000–1,800 body words "
        f"+ pronunciation block; hard cap 3,500 words per `build_episode_txt.py`.\n"
        f"- Use imperative `Pronounce \"X\" as \"Y\". Say it as one fluent word.` for every "
        f"Arabic term that appears in the chapter (consult `_phonetics.md` first).\n"
        f"- Length-tier-specific Opening directive — if Extended tier, include the exact "
        f"phrase: \"target a 30 to 45 minute deep-dive conversation\".\n"
        f"- Do NOT modify any file outside `{framing_path}`.\n\n"
        f"After authoring, run `python3 scripts/podcast/build_episode_txt.py "
        f"{book_dir} EP{chap_num}-{chapter_slug}` to validate. Fix any hard-gate failures "
        f"before exiting.\n\n"
        f"Exit when `{framing_path}` validates."
    )

    rc, stdout, stderr = _run_claude_p(
        prompt, timeout=timeout,
        book_dir=book_dir, phase="per-chapter", step=f"framing/{chapter_slug}",
    )
    _assert_artifact(
        phase=f"framing/{chapter_slug}",
        path=framing_path,
        rc=rc,
        stdout=stdout,
        stderr=stderr,
        manual_fallback=(
            f"1. /podcast — author the framing for chapter `{chapter_slug}` manually.\n"
            f"2. Run `build_episode_txt.py {book_dir} EP{chap_num}-{chapter_slug}` to validate.\n"
            f"3. Re-invoke orchestrate-book --resume."
        ),
    )
    return stdout


# ─── Challenger invocation (Phase B convergence loop calls this) ────────────
def invoke_challenger(book_dir: Path, chapter_slug: str,
                      timeout: int = CHALLENGER_TIMEOUT) -> str:
    """Invoke the podcast-challenger subagent on one chapter.

    Reads:  the full BOOK_DIR (the agent's cold-start file list)
    Writes: BOOK_DIR/_system/challenger-report.md
            content/podcast/.skill/_learning/findings.jsonl (append)
            content/podcast/.skill/_learning/health/<book-slug>.json
            BOOK_DIR/_system/health-trend.md (append)
    """
    book_slug = book_dir.name
    prompt = (
        f"Use the Agent tool with subagent_type=podcast-challenger to validate the "
        f"chapter `{chapter_slug}` of book `{book_slug}`. The challenger reads its "
        f"canonical spec from `.github/agents/podcast-challenger.agent.md`, runs the "
        f"convergence loop (max 5 internal iterations per invocation), writes "
        f"`{book_dir}/_system/challenger-report.md`, emits findings into "
        f"`content/podcast/.skill/_learning/findings.jsonl`, and writes the health JSON.\n\n"
        f"Invocation argument: `{book_slug} --chapter {chapter_slug}`\n\n"
        f"After the agent returns, exit immediately — do NOT take additional actions."
    )
    rc, stdout, stderr = _run_claude_p(
        prompt, timeout=timeout,
        book_dir=book_dir, phase="per-chapter", step=f"challenger/{chapter_slug}",
    )
    report = book_dir / "_system" / "challenger-report.md"
    if rc != 0:
        raise AuthoringError(
            phase=f"challenger/{chapter_slug}",
            message=f"claude -p (challenger) exited rc={rc}",
            manual_fallback=(
                "Invoke the podcast-challenger subagent manually on this chapter, "
                "then re-invoke orchestrate-book --resume."
            ),
            stdout=stdout,
            stderr=stderr,
        )
    if not report.exists() or report.stat().st_size == 0:
        raise AuthoringError(
            phase=f"challenger/{chapter_slug}",
            message=f"challenger did not produce a non-empty report at {report}",
            manual_fallback="Re-run challenger via Agent tool manually.",
            stdout=stdout,
            stderr=stderr,
        )
    return stdout


# ─── Fixer invocation (used when challenger surfaces P0/P1 findings) ────────
def invoke_fixer(book_dir: Path, chapter_slug: str, severity: str,
                 timeout: int = FIXER_TIMEOUT) -> str:
    """Invoke the conversational `/podcast` skill to fix open findings.

    The convergence loop (after a non-SHIP-READY challenger pass) calls this
    to address the P0 and P1 findings the challenger wrote into
    `challenger-report.md`. The fixer reads the report, applies fixes per the
    "Suggested fix" lines, and exits when done.

    severity is "P0" or "P1" — used in the prompt to scope which findings to fix.
    """
    book_slug = book_dir.name
    report = book_dir / "_system" / "challenger-report.md"
    if not report.exists():
        raise AuthoringError(
            phase=f"fixer/{chapter_slug}",
            message=f"no challenger-report.md at {report} — nothing to fix",
            manual_fallback="Run the challenger first.",
        )

    prompt = (
        f"You are the orchestrator's fixer pass for book `{book_slug}`, chapter "
        f"`{chapter_slug}`. Read `{report}` and address every **{severity}** finding "
        f"in the order listed. For each, follow the **Suggested fix** line in the "
        f"report.\n\n"
        f"Allowed edits (only these):\n"
        f"  - `{book_dir}/chapters/ch*-{chapter_slug}.txt`\n"
        f"  - `{book_dir}/_system/episode-drafts/EP*-{chapter_slug}/00-framing.md`\n\n"
        f"After every framing edit, run `python3 scripts/podcast/build_episode_txt.py "
        f"{book_dir} EP##-{chapter_slug}` to re-emit the episode `.txt`.\n\n"
        f"Do NOT modify the chapter contract, fixtures, _learning/* files, or any other "
        f"book/skill files. Exit when every {severity} finding listed in the report has "
        f"been addressed (or you have determined the finding cannot be fixed without "
        f"author judgment — in which case leave a one-line note at the end of the report)."
    )
    rc, stdout, stderr = _run_claude_p(
        prompt, timeout=timeout,
        book_dir=book_dir, phase="per-chapter", step=f"fixer/{chapter_slug}/{severity}",
    )
    if rc != 0:
        raise AuthoringError(
            phase=f"fixer/{chapter_slug}/{severity}",
            message=f"fixer rc={rc}",
            manual_fallback=f"Manually address {severity} findings in {report}, then --resume.",
            stdout=stdout,
            stderr=stderr,
        )
    return stdout


# ─── Trainer invocation (called once after all chapters ship) ────────────────
def invoke_trainer(book_dir: Path, timeout: int = TRAINER_TIMEOUT) -> str:
    """Invoke the podcast-trainer subagent after all chapters have shipped.

    Trainer's behavior is defined in `.github/agents/podcast-trainer.agent.md`:
    read `_learning/patterns.md` + open proposals → draft diffs → regression-gate
    via `test_challenger.py` in a worktree → promote (commit) or archive.
    """
    book_slug = book_dir.name
    prompt = (
        f"Use the Agent tool with subagent_type=podcast-trainer on book `{book_slug}`. "
        f"The trainer reads its canonical spec from `.github/agents/podcast-trainer.agent.md` "
        f"(v2 — substrate-driven). Follow its Protocol §1–§6:\n\n"
        f"  1. Run `python3 scripts/podcast/learn_aggregate.py` (ensures patterns.md is current)\n"
        f"  2. Read `content/podcast/.skill/_learning/patterns.md` + open proposals + health JSON\n"
        f"  3. For each proposer-eligible proposal: draft the smallest spec/handbook diff\n"
        f"  4. Regression-gate each diff in a `git worktree add` temp branch via "
        f"`python3 scripts/podcast/test_challenger.py` (all fixtures must stay green)\n"
        f"  5. On green: apply diff to the live book branch + commit with `[trainer]` tag, "
        f"move proposal to `_learning/promoted/` with decision-log block, bump "
        f"`CHALLENGER_VERSION` in `_rules.py` if the diff touched the challenger spec\n"
        f"  6. On red / INVARIANT / P0-class: move proposal to `_learning/archive/` with reason\n\n"
        f"Invocation argument: `{book_slug}`\n\n"
        f"After the agent returns, exit immediately."
    )
    rc, stdout, stderr = _run_claude_p(
        prompt, timeout=timeout,
        book_dir=book_dir, phase="trainer", step="invoke",
    )
    if rc != 0:
        raise AuthoringError(
            phase="trainer",
            message=f"trainer rc={rc}",
            manual_fallback="Invoke podcast-trainer manually then re-invoke orchestrate-book --resume.",
            stdout=stdout,
            stderr=stderr,
        )
    return stdout
