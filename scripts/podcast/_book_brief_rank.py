"""_book_brief_rank.py — what survives into the brief, and how many words each part gets.

THE ONE THING THIS PIPELINE DID NOT ALREADY HAVE
------------------------------------------------
Every other length decision in this repo allocates by SOURCE LENGTH: a chapter of
n words composes to roughly n words, and `_book_completeness` halts a compose when
it does not. That rule is correct for an edition, whose contract is that nothing
was dropped, and it is exactly wrong for a brief, whose contract is that almost
everything was.

So a brief needs the opposite gate and a decision the editions never make: which
material is worth its space. This module is that decision, and it is DELIBERATELY
DETERMINISTIC — no model call. A model already judged each point's weight while it
was reading one chapter; asking a second model to re-rank the whole book would be
asking for a judgement it has no better evidence for than arithmetic over the
first one's, and it would not be reproducible across runs.

FREQUENCY IS NOT IMPORTANCE, AND THE ARITHMETIC HAS TO SAY SO
-------------------------------------------------------------
The obvious ranking — count how often an idea recurs — gets a book backwards.
Dostoyevsky's dreamer says he is lonely on every page; he says the one thing that
ends the story once. So the model's own weight for a point spans 1..5 and carries
the ranking, while recurrence and dependency are BONUSES CAPPED AT 2.0 each. A
point mentioned once at weight 5 outranks a point mentioned in every chapter at
weight 2. That inequality is pinned by a test, because it is the whole thesis of
the file.

DEPENDENCY IS PROTECTION, NOT PREFERENCE
----------------------------------------
A point other points declare they depend on is a prerequisite. Cutting it does not
cost the reader that point; it costs them everything downstream of it — the
technical-book failure the spec calls out and the causal-chain failure it calls out
are the same defect seen from two genres. In-degree is therefore scored, and the
retention pass additionally pulls in any prerequisite of a retained point even when
that prerequisite scored below the line.

BUDGET IS ALLOCATED BEFORE A WORD IS WRITTEN
--------------------------------------------
Not trimmed afterwards. Compressing a finished draft is how a brief ends up
proportional to the source instead of to the material — the writer spends what the
chapter felt like it deserved and the trim takes it back evenly. Allocation up
front is what lets a fifty-page digression get fifty words.
"""

from __future__ import annotations

import re
from typing import Any

#: The presets, in words. `standard` is the default everywhere.
PRESETS: dict[str, int] = {"quick": 1500, "standard": 3500, "deep": 5000}
DEFAULT_PRESET = "standard"

#: Ordered most- to least-protected. `essential` may never be dropped by the
#: budget; `expendable` never survives it.
TIERS: tuple[str, ...] = ("essential", "important", "supporting", "optional", "expendable")

#: What KIND of material a point is. The bonus is small and exists to break ties
#: between points a model weighted identically: a definition or a turning point
#: carries more of a reader's understanding per word than an illustration does.
KIND_BONUS: dict[str, float] = {
    "thesis": 1.0,
    "turn": 1.0,
    "resolution": 1.0,
    "definition": 0.75,
    "framework": 0.75,
    "claim": 0.5,
    "event": 0.5,
    "cause": 0.5,
    "distinction": 0.5,
    "caveat": 0.5,
    "theme": 0.25,
    "relationship": 0.25,
    "evidence": 0.25,
    "context": 0.0,
    "example": -0.5,
    "anecdote": -0.75,
}

#: Score floors per tier. Absolute rather than percentile: a percentile cut forces
#: the same shape onto every book, so a tightly argued treatise and a rambling one
#: would come out with identical proportions of "essential" material, which is a
#: claim about the ranking rather than about the books.
TIER_FLOOR: dict[str, float] = {
    "essential": 5.5,
    "important": 4.0,
    "supporting": 2.75,
    "optional": 1.75,
}

#: Roughly how many words of finished prose one retained point costs. Measured
#: against the shape of the drafts this produces rather than assumed: below about
#: 30 the brief reads as a list, above about 55 it stops being a brief.
WORDS_PER_POINT = 42

