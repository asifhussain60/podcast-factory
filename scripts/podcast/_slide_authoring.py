#!/usr/bin/env python3
"""_slide_authoring.py — LLM-shellout helpers for slide-deck pair authoring.

Analogous to `_authoring.py` (which covers audio Phases 0b-0e + framing), this
module owns the per-chapter slide-deck deliverable: the two-file pair documented
in `skills-staging/podcast/references/slide-deck-format.md`.

For one chapter, the deck pair is:

  - BOOK_DIR/slide-decks/chNN-deck-<slug>.txt        (the SLIDE-DECK SOURCE — uploaded to NotebookLM)
  - BOOK_DIR/slide-decks/chNN-framing-<slug>.md      (the SLIDE CUSTOMIZE PROMPT — pasted into NotebookLM)

The authoring flow:

  1. Read the audio chapter (`chapters/chNN-<slug>.txt`).
  2. Read the discussion-spine if present (`_system/episode-drafts/EP##-<slug>/04-discussion-spine.md`).
  3. Heredoc a prompt naming the references (slide-deck-format.md + slide-deck-patterns.md
     + slide-deck-steering.md) and the audio source, then shell out to `claude -p` exactly
     like `_authoring.py:author_framing` does.
  4. After the call returns, subprocess-call `build_slide_deck.py` to validate the pair.
  5. On validation failure, append findings to the prompt as constraints and retry once.

The retry budget is 1 (MAX_AUTHORING_RETRIES). If the retry also fails, return
``AuthoringResult(success=False, validation_findings=[...])`` — the orchestrator
decides whether to halt or surface.

Density-gauge skip flow (per slide-deck-format.md):

  - `compute_density(spine_path)` returns count([VISUAL CANDIDATE]) / count(beats).
  - `should_skip_with_justification(density)` returns True when density < threshold (0.25).
  - `author_justified_skip(book_dir, slug, density)` writes the skip justification
    to `slide-decks/_skipped/chNN-<slug>-skip.md`. The Slide Deck Challenger
    Probe 7 verifies the justification before accepting slide-deck-status = not-needed.

This module does NOT modify any audio artifacts and never reaches outside
`BOOK_DIR/slide-decks/` (live deliverables) or
`BOOK_DIR/_system/slide-decks/<chapter>/` (internal scaffolds).
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Reuse the canonical claude -p invocation pattern + error type from _authoring.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _authoring import (  # noqa: E402
    AuthoringError,
    _run_claude_p,
)

SCRIPT_VERSION = "1.0"

# Density gauge — per slide-deck-format.md (visual-candidate density below this
# threshold should trigger a justified-skip rather than a full deck pair).
DENSITY_THRESHOLD = 0.25

# Retry budget. 1 means: if validation fails, retry once with findings appended.
MAX_AUTHORING_RETRIES = 1

# Per-pair timeout. Mirrors FRAMING_TIMEOUT from _authoring.py — slide-deck
# authoring reads the audio chapter (5,500-9,500 words), the spine, and three
# reference files, then writes two new files of comparable length.
SLIDE_DECK_TIMEOUT = 1800  # 30 min — deck source can exceed framing length

# Reference paths, relative to the repo root (auto-discovered relative to this
# script: scripts/podcast/_slide_authoring.py → repo root is 2 up).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REFERENCE_FORMAT = _REPO_ROOT / "skills-staging" / "podcast" / "references" / "slide-deck-format.md"
REFERENCE_PATTERNS = _REPO_ROOT / "skills-staging" / "podcast" / "references" / "slide-deck-patterns.md"
REFERENCE_STEERING = _REPO_ROOT / "skills-staging" / "podcast" / "references" / "slide-deck-steering.md"

# Path to the validator script (does not need to exist for compute_density /
# should_skip_with_justification / author_justified_skip).
BUILD_SLIDE_DECK_SCRIPT = Path(__file__).resolve().parent / "build_slide_deck.py"


# ─── Return type ─────────────────────────────────────────────────────────────
@dataclass
class AuthoringResult:
    """Result of an author_deck_pair call.

    Fields:
      success: True iff both files exist, are non-empty, AND validation passed
        (or the retry passed after the first validation failed).
      deck_path: Path to the deck source (`chNN-deck-<slug>.txt`).
      framing_path: Path to the deck framing (`chNN-framing-<slug>.md`).
      deck_words: Whitespace-split word count of the deck source.
      framing_words: Whitespace-split word count of the deck framing.
      validation_findings: List of validator findings from the final attempt.
        Empty list when success=True; populated when success=False.
      stdout: Captured stdout from the final claude -p call (debug aid).
      stderr: Captured stderr from the final claude -p call (debug aid).
      attempts: How many claude -p calls were made (1 = no retry needed,
        2 = one retry was triggered).
    """

    success: bool
    deck_path: Path
    framing_path: Path
    deck_words: int = 0
    framing_words: int = 0
    validation_findings: list[str] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    attempts: int = 0


# ─── Internal helpers ────────────────────────────────────────────────────────
def _resolve_chapter_file(book_dir: Path, slug: str) -> Path:
    """Resolve chapters/chNN-<slug>.txt for the given slug.

    Mirrors _authoring.py:author_framing — supports letter-suffixed chapters
    (ch14b-...) and plain ones (ch10-...).
    """
    matches = list((book_dir / "chapters").glob(f"ch*-{slug}.txt"))
    if not matches:
        raise AuthoringError(
            phase=f"slide-deck/{slug}",
            message=f"audio chapter file missing for slug {slug!r} under {book_dir / 'chapters'}",
            manual_fallback="Run Phase 0d first to produce the chapter files.",
        )
    return matches[0]


def _resolve_chap_num(chapter_file: Path) -> str:
    """Extract the digit-only chapter number from a chapter filename.

    Mirrors _authoring.py:author_framing — `ch14b-foo.txt` → "14"; `ch10-bar.txt` → "10".
    """
    prefix = chapter_file.stem.split("-", 1)[0]
    m = re.match(r"ch(\d+)", prefix)
    return m.group(1) if m else prefix[2:]


def _resolve_chap_prefix_for_deck(chapter_file: Path) -> str:
    """Return the `chNN` (or `chNNx`) prefix used in deck/framing filenames.

    Slide deck filenames mirror the audio chapter prefix exactly per
    slide-deck-format.md §"Slug + filename convention".
    """
    return chapter_file.stem.split("-", 1)[0]


def _resolve_spine_path(book_dir: Path, slug: str, chap_num: str) -> Path:
    """Resolve the discussion-spine path, if present.

    Returns a Path; existence is checked by the caller. EP## uses digit-only
    chapter number (same convention as _authoring.py).
    """
    return (
        book_dir
        / "_system"
        / "episode-drafts"
        / f"EP{chap_num}-{slug}"
        / "04-discussion-spine.md"
    )


def _wordcount(path: Path) -> int:
    if not path.exists():
        return 0
    return len(path.read_text(encoding="utf-8").split())


def _count_beats(spine_text: str) -> int:
    """Count beats in a discussion-spine.

    A beat is any line whose content starts with `### Beat ` (current convention
    in _system/episode-drafts/EP##-<slug>/04-discussion-spine.md). Tolerates `##`
    fallback for older spines.
    """
    n = 0
    for line in spine_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("### Beat ") or stripped.startswith("## Beat "):
            n += 1
    return n


def _count_visual_candidates(spine_text: str) -> int:
    """Count `[VISUAL CANDIDATE]` markers in a discussion-spine."""
    return len(re.findall(r"\[VISUAL CANDIDATE\]", spine_text))


def _build_pair_prompt(
    *,
    book_slug: str,
    slug: str,
    chap_num: str,
    chapter_file: Path,
    spine_path: Path | None,
    deck_path: Path,
    framing_path: Path,
    audio_words: int,
    extra_constraints: str = "",
) -> str:
    """Build the heredoc prompt for `claude -p` to author the deck pair.

    `extra_constraints` is appended to the prompt body — used by the retry path
    to inject the validator's findings as additional constraints.
    """
    spine_clause = (
        f"  - `{spine_path}` (the discussion-spine — every [VISUAL CANDIDATE] beat should map to a structure in the deck source)\n"
        if spine_path is not None and spine_path.exists()
        else "  - (no discussion-spine present for this episode — derive visual moments from the audio chapter alone)\n"
    )

    constraints_block = ""
    if extra_constraints.strip():
        constraints_block = (
            "\n\nADDITIONAL CONSTRAINTS (from prior validation failure — fix these):\n"
            f"{extra_constraints.strip()}\n"
        )

    # Word-count targets per slide-deck-format.md: deck source is 50-100% of audio
    # chapter wordcount with a hard floor of 2,000 words; framing is 150-250 words.
    deck_lo = max(2000, int(audio_words * 0.5))
    deck_hi = max(deck_lo + 500, audio_words)

    return (
        f"You are authoring the slide-deck PAIR for episode `EP{chap_num}-{slug}` "
        f"of book `{book_slug}`. The pair is one SOURCE file + one CUSTOMIZE PROMPT file, "
        f"both landing in `{deck_path.parent}/`.\n\n"
        f"AUTHORITIES (read these first — they govern shape and rules):\n"
        f"  - `{REFERENCE_FORMAT}` (deliverable shape — what each file contains)\n"
        f"  - `{REFERENCE_PATTERNS}` (diagram taxonomy — named-axis 2x2, comparison matrix, contrast pair, hierarchy, genealogy chain, process flow, timeline, annotated structure, visual metaphor, quadrant map)\n"
        f"  - `{REFERENCE_STEERING}` (steering phrases — pick 3-5 for the framing's `## Steering Phrases`)\n\n"
        f"INPUT:\n"
        f"  - `{chapter_file}` (the audio chapter — {audio_words} words; this is the SOURCE content to re-render structurally)\n"
        f"{spine_clause}"
        f"\nOUTPUTS (write EXACTLY these two files — no others):\n"
        f"  - `{deck_path}` (the SLIDE-DECK SOURCE — `.txt`, NotebookLM-uploadable)\n"
        f"  - `{framing_path}` (the SLIDE CUSTOMIZE PROMPT — `.md`, NotebookLM-pasteable)\n\n"
        f"DECK SOURCE rules (`{deck_path.name}`):\n"
        f"- H1: the chapter title (same as the audio chapter's H1).\n"
        f"- H2: the audio chapter's movements (preserved verbatim).\n"
        f"- Within each H2, body is STRUCTURES (tables, contrast columns, hierarchies, "
        f"genealogy chains, process flows). NO prose paragraphs longer than 100 words.\n"
        f"- Every structural moment matches a named diagram type from the patterns taxonomy.\n"
        f"- Word count target: {deck_lo}-{deck_hi} (50-100% of audio chapter's {audio_words}; "
        f"hard floor 2,000). If you cannot reach 2,000 words structurally, STOP and emit a "
        f"justified-skip explanation in the prompt's stdout — do not write a thin deck source.\n"
        f"- Contrast columns use `Column A:` / `Column B:` PREFIX LINES (not side-by-side "
        f"markdown columns — NotebookLM parses sequential text better).\n"
        f"- Genealogies use explicit `→` arrows in text, one chain per line.\n"
        f"- Citations / verbatim quotes preserved in blockquotes with attribution; no prose "
        f"around them.\n"
        f"- No em dashes (use commas or restructure). No emojis. No inline phonetic parens "
        f"on Arabic terms (R-PHONETICS-OUT — phonetics live in the customize prompt, not here).\n"
        f"- Every concept present in the audio chapter must appear (restructured) in the deck "
        f"source; the deck is a RE-PRESENTATION, not a SUMMARY.\n\n"
        f"FRAMING rules (`{framing_path.name}`):\n"
        f"- 150-250 words total.\n"
        f"- H1 (one line; file-label — NotebookLM users skip this line when pasting).\n"
        f"- Required H2 sections, in this order:\n"
        f"  1. `## Audience` — named concretely (no \"general audience\").\n"
        f"  2. `## Core Principle` — restate the audio-vs-slide division of labor in 1-2 sentences.\n"
        f"  3. `## Visual Priorities` — 2-4 specific visual moments matching structures in the deck source.\n"
        f"  4. `## Prohibited Patterns` — explicit list (no literal-text slides, no audio-restatement, "
        f"no stock-photo descriptions, no bullet-list-as-diagram).\n"
        f"  5. `## Steering Phrases` — 3-5 phrases drawn from `{REFERENCE_STEERING.name}`.\n\n"
        f"AFTER WRITING both files, print on stdout (one per line):\n"
        f"  DECK: {deck_path}\n"
        f"  FRAMING: {framing_path}\n"
        f"  DECK_WORDS: <integer>\n"
        f"  FRAMING_WORDS: <integer>\n\n"
        f"Constraints (hard):\n"
        f"- Do NOT modify any file other than `{deck_path}` and `{framing_path}`.\n"
        f"- Do NOT touch the audio chapter at `{chapter_file}` or any file under `chapters/`, "
        f"`chapter-contracts/`, or `_system/episode-drafts/` (read-only for this task).\n"
        f"- Do NOT wrap outputs in code fences or add preamble.\n"
        f"{constraints_block}"
        f"\nExit when both files exist and are non-empty."
    )


def _parse_stdout_counts(stdout: str) -> tuple[int, int]:
    """Parse `DECK_WORDS:` and `FRAMING_WORDS:` from the LLM's stdout, if present.

    Returns (deck_words, framing_words). Either may be 0 if not present.
    The authoritative source remains the on-disk file word count; these are a
    sanity-check / logging aid.
    """
    deck = 0
    framing = 0
    for line in stdout.splitlines():
        s = line.strip()
        if s.startswith("DECK_WORDS:"):
            try:
                deck = int(s.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif s.startswith("FRAMING_WORDS:"):
            try:
                framing = int(s.split(":", 1)[1].strip())
            except ValueError:
                pass
    return deck, framing


def _run_validator(
    book_dir: Path, deck_path: Path, framing_path: Path
) -> tuple[bool, list[str]]:
    """Subprocess-call build_slide_deck.py to validate the pair.

    Returns (ok, findings). `ok` is True iff the validator exits 0 OR the
    validator script is missing (treated as "no validator wired up yet — pass
    through"). `findings` is the validator's parsed stderr/stdout lines on
    failure.
    """
    if not BUILD_SLIDE_DECK_SCRIPT.exists():
        # Validator not yet implemented — treat as pass-through. The on-disk
        # existence + non-emptiness checks in author_deck_pair are still enforced.
        return True, []

    try:
        proc = subprocess.run(
            [
                sys.executable,
                str(BUILD_SLIDE_DECK_SCRIPT),
                str(book_dir),
                str(deck_path),
                str(framing_path),
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return False, ["validator timed out after 300s"]
    except FileNotFoundError:
        # python interpreter missing? Treat as pass-through, surface to caller.
        return True, []

    if proc.returncode == 0:
        return True, []

    # Parse findings — one per non-empty line of stderr (preferred) or stdout.
    blob = (proc.stderr or "").strip() or (proc.stdout or "").strip()
    findings = [ln.rstrip() for ln in blob.splitlines() if ln.strip()]
    if not findings:
        findings = [f"validator exited rc={proc.returncode} with no output"]
    return False, findings


# ─── Public API ──────────────────────────────────────────────────────────────
def author_deck_pair(
    book_dir: Path,
    slug: str,
    *,
    retry_on_validation_fail: bool = True,
    timeout: int = SLIDE_DECK_TIMEOUT,
) -> AuthoringResult:
    """Author the slide-deck SOURCE + framing pair for one chapter.

    Reads the audio chapter at `chapters/chNN-<slug>.txt` and the discussion-spine
    at `_system/episode-drafts/EP##-<slug>/04-discussion-spine.md` (if present),
    then invokes `claude -p` with `slide-deck-format.md` + `slide-deck-patterns.md`
    + `slide-deck-steering.md` as steering.

    Writes:
      - `slide-decks/chNN-deck-<slug>.txt`
      - `slide-decks/chNN-framing-<slug>.md`

    After authoring, calls `build_slide_deck.py` for validation. If validation
    fails and `retry_on_validation_fail` is True, re-invokes claude -p once with
    the validation findings appended to the prompt as constraints.

    Returns an :class:`AuthoringResult`. Raises :class:`AuthoringError` only for
    unrecoverable errors (claude not on PATH, timeout, missing prerequisites).
    """
    chapter_file = _resolve_chapter_file(book_dir, slug)
    chap_num = _resolve_chap_num(chapter_file)
    chap_prefix = _resolve_chap_prefix_for_deck(chapter_file)

    slide_decks_dir = book_dir / "slide-decks"
    slide_decks_dir.mkdir(parents=True, exist_ok=True)

    deck_path = slide_decks_dir / f"{chap_prefix}-deck-{slug}.txt"
    framing_path = slide_decks_dir / f"{chap_prefix}-framing-{slug}.md"

    spine_path = _resolve_spine_path(book_dir, slug, chap_num)
    audio_words = _wordcount(chapter_file)

    book_slug = book_dir.name
    extra_constraints = ""
    attempts = 0
    last_stdout = ""
    last_stderr = ""
    last_findings: list[str] = []

    while attempts <= (MAX_AUTHORING_RETRIES if retry_on_validation_fail else 0):
        attempts += 1
        prompt = _build_pair_prompt(
            book_slug=book_slug,
            slug=slug,
            chap_num=chap_num,
            chapter_file=chapter_file,
            spine_path=spine_path if spine_path.exists() else None,
            deck_path=deck_path,
            framing_path=framing_path,
            audio_words=audio_words,
            extra_constraints=extra_constraints,
        )

        rc, stdout, stderr = _run_claude_p(
            prompt,
            timeout=timeout,
            book_dir=book_dir,
            phase="slide-deck",
            step=f"pair/{slug}/attempt-{attempts}",
        )
        last_stdout = stdout
        last_stderr = stderr

        if rc != 0:
            raise AuthoringError(
                phase=f"slide-deck/{slug}",
                message=f"claude -p exited rc={rc} authoring slide-deck pair (attempt {attempts}).",
                manual_fallback=(
                    f"1. /podcast — author the slide-deck pair for `{slug}` manually using "
                    f"`{REFERENCE_FORMAT.name}` as the spec.\n"
                    f"2. Drop files at `{deck_path}` and `{framing_path}`.\n"
                    f"3. Re-invoke orchestrate-book --resume."
                ),
                stdout=stdout,
                stderr=stderr,
            )

        # Hard existence + non-emptiness checks.
        on_disk_ok = (
            deck_path.exists()
            and deck_path.stat().st_size > 0
            and framing_path.exists()
            and framing_path.stat().st_size > 0
        )
        if not on_disk_ok:
            last_findings = [
                f"missing or empty output: deck exists={deck_path.exists()} "
                f"size={deck_path.stat().st_size if deck_path.exists() else 0}; "
                f"framing exists={framing_path.exists()} "
                f"size={framing_path.stat().st_size if framing_path.exists() else 0}",
            ]
            if retry_on_validation_fail and attempts <= MAX_AUTHORING_RETRIES:
                extra_constraints = "\n".join(f"- {f}" for f in last_findings)
                continue
            # No retry budget left — return failure.
            return AuthoringResult(
                success=False,
                deck_path=deck_path,
                framing_path=framing_path,
                deck_words=_wordcount(deck_path),
                framing_words=_wordcount(framing_path),
                validation_findings=last_findings,
                stdout=stdout,
                stderr=stderr,
                attempts=attempts,
            )

        # Validator pass.
        ok, findings = _run_validator(book_dir, deck_path, framing_path)
        if ok:
            return AuthoringResult(
                success=True,
                deck_path=deck_path,
                framing_path=framing_path,
                deck_words=_wordcount(deck_path),
                framing_words=_wordcount(framing_path),
                validation_findings=[],
                stdout=stdout,
                stderr=stderr,
                attempts=attempts,
            )

        last_findings = findings
        if retry_on_validation_fail and attempts <= MAX_AUTHORING_RETRIES:
            extra_constraints = "\n".join(f"- {f}" for f in findings)
            continue
        # Exhausted retry budget; return validation-failure result.
        return AuthoringResult(
            success=False,
            deck_path=deck_path,
            framing_path=framing_path,
            deck_words=_wordcount(deck_path),
            framing_words=_wordcount(framing_path),
            validation_findings=findings,
            stdout=stdout,
            stderr=stderr,
            attempts=attempts,
        )

    # Should not reach here, but defensive.
    return AuthoringResult(
        success=False,
        deck_path=deck_path,
        framing_path=framing_path,
        deck_words=_wordcount(deck_path),
        framing_words=_wordcount(framing_path),
        validation_findings=last_findings or ["unknown failure (no attempts ran)"],
        stdout=last_stdout,
        stderr=last_stderr,
        attempts=attempts,
    )


def compute_density(spine_path: Path) -> float:
    """Compute visual-candidate density from a discussion-spine file.

    Returns count([VISUAL CANDIDATE]) / count(total beats).
    Returns 0.0 if spine file does not exist or has no beats.
    """
    if not spine_path.exists():
        return 0.0
    text = spine_path.read_text(encoding="utf-8")
    beats = _count_beats(text)
    if beats <= 0:
        return 0.0
    candidates = _count_visual_candidates(text)
    return candidates / beats


def should_skip_with_justification(
    density: float, *, threshold: float = DENSITY_THRESHOLD
) -> bool:
    """Per slide-deck-format.md density gauge: True if density < threshold."""
    return density < threshold


def author_justified_skip(book_dir: Path, slug: str, density: float) -> Path:
    """Author a justified-skip entry.

    Writes to `slide-decks/_skipped/chNN-<slug>-skip.md` with reasoning. The
    Slide Deck Challenger Probe 7 verifies this justification before accepting
    slide-deck-status = not-needed.
    """
    chapter_file = _resolve_chapter_file(book_dir, slug)
    chap_num = _resolve_chap_num(chapter_file)
    chap_prefix = _resolve_chap_prefix_for_deck(chapter_file)

    skip_dir = book_dir / "slide-decks" / "_skipped"
    skip_dir.mkdir(parents=True, exist_ok=True)
    skip_path = skip_dir / f"{chap_prefix}-{slug}-skip.md"

    spine_path = _resolve_spine_path(
        book_dir, slug, chap_num
    )
    book_slug = book_dir.name

    # Gather the inputs the Challenger Probe 7 expects to see cited.
    spine_present = spine_path.exists()
    spine_text = spine_path.read_text(encoding="utf-8") if spine_present else ""
    beat_count = _count_beats(spine_text)
    candidate_count = _count_visual_candidates(spine_text)

    prompt = (
        f"You are authoring a JUSTIFIED-SKIP entry for the slide-deck deliverable of "
        f"episode `EP{chap_num}-{slug}` of book `{book_slug}`. The density gauge from "
        f"`{REFERENCE_FORMAT}` was triggered: visual-candidate density = "
        f"{density:.3f} (threshold = {DENSITY_THRESHOLD}).\n\n"
        f"INPUT:\n"
        f"  - `{chapter_file}` (the audio chapter)\n"
        + (
            f"  - `{spine_path}` (discussion-spine — {candidate_count} [VISUAL CANDIDATE] "
            f"markers across {beat_count} beats)\n"
            if spine_present
            else "  - (no discussion-spine present)\n"
        )
        + f"OUTPUT: `{skip_path}` (the skip justification — markdown).\n\n"
        f"The justification MUST satisfy Slide Deck Challenger Probe 7 — it must name:\n"
        f"  (a) the source TYPE from the affinity matrix in `{REFERENCE_FORMAT.name}` "
        f"(e.g., \"pure narrative,\" \"editorial side-matter,\" \"manuscript history\"),\n"
        f"  (b) which [VISUAL CANDIDATE] tags from the discussion-spine were considered "
        f"(list them with their beat numbers),\n"
        f"  (c) why none of those candidates warranted a slide (specific source structure "
        f"that's absent — NOT generic phrases like \"no visual content\" or \"doesn't fit\").\n\n"
        f"OUTPUT FORMAT (write to `{skip_path}`, markdown):\n"
        f"```\n"
        f"# Slide Deck Skip — EP{chap_num}-{slug}\n\n"
        f"## Density gauge\n"
        f"- Visual-candidate density: {density:.3f}\n"
        f"- Threshold: {DENSITY_THRESHOLD}\n"
        f"- Visual candidates considered: {candidate_count}\n"
        f"- Total beats: {beat_count}\n\n"
        f"## Source type\n"
        f"<one paragraph naming the affinity-matrix category and why this chapter falls in it>\n\n"
        f"## Visual candidates considered\n"
        f"<one bullet per [VISUAL CANDIDATE] beat: beat-id, what was tagged, why no slide>\n\n"
        f"## Conclusion\n"
        f"slide-deck-status = not-needed. <one sentence summarizing the verdict>\n"
        f"```\n\n"
        f"Constraints:\n"
        f"- Write ONLY `{skip_path}`. Do NOT touch any other file.\n"
        f"- Do NOT use generic phrases (\"purely narrative,\" \"no visual content,\" "
        f"\"doesn't fit\") without naming specific absent structure.\n\n"
        f"Exit when `{skip_path}` exists and is non-empty."
    )

    rc, stdout, stderr = _run_claude_p(
        prompt,
        timeout=SLIDE_DECK_TIMEOUT,
        book_dir=book_dir,
        phase="slide-deck",
        step=f"justified-skip/{slug}",
    )
    if rc != 0:
        raise AuthoringError(
            phase=f"slide-deck-skip/{slug}",
            message=f"claude -p exited rc={rc} authoring justified-skip for `{slug}`.",
            manual_fallback=(
                f"Author `{skip_path}` manually per Slide Deck Challenger Probe 7 "
                f"requirements (see `{REFERENCE_FORMAT}`)."
            ),
            stdout=stdout,
            stderr=stderr,
        )
    if not skip_path.exists() or skip_path.stat().st_size == 0:
        raise AuthoringError(
            phase=f"slide-deck-skip/{slug}",
            message=f"justified-skip artifact missing or empty at {skip_path}",
            manual_fallback=f"Author `{skip_path}` manually then --resume.",
            stdout=stdout,
            stderr=stderr,
        )
    return skip_path


__all__ = [
    "SCRIPT_VERSION",
    "DENSITY_THRESHOLD",
    "MAX_AUTHORING_RETRIES",
    "SLIDE_DECK_TIMEOUT",
    "AuthoringResult",
    "author_deck_pair",
    "compute_density",
    "should_skip_with_justification",
    "author_justified_skip",
]
