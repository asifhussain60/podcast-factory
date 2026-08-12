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

from _book_compose import _arabic_run_count
from _narrative import ARABIC_DIRECTIVE, frame_prompt_directive
from _rules import narrative_person_for

# A long chapter is split into windows and the outputs are joined. A window that
# narrates one beat past its own last sentence produces the defect neither
# fidelity gate can see: the next window renders that beat properly, and the book
# prints the whole scene twice, in different words, a few paragraphs apart. Found
# in `the-master-and-the-disciple` ch7 on 2026-07-20 — a farewell, a journey, and
# a counsel, all told twice. The gates cannot catch it because each window passes
# on its own; only the join is wrong. So the instruction has to prevent it.
SCOPE_RULE = """Render the passage you were given and NOTHING beyond it. It may end mid-scene, mid-argument, or
mid-conversation — that is expected, and another passage continues from there. Do not narrate what
comes next, do not round the passage off with an ending it does not have, and do not add a
transitional sentence pointing forward. Your last sentence corresponds to the passage's last
sentence."""


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

SCOPE (stop where the passage stops)
{SCOPE_RULE}

REGISTER
{register}
{opening}
OUTPUT
Return ONLY the rendered prose. No title line, no preamble, no code fences.

CHAPTER "{title}"
{base_text}"""


# The REGISTER clause of the Book Articulation Standard, in ONE place because two
# prompts now depend on it. The chapters are articulated with it, and since
# 2026-08-03 so is the edition's introduction — Asif's rule: the introduction
# "should follow the same articulation style ... and not stand out as a different
# prose". An introduction written to its own register is exactly the seam a reader
# notices on page one, and two copies of a register clause is how that seam gets
# reintroduced six months from now.
#
# Everything AROUND it differs and should: the chapter prompt adds the fidelity
# rules (REQ-BA-030..060), which an introduction has no source to be faithful to.
ARTICULATION_REGISTER = """Dignified and bookish, but plain: prefer the simple word when it carries the meaning.
No contractions, no marketing tone. Render each technical term the SAME way on every
occurrence, matching the spelling this book already uses — never introduce a variant
spelling. Do not add parenthetical transliterations. Keep honorifics in the compact
form the surrounding text uses. If the passage already capitalizes pronouns referring
to God ("He", "His", "Him"), keep doing so consistently; if it uses lowercase, keep
that instead — never introduce a new convention mid-passage. American spelling."""


# The trailing block a pass may emit instead of writing a note into the prose
# itself (REQ-BA-160). `_book_voice._extract_articulation_notes` strips it before
# anything reaches book.md; a copy that survives extraction is a defect, not a
# feature, and reverts the window via `revoice_gates`.
_NOTES_BLOCK_INSTRUCTION = """
NOTES (REQ-BA-160 — report, never inline)
If something is genuinely ambiguous, if a modern reader may stumble on a passage
without help this pass is not authorized to add, or if a term deserves standardizing
book-wide, do NOT write a bracketed note, a parenthetical aside, or explanatory
context into the chapter. Instead append ONE block AFTER the chapter prose, in
exactly this form, and nothing else:

===ARTICULATION-NOTES===
AMBIGUITY: <what is unclear, in one sentence>
COMPREHENSION: <what a modern reader may stumble on, in one sentence>
TERMINOLOGY: <term> — <what rendering should be standardized>
===END-NOTES===

Omit the block entirely when there is nothing to report. Never put any of this
inside the chapter prose itself."""


# What the pass is actually fixing, which is not the same defect in every book.
#
# A translated book arrives calqued: word-for-word Arabic grammar wearing English
# words. A book WRITTEN in English does not have that defect and telling the model
# it does aims the pass at nothing — the prose is already idiomatic, and what makes
# it hard is that its sentences run long and periodic, its argument is carried in
# abstractions, and its vocabulary is a specialist's. REQ-BA-010 and -020 are the
# same contract either way; only the diagnosis differs.
_CALQUED_SOURCE = "The source below is a stiff, literal, Arabic-calqued draft.\nFix that completely."
_DIFFICULT_ENGLISH_SOURCE = (
    "The source below is already fluent English — it is not a translation, and it is "
    "not\nclumsy. What makes it hard is different: sentences that run long and hold "
    "several\nsubordinate clauses before they land, an argument carried in abstract "
    "nouns rather\nthan in things a reader can picture, and a specialist's vocabulary "
    "used without\nexplanation. Fix THAT. Do not hunt for calques; there are none."
)


def _source_defect(source_language: str) -> str:
    lang = (source_language or "").strip().lower()
    return _DIFFICULT_ENGLISH_SOURCE if lang in ("en", "english") else _CALQUED_SOURCE


def _arabic_tally(base_text: str) -> str:
    """State the NUMBER of Arabic runs the gate will count, to the model.

    The prompt already forbade dropping Arabic, in prose, and that was enough for
    a book with a few dozen runs. It was not enough for `surah-al-fateha`, a
    linguistic commentary where the Arabic IS the subject: the first six chapters
    all reverted on this gate, one window losing 27 runs of 132. Under heavy
    rewriting a parenthetical script is the easiest thing in a sentence to let go
    of, and "never drop Arabic" gives a model nothing to check itself against.

    A count does. It is the SAME count `revoice_gates` applies (`_arabic_run_count`,
    imported rather than re-derived), so the number the model is asked to hit and
    the number that decides whether its work survives cannot differ — this module's
    standing contract that a gate and its prompt are worded once, together.

    Silent when the passage has no Arabic, so nothing is said to books this does
    not concern.
    """
    count = _arabic_run_count(base_text)
    if not count:
        return ""
    return f"""
