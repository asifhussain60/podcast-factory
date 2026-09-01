"""Whether a chapter's read-along timings are fit to publish.

WHAT THIS REPLACES, and why (2026-08-31). The read-along lane decided this with
one number: the share of transcript cues that could support their own placement,
against a threshold of 0.55. That number answers a question about CUE
GRANULARITY, not about accuracy. A subtitle cue is one or two seconds — "Welcome
to my lecture." — and a paragraph is a hundred words, so the shorter the cues get
relative to the paragraphs, the lower the score falls no matter how perfectly the
two are paired.

It held up while every session book was one chapter per recording, where cues and
chapters are comparable in size: `surah-al-fateha` and `love-of-the-prophet` both
score 0.80-0.89 that way. `purification-of-the-heart` is twenty-four chapters
across two ten-hour recordings, and every one of its chapters scored 0.22-0.52
while being aligned in perfect order with 94-100% of paragraphs timed. Zero would
have published, and the reason was arithmetic about cue length.

WHAT THIS ASKS INSTEAD. The failure the gate exists to prevent is a paragraph
lit up while a different one is being spoken. Every condition below is a direct
statement about that, so the gate now tests the mistake rather than a proxy for
it. The cue score is still computed and still recorded in the manifest — it is a
useful diagnostic — it simply no longer decides.

The conditions are an ORDERED, NAMED array on purpose: a refusal names the
condition that refused, so a chapter published without highlighting says which
property of the pairing failed rather than quoting a percentage nobody can act
on. Adding a condition is one entry here and nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

#: Share of a chapter's paragraphs that must carry a timing. Below this the
#: reader would follow the recording in fits, with silent gaps where the
#: highlight simply stops — worse than not highlighting at all.
MIN_COVERAGE = 0.90

#: How far past the chapter's typical paragraph one paragraph may stretch before
#: it is read as a bucket for audio rather than a timing. Generous on purpose: a
#: long paragraph is ordinary, and the failure this catches is not long, it is
#: absurd — 137 minutes against a median of one, which is what paragraph one of
#: "Love of the World" measured when it absorbed two hours of opening audio that
#: matches no chapter in the book.
MAX_SPAN_OVER_MEDIAN = 20.0

#: Slack allowed where one chapter's span meets the next. The recordings run
#: continuously and the seam between two chapters is a sentence, not a cut, so
#: demanding a strict inequality would refuse a correct pairing for sharing a
#: second with its neighbour.
NEIGHBOUR_SLACK_S = 2.0


@dataclass(frozen=True)
class Timing:
    """One chapter's timings, and what they must be judged against."""

    paragraphs: int
    #: Timed paragraphs in reading order: dicts carrying `startS` and `endS`.
    cues: list[dict]
    #: Whether the aligner's own path through the recording held its order.
    monotonic: bool
    recording_s: float
    #: Where the previous chapter ended and the next one began in this same
    #: recording, when there is one. None means this chapter has no neighbour on
    #: that side, which is not evidence of anything.
    before_end_s: float | None = None
    after_start_s: float | None = None


@dataclass(frozen=True)
class Verdict:
    ok: bool
    #: Plain-English reasons, one per condition that refused, in array order.
    failures: list[str] = field(default_factory=list)
    #: Every condition that was asked, so a pass is as legible as a refusal.
    checked: list[str] = field(default_factory=list)

    @property
    def reason(self) -> str:
        return "; ".join(self.failures)


def _has_timings(t: Timing) -> str | None:
    if not t.cues:
        return "no paragraph could be placed in the recording"
    return None


def _alignment_held(t: Timing) -> str | None:
    if not t.monotonic:
        return "the alignment ran backwards through the recording"
    return None


def _paragraphs_in_order(t: Timing) -> str | None:
    for a, b in zip(t.cues, t.cues[1:]):
        if b["startS"] < a["startS"] or b["endS"] < a["endS"]:
            return "a paragraph is timed before the one above it"
    return None


def _spans_run_forward(t: Timing) -> str | None:
    for c in t.cues:
        if c["endS"] < c["startS"]:
            return "a paragraph ends before it begins"
    return None


def _coverage(t: Timing) -> str | None:
    if t.paragraphs <= 0:
        return "the chapter has no paragraphs to time"
    share = len(t.cues) / t.paragraphs
    if share < MIN_COVERAGE:
        return f"only {share:.0%} of paragraphs could be timed, below {MIN_COVERAGE:.0%}"
    return None


def _within_the_recording(t: Timing) -> str | None:
    # Every condition is asked even after an earlier one fails, so each must
    # survive the states the earlier ones catch — here, a chapter with nothing
    # timed at all. Reporting "no timings" three times helps nobody.
    if t.recording_s <= 0 or not t.cues:
        return None
    last = max(c["endS"] for c in t.cues)
    if last > t.recording_s + NEIGHBOUR_SLACK_S:
        return f"a paragraph is timed at {last:.0f}s, past the end of a {t.recording_s:.0f}s recording"
    return None


