"""_student_reader.py — read a chapter as a STUDENT, and ask what stops them.

The Companion's other lanes read as a teacher: they make a passage click. This one
reads as someone meeting the text cold and finds the two places a student gets
stuck — where they cannot tell what is meant, and where the book asserts something
and offers nothing behind it (Asif, 2026-08-06).

IT DOES NOT ANSWER, AND THAT IS THE POINT (Asif, 2026-08-06, second pass)
------------------------------------------------------------------------
Its first version wrote the card itself, and every card came out as a complaint
about the book: "these two numbers simply arrive… a first-time reader is left
holding two figures with nothing behind them." True, and useless — the reader
already knew they were stuck, which is why the passage was flagged. Worse, on a
religious text it reads as a review of the book rather than help with it.

So the lane now produces a QUESTION and hands it to the Ismaili Scholar — the same
persona, the same grounding and the same word cap as the Explain button on the
Book Composer, reached through `plan-dashboard/scripts/gem-card.mjs`. What this
module decides is WHICH passage and WHAT TO ASK. What the card then says is the
Scholar's, and this module never sees it before it is filed.

DETERMINISM — what it means here, and where it lives
----------------------------------------------------
"Deterministic, not random" is Asif's requirement and it is a requirement about
SELECTION, not about prose: a model may notice things, and nothing a model says
decides what survives. Every decision below is pure Python driven by a stated
rule, so the same chapter yields the same findings, in the same order, with the
same identities, on every run:

  * The model may only classify into `DEFECT_KINDS`, a CLOSED vocabulary. A
    finding carrying anything else is dropped rather than coerced — an open
    vocabulary is the model choosing the criteria, which is the thing being
    refused.
  * `PRIORITY` ranks those kinds. It is a stated editorial judgement (a passage a
    reader cannot parse hurts more than one they merely cannot corroborate), not
    a model's sense of importance, and it is the same on every run.
  * Ties break on POSITION IN THE CHAPTER — earlier first, since a confusion the
    reader hits first is the one that colours the rest. Position is also a total
    order, so no tie survives to be broken arbitrarily.
  * `chapter_budget` scales with length. A flat per-chapter cap either starves
    the long chapters or floods the short ones; this book runs 1,160 words to
    15,167, a thirteenfold spread, which no single number serves.
  * `note_id` is derived from the chapter and the anchored sentence, so a second
    run UPDATES the note it wrote last time instead of filing a duplicate. The
    Studio store honours a supplied id on create for exactly this.

WHERE THE EVIDENCE RULES WENT
-----------------------------
This module used to carry a citation fence — a closed list of citable corpora and
a check that a note claiming support named one. It is gone, and its absence is not
a relaxation. The Scholar grounds itself: `prepareCard` retrieves knowledge-base
atoms and verified morphology roots before the model writes a word, `finishCard`
resolves every Qur'anic citation against the repo's own mushaf and drops any
etymology whose claimed root the corpus contradicts. Keeping a second, weaker
fence here would have been a second answer to where evidence comes from. The
`citations` field those rules produced was written by this lane and read by
nothing — no renderer, no Python consumer — which is how it could be retired
without touching a single reader.

Pure and side-effect-free: nothing here opens a file, runs a model, or writes a
note. The driver (`student_reader_notes.py`) does those, against these rules.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any

#: The ONLY defects this lane reports. Closed on purpose: an open vocabulary
#: would let the model decide what counts as a problem, which is the judgement
#: this design keeps in the rules.
DEFECT_KINDS: tuple[str, ...] = (
    "unresolved-double-reading",  # the sentence admits two readings, chapter resolves neither
    "ambiguous-referent",  # a pronoun or title whose referent is never fixed
    "undefined-term",  # a technical term used as if already known
    "unexplained-leap",  # a conclusion that does not follow from what precedes it
    "unsupported-claim",  # an assertion the chapter offers nothing behind
)

#: Rank order when the budget cannot take everything. A passage the reader cannot
#: PARSE outranks one they merely cannot corroborate: being unable to read a
#: sentence stops them, being unable to source it does not. Stated here so the
#: ranking is auditable and identical across runs.
PRIORITY: dict[str, int] = {kind: i for i, kind in enumerate(DEFECT_KINDS)}

WORDS_PER_NOTE = 1200
MIN_NOTES = 2
MAX_NOTES = 8

#: A question short enough to be a label is not a question; one long enough to be
#: a paragraph is the student explaining instead of asking.
_MIN_QUESTION_WORDS = 6
_MAX_QUESTION_WORDS = 60
#: A quote must be long enough to locate a sentence. Anything shorter matches in
#: several places and the reader is shown a highlight that is not the passage.
_MIN_QUOTE_WORDS = 4

#: Assistant-voice leakage that must never reach the Scholar. Deliberately
#: NARROWER than the equivalent in `_book_companion`: that one also rejects "the
#: passage above" and "here is the", which are fine there and wrong here — this
#: lane's entire job is to talk ABOUT a passage.
#: "I cannot" and "I am unable" are NOT here, and must not be added back. They
#: are this lane's own voice: the prompt asks the reader to mark where "you
#: cannot tell what is meant". Measured on this book 2026-08-06 — every one of
#: the six candidates the gate threw away across eight chapters was rejected for
#: saying exactly that, including both of chapter 1's, which is why that chapter
#: came back with nothing.
_META_RE = re.compile(
    r"\b(as an AI|as a language model|in this task|as requested|I'm unable to (?:help|assist))\b",
    re.I,
)

_WS_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Whitespace-folded, case-folded — the form quotes are compared in."""
    return _WS_RE.sub(" ", (text or "").strip()).casefold()


