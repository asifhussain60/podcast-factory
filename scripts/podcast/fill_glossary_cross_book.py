#!/usr/bin/env python3
"""fill_glossary_cross_book.py — borrow Arabic script another book already proved.

WHY THIS EXISTS
---------------
`fill_glossary_arabic` grounds every fill in the book's OWN Arabic scan: the
Quranic morphology corpus guides the lookup, and the winning lemma must occur as
a whole word in that book's OCR before a character is written. That guard is
load-bearing, not bureaucratic. Measured on `al-anwaar-al-lateefah` (2026-08-03),
which has NO scan, a corpus-only fill resolved 31 terms "uniquely" and got at
least six of the first fourteen wrong: `maratib` -> مرتاب (should be مراتب),
`martaba` -> مرتاب, `musabbah` -> مصباح ("lamp" for "glorifier"), `hayula` ->
حيلة, `ghayatuhu` -> غيث, `al-ilahiyyah` -> لاهية. Latin consonants fold
ambiguously (s -> س/ص/ث, h -> ه/ح/خ) and without the book's own pages to check
against, "unique in the corpus" is not "right for this book".

So a book with no scan cannot be filled from the corpus. It CAN be filled from
another book that does have one: `hudud`, `tawhid`, `zahir`, `tawil` are shared
vocabulary, and their script in `degrees-of-excellence` or `asaas-al-taveel` was
grounded in a real Azure OCR of a real page. That is a genuine provenance step
down — a different book's scan, not this one's — so every fill records where it
came from in `_system/glossary-cross-fill.json`, and the term is matched on the
FULL normalized phonetic, never on a fold. Same romanization, same word.

What it will NOT do is guess. A term no other book carries is left empty and
reported, which on `al-anwaar` is most of them — that book needs its Arabic
scanned, and this script says so rather than papering over it.

    python3 scripts/podcast/fill_glossary_cross_book.py <slug> [--dry-run]
    python3 scripts/podcast/fill_glossary_cross_book.py --all [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _gloss_terms import normalize_term  # noqa: E402
from _glossary_io import load_glossary  # noqa: E402
from _paths import iter_content  # noqa: E402

RECORD_NAME = "glossary-cross-fill.json"
SCHEMA = "book.glossary-cross-fill/v1"


def _glossary_path(book_dir: Path) -> Path:
    return Path(book_dir) / "_system" / "glossary.yml"


#: Below this many Arabic runs a "scan" is not a scan. `text/raw-extract.md` is
#: the ENGLISH extract and carries zero; `kunooz-al-hikmah` carries seven, which
#: is stray characters rather than ground truth. The books that really have one
#: carry six to sixty-eight THOUSAND, so no threshold in between is delicate.
_SCAN_FLOOR = 200

_ARABIC_RUN = re.compile(r"[؀-ۿ]{2,}")


def _has_own_scan(book_dir: Path) -> bool:
    """Does this book have ARABIC ground truth of its own?

    Checking that a `raw-extract.md` EXISTS is not the same question, and getting
    it wrong is a provenance hole rather than a cosmetic bug: `text/raw-extract.md`
    is the English extract, so `kitab-al-riyad` — which has no Arabic anywhere —
    was admitted to the pool and lent spellings to `al-anwaar` as though they had
    been read off a page. A book may only contribute what its own scan proves.
    """
    runs = 0
    for rel in ("_system/source/ocr/raw-extract.md", "_system/source/text/raw-extract.md"):
        path = Path(book_dir) / rel
        if path.exists():
            runs += len(_ARABIC_RUN.findall(path.read_text(encoding="utf-8", errors="ignore")))
    return runs >= _SCAN_FLOOR


def build_pool(book_dirs: list[Path]) -> dict[str, tuple[str, str]]:
    """``{normalized phonetic: (script, source slug)}`` from every book with a scan.

    Only books that HAVE their own Arabic ground truth contribute. A book filled
    by this script must never become a source for the next one, or one unverified
    spelling would propagate across the library as though it were evidence.
    """
    pool: dict[str, tuple[str, str]] = {}
    for bd in book_dirs:
        if not _has_own_scan(bd) or not _glossary_path(bd).exists():
            continue
        slug = bd.name if bd.name.startswith("vol-") is False else f"{bd.parent.name}/{bd.name}"
        for entry in load_glossary(_glossary_path(bd))[0]:
            key = normalize_term(entry.get("phonetic") or "")
            script = str(entry.get("arabic_script") or "").strip()
            if key and script:
                pool.setdefault(key, (script, slug))
    return pool


def plan(book_dir: Path, pool: dict[str, tuple[str, str]]) -> dict[str, Any]:
    book_dir = Path(book_dir)
    entries = load_glossary(_glossary_path(book_dir))[0] if _glossary_path(book_dir).exists() else []
    empty = [e for e in entries if not str(e.get("arabic_script") or "").strip()]
    fills, missing = [], []
    for entry in empty:
        phonetic = str(entry.get("phonetic") or "").strip()
        hit = pool.get(normalize_term(phonetic))
        # Never borrow from a book's own pool entry — that is a no-op that would
        # look like a fill in the record.
        if hit and hit[1] != book_dir.name:
            fills.append({"phonetic": phonetic, "arabic_script": hit[0], "from": hit[1]})
        elif phonetic:
            missing.append(phonetic)
    return {"entries": len(entries), "empty": len(empty), "fills": fills, "missing": missing}


def apply(book_dir: Path, plan_: dict[str, Any]) -> int:
    import yaml

    path = _glossary_path(Path(book_dir))
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    by_phonetic = {str(f["phonetic"]): f for f in plan_["fills"]}
    n = 0
    for entry in data.get("entries") or []:
        hit = by_phonetic.get(str(entry.get("phonetic") or "").strip())
        if hit and not str(entry.get("arabic_script") or "").strip():
            entry["arabic_script"] = hit["arabic_script"]
            entry["script_source"] = f"cross-book:{hit['from']}"
            n += 1
    if n:
        path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        record = Path(book_dir) / "_system" / RECORD_NAME
        record.write_text(
            json.dumps(
                {"schema": SCHEMA, "filled": plan_["fills"], "still_empty": plan_["missing"]},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return n


def _book_dirs() -> list[Path]:
    out: list[Path] = []
    for row in iter_content():
        book_dir = row[2] if isinstance(row, tuple) else row
        if _glossary_path(Path(book_dir)).exists():
            out.append(Path(book_dir))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug", nargs="?", default="")
    ap.add_argument("--all", action="store_true", help="every book with a glossary")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    everything = _book_dirs()
    pool = build_pool(everything)
    print(f"cross-book pool: {len(pool)} term(s) with scan-grounded script", file=sys.stderr)

    if args.all:
        targets = everything
    else:
        from _paths import find_content

        found = find_content(args.slug)
        if not found:
            print(f"book not found: {args.slug}", file=sys.stderr)
            return 2
        targets = [found[2]]

    total = 0
    for book_dir in targets:
        p = plan(book_dir, pool)
        if not p["empty"]:
            continue
        n = 0 if args.dry_run else apply(book_dir, p)
        total += n or len(p["fills"])
        print(
            f"  {book_dir.name:26s} {p['empty']:4d} empty · {len(p['fills']):4d} fillable"
            f"{'' if args.dry_run else f' · {n} written'} · {len(p['missing'])} still need a scan",
            file=sys.stderr,
        )
    if args.dry_run:
        print("--- dry run: nothing written ---", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