def _no_paragraph_swallows_the_chapter(t: Timing) -> str | None:
    """No single paragraph may hold a wildly disproportionate stretch of audio.

    The aligner must place every cue somewhere, so audio that matches nothing in
    the book piles onto whichever paragraph is nearest — usually the first. The
    result reads as a timing and behaves as a bucket: the reader watches one
    paragraph stay lit for two hours. Every other condition here passed it.
    """
    if len(t.cues) < 3:
        return None
    spans = sorted(c["endS"] - c["startS"] for c in t.cues)
    median = spans[len(spans) // 2]
    if median <= 0:
        return None
    if spans[-1] > median * MAX_SPAN_OVER_MEDIAN:
        return (
            f"one paragraph spans {spans[-1] / 60:.0f} min against a typical "
            f"{median / 60:.1f} min — it is holding audio that matches no text"
        )
    return None


def _clear_of_neighbours(t: Timing) -> str | None:
    if not t.cues:
        return None
    first = min(c["startS"] for c in t.cues)
    last = max(c["endS"] for c in t.cues)
    if t.before_end_s is not None and first < t.before_end_s - NEIGHBOUR_SLACK_S:
        return "this chapter begins inside the one before it"
    if t.after_start_s is not None and last > t.after_start_s + NEIGHBOUR_SLACK_S:
        return "this chapter runs into the one after it"
    return None


#: The gate, in order. Each entry is (name, question it answers, check).
#: The first three are structural — without them nothing below can be trusted —
#: so the order is meaningful and a caller reports failures in it.
CONDITIONS: tuple[tuple[str, str, Callable[[Timing], "str | None"]], ...] = (
    ("has-timings", "did any paragraph find a place in the recording", _has_timings),
    ("alignment-held", "did the pairing keep the recording's own order", _alignment_held),
    ("paragraphs-in-order", "does each paragraph follow the one above it", _paragraphs_in_order),
    ("spans-run-forward", "does every paragraph end after it begins", _spans_run_forward),
    ("coverage", "did enough of the chapter get timed to follow along", _coverage),
    ("within-the-recording", "is every timing inside the audio that exists", _within_the_recording),
    (
        "no-paragraph-swallows-the-chapter",
        "is any paragraph holding unmatched audio",
        _no_paragraph_swallows_the_chapter,
    ),
    ("clear-of-neighbours", "does this chapter stay out of its neighbours' spans", _clear_of_neighbours),
)


def drop_swallowing_paragraphs(cues: list[dict]) -> tuple[list[dict], list[dict]]:
    """Remove the paragraphs holding audio that matches no text. Returns (kept, dropped).

    The same rule `_no_paragraph_swallows_the_chapter` judges by, applied one
    paragraph at a time instead of to the whole chapter — and it uses that
    condition's own constant, so the two can never disagree about what counts as
    swallowing.

    WHY DROP RATHER THAN REFUSE. This is the rule the timing pass already applies
    to a paragraph no cue landed on: skip it rather than guess a span, because a
    guessed span lights it up during somebody else's sentence. A swallowing
    paragraph is the same defect arriving from the other direction — it has a
    span, and the span is wrong. Refusing the whole chapter for it costs the
    other two hundred and forty-five paragraphs their correct timings, which is a
    heavy price for one. `purification-of-the-heart`'s final chapter is exactly
    that case: one paragraph holding twenty-four minutes, and 245 good ones.

    Coverage still has the last word. A chapter that loses so many paragraphs
    this way that a reader could not follow it is refused by that condition,
    which is where the judgement belongs.
    """
    if len(cues) < 3:
        return cues, []
    spans = sorted(c["endS"] - c["startS"] for c in cues)
    median = spans[len(spans) // 2]
    if median <= 0:
        return cues, []
    limit = median * MAX_SPAN_OVER_MEDIAN
    kept = [c for c in cues if (c["endS"] - c["startS"]) <= limit]
    dropped = [c for c in cues if (c["endS"] - c["startS"]) > limit]
    # `idx` is the position a reader's highlight steps through, so it has to be
    # renumbered after a removal or the sequence has a hole in it.
    for position, cue in enumerate(kept):
        cue["idx"] = position
    return kept, dropped


def verdict(t: Timing) -> Verdict:
    """Judge one chapter's timings against every condition, in order.

    Every condition is asked even after one fails, so a chapter that is wrong in
    two ways reports both rather than the first — the second is usually what
    explains the first.
    """
    failures: list[str] = []
    checked: list[str] = []
    for name, _question, check in CONDITIONS:
        checked.append(name)
        problem = check(t)
        if problem:
            failures.append(f"{name}: {problem}")
    return Verdict(ok=not failures, failures=failures, checked=checked)
