"""_vowel_recovery.py — salvage a refused vowelling instead of losing the whole run.

THE PROBLEM THIS EXISTS FOR (Asif, 2026-07-30). `_vowelling.rejection_reason` is
all-or-nothing per RUN: a candidate whose consonantal skeleton differs from the
source's by one character is refused, and the run stays completely bare. That gate
is correct and stays exactly as it is — letters may not move under cover of marking.
But its blast radius was the entire run, and on the first real source pass that cost
6.9% of one book: 94 refusals, 92 of them for a SINGLE changed letter.

The paragraph that surfaced it reads, in the scan, `فأقبل العالم يتلو العهد على
الغلام ويرثله` — and the model answered `ويرتله`, i.e. `يُرَتِّلُهُ`, "recites it
measuredly", which is plainly the right word beside `يتلو العهد`; the scanner misread
ت as ث. The gate refused, correctly, because it cannot know which of the two is the
error. What was wrong is that ~120 characters of perfectly good vowelling went with
it, leaving a bare hole in the middle of a marked paragraph.

THE FIX IS NOT A LOOSER GATE. It is the same gate applied to smaller units: cut the
refused run at sentence boundaries, ask for each piece separately, and keep the
pieces whose skeleton matches. Only the fragment actually holding the disputed letter
stays bare, and it is reported as that fragment rather than as the paragraph.

Two properties make this safe to assemble blind:

  1. The cut is LOSSLESS — ``"".join(segments(run)) == run`` for every run, verified
     by test — so a segment left un-vowelled contributes its source bytes exactly.
  2. The reassembly is re-checked against the ORIGINAL gate before it is returned. A
     partial result that somehow fails is discarded whole and the run stays bare, so
     this can only ever add marks that the unmodified gate has already admitted.

Pipeline-side only, deliberately: it is a recovery STRATEGY, not part of the
admissibility contract, so it carries no mirror obligation to
``plan-dashboard/scripts/lib/vowelling.mjs``. The gate it calls is the mirrored one.
"""

from __future__ import annotations

from collections.abc import Callable

from _vowelling import (
    is_arabic_passage,
    is_vowelling_candidate,
    reflow_to_source_whitespace,
    rejection_reason,
)

# Sentence enders, coarse pass. `؛` is included because this OCR uses it where a
# translator would use a colon, so it ends a clause as firmly as a full stop.
_ENDERS_COARSE = "؟!.؛"
# The fine pass adds the Arabic comma.
_ENDERS_FINE = _ENDERS_COARSE + "،"

# A coarse fragment longer than this is cut again at its commas. Sentence-level is
# the right FIRST cut — more context means a better reading, and the gate cannot
# tell a poorly-chosen vowel from a well-chosen one — but it is not enough on its
# own: the first real salvage pass left ¶83 of `the-master-and-the-disciple` still
# bare because its whole opening, `فأقبل العالم ... حتى بلغ؛`, is ONE sentence and
# the disputed `ويرثله` sits inside it. Sub-cutting on commas isolates the clause
# that actually holds the dispute and marks the four around it. Set above the
# length where a clause carries its own sense, so short sentences stay whole.
_SUBCUT_OVER_CHARS = 100

# Below this a fragment is not worth a model call: the surrounding sense a
# vocalisation depends on is not inside it. Matches the spirit of
# `_vowelling.MIN_RUN_CHARS`, applied to a piece rather than a run.
_MIN_SEGMENT_CHARS = 12


def _cut(run: str, enders: str) -> list[str]:
    """Split after each ender, keeping the ender and its trailing whitespace.

    LOSSLESS BY CONSTRUCTION: every character of ``run`` lands in exactly one
    segment, in order, so ``"".join(_cut(run, e)) == run``. That is the property the
    reassembly depends on — a segment that is left alone must contribute its source
    bytes unchanged, or the skeleton of the whole would move.
    """
    out: list[str] = []
    start = i = 0
    while i < len(run):
        if run[i] in enders:
            j = i + 1
            while j < len(run) and (run[j] in enders or run[j].isspace()):
                j += 1
            out.append(run[start:j])
            start = i = j
            continue
        i += 1
    if start < len(run):
        out.append(run[start:])
    return out