#: Reserves, as a fraction of the total with hard floors and ceilings. The opening
#: has to orient a reader who has read nothing; the close has to land. Both are
#: capped so they cannot become the essay-with-a-summary-attached shape that
#: over-represents introduction and conclusion.
_OPENING_FRACTION, _OPENING_MIN, _OPENING_MAX = 0.055, 120, 260
_CLOSING_FRACTION, _CLOSING_MIN, _CLOSING_MAX = 0.075, 140, 320

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]+")
_STOP = frozenset(
    """a an and are as at be but by for from had has have he her him his i in is it its
    of on or she that the their them they this to was were which who with you your not
    there here when what where how why all any been more most other some such than then
    these those into over under about after before while during between""".split()
)


def _keywords(text: str) -> frozenset[str]:
    """Content words of a point, for the recurrence signal. Crude on purpose.

    A semantic recurrence measure would need embeddings and would make this file
    non-deterministic and expensive for a signal that is capped at 2.0 anyway.
    Lexical overlap under-counts paraphrase, which errs toward trusting the
    model's weight — the direction this module already argues is correct.
    """
    return frozenset(w for w in (m.group(0).lower() for m in _WORD_RE.finditer(text or "")) if w not in _STOP)


def normalize_points(analyses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten per-section analyses into one list of points with stable ids.

    Ids are positional (`S02-P03`) rather than content-derived so that a point's
    identity survives a re-word of its own text — the coverage check and the
    dependency graph both address points by id across two model calls.
    """
    points: list[dict[str, Any]] = []
    for s_i, section in enumerate(analyses, start=1):
        for p_i, raw in enumerate(section.get("points") or [], start=1):
            text = str(raw.get("text") or "").strip()
            if not text:
                continue
            points.append(
                {
                    "id": f"S{s_i:02d}-P{p_i:02d}",
                    "section_index": s_i,
                    "section_title": str(section.get("title") or f"Section {s_i}"),
                    "text": text,
                    "kind": str(raw.get("kind") or "claim").strip().lower(),
                    "weight": max(1.0, min(5.0, float(raw.get("weight") or 3))),
                    "depends_on": [str(d).strip() for d in (raw.get("depends_on") or []) if str(d).strip()],
                    "entities": [str(e).strip() for e in (raw.get("entities") or []) if str(e).strip()],
                }
            )
    return points


def score_points(points: list[dict[str, Any]], *, section_count: int | None = None) -> list[dict[str, Any]]:
    """Add `score` and its component parts to every point. Pure; returns the same list."""
    section_count = section_count or max((p["section_index"] for p in points), default=1)
    ids = {p["id"] for p in points}

    in_degree: dict[str, int] = {p["id"]: 0 for p in points}
    for p in points:
        for dep in p["depends_on"]:
            if dep in ids and dep != p["id"]:
                in_degree[dep] += 1

    keys = {p["id"]: _keywords(p["text"]) | {e.lower() for e in p["entities"]} for p in points}
    sections_of: dict[str, set[int]] = {}
    for p in points:
        mine = keys[p["id"]]
        if not mine:
            sections_of[p["id"]] = {p["section_index"]}
            continue
        seen = set()
        for q in points:
            overlap = mine & keys[q["id"]]
            if len(overlap) >= 2 or (len(mine) == 1 and overlap):
                seen.add(q["section_index"])
        sections_of[p["id"]] = seen or {p["section_index"]}

    for p in points:
        recurrence = min(2.0, 0.5 * (len(sections_of[p["id"]]) - 1))
        dependency = min(2.0, 0.75 * in_degree[p["id"]])
        kind = KIND_BONUS.get(p["kind"], 0.0)
        # Position, capped hard at 0.5. The first and last sections of a book do
        # carry thesis and resolution disproportionately often — and rewarding
        # that generously is precisely how a brief comes out as a long paraphrase
        # of the introduction with the middle missing.
        position = 0.5 if p["section_index"] in (1, section_count) else 0.0
        p["in_degree"] = in_degree[p["id"]]
        p["recurrence_sections"] = len(sections_of[p["id"]])
        p["score"] = round(p["weight"] + recurrence + dependency + kind + position, 3)
    return points


#: Two points are the same point above this much keyword overlap (Jaccard). Tuned
#: against White Nights, where the producer's introduction restates the entire plot
#: and every one of its claims collided with the chapter that actually tells it.
DUPLICATE_OVERLAP = 0.55


def deduplicate(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse points that say the same thing, keeping the best-scoring one.

    Books restate themselves — a nonfiction author develops one idea across five
    chapters, a foreword tells you the plot before the story does — and without
    this the brief explains the same thing as many times as the book did. That is
    the spec's redundancy stage and it belongs HERE rather than in a model call:
    the alternative is asking a model to compare 85 points pairwise, which is
    expensive, non-deterministic, and no better than set overlap at recognising a
    sentence it just read twice.

    KEEPING THE REFINEMENT, not just the first statement. The survivor is the
    highest-SCORING instance, not the earliest — a foreword's broad summary and the
    chapter's actual account overlap heavily, and it is the chapter that has the
    detail. Losers record `duplicate_of` and are dropped, and every `depends_on`
    pointing at a loser is repointed at the survivor so the prerequisite closure
    still finds its target.
    """
    keys = {p["id"]: _keywords(p["text"]) | {e.lower() for e in p["entities"]} for p in points}
    survivors: list[dict[str, Any]] = []
    remap: dict[str, str] = {}
    for p in sorted(points, key=lambda q: (-q["score"], q["section_index"], q["id"])):
        mine = keys[p["id"]]
        if not mine:
            survivors.append(p)
            continue
        hit = next(
            (
                s
                for s in survivors
                if (keys[s["id"]] & mine) and len(keys[s["id"]] & mine) / len(keys[s["id"]] | mine) >= DUPLICATE_OVERLAP
            ),
            None,
        )
        if hit is None:
            survivors.append(p)
        else:
            p["duplicate_of"] = hit["id"]
            remap[p["id"]] = hit["id"]
    for p in survivors:
        p["depends_on"] = [remap.get(d, d) for d in p["depends_on"]]
    return sorted(survivors, key=lambda p: (p["section_index"], p["id"]))


#: No more than this share of a book's points may be `essential`. The floors above
#: assume a model that used the 1..5 scale; the first real book came back with 71
#: of 85 points at weight 5, which is not a ranking at all — and an "essential" set
#: that large cannot be protected from a budget, so the protection silently becomes
#: nothing and the brief comes out allocated evenly across every chapter, which is
#: the exact failure this file exists to prevent.
ESSENTIAL_SHARE_CAP = 0.25

#: The relative fallback, as cumulative shares. Used ONLY when the cap above trips.
_RELATIVE_BANDS = ((0.20, "essential"), (0.45, "important"), (0.70, "supporting"), (0.90, "optional"))

#: Below this many points there is no distribution to rank against, so the absolute
#: floors stand however inflated they look.
_RELATIVE_MIN_POINTS = 12


def assign_tiers(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add `tier`, guaranteeing a non-empty `essential` set.

    The thresholds are absolute, so a book whose model weights all ran low could
    produce no essential material at all — a brief with nothing protected from the
    budget. The fallback promotes the top decile (at least three points) rather
    than lowering the threshold, so the guarantee is about COVERAGE and never
    changes what the scores mean.
    """
    for p in points:
        s = p["score"]
        p["tier"] = next((t for t in TIERS[:-1] if s >= TIER_FLOOR[t]), "expendable")
    if not points:
        return points

    essential = sum(1 for p in points if p["tier"] == "essential")
    # The cap needs enough points to rank before it means anything. Below this it
    # was doing real harm: a four-point fixture whose ONE strong point cleared the
    # absolute floor tripped the cap (1 > 0.25 x 4 is false, but 1 > 0.25 x 2 is
    # not) and the relative bands then gave that book no essential material at all
    # — a brief with nothing protected, produced by the guard that exists to
    # protect things.
    if len(points) >= _RELATIVE_MIN_POINTS and essential > ESSENTIAL_SHARE_CAP * len(points):
        # THE MODEL DID NOT USE THE SCALE. Fall back to the book's own distribution
        # — rank order is still information even when the absolute numbers are not.
        # Recorded on every point, because a brief built from a relative ranking is
        # a weaker artifact than one built from an honest absolute one, and the
        # report should be able to say so rather than presenting both alike.
        ranked = sorted(points, key=lambda p: (-p["score"], p["section_index"], p["id"]))
        for i, p in enumerate(ranked):
            share = (i + 1) / len(ranked)
            p["tier"] = next((t for cut, t in _RELATIVE_BANDS if share <= cut), "expendable")
            p["tiered_relatively"] = True
        # A floor, not a share: the bands are percentages and a small book can round
        # every one of them away. Whatever else is true, the top three points of a
        # book are protected from the budget.
        for p in ranked[:3]:
            p["tier"] = "essential"
    elif essential == 0:
        for p in sorted(points, key=lambda p: -p["score"])[: max(3, len(points) // 10)]:
            p["tier"] = "essential"
    return points


def _retain(points: list[dict[str, Any]], capacity: int) -> list[dict[str, Any]]:
    """Choose the points the brief will carry, best-first, then close prerequisites.

    Every `essential` point is taken whatever the capacity — the budget may shrink
    what each one gets said about it, never delete it. Below that, points are taken
    by score until the capacity is spent. `expendable` is never taken.

    The prerequisite closure runs AFTER the cut and can overshoot the capacity by
    design: a retained point whose premise was dropped is worse than a brief that
    is four points denser than planned, and the word budget below absorbs the
    difference by giving every point slightly less room.
    """
    by_id = {p["id"]: p for p in points}
    ranked = sorted(points, key=lambda p: (-p["score"], p["section_index"], p["id"]))
    kept: dict[str, dict[str, Any]] = {p["id"]: p for p in ranked if p["tier"] == "essential"}
    for p in ranked:
        if len(kept) >= capacity:
            break
        if p["id"] in kept or p["tier"] == "expendable":
            continue
        kept[p["id"]] = p

    frontier = list(kept.values())
    while frontier:
        nxt = []
        for p in frontier:
            for dep in p["depends_on"]:
                if dep in by_id and dep not in kept:
                    kept[dep] = by_id[dep]
                    kept[dep]["retained_as_prerequisite"] = True
                    nxt.append(by_id[dep])
        frontier = nxt
    return sorted(kept.values(), key=lambda p: (p["section_index"], p["id"]))


def allocate_budget(retained: list[dict[str, Any]], *, body_words: int) -> dict[int, int]:
    """Split the body budget across sections by retained IMPORTANCE, not by source length.

    A section from which nothing survived gets nothing — no floor, deliberately.
    A floor per section is how a brief becomes proportional to the table of
    contents, which is the shape the whole exercise exists to avoid.
    """
    mass: dict[int, float] = {}
    for p in retained:
        mass[p["section_index"]] = mass.get(p["section_index"], 0.0) + p["score"]
    total = sum(mass.values()) or 1.0
    alloc = {idx: int(round(body_words * m / total)) for idx, m in mass.items()}
    # Round-off lands on the heaviest section rather than being dropped, so the
    # allocations sum to the body budget exactly and the writer is told the truth.
    if alloc:
        drift = body_words - sum(alloc.values())
        heaviest = max(alloc, key=lambda i: mass[i])
        alloc[heaviest] += drift
    return alloc


def plan(analyses: list[dict[str, Any]], *, total_words: int) -> dict[str, Any]:
    """The whole deterministic half: rank, tier, retain, allocate. No model call.

    Returns the object the drafting prompt is built from and the coverage check is
    judged against, so both stages are looking at one ranking rather than each
    forming its own opinion of what mattered.
    """
    scored = score_points(normalize_points(analyses))
    points = assign_tiers(deduplicate(scored))
    # Collected AFTER the pass that marks them — `deduplicate` is what sets
    # `duplicate_of`, so reading `scored` first would always find nothing.
    duplicates = [p for p in scored if "duplicate_of" in p]
    opening = max(_OPENING_MIN, min(_OPENING_MAX, int(round(total_words * _OPENING_FRACTION))))
    closing = max(_CLOSING_MIN, min(_CLOSING_MAX, int(round(total_words * _CLOSING_FRACTION))))
    body = max(1, total_words - opening - closing)
    retained = _retain(points, capacity=max(1, body // WORDS_PER_POINT))
    kept = {p["id"] for p in retained}
    return {
        "total_words": total_words,
        "opening_words": opening,
        "closing_words": closing,
        "body_words": body,
        "section_words": allocate_budget(retained, body_words=body),
        "points": points,
        "retained": retained,
        "dropped": [p for p in points if p["id"] not in kept],
        "essential_ids": [p["id"] for p in points if p["tier"] == "essential"],
        "duplicates": [{"id": p["id"], "of": p["duplicate_of"], "text": p["text"]} for p in duplicates],
        "tiered_relatively": any(p.get("tiered_relatively") for p in points),
    }
