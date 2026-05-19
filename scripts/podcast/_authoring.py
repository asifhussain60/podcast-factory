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
FRAMING_TIMEOUT = 900         # 15 min per framing
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


def _run_claude_p(
    prompt: str,
    *,
    cwd: Path | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[int, str, str]:
    """Run `claude -p "<prompt>"` synchronously. Return (rc, stdout, stderr).

    Raises AuthoringError if the `claude` binary is not on PATH or the call
    times out. Non-zero return codes are returned to the caller for handling.
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
            f"Constraints (same as the whole-book Phase 0b — apply at the window scope):\n"
            f"- Do NOT modify any file other than `{win_out}`.\n"
            f"- Do NOT invent content not present in the INPUT — fidelity to the source is mandatory.\n"
            f"- Preserve every Arabic-derived term in transliteration form (al-Razi, al-Kirmani, etc.).\n"
            f"- Preserve every citation (verse references, hadith collection numbers).\n"
            f"- Do NOT wrap output in code fences or add preamble like 'Here is the refined text:'.\n\n"
            f"Exit when `{win_out}` is non-empty."
        )

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


# ─── Phase 0d — Chapter design ───────────────────────────────────────────────
def author_phase_0d(book_dir: Path, *, length_tier: str = "extended",
                    unit_mode: str = "auto",
                    timeout: int = DEFAULT_TIMEOUT) -> str:
    """Segment the refined source into meaningful, balanced **episode units**.

    `unit_mode` controls how source structure maps to episodes:

      - `chapter` — each source chapter becomes exactly one episode (one
        chapter file + one contract). Good for short/medium books where
        source chapters already fit the tier band.

      - `section` — each source chapter is split into multiple sections;
        each section becomes its own episode. Naming uses suffixes:
        `ch03a-...txt`, `ch03b-...txt`, etc. Good for long books where a
        single source chapter would exceed the tier band by >50%.

      - `auto` (default) — the LLM decides per source chapter: keep whole
        if it fits the tier band within ±50%, else split into sections.
        This is the recommended setting for any unfamiliar book.

    Reads:  BOOK_DIR/_system/source/text/refined-english.md
            BOOK_DIR/_system/source/text/_phonetics.md
    Writes: BOOK_DIR/chapters/ch##[a-z]?-<slug>.txt
            BOOK_DIR/chapter-contracts/<slug>.yml (one per episode)
            BOOK_DIR/_system/source/text/chapters-rationale.md
            BOOK_DIR/_system/source/text/source-chapter-map.md
                (table of source-chapter → episode-list; required when
                 unit_mode != 'chapter')
    """
    book_slug = book_dir.name
    in_refined = book_dir / "_system" / "source" / "text" / "refined-english.md"
    in_phonetics = book_dir / "_system" / "source" / "text" / "_phonetics.md"
    out_rationale = book_dir / "_system" / "source" / "text" / "chapters-rationale.md"
    out_source_map = book_dir / "_system" / "source" / "text" / "source-chapter-map.md"
    chapters_dir = book_dir / "chapters"
    contracts_dir = book_dir / "chapter-contracts"

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

    tier_band = {
        "default_deep_dive": "1,800–2,800 words per episode",
        "longer": "2,800–4,500 words per episode",
        "extended": "5,500–9,500 words per episode",
    }.get(length_tier, "5,500–9,500 words per episode (extended)")

    unit_directive = {
        "chapter": (
            "UNIT MODE: **chapter** — each source chapter becomes exactly ONE episode. "
            "Do NOT split any source chapter, even if it overflows the tier band."
        ),
        "section": (
            "UNIT MODE: **section** — each source chapter is split into one or more "
            "thematic sections; each section becomes its OWN episode. Use suffix letters "
            "(`ch03a-...`, `ch03b-...`) when multiple episodes come from the same source "
            "chapter; otherwise just `chNN-...` if the source chapter yields exactly one "
            "section. Every episode MUST land inside the tier band."
        ),
        "auto": (
            "UNIT MODE: **auto** — for each source chapter, decide: if its word count is "
            "within ±50% of the tier band midpoint, emit ONE episode for the whole chapter. "
            "If it exceeds 1.5× the band's upper bound, SPLIT it into sections (each section "
            "is its own episode, named `chNN<suffix>-...` where suffix is a single lowercase "
            "letter when multiple episodes come from the same source chapter). Aim for "
            "all episodes within ~30% of each other."
        ),
    }[unit_mode]

    source_map_instruction = (
        f"- Write `{out_source_map}` with a pipe table mapping each source chapter to its "
        f"resulting episode(s). Header: `| source chapter | source title | episode(s) | "
        f"split reason |`. This audit trail is REQUIRED when unit_mode is `section` or `auto`."
        if unit_mode in ("section", "auto") else
        f"- (unit_mode=chapter) Skip `source-chapter-map.md`."
    )

    prompt = (
        f"You are driving Phase 0d (Chapter / Episode Design) of the /podcast skill on "
        f"book-slug `{book_slug}`. Read the canonical procedure from "
        f"`skills-staging/podcast/SKILL.md` (search `### PHASE 0d`) and apply it.\n\n"
        f"INPUT:  `{in_refined}`, `{in_phonetics}`\n"
        f"OUTPUTS:\n"
        f"  - `{chapters_dir}/ch##[a-z]?-<slug>.txt` — one per episode\n"
        f"  - `{contracts_dir}/<slug>.yml` (one per episode, per chapter-contract.template.yml)\n"
        f"  - `{out_rationale}` (one paragraph per episode explaining the segmentation)\n"
        f"  - `{out_source_map}` (source-chapter → episode mapping, when unit_mode != chapter)\n\n"
        f"Length tier: **{length_tier}** — each episode MUST land in {tier_band}. "
        f"Episodes in a series should be within ~30% of each other within the tier.\n\n"
        f"{unit_directive}\n\n"
        f"Constraints:\n"
        f"- Do NOT modify any file outside the named outputs.\n"
        f"- Episode slugs are short kebab-case (e.g. `the-lineage-of-a-lost-argument`). "
        f"When a source chapter is split into sections, each section gets its own "
        f"distinct slug — do NOT reuse the source chapter's slug across sections.\n"
        f"- Each `chapter-contracts/<slug>.yml` carries: chapter_ref, slug, source_type, "
        f"book_slug, episode_number, title, audience, angle, episode_format=deep_dive, "
        f"host_dynamic, length_target, key_tensions, tone_constraints, anchor_passages, "
        f"adaptation_mode=faithful, phonetic_overrides, show_notes.\n"
        f"  - When this episode is a section of a longer source chapter, also include "
        f"`source_chapter_ref` and `section_index` (1-based) in the contract.\n"
        f"- Re-segment by THEME, not by the source's own chapter breaks (the source's "
        f"breaks are a STARTING point, not a constraint).\n"
        f"{source_map_instruction}\n\n"
        f"Exit when every episode file + contract is written and `{out_rationale}` is non-empty."
    )

    rc, stdout, stderr = _run_claude_p(prompt, timeout=timeout)
    _assert_artifact(
        phase="0d",
        path=out_rationale,
        rc=rc,
        stdout=stdout,
        stderr=stderr,
        manual_fallback=(
            "1. /podcast — drive Phase 0d on this BOOK_DIR manually.\n"
            "2. When chapters/ + chapter-contracts/ are populated, re-invoke "
            "orchestrate-book --resume."
        ),
    )
    # Verify that at least one chapter + contract was produced.
    if not list(chapters_dir.glob("ch*.txt")):
        raise AuthoringError(
            phase="0d",
            message=f"Phase 0d produced no chapter files under {chapters_dir}",
            manual_fallback="Re-run Phase 0d via /podcast on this BOOK_DIR.",
        )
    if not list(contracts_dir.glob("*.yml")):
        raise AuthoringError(
            phase="0d",
            message=f"Phase 0d produced no contracts under {contracts_dir}",
            manual_fallback="Author the per-chapter contracts via /podcast, then --resume.",
        )
    if unit_mode in ("section", "auto") and not out_source_map.exists():
        raise AuthoringError(
            phase="0d",
            message=(
                f"unit_mode={unit_mode!r} requires source-chapter-map.md but it was not "
                f"written at {out_source_map}"
            ),
            manual_fallback="Author source-chapter-map.md manually via /podcast, then --resume.",
        )
    return stdout


# ─── Phase 0e — Chapter enrichment ──────────────────────────────────────────
def author_phase_0e(book_dir: Path, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Enrich each chapter with citations from the seven-tier whitelist.

    Reads:  every BOOK_DIR/chapters/ch*.txt
            content/podcast/.skill/handbook/enrichment-sources.md
            content/_shared/arabic/03-arabic-english-manifest.md
    Writes: enriched BOOK_DIR/chapters/ch*.txt (in place)
            BOOK_DIR/_system/enrichment-log.md (per-chapter status)
    """
    book_slug = book_dir.name
    chapters_dir = book_dir / "chapters"
    enrichment_log = book_dir / "_system" / "enrichment-log.md"

    if not list(chapters_dir.glob("ch*.txt")):
        raise AuthoringError(
            phase="0e",
            message=f"no chapters to enrich under {chapters_dir} (Phase 0d should have produced them)",
            manual_fallback="Run Phase 0d first.",
        )

    prompt = (
        f"You are driving Phase 0e (Chapter Enrichment from Outside Sources) of the /podcast "
        f"skill on book-slug `{book_slug}`. Read the canonical procedure from "
        f"`skills-staging/podcast/SKILL.md` (search for `### PHASE 0e`) and apply it.\n\n"
        f"INPUT:  every `{chapters_dir}/ch*.txt`\n"
        f"AUTHORITY:\n"
        f"  - `content/podcast/.skill/handbook/enrichment-sources.md` (seven-tier whitelist + "
        f"60% cap + tier-diversity rule)\n"
        f"  - `content/_shared/arabic/03-arabic-english-manifest.md`\n"
        f"  - `content/podcast/.skill/handbook/notebooklm-source-chapter-rules.md` (R-rules)\n"
        f"OUTPUTS:\n"
        f"  - enriched chapter files (in place — every `{chapters_dir}/ch*.txt`)\n"
        f"  - `{enrichment_log}` (per-chapter enrichment status)\n\n"
        f"Constraints:\n"
        f"- Outside material ≤ 60% of any chapter's word count. The original author's "
        f"argument stays the spine.\n"
        f"- Tier diversity required — don't pull all enrichments from one tier.\n"
        f"- Every citation carries author, work, page or section, and translator (for Quranic translations).\n"
        f"- Apply R-PHONETICS-OUT: no inline `*term* (PHO-NE-TIC)` parens in chapters; "
        f"phonetic discipline lives in the customize prompt only.\n"
        f"- Apply R-HONORIFIC-ONCE: each honorific phrase form expanded ≤ 1× per chapter.\n"
        f"- Do NOT modify any file outside the named chapter files + enrichment-log.md.\n\n"
        f"After enrichment, verify each chapter still passes "
        f"`python3 scripts/podcast/build_episode_txt.py` (you may need to run this after each "
        f"chapter — fix any hard-gate failures before exiting).\n\n"
        f"Exit when every chapter is enriched and `{enrichment_log}` records the per-chapter status."
    )

    rc, stdout, stderr = _run_claude_p(prompt, timeout=timeout)
    _assert_artifact(
        phase="0e",
        path=enrichment_log,
        rc=rc,
        stdout=stdout,
        stderr=stderr,
        manual_fallback=(
            "1. /podcast — drive Phase 0e on this BOOK_DIR manually.\n"
            "2. When enrichment-log.md is non-empty, re-invoke orchestrate-book --resume."
        ),
    )
    return stdout


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
    chap_num = chapter_file.stem.split("-", 1)[0][2:]   # "ch01" → "01"
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

    rc, stdout, stderr = _run_claude_p(prompt, timeout=timeout)
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
    rc, stdout, stderr = _run_claude_p(prompt, timeout=timeout)
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
    rc, stdout, stderr = _run_claude_p(prompt, timeout=timeout)
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
    rc, stdout, stderr = _run_claude_p(prompt, timeout=timeout)
    if rc != 0:
        raise AuthoringError(
            phase="trainer",
            message=f"trainer rc={rc}",
            manual_fallback="Invoke podcast-trainer manually then re-invoke orchestrate-book --resume.",
            stdout=stdout,
            stderr=stderr,
        )
    return stdout
