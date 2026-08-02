#!/usr/bin/env python3
"""harvest_gloss_terms.py — teach the glossary the vocabulary the book already teaches.

THE ROOT FIX for a book whose Arabic never reaches the page.

`build_glossary.py` derives the glossary from `_system/source/text/_phonetics.md`.
Nothing has written that file since 2026-06-08, when the windowed phonetics
extraction was retired, so for every book created since then the real generator
is the fallback: `CANONICAL_FALLBACK_TERMS`, a hard-coded list of thirty terms.
`degrees-of-excellence` matched none of them and got ZERO entries from the
automated path; its eleven were hand-typed in July to unblock a ship gate. The
result is a book that glosses 177 Arabic terms in its own prose while its
glossary knows 11, so `5a-arabic` had almost nothing to annotate.

The book itself is the missing input. A scholarly edition teaches its vocabulary
in parentheses — `the ranks (hudud)`, `governance (siyasa)` — and 181 of this
book's 188 glosses come straight from the source, so reading them back out is
recovering the source's own apparatus rather than inventing one. `_gloss_terms`
does the finding; this script decides what is NEW and files it.

WHAT THIS SCRIPT DOES NOT DO: fill in Arabic script. It writes rows with an empty
`arabic_script`, which is exactly the shape `fill_glossary_arabic.py` exists to
complete — from the book's OCR, never from a model's memory of the word. A term
whose script cannot be found stays empty and is simply never annotated.

    python3 scripts/podcast/harvest_gloss_terms.py --book-dir content/Islamic/<slug> [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _gloss_terms import gloss_candidates, normalize_term
from _glossary_io import load_glossary, save_glossary

#: Written beside the glossary so a re-compose does not re-harvest. Same idiom as
#: `_system/etymology-report.json`: the harvest is cheap, but `fill_glossary_arabic`
#: downstream re-reads a 400 KB OCR per batch and is not.
MARKER = "gloss-harvest.json"


def read_source(book_dir: Path) -> str:
    """The source text, for the diacritic evidence that marks a candidate strong."""
    out: list[str] = []
    for rel in (
        "_system/source/text/refined-english.md",
        "_system/source/ocr/raw-extract.md",
    ):
        path = book_dir / rel
        if path.exists():
            out.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(out)


def harvest(book_dir: Path) -> dict:
    """Find glossed terms the glossary does not know. Returns the plan; writes nothing."""
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        return {"error": f"no composed book at {book_md}", "new": [], "known": 0}

    entries, top = load_glossary(book_dir / "_system" / "glossary.yml")
    known = {normalize_term(e.get("phonetic") or e.get("transliteration") or "") for e in entries}
    known.discard("")

    candidates = gloss_candidates(book_md.read_text(encoding="utf-8"), read_source(book_dir))
    new = [c for c in candidates if normalize_term(c["term"]) not in known]
    return {
        "candidates": len(candidates),
        "known": len(known),
        "new": new,
        "entries": entries,
        "top": top,
    }


def apply(book_dir: Path, plan: dict) -> int:
    """Append the new terms as empty-script rows. Returns how many were added."""
    if not plan["new"]:
        return 0
    entries = list(plan["entries"])
    for c in plan["new"]:
        # `phonetic` is the ROMANIZED anchor everything downstream matches on —
        # the inline overlay, the reader, the PLS dictionary. It must be the form
        # that actually appears in the prose, so it is the gloss verbatim.
        entries.append(
            {
                "phonetic": c["term"],
                "transliteration": c["term"],
                "arabic_script": "",
                "audio_phonetic": "",
                "first_seen_snippet": c["first_seen_snippet"][:160],
                "harvested_confidence": c["confidence"],
            }
        )
    save_glossary(book_dir / "_system" / "glossary.yml", entries, plan["top"] or {"schema_version": 1})
    (book_dir / "_system" / MARKER).write_text(
        json.dumps(
            {
                "schema": "book.gloss-harvest/v1",
                "candidates": plan["candidates"],
                "added": len(plan["new"]),
                "terms": [c["term"] for c in plan["new"]],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return len(plan["new"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("--book-dir", required=True, type=Path)
    ap.add_argument("--dry-run", action="store_true", help="Report what would be added; write nothing.")
    args = ap.parse_args()

    book_dir = args.book_dir.resolve()
    plan = harvest(book_dir)
    if plan.get("error"):
        print(f"harvest: {plan['error']}", file=sys.stderr)
        return 1

    strong = [c for c in plan["new"] if c["confidence"] == "strong"]
    print(
        f"harvest: {plan['candidates']} glossed terms in the prose · "
        f"{plan['known']} already in the glossary · {len(plan['new'])} new "
        f"({len(strong)} strong, {len(plan['new']) - len(strong)} weak)"
    )
    for c in plan["new"][:400]:
        print(f"    {c['confidence']:6s} x{c['count']:<3d} {c['term']}")

    if args.dry_run:
        print("\n(dry run — nothing written)")
        return 0
    added = apply(book_dir, plan)
    print(f"\nwrote {added} rows with empty arabic_script — run fill_glossary_arabic.py next")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
