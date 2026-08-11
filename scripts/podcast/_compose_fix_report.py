"""What one `compose_fix` run FOUND, said on screen.

Split out of `compose_fix.py` on 2026-08-11, when the preface check pushed that
module past its line-count gate. The seam is the one the file already had: above
this line it decides what is wrong with a book and repairs what it safely can;
here it says so.

Almost nothing is written HERE, and that is the arrangement rather than an
accident. Four modules own the wording of their own findings — `_quote_cards`,
`_book_preface`, `_book_arabic_audit`, `_book_defect_fixes` — because the module
that decides what a defect IS must own the sentence describing it, or a change to
one leaves the other asserting something no longer true. What is left is the
frame: the heading, the per-chapter table, and the one line saying the book is
clean.

`FIXES` arrives as an argument rather than an import, so this module can be read
without loading the repair machinery it only names.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _book_arabic_audit import print_provenance_findings  # noqa: E402
from _book_defect_fixes import print_romanization_proposals  # noqa: E402
from _book_preface import print_preface_findings  # noqa: E402


def print_report(report: dict, proposals: list[tuple[str, str]], FIXES: dict) -> None:
    from _quote_cards import print_quote_card_findings

    print(f"\n{report['book']} — {len(report['chapters'])} chapter(s) checked")
    # FIRST, because it is the only finding about the book rather than about a
    # passage inside it. Printed by the module that owns the contract, like the
    # quote-card findings below and for the same reason.
    print_preface_findings(report)
    print_provenance_findings(report)
    # Printed by the module that owns the contract, so the wording of a rule and the
    # wording of the finding cannot drift apart.
    print_quote_card_findings(report)
    any_found = False
    for chapter in report["chapters"]:
        if not chapter["defects"]:
            continue
        any_found = True
        print(f"\n  {chapter['heading']}  ({chapter['words']} words)")
        for name, hits in chapter["defects"].items():
            mark = "repairable" if name in FIXES else "needs your judgment"
            print(f"      {name:26} {len(hits):>4}   {mark}")
            for hit in hits[:3]:
                print(f"          {str(hit[0])[:88]}")
    if not any_found:
        # "Clean" has to mean every check, not the chapter-scoped ones: a run that
        # printed the card findings above and then said "clean" would read as though it
        # had found nothing.
        if not (
            report.get("stale_provenance")
            or report.get("quote_card_rules")
            or report.get("orphaned_quote_kind")
            or report.get("preface")
        ):
            print("\n  clean — none of the eight defects in these chapters, and the book opens with a preface")
        return
    if report["repairable"]:
        print(f"\n  --fix would repair: {', '.join(report['repairable'])}")
    print_romanization_proposals(proposals)