def segments(run: str) -> list[str]:
    """The pieces to retry a refused run as, cut sentence-first then clause-deep.

    Hierarchical rather than one-level: sentences keep enough context for the
    reading to be chosen well, and any sentence still long enough to hide a
    disputed letter behind four good clauses is cut again at its commas. Both cuts
    are lossless, so the flattened result still rejoins to ``run`` exactly.
    """
    out: list[str] = []
    for piece in _cut(run, _ENDERS_COARSE):
        if len(piece.strip()) > _SUBCUT_OVER_CHARS:
            out += _cut(piece, _ENDERS_FINE)
        else:
            out.append(piece)
    return out


def askable(segment: str) -> bool:
    """Is this piece worth a model call, or does it pass through as-is?"""
    return len(segment.strip()) >= _MIN_SEGMENT_CHARS and is_arabic_passage(segment) and is_vowelling_candidate(segment)


def plan(run: str) -> list[str] | None:
    """The segments to retry, or None when the run offers no useful cut."""
    parts = segments(run)
    if len(parts) < 2:
        return None
    if not any(askable(p) for p in parts):
        return None
    return parts


def assemble(run: str, parts: list[str], answers: dict[int, str]) -> tuple[str, list[str]]:
    """Rebuild the run from vowelled pieces, keeping the source where one failed.

    Returns ``(text, still_bare)``. ``still_bare`` lists the fragments that could not
    be marked — the thing a human should actually look at, rather than the paragraph
    they happen to sit in.

    Fails CLOSED: if the assembled text does not itself pass the unmodified gate
    against the original run, the original is returned and nothing is claimed. So
    this function cannot widen what the gate admits, only narrow what a refusal costs.
    """
    rebuilt: list[str] = []
    still_bare: list[str] = []
    for i, part in enumerate(parts):
        marked = answers.get(i)
        if marked is None:
            if askable(part):
                still_bare.append(part.strip())
            rebuilt.append(part)
            continue
        rebuilt.append(marked)
    text = "".join(rebuilt)
    if rejection_reason(run, text):
        # Should be unreachable — every accepted piece already passed the gate on its
        # own and the cut is lossless — but a silent skeleton drift here would write a
        # corrupted source, so the assembly is checked rather than trusted.
        return run, [run.strip()]
    return text, still_bare


def segment_answer(segment: str, raw: str) -> str | None:
    """One piece's answer, gated exactly as a whole run's would be."""
    candidate = reflow_to_source_whitespace(segment, raw)
    if rejection_reason(segment, candidate):
        return None
    return candidate


def recover(
    run: str,
    *,
    ask: Callable[[str], str],
    log: Callable[[str], None] = print,
) -> tuple[str, list[str]] | None:
    """Retry one refused run piecewise. None when there was nothing to try.

    Sequential; callers with many refused runs should drive `plan`/`segment_answer`/
    `assemble` themselves across a pool. Kept here so a single-run caller — a test,
    or a human re-running one passage — has the whole strategy in one call.
    """
    parts = plan(run)
    if parts is None:
        return None
    answers: dict[int, str] = {}
    for i, part in enumerate(parts):
        if not askable(part):
            continue
        try:
            answers[i] = segment_answer(part, ask(part)) or ""
        except Exception as e:  # one bad piece must not cost the others
            log(f"      segment {i}: {e}")
            continue
        if not answers[i]:
            del answers[i]
    if not answers:
        return None
    return assemble(run, parts, answers)


__all__ = [
    "assemble",
    "askable",
    "plan",
    "recover",
    "segment_answer",
    "segments",
]
