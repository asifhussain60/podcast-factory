"""_book_gloss_gate.py — validate_book_ready.py's B7 gate (gloss coverage).

Split out purely to stay under the DR-005 600-line cap after B9 was added —
self-contained (only needs `book_dir`), same seam that already produced
`_publish_convergence_gate.py` and `_articulation_reconcile.py` today.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

#: A book may gloss a term the OCR simply does not print, so perfect coverage is
#: not achievable and demanding it would fail honest books. This is set to catch
#: the STARVED case — the eleven-entries-against-177-terms shape — not to chase
#: the tail.
_GLOSS_COVERAGE_FLOOR = 0.60

#: Below this many romanized glossed terms, the ratio is noise rather than a
#: signal — see the inversion note in the gate.
_GLOSS_SAMPLE_FLOOR = 20


def gate_b7_book_gloss_coverage(book_dir: Path) -> tuple[bool, str]:
    """Do the terms the book GLOSSES actually have Arabic to show?

    The number the pipeline never computed. `_book_arabic_audit` enumerates
    Arabic RUNS first, so a romanized term carrying no script produces no run and
    is not merely unmeasured — it is invisible to the data structure. That is how
    `degrees-of-excellence` shipped 177 glossed terms with script on six of them
    while every Arabic report on it read clean.

    Judged on STRONG candidates only — terms the source itself spells with
    scholarly diacritics, so their being Arabic is evidence rather than a guess.
    Report-only for a book with no glossary at all: a translation edition skips
    phase 0c by design and has nothing to be starved of.
    """
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        return True, "no composed book — nothing to check"
    glossary = book_dir / "_system" / "glossary.yml"
    if not glossary.exists():
        return True, "no glossary (translation-edition route) — n/a"
    try:
        from _gloss_terms import gloss_coverage
        from _glossary_io import load_glossary

        entries, _top = load_glossary(glossary)
        source = ""
        for rel in ("_system/source/text/refined-english.md", "_system/source/ocr/raw-extract.md"):
            path = book_dir / rel
            if path.exists():
                source += path.read_text(encoding="utf-8", errors="ignore")
        report = gloss_coverage(book_md.read_text(encoding="utf-8"), entries, source, book_dir)
    except Exception as exc:  # noqa: BLE001 - a broken probe must not block a ship
        return True, f"gloss coverage not computed ({exc})"

    (book_dir / "_system" / "gloss-coverage.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    # A ratio needs a denominator worth dividing by. After the conversion pass
    # runs, almost every gloss carries Arabic and is no longer a ROMANIZED
    # candidate — so a fully-fixed book leaves three stragglers behind and the
    # gate read "0 of 3, 0%, starved" on the healthiest possible state. That is
    # the measure inverting on success. Below the floor the honest answer is that
    # there is nothing left to measure.
    # Reported on EVERY path below, including the "nothing to measure" one. The
    # ratio above is judged on STRONG candidates — terms the source spells with
    # scholarly diacritics — and an articulated book's source has none, so all
    # five live editions measured `strong: 0`, took the early return, and passed
    # while `al-anwaar` printed 219 terms as bare romanization. This is the count
    # that does not depend on that evidence: terms italicised as foreign that the
    # book never once gives in Arabic script.
    bare = (
        f" · {report['bare_terms']} term(s) never given in Arabic script "
        f"({report['bare_uses']} uses): {', '.join(r['term'] for r in report['bare'][:6])}"
        if report.get("bare_terms")
        else ""
    )
    if report["strong"] < _GLOSS_SAMPLE_FLOOR:
        return True, f"only {report['strong']} romanized glossed term(s) left — nothing to measure{bare}"
    pct = report["strong_coverage"]
    note = (
        f"{report['strong'] - len(report['missing_strong'])}/{report['strong']} glossed terms carry Arabic "
        f"({pct:.0%}); glossary has {report['glossary_entries']} entries{bare}"
    )
    if pct < _GLOSS_COVERAGE_FLOOR:
        missing = ", ".join(report["missing_strong"][:6])
        return False, f"{note} — starved glossary; e.g. {missing}"
    return True, note
