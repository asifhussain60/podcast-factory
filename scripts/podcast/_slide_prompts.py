#!/usr/bin/env python3
"""_slide_prompts.py — prompt builders for slide-deck pair authoring.

Extracted verbatim from ``_slide_authoring.py`` (R3 DR-005 split, 2026-07-18).
Pure functions of their keyword arguments plus the REFERENCE_* path constants —
no LLM shellouts, no filesystem writes. The prompt WORDING is maintained here,
apart from the retry/validation orchestration in ``_slide_authoring`` (the same
prompt-apart-from-orchestration outcome Spec-2 reached for Phase 0d's TOC
prompt). ``_slide_authoring`` re-exports every name so patch targets hold.
"""

from __future__ import annotations

from pathlib import Path

# Reference paths, relative to the repo root (auto-discovered relative to this
# script: scripts/podcast/_slide_prompts.py → repo root is 2 up).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REFERENCE_FORMAT = _REPO_ROOT / "skills-staging" / "podcast" / "references" / "slide-deck-format.md"
REFERENCE_PATTERNS = _REPO_ROOT / "skills-staging" / "podcast" / "references" / "slide-deck-patterns.md"
REFERENCE_STEERING = _REPO_ROOT / "skills-staging" / "podcast" / "references" / "slide-deck-steering.md"


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
    visual_constraints: str = "",
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
            f"\n\nADDITIONAL CONSTRAINTS (from prior validation failure — fix these):\n{extra_constraints.strip()}\n"
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
        f"{visual_constraints}"
        f"FRAMING rules (`{framing_path.name}`):\n"
        f"- 150-250 words total.\n"
        f"- H1 (one line; file-label — NotebookLM users skip this line when pasting).\n"
        f"- Required H2 sections, in this order:\n"
        f'  1. `## Audience` — named concretely (no "general audience").\n'
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


