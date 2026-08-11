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
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from _book_edits import base_fingerprint_for, record_edit


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
    from vowel_book import vowel_text

    book_md = book_dir / "book" / "book.md"
    md = book_md.read_text(encoding="utf-8")
    applied: list[dict] = []
    totals = {"marked": 0, "refused": 0, "transferred": 0}

    for chapter in selection:
        start, end = section_text(md, chapter["heading"])
        section = md[start:end]
        marked, stats = vowel_text(section, log=lambda *_: None)
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
    return {"applied": applied, "chapters_changed": len(applied), **totals}
