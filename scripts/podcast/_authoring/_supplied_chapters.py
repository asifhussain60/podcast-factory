"""The chapter set an operator SUPPLIED, and holding phase 0d's plan to it.

Split out of `_chapter_design.py` (2026-08-31, DR-005): that file is a
grandfathered over-limit module — "split, never grow" — and this was the growth.
It belongs on its own regardless. `_chapter_design.py` is the phase-0d
orchestration; this is one cohesive question with two halves that must stay
together, in the same way `_verbatim_episode.py` holds the thing that runs
INSTEAD of authoring.

The two halves are the point, and neither works alone. `_supplied_chapters_block`
ASKS for the supplied set, in a prompt whose own step 1 otherwise says the
source's chapter breaks are advisory and should be merged, split, dropped and
re-drawn. `_supplied_chapter_violations` CHECKS what came back. A prompt is a
request; the gate is what makes the request a contract.

See `_pipeline_flags.supplied_chapter_titles` for where the list comes from —
and for why a list is authoritative only when the book's segmentation answer
actually says to follow it.
"""

from __future__ import annotations


def _supplied_chapters_block(titles) -> str:
    """The instruction that REPLACES step 1's own segmentation, when the operator
    supplied the chapter list.

    Step 1 otherwise tells the model in as many words that "the source's own
    chapter breaks are ADVISORY, not authoritative" and to MERGE, SPLIT, DROP and
    RE-DRAW them. That is right for a book being reconfigured into a podcast and
    exactly wrong for a series teaching through a published work chapter by
    chapter: it is what turned two of `purification-of-the-heart`'s chapters into
    one called "The World and the Envious Heart" (2026-08-31).

    So this does not soften those four verbs — it forbids them, first, before
    they are read. The model still does the hard part, which is finding where
    each named chapter begins and ends in the transcript; it no longer decides
    WHICH chapters exist. `_supplied_chapter_violations` then checks the plan it
    returns against the same list, because a prompt is a request and this repo
    gates on the answer.
    """
    if not titles:
        return ""
    listing = "\n".join(f"     {i + 1}. {t}" for i, t in enumerate(titles))
    return (
        "0. THE CHAPTER SET IS GIVEN. IT IS NOT YOURS TO DECIDE. This series\n"
        "   teaches through a published work chapter by chapter, and these are that\n"
        f"   work's own chapters — all {len(titles)} of them, in order:\n\n"
        f"{listing}\n\n"
        "   Your job for step 1 is to LOCATE each of these in the source and pin its\n"
        "   line range. Every rule below about merging, splitting, dropping or\n"
        "   re-drawing chapter boundaries is SUSPENDED and must not be applied to the\n"
        "   chapter set:\n"
        f"   - Emit EXACTLY {len(titles)} `source_chapters[]` entries, in this order.\n"
        "   - `source_title` must be the title above, character for character. Do not\n"
        "     retitle, reword, expand or shorten it.\n"
        "   - Do NOT merge two of these into one entry, do NOT split one into two, and\n"
        "     do NOT add a chapter that is not on the list.\n"
        "   - A recording is NOT one chapter. One sitting may cover several of these,\n"
        "     and one of these may span two recordings; follow the teaching, not the\n"
        "     file boundary.\n"
        "   - If the source genuinely never reaches one of these chapters, still emit\n"
        "     its entry with `start_line` and `end_line` both null and say so in\n"
        "     `split_reason`. Never silently drop it, and never pad it with text that\n"
        "     belongs to its neighbours.\n"
        "   The steps below still apply to everything EXCEPT which chapters exist:\n"
        "   line ranges, word counts, topics, and how each chapter divides into\n"
        "   episodes.\n\n"
    )


def _supplied_chapter_violations(source_chapters, titles) -> list[str]:
    """Where the returned plan disagrees with the supplied chapter list.

    Deterministic, and the reason the prompt above can be trusted: the model is
    ASKED for these titles and the plan is CHECKED for them. Compared on the
    exact strings, in order — a plan that renames "Boasting & Arrogance" to
    "Boasting and Arrogance" has renamed a chapter of somebody's book.
    """
    if not titles:
        return []
    got = [str(sc.get("source_title") or "").strip() for sc in source_chapters]
    if len(got) != len(titles):
        out = [f"plan has {len(got)} chapters, the supplied list has {len(titles)}"]
        missing = [t for t in titles if t not in got]
        extra = [g for g in got if g not in titles]
        if missing:
            out.append("missing: " + ", ".join(missing[:8]) + ("…" if len(missing) > 8 else ""))
        if extra:
            out.append("not on the list: " + ", ".join(extra[:8]) + ("…" if len(extra) > 8 else ""))
        return out
    return [
        f"chapter {i + 1} is {g!r}, the supplied list says {t!r}" for i, (g, t) in enumerate(zip(got, titles)) if g != t
    ]


def supplied_titles_for(book_dir, log=print) -> list[str]:
    """The chapter set phase 0d must use, or ``[]``, with the log line.

    Here rather than in the caller for the DR-005 reason `_verbatim_episode`
    gives: `_chapter_design.py` is grandfathered over its line ceiling and may
    shrink but never grow, so the bookkeeping that belongs to this concern lives
    with the concern and the caller stays a single short call.

    Degrades to ``[]`` rather than raising: a book whose flags cannot be read is
    a book phase 0d should still segment the way it always has.
    """
    try:
        from _pipeline_flags import supplied_chapter_titles

        titles = supplied_chapter_titles(book_dir)
    except Exception:
        return []
    if titles:
        log(f"    chapter set supplied: {len(titles)} chapters — 0d will locate, not choose")
    return titles


def assert_plan_matches(source_chapters, titles, *, toc_path, error_cls) -> None:
    """Halt step 1 when the plan disagrees with the supplied chapter set.

    Halting is the CHEAP failure. The alternative is discovering at the end of
    the run that every chapter was authored under a heading nobody chose — which
    on this book would be twenty-four chapters of paid work to throw away.

    `error_cls` is passed in rather than imported so this module stays free of
    `_authoring._core`, which imports the phase machinery.
    """
    problems = _supplied_chapter_violations(source_chapters, titles)
    if not problems:
        return
    raise error_cls(
        phase="0d-toc",
        message="the plan does not match the supplied chapter list: " + "; ".join(problems),
        manual_fallback=(
            f"Delete `{toc_path}` and retry Phase 0d (--resume --retry-phase 0d). "
            f"If the chapter list itself is wrong, fix `chapter_list` in "
            f"_system/series-config.yaml first — the plan is held to it exactly."
        ),
    )
