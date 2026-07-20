"""Prompt builders for the book re-voice and fluency passes.

Extracted from ``_book_voice.py`` (DR-005 line-count gate, 2026-07-20) following
the repo's ``_build_*_prompt`` convention — see ``_book_companion_prompts.py``.
Both builders are pure functions of their arguments, so the split is mechanical.

The stance and register clauses FOLLOW the narrative frame: a third-person book
instructed to write "your own intimate first-person register" would fail its own
gate on every chapter. The frame's binding directives come from ``_narrative``,
the same module the gates read, so the instruction and the check cannot drift.
"""

from __future__ import annotations

from _narrative import ARABIC_DIRECTIVE, frame_prompt_directive
from _rules import narrative_person_for


def _voice_prompt(
    title: str,
    base_text: str,
    previous_tail: str = "",
    *,
    frame: str = "",
    narrator: str = "",
) -> str:
    directives = frame_prompt_directive(frame, narrator) + ARABIC_DIRECTIVE if frame else ""
    continuity = (
        "\nCONTINUITY\nThis passage continues a chapter already in progress. The preceding passage ended "
        "with the words below. Carry the same voice straight on from it — do not re-introduce the chapter, "
        "do not summarize what came before, and do not repeat these words:\n"
        f"{previous_tail}\n"
        if previous_tail
        else ""
    )
    # The opening rule governs how a CHAPTER begins, so it is addressed only to the
    # passage that actually opens one. Applying it to a continuation window would
    # revert legitimate mid-chapter prose that happens to say "let me tell you".
    opening = (
        ""
        if previous_tail
        else """
OPENING (a chapter begins as a chapter does)
Do NOT open by announcing that you are about to recount, set down, or tell what happened — that is
narrating the act of narration, not the chapter. Forbidden opening moves: "Let me tell you...",
"Let me set down, as faithfully as I can...", "I want to tell you what happened...", "Before I tell
you anything else...", "I shall now recount...". Begin directly in the chapter's own action, scene,
or teaching instead.
"""
    )
    # The stance and the register clause BOTH follow the frame. A third-person
    # book told to write "your own intimate first-person register" would fail its
    # own gate on every chapter — the prompt and the guard must agree.
    third_person = frame and narrative_person_for(frame) == "third"
    stance = (
        "You are preparing a modern reading edition of this Islamic teaching text."
        if third_person
        else "You are the author of this Islamic teaching text, preparing a modern reading edition of\nyour own work."
    )
    task = (
        "Render the passage below as dignified, readable modern English prose."
        if third_person
        else "Re-voice the passage below into your intimate, direct first-person register."
    )
    register = (
        """Contemporary literary English, plain and dignified. Restrained, not ornamented: the
translator is invisible. No archaic diction, no conversational address, no podcast language, no
meta-commentary, no headings. Render each technical term the SAME way on every occurrence — do not
vary a term for freshness. Write the chapter, not about it."""
        if third_person
        else """Contemporary literary English, first person, addressed warmly to the reader. No archaic diction, no
podcast language, no meta-commentary, no headings. Render each technical term the SAME way on every
occurrence — do not vary a term for freshness. Write the chapter, not about it."""
    )
    return f"""{stance}
{task}
{directives}{continuity}

ABSOLUTE FAITHFULNESS
Preserve every teaching, argument, example, named person, citation, Quran verse, hadith, quote, and
Arabic script exactly as given. Keep every Arabic-script quotation verbatim (do not romanize it away,
do not drop it). You may smooth connective prose and English word order inherited from the Arabic;
you may NOT add, remove, summarize, or alter any teaching. Output must be about the same length as
the input — never shorter.

REGISTER
{register}
{opening}
OUTPUT
Return ONLY the rendered prose. No title line, no preamble, no code fences.

CHAPTER "{title}"
{base_text}"""


def _fluency_prompt(
    title: str,
    base_text: str,
    previous_tail: str = "",
    *,
    frame: str = "",
    narrator: str = "",
) -> str:
    directives = frame_prompt_directive(frame, narrator) + ARABIC_DIRECTIVE if frame else ""
    # The register clause follows the frame, exactly as it does in `_voice_prompt`.
    # Hardcoding "third-person" here contradicted the directives block twenty lines
    # above it: a book declaring `first_person_author` was told to narrate in the
    # first person throughout and then, in the same prompt, forbidden from doing
    # it. The frame is a SOURCE property and independent of the route, so any
    # route that hardcodes a person will eventually meet a book that disagrees.
    third_person = not frame or narrative_person_for(frame) == "third"
    register_clause = "the SAME third-person scholarly register" if third_person else "the SAME first-person register"
    person_clause = (
        "Do not switch to first person"
        if third_person
        else "Do not switch out of first person into third-person report"
    )
    continuity = (
        "\nCONTINUITY\nThis passage continues a chapter already in progress. The preceding passage "
        "ended with the words below. Carry straight on from it — do not re-introduce the chapter, do "
        "not summarize what came before, and do not repeat these words:\n"
        f"{previous_tail}\n"
        if previous_tail
        else ""
    )
    return f"""You are polishing one chapter of a faithful Islamic reading edition into fluent,
idiomatic modern English. This is a de-calque pass: fix stiff, word-for-word-from-Arabic
phrasing so it reads like a book, NOT like a literal gloss.
{directives}{continuity}

ABSOLUTE FAITHFULNESS (a de-calque is not a rewrite)
Keep the SAME meaning, {register_clause}, and every teaching, argument,
named person, citation, Quran verse, hadith, quote, and Arabic script exactly as given. Keep every
Arabic-script quotation verbatim. You may only smooth connective prose and Arabic word-order that
reads awkwardly in English. {person_clause}, do not add, remove, summarize, or
reinterpret anything. Output must be about the same length — never shorter.

OUTPUT
Return ONLY the polished chapter prose. No title line, no preamble, no code fences.

CHAPTER "{title}"
{base_text}"""
