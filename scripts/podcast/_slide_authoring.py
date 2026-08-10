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

R3 DR-005 split (2026-07-18): the three prompt builders + REFERENCE_* constants
moved verbatim to `_slide_prompts.py`; the deterministic helpers, density gauge,
and validators moved verbatim to `_slide_checks.py`. Every moved name is
re-exported here (`X as X`, the `_azure.py` pattern) so importers and test
patch-targets keep working unchanged. What remains here is the LLM-shellout
orchestration: the authoring loops, retry budgets, and the justified-skip call
(whose prompt is inline because it interpolates a dozen call-site locals — a
builder would need the same long parameter list Spec-2 declined).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

# Reuse the canonical claude -p invocation pattern + error type from _authoring.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _authoring import (
    AuthoringError,
    _run_claude_p,
)
from _runlog import log_event
from _slide_checks import (
    _BOOK_FRAMING_REQUIRED_H2 as _BOOK_FRAMING_REQUIRED_H2,
)

# R3 DR-005 re-exports — moved names, kept importable/patchable from this module.
from _slide_checks import (
    BUILD_SLIDE_DECK_SCRIPT as BUILD_SLIDE_DECK_SCRIPT,
)
from _slide_checks import (
    DENSITY_THRESHOLD as DENSITY_THRESHOLD,
)
from _slide_checks import (
    _count_beats as _count_beats,
)
from _slide_checks import (
    _count_visual_candidates as _count_visual_candidates,
)
from _slide_checks import (
    _parse_stdout_counts as _parse_stdout_counts,
)
from _slide_checks import (
    _resolve_chap_num as _resolve_chap_num,
)
from _slide_checks import (
    _resolve_chap_prefix_for_deck as _resolve_chap_prefix_for_deck,
)
from _slide_checks import (
    _resolve_chapter_file as _resolve_chapter_file,
)
from _slide_checks import (
    _resolve_spine_path as _resolve_spine_path,
)
from _slide_checks import (
    _run_validator as _run_validator,
)
from _slide_checks import (
    _validate_book_pair as _validate_book_pair,
)
from _slide_checks import (
    _wordcount as _wordcount,
)
from _slide_checks import (
    compute_density as compute_density,
)
from _slide_checks import (
    should_skip_with_justification as should_skip_with_justification,
)
from _slide_prompts import (
    REFERENCE_FORMAT as REFERENCE_FORMAT,
)
from _slide_prompts import (
    REFERENCE_PATTERNS as REFERENCE_PATTERNS,
)
from _slide_prompts import (
    REFERENCE_STEERING as REFERENCE_STEERING,
)
from _slide_prompts import (
    _build_book_pair_prompt as _build_book_pair_prompt,
)
from _slide_prompts import (
    _build_pair_prompt as _build_pair_prompt,
)
from _slide_prompts import (
    _build_pair_prompt_technical as _build_pair_prompt_technical,
)
from _subprocess import err as _err

# Cost-ledger wiring (AU-S3-001 fix): every `claude -p` invocation in this
# module flows through `_authoring._run_claude_p(book_dir=...)`, which
# internally calls `_cost_ledger.append_from_claude_p_stdout` to append a
# per-call row to `<book_dir>/_system/cost-ledger.jsonl`. Calls below pass
# `phase="11b-slide-authoring"` so cost-ledger analysis can split slide-deck
# spend from audio spend, and so the orchestrator's `$50` cost cap (which
# sums `cost_usd` across all ledger rows in `orchestrate_book.py`'s
# `book_cost_usd()`) catches slide-deck overruns. Import made explicit so
# the regression-isolation grep finds `cost_ledger` here.

SCRIPT_VERSION = "1.0"

# Retry budget. 1 means: if validation fails, retry once with findings appended.
MAX_AUTHORING_RETRIES = 1

# Per-pair timeout. Mirrors FRAMING_TIMEOUT from _authoring.py — slide-deck
# authoring reads the audio chapter (5,500-9,500 words), the spine, and three
# reference files, then writes two new files of comparable length.
SLIDE_DECK_TIMEOUT = 1800  # 30 min — deck source can exceed framing length


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