def chapter_budget(word_count: int) -> int:
    """How many notes one chapter may carry, from its length.

    One per ~1,200 words, floored at 2 and capped at 8. The floor keeps a short
    chapter from being passed over entirely; the cap keeps the longest from
    dominating the book. On this book that is 2 notes for the 1,160-word opener
    and 8 for the 15,167-word finale — about thirty across the eight chapters,
    which is the density Asif asked for over the ~135 the previous automatic
    pass produced.
    """
    if word_count <= 0:
        return MIN_NOTES
    return max(MIN_NOTES, min(MAX_NOTES, math.ceil(word_count / WORDS_PER_NOTE)))


def note_id(chapter_key: str, quote: str) -> str:
    """Stable identity: the chapter plus the sentence the note is anchored to.

    Deliberately NOT derived from the question or the answer. Both are model
    prose and will differ between runs; the passage they are about will not.
    Keying on either would file a new note every run and leave the old one behind
    — the duplicate-forever failure this exists to prevent.

    The `student:` prefix survives the change of byline to "Ismaili Scholar"
    (2026-08-06) and must not be renamed. It is what `_student_reader_store`
    checks to know which notes are this pass's to rewrite; the byline is what the
    reader sees, the prefix is what the writer owns.
    """
    digest = hashlib.sha256(f"{normalize(chapter_key)}\x00{normalize(quote)}".encode()).hexdigest()
    return f"student:{digest[:16]}"


def gate_finding(finding: dict[str, Any], prose: str) -> tuple[bool, list[str]]:
    """Does this finding prove itself? Returns (ok, reasons-it-did-not).

    Every check is a fact about the finding and the chapter — none is a judgement
    of how good it is. A finding that cannot prove itself is DROPPED, never
    softened and never repaired: repairing it would mean deciding what it meant
    to ask.
    """
    reasons: list[str] = []

    kind = str(finding.get("defect") or "").strip().lower()
    if kind not in DEFECT_KINDS:
        reasons.append(f"defect {kind!r} is not one of the {len(DEFECT_KINDS)} this lane reports")

    question = str(finding.get("question") or "").strip()
    words = question.split()
    if len(words) < _MIN_QUESTION_WORDS:
        reasons.append(f"question is {len(words)} words, under the {_MIN_QUESTION_WORDS} minimum")
    elif len(words) > _MAX_QUESTION_WORDS:
        reasons.append(f"question is {len(words)} words, over the {_MAX_QUESTION_WORDS} maximum")
    if question and not question.endswith("?"):
        reasons.append("question does not end in a question mark — it is a statement")
    if _META_RE.search(question):
        reasons.append("question carries model process-chatter")

    quote = str(finding.get("quote") or "").strip()
    if len(quote.split()) < _MIN_QUOTE_WORDS:
        reasons.append(f"quote is under {_MIN_QUOTE_WORDS} words — too short to locate a sentence")
    elif normalize(quote) not in normalize(prose):
        reasons.append("quote is not a verbatim passage of this chapter")

    return (not reasons), reasons


def dedupe(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One finding per passage. First occurrence wins; input order decides."""
    seen: set[str] = set()
    kept: list[dict[str, Any]] = []
    for n in findings:
        key = normalize(str(n.get("quote") or ""))
        if key in seen:
            continue
        seen.add(key)
        kept.append(n)
    return kept


def select(findings: list[dict[str, Any]], prose: str, budget: int) -> list[dict[str, Any]]:
    """The chapter's findings, chosen and ordered by rule alone.

    Ranked by defect priority, ties broken by position in the chapter, cut to the
    budget — and then RESTORED to reading order, because the reader meets them
    while reading, not in order of severity. Both orders are total, so the result
    is identical on every run over the same input.
    """
    haystack = normalize(prose)
    ranked = sorted(
        findings,
        key=lambda n: (
            PRIORITY.get(str(n.get("defect") or "").strip().lower(), len(DEFECT_KINDS)),
            haystack.find(normalize(str(n.get("quote") or ""))),
        ),
    )
    chosen = ranked[:budget]
    return sorted(chosen, key=lambda n: haystack.find(normalize(str(n.get("quote") or ""))))


def to_companion_note(
    finding: dict[str, Any],
    chapter_key: str,
    *,
    anchor: str,
    body: str,
    etymology: list[str] | None = None,
) -> dict[str, Any]:
    """The on-disk Companion shape, mirroring companion/types.ts CompanionNote.

    Everything a reader sees comes from the Scholar: `body`, `etymology` and
    `anchor` are what `gem-card.mjs` returned, unedited. This lane contributes
    the identity and the passage, which is what it decided.

    Filed as `review: "proposed"` — Asif asked for notes filed directly rather
    than queued, which only works if a filed note can say nobody has looked at it
    yet. Its predecessor stamped machine cards `manual` — rendered on the site as
    "You" — and a hundred explanations under his own byline is why automatic
    authoring was withdrawn on 2026-08-02.

    `kind` is "explanation" and the source is the Scholar, which makes a filed
    card indistinguishable from one made by pressing Explain. That is the point:
    the two are made by the same persona through the same code, so they must not
    render as different species.
    """
    quote = str(finding.get("quote") or "").strip()
    note: dict[str, Any] = {
        "id": note_id(chapter_key, quote),
        "kind": "explanation",
        "body": body.strip(),
        "anchor": anchor.strip() or None,
        "quote": quote,
        "review": "proposed",
        "source": {
            "provider": "scholar",
            "label": "Ismaili Scholar",
            "ref": str(finding.get("defect") or ""),
        },
    }
    if etymology:
        note["etymology"] = list(etymology)
    return note
