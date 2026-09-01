"""The spoken lane itself: its step sequence, and the state file that records it.

WHY THIS IS NOT IN `sessions/ingest.py` ANY MORE. It was, until 2026-09-01, and
that made the lane inseparable from one source: a second spoken source could only
join by copying a module that reads `KSessions.sql`, a hardcoded series registry
and a Google Drive mount. Asif's correction was exact — the spoken track must not
need a KSESSIONS ingest. So the lane lives here, sources are adapters, and adding
a third one means writing an adapter and touching nothing else.

WHAT AN ADAPTER STILL OWNS. Its own `meta.yml` and `series-config.yaml`. Those
files are mostly explanatory prose about the source — why a lecture's narrative
frame is expository, why a novel's is an external narrator — and folding them in
here would mean parameterising paragraphs of commentary to say something
different for every caller. That is worse than two short writers that each say
one true thing. What is shared is what must NOT diverge: the step sequence, and
how progress through it is recorded.

DELIBERATELY THE SAME STATE FILE the orchestrator writes, under the same key. A
second progress file for a second lane would be a second answer to one question,
and the first tool to read the wrong one would be silently wrong.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

#: The lane, in order. This is the definition — every consumer that shows
#: progress (`_phase_vocabulary`, the Studio track, the cross-book dashboard)
#: reads a book's position within it.
LANE_STEPS: tuple[str, ...] = (
    "sessions-ingest",
    "sessions-transcribe",
    "sessions-articulate",
    "sessions-read-along",
    "sessions-preface",
    "sessions-apparatus",
)

#: The step an ingest never performs — `articulate.py` does, on its own, because
#: it is hours of model calls. Named so `write_state` and `articulate.py` cannot
#: disagree about which step that is.
ARTICULATE_STEP = "sessions-articulate"

#: The step that pairs a spoken chapter's prose against the recording it came
#: from. Also not run by an ingest, and also long enough that its status must be
#: carried over rather than derived from position — same reasoning as
#: ARTICULATE_STEP, one step later in the lane.
READ_ALONG_STEP = "sessions-read-along"

#: The value in `orchestrator-state.json` that selects this lane. Read by
#: `_publish_sessions_gates.is_sessions_lane`, `compose_articulate`, the publish
#: convergence allowlist and `studio-pipeline.ts`. The name is historical — the
#: lane was built for Sessions and now carries audiobooks too — and is kept
#: BECAUSE it is written into three shipped books' state files and read by six
#: consumers plus their tests. Renaming it would buy a better word and risk a
#: live regression on books that are already published.
PIPELINE_MODE = "sessions_lane"

#: Steps whose status is carried over from any prior run rather than derived from
#: position, because an ingest does not perform them.
_CARRIED_OVER = (ARTICULATE_STEP, READ_ALONG_STEP)


def write_state(
    book_dir: Path,
    *,
    slug: str,
    branch: str,
    category: str,
    done_through: str,
) -> None:
    """Record what this lane has actually finished, and claim nothing else.

    `status` is `draft` and stays `draft`: publishing is a decision a person
    makes, and nothing here may make a book audience-facing by running.

    `branch` and `category` are passed in rather than derived. They used to be
    hardcoded as `f"Sessions/{slug}"` and `"lectures"`, which is precisely what
    made this writer unable to describe a book outside one bucket. Callers get
    them from `_branching.branch_name(profile=…)` and the content-type registry,
    so a bucket and its branch can never drift apart.
    """
    path = book_dir / "_system" / "orchestrator-state.json"
    prior: dict = {}
    if path.exists():
        try:
            prior = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            prior = {}

    cut = LANE_STEPS.index(done_through)
    phases = {step: {"status": "completed" if i <= cut else "pending"} for i, step in enumerate(LANE_STEPS)}

    # Carrying the prior status over UNCONDITIONALLY would make this a no-op for
    # the one step it exists to record: the value read here is always the
    # PRE-completion status. Found 2026-08-15, when `read_along.py` printed
    # success on every run and never once left `completed` behind.
    for carried in _CARRIED_OVER:
        if done_through != carried:
            prior_entry = (prior.get("phases") or {}).get(carried) or {}
            phases[carried] = {"status": str(prior_entry.get("status") or "pending")}

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "book_slug": slug,
                "category": category,
                "branch": branch,
                "pipeline_mode": PIPELINE_MODE,
                "phase": done_through,
                "phase_status": "completed",
                "last_completed_phase": done_through,
                "next_phase": LANE_STEPS[cut + 1] if cut + 1 < len(LANE_STEPS) else None,
                "last_error": None,
                "phases": phases,
                # Never promoted here. `publish_to_library.py` is what flips it,
                # and only after a person has looked at the book.
                "status": prior.get("status", "draft"),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def heard_text(book_dir: Path, episode: int | None) -> str:
    """What the recording says, as paragraphs, or "" when there is no transcript.

    Lives here rather than in `sessions/` because nothing about it is KSESSIONS':
    it reads `transcripts/ep{NN}.vtt`, which is the LANE's contract with whoever
    transcribed the audio. An audiobook adapter needing this had to import a
    private name out of the KSESSIONS module, which is the coupling this package
    exists to remove. `sessions.spoken._heard_text` re-exports it, so no caller
    moved.

    The cues are grouped into paragraphs rather than emitted one per line: a VTT
    cue is a breath, not a sentence, and one line per breath reads as a subtitle
    file rather than as a chapter. `group_into_paragraphs` decides where they
    break — at a sentence end, never at a cue count. See its docstring for what
    the count-based rule did to 46% of White Nights.
    """
    if episode is None:
        return ""
    path = Path(book_dir) / "transcripts" / f"ep{episode:02d}.vtt"
    if not path.exists():
        return ""

    from _transcript import from_vtt  # local: only this branch needs it

    cues = [cue.text.strip() for cue in from_vtt(path.read_text(encoding="utf-8")) if cue.text.strip()]
    return group_into_paragraphs(cues)


#: A cue that completes a sentence. The closing bracket allows for a quotation
#: mark or parenthesis after the stop — `he said."` ends a sentence just as
#: `he said.` does.
_SENTENCE_END = re.compile(r"[.!?][\"'’”)\]]*$")

#: Words a paragraph should reach before it is allowed to close. Below this a
#: sentence-per-paragraph reads as dialogue transcript rather than prose; the old
#: twelve-cue rule produced a median of 74, so this stays in the same register
#: while letting the break land where the sentence actually ends.
_PARAGRAPH_TARGET_WORDS = 70

#: A paragraph that begins the way a sentence does.
_SENTENCE_START = re.compile(r"[\"'(\[A-Z0-9]")


def group_into_paragraphs(cues: list[str], target_words: int = _PARAGRAPH_TARGET_WORDS) -> str:
    """Join cues into paragraphs that BREAK WHERE SENTENCES DO.

    Asif, 2026-09-01, circling two of them in the Composer: "Fix the review step
    to check for broken sentences split between paragraphs."

    The rule this replaces was `lines[i:i+12]` — a new paragraph every twelfth
    cue, counted without ever looking at the words. A VTT cue is a breath, so
    twelve of them land wherever the narrator happened to be, and in White Nights
    that put **168 of 359 paragraphs (46%)** starting mid-sentence:

        ...he meets Nastenka, a young woman weeping on

        a bench. Over the course of four nights...

    Detecting that afterwards was the first instinct and it is the wrong one: the
    defect is manufactured HERE, deterministically, for free, and a check that
    reports a self-inflicted wound every time is not a check. `prose_review` still
    carries the check, because a transcript can arrive with no terminal
    punctuation at all and then no grouping rule can save it — but it should be
    reporting the exception, not the norm.

    The cue text is NEVER altered: cues are joined, and the only decision is
    where a paragraph ends. That keeps the read-along pairing intact, which
    depends on the words being the ones on the tape.
    """
    paragraphs: list[str] = []
    current: list[str] = []
    words = 0
    for cue in cues:
        current.append(cue)
        words += len(cue.split())
        # Close only on a completed sentence that has reached a readable length.
        # Either condition alone is wrong: length alone is the old bug, and a
        # sentence boundary alone gives one-sentence paragraphs.
        if words >= target_words and _SENTENCE_END.search(cue):
            paragraphs.append(" ".join(current))
            current, words = [], 0
    if current:
        tail = " ".join(current)
        # A tail too short to have closed a paragraph joins the previous one
        # rather than becoming a stub. Making it its own paragraph would
        # reintroduce the exact defect this function exists to remove: a
        # paragraph opening mid-sentence, lowercase, because the words before it
        # are somewhere above.
        #
        # The one exception is a tail that stands on its own — begins like a
        # sentence and ends like one. A short closing line is a real paragraph.
        # (An earlier version tested the PREVIOUS paragraph instead, which is
        # backwards: it left the fragment stranded precisely when the paragraph
        # above it was well-formed, which is nearly always.)
        stands_alone = _SENTENCE_START.match(tail) and _SENTENCE_END.search(tail)
        if paragraphs and not stands_alone:
            paragraphs[-1] = paragraphs[-1] + " " + tail
        else:
            paragraphs.append(tail)
    return "\n\n".join(paragraphs)
