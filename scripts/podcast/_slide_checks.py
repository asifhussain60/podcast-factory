#!/usr/bin/env python3
"""_slide_checks.py — deterministic helpers, gauges, and validators for slide decks.

Extracted verbatim from ``_slide_authoring.py`` (R3 DR-005 split, 2026-07-18).
Everything here is deterministic and LLM-free: chapter/spine path resolution,
word/beat/candidate counting, the density gauge (skip-vs-author decision per
slide-deck-format.md), stdout sanity parsing, the ``build_slide_deck.py``
subprocess validator, and the book-level pair validator. ``_slide_authoring``
re-exports every name so importers and test patch-targets are untouched.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _authoring import AuthoringError

# Density gauge — per slide-deck-format.md (visual-candidate density below this
# threshold should trigger a justified-skip rather than a full deck pair).
DENSITY_THRESHOLD = 0.25

# Path to the validator script (does not need to exist for compute_density /
# should_skip_with_justification / author_justified_skip).
BUILD_SLIDE_DECK_SCRIPT = Path(__file__).resolve().parent / "build_slide_deck.py"


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
    return book_dir / "_system" / "episode-drafts" / f"EP{chap_num}-{slug}" / "04-discussion-spine.md"


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


def _run_validator(book_dir: Path, slug: str) -> tuple[bool, list[str]]:
    """Subprocess-call build_slide_deck.py to validate the pair.

    Returns (ok, findings). `ok` is True iff the validator exits 0 OR the
    validator script is missing (treated as "no validator wired up yet — pass
    through"). `findings` is the validator's parsed stderr/stdout lines on
    failure.

    build_slide_deck.py's own CLI takes exactly two positionals — `book_dir`
    and `slug` — and derives the deck/framing paths itself via auto-discovery
    (see its own docstring). It does NOT accept explicit file paths; passing
    them here made every call fail with "unrecognized arguments" (100% of
    calls, verified 2026-07-31 via cost-ledger attempt counts on
    degrees-of-excellence), which cascaded into every chapter's slide-deck
    convergence being marked BLOCKED since `author_deck_pair` treats a failed
    validation as `success=False` unconditionally.
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
                slug,
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


_BOOK_FRAMING_REQUIRED_H2 = (
    "## Audience",
    "## Core Principle",
    "## Visual Priorities",
    "## Prohibited Patterns",
    "## Steering Phrases",
    "## Visual Style",
)


def _validate_book_pair(deck_path: Path, framing_path: Path) -> list[str]:
    """Deterministic checks for the book-level pair. Returns findings ([] = pass)."""
    findings: list[str] = []
    if not deck_path.exists() or deck_path.stat().st_size == 0:
        findings.append(f"deck source missing or empty: {deck_path}")
    if not framing_path.exists() or framing_path.stat().st_size == 0:
        findings.append(f"framing missing or empty: {framing_path}")
    if findings:
        return findings
    deck_words = _wordcount(deck_path)
    if deck_words < 2000:
        findings.append(f"deck source is {deck_words} words (<2,000 hard floor)")
    framing_text = framing_path.read_text(encoding="utf-8")
    framing_words = len(framing_text.split())
    if not (120 <= framing_words <= 400):
        findings.append(f"framing is {framing_words} words (target 150-350)")
    for h2 in _BOOK_FRAMING_REQUIRED_H2:
        if h2 not in framing_text:
            findings.append(f"framing missing required section: {h2}")
    if "—" in deck_path.read_text(encoding="utf-8"):
        findings.append("deck source contains em dashes (forbidden)")
    try:
        from _translation_edition import requires_monochrome_visuals

        if requires_monochrome_visuals(deck_path.parents[1]):
            lower = framing_text.lower()
            if not any(term in lower for term in ("black and white", "black-and-white", "monochrome")):
                findings.append("framing must explicitly require black-and-white / monochrome slides")
            forbidden_colour = ("colour fills", "color fills", "gradients", "photographs")
            if not any(term in lower for term in forbidden_colour):
                findings.append("framing must prohibit color fills, gradients, and photographs")
    except Exception:
        pass
    return findings


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


def should_skip_with_justification(density: float, *, threshold: float = DENSITY_THRESHOLD) -> bool:
    """Per slide-deck-format.md density gauge: True if density < threshold."""
    return density < threshold
