"""_compose_fix_vowel.py — putting the vowel marks on a finished book's bare Arabic.

Asif does not read Arabic, so an unvowelled run is not "unverified" to him, it is
unreadable (the rule locked 2026-07-29). The compose-time pass marks a book as it is
built; this is the same work asked for AFTER the fact, on chosen chapters of a book that
is already composed, so a passage that reached the page bare can be repaired without
re-composing the chapter around it.

Split out of `compose_fix` on 2026-08-11 when that module crossed the DR-005 line cap —
the same move `_compose_skips` made out of `validate_book_ready` on 2026-08-02. It is a
clean seam rather than an arbitrary cut: this is the one repair in that tool which SPENDS
MONEY, and keeping it behind its own import is what makes "plain `--fix` never reaches
for a model" a property of the file layout rather than of a reader's memory.

AND BECAUSE IT SPENDS MONEY, IT SAYS SO (fixed 2026-08-11, F-MET1)

Until that date it did not. It called `vowel_book.vowel_text` and skipped
`vowel_book.record_spend`, which sits one import away and exists because the identical
omission had already been fixed once on the whole-book path — so a pass making metered
Gemini calls was missing from `cost-ledger.jsonl` and `model-provenance.jsonl` both, and
wrote no `book-vowelling.json`. Love Of The Prophet was vowelled this way and there is
no record anywhere of what that cost or what it refused.

One instance of the same gap is still open and is NOT here: the Book Composer's
Diacritics button is a separate TypeScript implementation in
`plan-dashboard/src/pages/api/studio/vowelling.ts` calling Gemini directly, and there is
no ledger writer on that side to call. Recorded as the second half of F-MET1.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from _book_edits import anchor_key, base_fingerprint_for, record_edit

# The numeric half of a `vowel_text` run's stats. Named here so the accumulation
# below sums exactly what the engine counts and silently invents nothing when the
# engine grows a counter.
_COUNTERS = (
    "vowelled",
    "marks_added",
    "already",
    "quranic",
    "from_mushaf",
    "refused",
    "recovered",
    "transferred",
    "in_chars",
    "out_chars",
)


def vowel_chapters(
    book_dir: Path,
    selection: list[dict],
    *,
    section_text,
    log=print,
) -> dict:
    """Put the vowel marks on the selected chapters' bare Arabic.

    Its own function rather than an entry in `FIXES`, for the reason
    `resolve_romanizations` is: it needs a model, and plain `--fix` must never
    reach for one. Same engine the pipeline runs at compose time
    (`vowel_book.vowel_text`), so a passage marked here and the same passage
    marked by a compose come out the same way.

    IT DOES NOT SEARCH THE SOURCE, and that is the instruction rather than an
    omission (Asif, 2026-08-11). The romanization repair in `compose_fix` hunts
    the scan, the OCR and the knowledge base for a spelling somebody already
    wrote; a vocalisation is not written down anywhere to be found. It is asked
    for, from a model told to read the passage as the Ismaili tradition reads it,
    under a gate that admits a change of MARKS and nothing else. Scripture is the
    one exception and it is not asked at all: `_mushaf` answers a Qur'anic run out
    of the canonical text in the repo.

    Each repaired chapter is recorded as a Composer edit like every other repair
    there, so the marks survive the next compose and the chapter is not
    regenerated over them.

    `section_text` is passed in rather than imported: it is `compose_fix`'s own
    chapter-slicing rule, and one definition of where a chapter starts and ends is
    the thing that keeps the slice this writes back into identical to the slice
    every other repair reads.
    """
    from vowel_book import record_spend, vowel_text

    book_md = book_dir / "book" / "book.md"
    md = book_md.read_text(encoding="utf-8")
    applied: list[dict] = []
    totals = {"marked": 0, "refused": 0, "transferred": 0}
    # What this run did across every chapter it touched, for the same report
    # `vowel_book` writes on the whole-book path. `scope` names the chapters, and
    # it is the difference between the two writers: a file with no `scope` covers
    # the whole book, a file with one covers exactly the chapters it lists.
    run: dict = {"scope": [], "refusals": [], **{key: 0 for key in _COUNTERS}}

    for chapter in selection:
        start, end = section_text(md, chapter["heading"])
        section = md[start:end]
        marked, stats = vowel_text(section, log=lambda *_: None)

        # The ledgers first, and UNCONDITIONALLY — before the no-change check
        # below. The model has already answered by this point, so the spend is
        # real whether or not a single mark reached the page, and a chapter the
        # gate refused outright is the one whose refusals a person most needs to
        # read. Recording after the check is how this pass came to be invisible
        # in both ledgers while `record_spend` sat one import away.
        # The step NAMES the chapter, and `number` is None whenever the heading
        # carries no ordinal — which is every chapter of Love Of The Prophet, the
        # very book whose unrecorded spend this ledger was added for. Formatting
        # None with `:02d` raises, so the pass that had merely been invisible
        # became one that crashed outright on the first book it was pointed at.
        #
        # The anchor key is the fallback rather than a running index: it is the
        # identifier the whole Composer path already addresses a chapter by, so a
        # ledger row can still be matched to a chapter after a re-compose moves it.
        step = (
            f"vowel/{chapter['number']:02d}"
            if chapter["number"] is not None
            else f"vowel/{anchor_key(chapter['heading'])}"
        )
        record_spend(book_dir, phase="compose-fix", step=step, stats=stats)
        run["scope"].append(chapter["heading"])
        run["refusals"].extend(stats.get("refusals", []))
        for key in _COUNTERS:
            run[key] += stats.get(key, 0)

        if marked == section:
            continue
        md = md[:start] + marked + md[end:]
        totals["marked"] += stats.get("vowelled", 0)
        totals["refused"] += stats.get("refused", 0)
        totals["transferred"] += stats.get("transferred", 0)
        body = marked.split("\n", 1)[1].strip() if "\n" in marked else ""
        record_edit(
            book_dir,
            chapter_key=chapter["key"],
            body_md=body,
            base_fingerprint=base_fingerprint_for(book_dir, chapter["key"]),
            saved_at=datetime.now(timezone.utc).isoformat(),
        )
        applied.append(
            {
                "number": chapter["number"],
                "heading": chapter["heading"],
                "marked": stats.get("vowelled", 0),
                "refused": stats.get("refused", 0),
            }
        )
        log(f"    {chapter['heading']}: {stats.get('vowelled', 0)} run(s) marked, {stats.get('refused', 0)} refused")

    if applied:
        tmp = book_md.with_suffix(".md.tmp")
        tmp.write_text(md, encoding="utf-8")
        os.replace(tmp, book_md)

    # The refusal list is the human-facing half of this pass, exactly as it is on
    # the whole-book path — every run the gate turned away, with its reason, so a
    # passage the model cannot vowel is visible rather than quietly left bare.
    # Written even when nothing changed: a run that refused everything is the one
    # worth looking at.
    if run["scope"]:
        report = book_dir / "_system" / "book-vowelling.json"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {"applied": applied, "chapters_changed": len(applied), **totals}
