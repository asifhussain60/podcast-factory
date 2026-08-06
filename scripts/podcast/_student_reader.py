"""_student_reader.py — read a chapter as a STUDENT, and mark what stops them.

The Companion's other lanes read as a teacher: they make a passage click. This one
reads as someone meeting the text cold and marks the two places a student gets
stuck — where they cannot tell what is meant, and where the book asserts
something and offers nothing behind it (Asif, 2026-08-06).

DETERMINISM — what it means here, and where it lives
----------------------------------------------------
"Deterministic, not random" is Asif's requirement and it is a requirement about
SELECTION, not about prose: a model may notice things, and nothing a model says
decides what survives. Every decision below is pure Python driven by a stated
rule, so the same chapter yields the same notes, in the same order, with the same
identities, on every run:

  * The model may only classify into `DEFECT_KINDS`, a CLOSED vocabulary. A
    candidate carrying anything else is dropped rather than coerced — an open
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

WHAT A NOTE MAY SAY ABOUT EVIDENCE
----------------------------------
`unsupported-claim` is the one kind that could become a model's opinion of a
religious tradition, so it is fenced: a note may state what the book asserts and
where it stops, and may cite corroboration it actually LOCATED in this repo's
corpora. Where it locates nothing it asks the student's question instead of
returning a verdict. `gate_note` enforces the fence — a note claiming support
must carry a citation, and a citation must name a real corpus.

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

#: Corpora a citation may name. A citation naming anything else is a model
#: inventing a source, and the note is dropped rather than trimmed.
CITABLE_CORPORA: frozenset[str] = frozenset({"ksessions", "doctrine", "quran", "hadith"})

WORDS_PER_NOTE = 1200
MIN_NOTES = 2
MAX_NOTES = 8

_MIN_BODY_WORDS = 25
_MAX_BODY_WORDS = 220
#: A quote must be long enough to locate a sentence. Anything shorter matches in
#: several places and the reader is shown a highlight that is not the passage.
_MIN_QUOTE_WORDS = 4

#: Model process-chatter that must never reach a card.
_META_RE = re.compile(
    r"\b(as an AI|I cannot|I'm unable|the passage above|in this task|as requested|here (?:is|are) the)\b",
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

    Deliberately NOT derived from the note's body. The body is model prose and
    will differ slightly between runs; the passage it explains will not. Keying
    on the body would file a new note every run and leave the old one behind —
    the duplicate-forever failure this exists to prevent.
    """
    digest = hashlib.sha256(f"{normalize(chapter_key)}\x00{normalize(quote)}".encode()).hexdigest()
    return f"student:{digest[:16]}"


def _citation_ok(cite: Any) -> bool:
    """A citation names a real corpus and says where inside it."""
    if not isinstance(cite, dict):
        return False
    corpus = str(cite.get("corpus") or "").strip().lower()
    ref = str(cite.get("ref") or "").strip()
    return corpus in CITABLE_CORPORA and bool(ref)


def gate_note(note: dict[str, Any], prose: str) -> tuple[bool, list[str]]:
    """Does this candidate prove itself? Returns (ok, reasons-it-did-not).

    Every check is a fact about the candidate and the chapter — none is a
    judgement of how good the note is. A candidate that cannot prove itself is
    DROPPED, never softened and never repaired: repairing it would mean deciding
    what it meant to say.
    """
    reasons: list[str] = []

    kind = str(note.get("defect") or "").strip().lower()
    if kind not in DEFECT_KINDS:
        reasons.append(f"defect {kind!r} is not one of the {len(DEFECT_KINDS)} this lane reports")

    body = str(note.get("body") or "").strip()
    words = body.split()
    if len(words) < _MIN_BODY_WORDS:
        reasons.append(f"body is {len(words)} words, under the {_MIN_BODY_WORDS} minimum")
    elif len(words) > _MAX_BODY_WORDS:
        reasons.append(f"body is {len(words)} words, over the {_MAX_BODY_WORDS} maximum")
    if _META_RE.search(body):
        reasons.append("body carries model process-chatter")

    quote = str(note.get("quote") or "").strip()
    if len(quote.split()) < _MIN_QUOTE_WORDS:
        reasons.append(f"quote is under {_MIN_QUOTE_WORDS} words — too short to locate a sentence")
    elif normalize(quote) not in normalize(prose):
        reasons.append("quote is not a verbatim passage of this chapter")

    # The evidence fence. A note may only claim support it actually located.
    cites = note.get("citations") or []
    if not isinstance(cites, list):
        reasons.append("citations must be a list")
        cites = []
    bad = [c for c in cites if not _citation_ok(c)]
    if bad:
        reasons.append(f"{len(bad)} citation(s) name no real corpus or no reference within it")
    if note.get("claims_support") and not cites:
        reasons.append("claims the tradition supports this but cites nothing — a verdict, not a finding")

    return (not reasons), reasons


def dedupe(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One note per passage. First occurrence wins; input order decides."""
    seen: set[str] = set()
    kept: list[dict[str, Any]] = []
    for n in notes:
        key = normalize(str(n.get("quote") or ""))
        if key in seen:
            continue
        seen.add(key)
        kept.append(n)
    return kept


def select(notes: list[dict[str, Any]], prose: str, budget: int) -> list[dict[str, Any]]:
    """The chapter's notes, chosen and ordered by rule alone.

    Ranked by defect priority, ties broken by position in the chapter, cut to the
    budget — and then RESTORED to reading order, because the reader meets them
    while reading, not in order of severity. Both orders are total, so the result
    is identical on every run over the same input.
    """
    haystack = normalize(prose)
    ranked = sorted(
        notes,
        key=lambda n: (
            PRIORITY.get(str(n.get("defect") or "").strip().lower(), len(DEFECT_KINDS)),
            haystack.find(normalize(str(n.get("quote") or ""))),
        ),
    )
    chosen = ranked[:budget]
    return sorted(chosen, key=lambda n: haystack.find(normalize(str(n.get("quote") or ""))))


def to_companion_note(note: dict[str, Any], chapter_key: str) -> dict[str, Any]:
    """The on-disk Companion shape, mirroring companion/types.ts CompanionNote.

    Filed as `review: "proposed"` under the `student` provider: Asif asked for
    notes filed directly rather than queued, which only works if a filed note can
    say nobody has looked at it yet. Its predecessor stamped machine cards
    `manual` — rendered on the site as "You" — and a hundred explanations under
    his own byline is why automatic authoring was withdrawn on 2026-08-02.
    """
    quote = str(note.get("quote") or "").strip()
    cites = [c for c in (note.get("citations") or []) if _citation_ok(c)]
    return {
        "id": note_id(chapter_key, quote),
        "kind": "question" if str(note.get("defect")) != "unsupported-claim" else "note",
        "body": str(note.get("body") or "").strip(),
        "anchor": str(note.get("anchor") or "").strip() or None,
        "quote": quote,
        "review": "proposed",
        "source": {
            "provider": "student",
            "label": "Student reader",
            "ref": str(note.get("defect") or ""),
        },
        "citations": cites,
    }