# ─── Public API ──────────────────────────────────────────────────────────────
def author_deck_pair(
    book_dir: Path,
    slug: str,
    *,
    retry_on_validation_fail: bool = True,
    timeout: int = SLIDE_DECK_TIMEOUT,
    prior_findings: list[dict] | None = None,
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

    `prior_findings` — Slide Deck Challenger findings from the OUTER
    convergence loop's previous iteration (`_slide_convergence.run_slide_convergence`),
    shaped as `[{"id", "severity", "slides", "notes", "scope"}, ...]`. When
    given, the FIRST authoring attempt already carries them as constraints,
    so a re-author actually responds to what the Challenger flagged instead
    of regenerating blind. Without this the outer loop retries identically
    on every iteration.

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
    if prior_findings:
        extra_constraints = "\n".join(
            f"- [{f.get('id', '?')}] {f.get('notes', '')} (slides: {f.get('slides', '?')})" for f in prior_findings
        )
    else:
        extra_constraints = ""
    attempts = 0
    last_stdout = ""
    last_stderr = ""
    last_findings: list[str] = []

    # ── Category-aware prompt routing ─────────────────────────────────────
    # Islamic/scholarly → Islamic visual design (_build_pair_prompt)
    # Technical/explainers → developer-audience visual design (_build_pair_prompt_technical)
    # Sites/consumer → Islamic prompt (no dedicated variant yet; adequate for consumer finance)
    from _authoring._core import ARABIC_SCHOLARLY_CATEGORIES, _read_category

    _category = _read_category(book_dir)
    _prompt_builder = (
        _build_pair_prompt_technical
        if _category not in ARABIC_SCHOLARLY_CATEGORIES and _category == "explainers"
        else _build_pair_prompt
    )
    visual_constraints = ""
    try:
        from _translation_edition import requires_monochrome_visuals

        if requires_monochrome_visuals(book_dir):
            visual_constraints = (
                "BLACK-AND-WHITE VISUAL STYLE (hard):\n"
                "- The NotebookLM deck must be black and white only, minimal and elegant: black ink, "
                "white background, gray shading only when needed. NEVER a dark or coloured background.\n"
                "- Ask for line-art diagrams, tables, hierarchy trees, contrast panels, and process flows.\n"
                "- No color fills, no color-coded categories, no gradients, no photographs, no stock imagery.\n"
                "- Include this requirement in the framing's `## Prohibited Patterns` and `## Steering Phrases` sections.\n\n"
            )
    except Exception:
        pass

    while attempts <= (MAX_AUTHORING_RETRIES if retry_on_validation_fail else 0):
        attempts += 1
        prompt = _prompt_builder(
            book_slug=book_slug,
            slug=slug,
            chap_num=chap_num,
            chapter_file=chapter_file,
            spine_path=spine_path if spine_path.exists() else None,
            deck_path=deck_path,
            framing_path=framing_path,
            audio_words=audio_words,
            visual_constraints=visual_constraints,
            extra_constraints=extra_constraints,
        )

        rc, stdout, stderr = _run_claude_p(
            prompt,
            timeout=timeout,
            book_dir=book_dir,
            phase="11b-slide-authoring",
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
        ok, findings = _run_validator(book_dir, slug)
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
            # Record WHY. Findings used to be consumed into the retry prompt and
            # dropped, so a retry firing on 100% of authorings (16/16 on
            # 2026-07-31, a wasted model call each) left no evidence anywhere.
            _err(f"slide-deck[{slug}]: attempt {attempts} failed validation, retrying — " + "; ".join(findings[:3]))
            log_event(
                "slide.authoring.validation_retry",
                book_dir=book_dir,
                level="warn",
                phase="11b-slide-authoring",
                slug=slug,
                msg=findings[0] if findings else "",
                attempt=attempts,
                findings=findings,
            )
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


def author_book_deck_pair(
    book_dir: Path,
    *,
    retry_on_validation_fail: bool = True,
    timeout: int = SLIDE_DECK_TIMEOUT,
    model_flag: str | None = None,
) -> AuthoringResult:
    """Author ONE slide-deck pair covering the whole book (slide_deck_mode: book).

    Writes:
      - `slide-decks/book-deck-source.txt`
      - `slide-decks/book-framing.md`

    The user pastes book-framing.md into NotebookLM's Slide-deck Describe box
    (with book-deck-source.txt uploaded as the source), exports ONE deck, and
    drops it at `slide-decks/book-deck.pdf` — the path `_slide_import.py`'s
    book-level branch already consumes.

    model_flag overrides the default model (Opus) for the deck-authoring call —
    this is presentational NotebookLM framing text over already-translated
    content, not new translation, so callers may safely pass a lighter model
    (e.g. translation-edition passes Sonnet). None preserves the prior default.
    """
    chapter_files = sorted((book_dir / "chapters").glob("ch*.txt"))
    if not chapter_files:
        raise AuthoringError(
            phase="slide-deck/book",
            message=f"no chapter files under {book_dir / 'chapters'}",
            manual_fallback="Run Phase 0d first.",
        )
    deck_dir = book_dir / "slide-decks"
    deck_dir.mkdir(parents=True, exist_ok=True)
    deck_path = deck_dir / "book-deck-source.txt"
    framing_path = deck_dir / "book-framing.md"

    extra_constraints = ""
    attempts = 0
    last_stdout = ""
    last_stderr = ""
    last_findings: list[str] = []
    while attempts <= (MAX_AUTHORING_RETRIES if retry_on_validation_fail else 0):
        attempts += 1
        prompt = _build_book_pair_prompt(
            book_slug=book_dir.name,
            chapter_files=chapter_files,
            deck_path=deck_path,
            framing_path=framing_path,
            extra_constraints=extra_constraints,
        )
        rc, stdout, stderr = _run_claude_p(
            prompt,
            timeout=timeout,
            book_dir=book_dir,
            phase="11b-slide-authoring",
            step=f"book-pair/attempt-{attempts}",
            model_flag=model_flag,
        )
        last_stdout, last_stderr = stdout, stderr
        if rc != 0:
            raise AuthoringError(
                phase="slide-deck/book",
                message=f"claude -p exited rc={rc} authoring book deck pair (attempt {attempts}).",
                manual_fallback=(
                    f"Author `{deck_path}` + `{framing_path}` manually per "
                    f"`{REFERENCE_FORMAT.name}`, then re-run --resume."
                ),
                stdout=stdout,
                stderr=stderr,
            )
        last_findings = _validate_book_pair(deck_path, framing_path)
        if not last_findings:
            return AuthoringResult(
                success=True,
                deck_path=deck_path,
                framing_path=framing_path,
                deck_words=_wordcount(deck_path),
                framing_words=_wordcount(framing_path),
                stdout=stdout,
                stderr=stderr,
                attempts=attempts,
            )
        extra_constraints = "\n".join(f"- {f}" for f in last_findings)
    return AuthoringResult(
        success=False,
        deck_path=deck_path,
        framing_path=framing_path,
        deck_words=_wordcount(deck_path) if deck_path.exists() else 0,
        framing_words=_wordcount(framing_path) if framing_path.exists() else 0,
        validation_findings=last_findings,
        stdout=last_stdout,
        stderr=last_stderr,
        attempts=attempts,
    )


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

    spine_path = _resolve_spine_path(book_dir, slug, chap_num)
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
        f'(e.g., "pure narrative," "editorial side-matter," "manuscript history"),\n'
        f"  (b) which [VISUAL CANDIDATE] tags from the discussion-spine were considered "
        f"(list them with their beat numbers),\n"
        f"  (c) why none of those candidates warranted a slide (specific source structure "
        f'that\'s absent — NOT generic phrases like "no visual content" or "doesn\'t fit").\n\n'
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
        f'- Do NOT use generic phrases ("purely narrative," "no visual content," '
        f'"doesn\'t fit") without naming specific absent structure.\n\n'
        f"Exit when `{skip_path}` exists and is non-empty."
    )

    rc, stdout, stderr = _run_claude_p(
        prompt,
        timeout=SLIDE_DECK_TIMEOUT,
        book_dir=book_dir,
        phase="11b-slide-authoring",
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
    "author_book_deck_pair",
    "compute_density",
    "should_skip_with_justification",
    "author_justified_skip",
]