def _build_pair_prompt_technical(
    *,
    book_slug: str,
    slug: str,
    chap_num: str,
    chapter_file: Path,
    spine_path: Path | None,
    deck_path: Path,
    framing_path: Path,
    audio_words: int,
    visual_constraints: str = "",
    extra_constraints: str = "",
) -> str:
    """Build the heredoc prompt for technical/developer content (explainers category).

    Replaces the Islamic scholarly version with developer-audience visual design:
    CLI workflow diagrams, comparison tables, architecture flows, code-first structures.
    No Arabic calligraphy directives, no spiritual imagery, no doctrinal constraints.
    """
    spine_clause = (
        f"  - `{spine_path}` (the discussion-spine — every [VISUAL CANDIDATE] beat should map "
        f"to a structure in the deck source)\n"
        if spine_path is not None and spine_path.exists()
        else "  - (no discussion-spine present for this episode — derive visual moments from the audio chapter alone)\n"
    )

    constraints_block = ""
    if extra_constraints.strip():
        constraints_block = (
            f"\n\nADDITIONAL CONSTRAINTS (from prior validation failure — fix these):\n{extra_constraints.strip()}\n"
        )

    deck_lo = max(2000, int(audio_words * 0.5))
    deck_hi = max(deck_lo + 500, audio_words)

    return (
        f"You are authoring the slide-deck PAIR for episode `EP{chap_num}-{slug}` "
        f"of technical series `{book_slug}`. The audience is professional software developers. "
        f"The pair is one SOURCE file + one CUSTOMIZE PROMPT file, "
        f"both landing in `{deck_path.parent}/`.\n\n"
        f"AUTHORITIES (read these first — they govern shape and rules):\n"
        f"  - `{REFERENCE_FORMAT}` (deliverable shape — what each file contains)\n"
        f"  - `{REFERENCE_PATTERNS}` (diagram taxonomy — comparison matrix, contrast pair, "
        f"process flow, feature table, decision tree, architecture flow)\n"
        f"  - `{REFERENCE_STEERING}` (steering phrases — pick 3-5 for the framing's "
        f"`## Steering Phrases`)\n\n"
        f"INPUT:\n"
        f"  - `{chapter_file}` (the audio chapter — {audio_words} words; this is the "
        f"SOURCE content to re-render structurally)\n"
        f"{spine_clause}"
        f"\nOUTPUTS (write EXACTLY these two files — no others):\n"
        f"  - `{deck_path}` (the SLIDE-DECK SOURCE — `.txt`, NotebookLM-uploadable)\n"
        f"  - `{framing_path}` (the SLIDE CUSTOMIZE PROMPT — `.md`, NotebookLM-pasteable)\n\n"
        f"DECK SOURCE rules (`{deck_path.name}`):\n"
        f"- H1: the episode title (same as the audio chapter's H1).\n"
        f"- H2: the audio chapter's major sections (preserved verbatim).\n"
        f"- Within each H2, body is STRUCTURES: comparison tables, CLI workflow steps, "
        f"feature matrices, architecture flows, before/after contrast columns. "
        f"NO prose paragraphs longer than 100 words.\n"
        f"- Every structural moment matches a named diagram type from the patterns taxonomy.\n"
        f"- Word count target: {deck_lo}-{deck_hi} (50-100% of audio chapter's {audio_words}; "
        f"hard floor 2,000). If you cannot reach 2,000 words structurally, STOP and emit a "
        f"justified-skip explanation — do not write a thin deck source.\n"
        f"- Contrast columns use `Column A:` / `Column B:` PREFIX LINES (not side-by-side "
        f"markdown columns — NotebookLM parses sequential text better).\n"
        f"- CLI commands and code blocks must be verbatim from the source — no paraphrasing.\n"
        f"- Version numbers and product names must be exact (no 'the latest version').\n"
        f"- Acronyms used in structures must be expanded on first use in the deck source.\n"
        f"- No em dashes (use commas or restructure). No emojis.\n"
        f"- Every concept present in the audio chapter must appear (restructured) in the deck; "
        f"the deck is a RE-PRESENTATION, not a SUMMARY.\n\n"
        f"{visual_constraints}"
        f"FRAMING rules (`{framing_path.name}`):\n"
        f"- 150-250 words total.\n"
        f"- H1 (one line; file-label — NotebookLM users skip this line when pasting).\n"
        f"- Required H2 sections, in this order:\n"
        f"  1. `## Audience` — professional software developers (be specific about their level).\n"
        f"  2. `## Core Principle` — restate the audio-vs-slide division of labor in 1-2 sentences.\n"
        f"  3. `## Visual Priorities` — 2-4 specific technical visual moments (CLI workflows, "
        f"comparison tables, architecture diagrams) matching structures in the deck source.\n"
        f"  4. `## Prohibited Patterns` — explicit list: no literal-text slides, no audio-restatement, "
        f"no spiritual or doctrinal imagery, no bullet-list-as-diagram, no vague 'modern' metaphors.\n"
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


def _build_book_pair_prompt(
    *,
    book_slug: str,
    chapter_files: list[Path],
    deck_path: Path,
    framing_path: Path,
    extra_constraints: str = "",
) -> str:
    """Book-level variant of _build_pair_prompt: ONE deck pair for the whole book.

    The book deck is a SELECTION (the book's most diagram-worthy structures,
    2-4 per chapter), not a full re-presentation — a whole book's audio word
    count cannot map 50-100% into a single NotebookLM deck.
    """
    chapter_list = "\n".join(f"  - `{p}`" for p in chapter_files)
    constraints_block = ""
    if extra_constraints.strip():
        constraints_block = (
            f"\n\nADDITIONAL CONSTRAINTS (from prior validation failure — fix these):\n{extra_constraints.strip()}\n"
        )
    try:
        from _translation_edition import requires_monochrome_visuals

        monochrome = requires_monochrome_visuals(deck_path.parents[1])
    except Exception:
        monochrome = False
    style_clause = (
        "black-and-white line-art illustration style: conceptual diagrams in the manner "
        "of pen-and-ink scholarly illustrations (hierarchies as tree diagrams, contrast "
        "pairs as two-panel layouts, genealogy chains as flowing arrow diagrams, process "
        "flows as numbered-step illustrations). No colour fills, no photographs, no "
        "gradients. Clean geometric shapes and lines only."
        if monochrome
        else "clear scholarly visual style: conceptual diagrams over decorative slides."
    )
    return (
        f"You are authoring the BOOK-LEVEL slide-deck PAIR for book `{book_slug}` — "
        f"ONE deck covering the whole book (slide_deck_mode: book). The pair is one "
        f"SOURCE file + one CUSTOMIZE PROMPT file, both landing in `{deck_path.parent}/`.\n\n"
        f"AUTHORITIES (read these first — they govern shape and rules):\n"
        f"  - `{REFERENCE_FORMAT}` (deliverable shape)\n"
        f"  - `{REFERENCE_PATTERNS}` (diagram taxonomy)\n"
        f"  - `{REFERENCE_STEERING}` (steering phrases — pick 3-5 for the framing)\n\n"
        f"INPUT (every audio chapter of the book, in order):\n{chapter_list}\n\n"
        f"OUTPUTS (write EXACTLY these two files — no others):\n"
        f"  - `{deck_path}` (the BOOK SLIDE-DECK SOURCE — `.txt`, NotebookLM-uploadable)\n"
        f"  - `{framing_path}` (the SLIDE CUSTOMIZE PROMPT — `.md`, NotebookLM-pasteable)\n\n"
        f"DECK SOURCE rules (`{deck_path.name}`):\n"
        f"- H1: the book title.\n"
        f"- H2: one per chapter, in book order, using the chapter's own title.\n"
        f"- Within each H2: the chapter's 2-4 MOST diagram-worthy structures (tables, "
        f"contrast columns, hierarchies, genealogy chains, process flows) — a SELECTION "
        f"of the book's strongest visual moments, NOT a full re-presentation. NO prose "
        f"paragraphs longer than 100 words.\n"
        f"- Every structural moment matches a named diagram type from the patterns taxonomy.\n"
        f"- Word count target: 3,000-6,000 (hard floor 2,000).\n"
        f"- Contrast columns use `Column A:` / `Column B:` PREFIX LINES. Genealogies use "
        f"explicit `→` arrows, one chain per line. Citations / verbatim quotes preserved "
        f"in blockquotes with attribution.\n"
        f"- No em dashes. No emojis. No inline phonetic parens on Arabic terms "
        f"(R-PHONETICS-OUT).\n\n"
        f"FRAMING rules (`{framing_path.name}`):\n"
        f"- 150-350 words total.\n"
        f"- H1 (one line; file-label).\n"
        f"- Required H2 sections, in this order:\n"
        f"  1. `## Audience` — named concretely.\n"
        f"  2. `## Core Principle` — the deck visualizes the book's STRUCTURES; the audio "
        f"episodes carry the argument. 1-2 sentences.\n"
        f"  3. `## Visual Priorities` — 3-5 specific visual moments matching structures in "
        f"the deck source, spanning the whole book's arc.\n"
        f"  4. `## Prohibited Patterns` — explicit list (no literal-text slides, no "
        f"audio-restatement, no stock-photo descriptions, no bullet-list-as-diagram).\n"
        f"  5. `## Steering Phrases` — 3-5 phrases drawn from `{REFERENCE_STEERING.name}`.\n"
        f"  6. `## Visual Style` — instruct the generator to use {style_clause} "
        f"Each slide must be a drawn diagram rather than a "
        f"text-heavy bullet list.\n\n"
        f"AFTER WRITING both files, print on stdout (one per line):\n"
        f"  DECK: {deck_path}\n"
        f"  FRAMING: {framing_path}\n"
        f"  DECK_WORDS: <integer>\n"
        f"  FRAMING_WORDS: <integer>\n\n"
        f"Constraints (hard):\n"
        f"- Do NOT modify any file other than `{deck_path}` and `{framing_path}`.\n"
        f"- All chapter files and everything under `chapters/`, `chapter-contracts/`, "
        f"`_system/` are READ-ONLY for this task.\n"
        f"- Do NOT wrap outputs in code fences or add preamble.\n"
        f"{constraints_block}"
        f"\nExit when both files exist and are non-empty."
    )