ARABIC RUN COUNT (mechanical — this exact number is checked)
This passage contains {count} Arabic-script runs. Your output must contain all {count},
each character-for-character identical to the one it replaces: same letters, same vowel
marks, nothing romanized in its place. Count them in your output before you answer.
A run you cannot fit into a rewritten sentence is a run you leave exactly where it
stands and build the sentence around. If the count comes back lower, the whole passage
is discarded and the original kept — so one dropped run costs every improvement in it.
"""


def _articulation_prompt(
    title: str,
    base_text: str,
    previous_tail: str = "",
    *,
    frame: str = "",
    narrator: str = "",
    source_language: str = "",
) -> str:
    """The REQ-BA prompt (docs/standards/book-articulation.md) — the single
    builder shared by the automatic 0book-fluency pass and the on-demand
    Rearticulate action, so the two routes cannot silently drift apart."""
    directives = frame_prompt_directive(frame, narrator) + ARABIC_DIRECTIVE if frame else ""
    arabic_tally = _arabic_tally(base_text)
    continuity = (
        "\nCONTINUITY\nThis passage continues a chapter already in progress. The preceding "
        "passage ended with the words below. Carry straight on — do not re-introduce the "
        "chapter, do not summarize what came before, and do not repeat these words:\n"
        f"{previous_tail}\n"
        if previous_tail
        else ""
    )
    return f"""You are articulating one chapter of a scholarly Islamic book so it reads like a
professionally published edition: modern, lucid, simple English that a general reader
understands on first read. {_source_defect(source_language)}
(Contract: the Book Articulation Standard, REQ-BA-010..160.)
{directives}{continuity}

YOU MAY (REQ-BA-020, -130)
Rebuild sentence and paragraph grammar freely: split long sentences, merge fragments,
reorder clauses, replace calqued constructions ("the most X of them in Y and the most
Z of them in W") with natural English. Re-draw paragraph breaks to serve the reading,
keeping one paragraph per speech turn in dialogue. Distinguish meaningful repetition
(rhythm, emphasis, deliberate parallelism) from mechanical repetition carried over
literally: preserve the former in refined form, and only condense the latter where
doing so drops no idea and weakens no emphasis the source intends. A repetitive
dialogue tag's WORDING may vary ("he replied", "he asked" for "the boy said") as long
as the speaker stays unambiguous — this does not permit adding, removing, or
re-pointing a tag.

YOU MAY NOT (REQ-BA-030..060)
- Change meaning. Every teaching, argument, example, named person, citation, and
  enumerated list survives with its content intact. Add nothing: no outside facts, no
  analogies, no explanations not in the source. Drop nothing, summarize nothing.
- Touch the artifacts. Direct speech, Quran verses, hadith, poetry, prayers, and quoted
  sayings keep their boundaries, their speakers, and their content. Never add, remove,
  or re-point a speech tag. Inside a quote, de-calque the wording only — never
  paraphrase away a point, an image, or a claim.
- Flatten imagery. Metaphors, similes, and parables keep their concrete images: a
  wellspring stays a wellspring, "struck the mark" stays an image of striking, branches
  bearing fruit stay branches. Recast grammar AROUND an image, never replace the image
  with an abstraction ("preached effectively" for "struck the mark" is the canonical
  violation).
- Alter Arabic. Arabic-script runs are copied verbatim — never romanized away, never
  re-vowelled, never dropped. Transliteration stays beside script, never replaces it.

REGISTER (REQ-BA-010, -070..110, -140)
{ARTICULATION_REGISTER} The
output must be about the same length as the source — this is a rewording, never an
abridgement.

SCOPE (stop where the passage stops)
{SCOPE_RULE}
{arabic_tally}{_NOTES_BLOCK_INSTRUCTION}

OUTPUT
Return ONLY the articulated chapter prose, optionally followed by one
===ARTICULATION-NOTES=== block as described above. No title line, no preamble, no
code fences.

CHAPTER "{title}"
{base_text}"""
