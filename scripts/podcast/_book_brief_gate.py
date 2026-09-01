"""_book_brief_gate.py — the two deterministic judgements the brief lane makes.

Split out of `_book_brief` at its DR-005 ceiling, on a real seam rather than an
arbitrary cut: everything here is a PURE FUNCTION over text, decides something
without a model and without touching disk, and is what the lane's tests actually
pin. The lane beside it is orchestration — caching, subprocesses, injection — and
mixing the two meant the rules a brief is judged by could only be read by reading
past the plumbing that applies them.

THE GATE INVERTS THIS REPO'S USUAL LENGTH CONTRACT, DELIBERATELY.
`_book_completeness` halts a compose when a chapter came back SHORTER than its
source, because an edition that quietly drops text is the defect the whole pipeline
exists to prevent. A brief drops almost everything by design, so it cannot borrow
that gate and must not be allowed to weaken it — hence a second, opposite one here,
scoped to a single apparatus section.

AND IT REFUSES RATHER THAN TRIMS. A gate that cut the text to the word count would
produce the one failure a reader always notices: a brief that stops mid-sentence.
Refusing hands the problem back to a repair call that can shorten by rewriting.
"""

from __future__ import annotations

import re
from typing import Any

#: Below this fraction of the target, the brief is not a brief. Generous on
#: purpose: a short book with little in it should come in well under its preset
#: rather than be padded to reach one.
MIN_FRACTION = 0.5

#: Each of these is a shape that survives every other check in this repo — a
#: table-of-contents summary is fluent, correctly spelled and correctly vowelled
#: prose. They are the failure modes the condensation brief names, in the order it
#: names them, and every one is here because a gate is the only thing that can
#: refuse a well-formed sentence for being the wrong KIND of sentence.
_META_RE = re.compile(
    r"\b(in|the)\s+(chapter|section)\s+\w+"
    r"|\bchapter\s+\d+\s+(discusses|describes|covers|argues)"
    r"|\bthe (author|book) (then |also |next )?(discusses|says|argues|tells us|goes on)"
    r"|\bthis (book|section|summary|condensation)\b"
    r"|\bin the (next|following) (chapter|section)\b",
    re.I,
)
_LIST_RE = re.compile(r"(?m)^\s*[-*•]\s+|^\s*\d+\.\s+\w+\s*$")
_CHATTER_RE = re.compile(r"\bas an ai\b|\bhere is (the|a)\b|\bword count\b|\bI (?:cannot|can't)\b", re.I)


def gate_brief(text: str, *, total_words: int) -> tuple[bool, list[str]]:
    """Refuse the shapes a brief may never take. Cannot judge whether it is TRUE.

    Truth is the challenger's job and the coverage check's; this is shape. The
    division is the same one `gate_introduction` documents: a deterministic gate
    can refuse a size, a format and a phrasing, and asserting that it also refuses
    a false claim is how a false claim gets through.
    """
    reasons: list[str] = []
    body = (text or "").strip()
    words = body.split()
    floor = int(total_words * MIN_FRACTION)
    if len(words) < floor:
        reasons.append(f"too short to stand alone ({len(words)}<{floor} words)")
    if len(words) > total_words:
        reasons.append(f"over the hard word limit ({len(words)}>{total_words} words)")
    if _META_RE.search(body):
        reasons.append("reads as a description of the book rather than as the book's substance")
    if _LIST_RE.search(body):
        reasons.append("bullet or numbered list — a brief is narrative prose")
    if len(re.findall(r"(?m)^###\s+", body)) > 3:
        reasons.append("more than three subheadings — a brief is one piece, not a structure")
    if re.search(r"(?m)^##\s+", body):
        reasons.append("contains a `## ` heading, which would break the book's section structure")
    if _CHATTER_RE.search(body):
        reasons.append("process chatter")
    if body and body[-1] not in ".!?\"')":
        reasons.append("ends mid-sentence — a compressor trimmed by counting words")
    return (not reasons), reasons


_LEX_RE = re.compile(r"[A-Za-z][A-Za-z'-]+")
_LEX_STOP = frozenset(
    """a an and are as at be but by for from had has have he her him his i in is it its of on or
    she that the their them they this to was were which who with you your not there when what
    all any been more most other some such than then these those into over under about""".split()
)


def lexical_shortlist(draft: str, points: list[dict[str, Any]], *, threshold: float = 0.5) -> list[dict[str, Any]]:
    """Points whose content words are largely absent from the draft.

    A SHORTLIST, never a verdict. Lexical overlap cannot see paraphrase and a brief
    is paraphrase by construction, so anything this returns is a question for the
    adjudication call rather than an omission. Its real job is the common case: when
    it returns nothing, the coverage check costs nothing, and a book whose brief is
    already complete is not charged for proving it.
    """
    have = {m.group(0).lower() for m in _LEX_RE.finditer(draft or "")} - _LEX_STOP
    out: list[dict[str, Any]] = []
    for p in points:
        want = {m.group(0).lower() for m in _LEX_RE.finditer(p.get("text") or "")} - _LEX_STOP
        want |= {str(e).lower() for e in (p.get("entities") or [])}
        if not want:
            continue
        if len(want & have) / len(want) < threshold:
            out.append(p)
    return out
