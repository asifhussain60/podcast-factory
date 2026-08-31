"""_book_typography.py — the compose apparatus's TYPOGRAPHIC pair.

Two steps that read the finished `book/book.md` and change how it is SET, never
what it says (2026-08-31, when the DR-005 line cap forced a split and these two
were the coherent seam — `_book_apparatus` was at 594 of its 600 lines, so the
next step of any kind was going to breach it):

  spelling   one spelling standard for the whole edition
  opening    every chapter begins with a capital letter

Both are deterministic, whole-book, idempotent, model-free and cost nothing. Both
are PAGE_ALTERING in `_compose_skips` — losing either shows on the page, as a book
that spells "honour" in one chapter and "honor" in the next, or a chapter whose
drop cap is lowercase.

WHY THEY RUN LATE, AND IN THIS ORDER. Each needs the FINAL wording: every earlier
pass may still rewrite prose, and a spelling standard applied before the last
rewrite is a standard applied to text nobody ships. `opening` follows `spelling`
for the same reason and one more — spelling can change the first word of a
chapter, and the capital belongs on the word that survives.

They keep their exact position in the sequence: after `arabic-substitution`,
before the report-only tail in `_book_reports`.
"""

from __future__ import annotations

from pathlib import Path

from _apparatus_steps import record_ok as _ok
from _compose_skips import record_skip as _record_skip


def run_typography_steps(book_dir: Path, *, log=print) -> None:
    """Run both typographic steps, each isolated behind its own recorder.

    Recorders are IMPORTED, exactly as `_book_reports` imports them, and not
    passed in. The pins that keep the step catalog honest find each step by
    grepping these modules for its recorded skip call, so a call made through a
    renamed parameter would hide both steps from the very checks that exist to
    notice a step going missing — the failure the 2026-08-08 extraction caused
    once already.
    """
    # 5a-spelling. The drafting and re-voicing models have no consistent
    #     preference, so without this a single book ships both forms. Whole-word,
    #     skips fenced blocks; source records under _system/source/ are never in
    #     scope — this only touches book.md, prose the pipeline itself authored.
    from _american_spelling import to_american

    try:
        md = book_dir / "book" / "book.md"
        if md.exists():
            before = md.read_text(encoding="utf-8")
            after = to_american(before)
            if after != before:
                md.write_text(after, encoding="utf-8")
                log("    spelling: normalized to American forms")
        _ok(book_dir, "spelling")
    except Exception as e:  # a spelling pass is never worth a finished book
        _record_skip(book_dir, "spelling", e, log)

    # 5a-opening. One letter, first paragraph. A chapter opening on a FRAGMENT is
    #     reported rather than disguised — see _chapter_opening.py for why it was
    #     ever lowercase and what the rule refuses to do.
    from _chapter_opening import apply_chapter_openings

    try:
        apply_chapter_openings(book_dir, log=log)
        _ok(book_dir, "opening")
    except Exception as e:  # a capital letter is never worth a finished book
        _record_skip(book_dir, "opening", e, log)
