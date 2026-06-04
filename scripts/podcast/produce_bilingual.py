#!/usr/bin/env python3
"""produce_bilingual.py — WC8-bilingual: per-chapter bilingual content bake.

Produces _stages/<ch>/bilingual.json, which powers the Studio Arabic toggle
beyond glossary terms. Three sources:

  1. QURAN VERSES — pulled from KQUR by surah:ayah reference (canonical Arabic
     with full diacritics). References come from knowledge-report.json (verified
     citations). Uses source_library_queries.quran_lookup() → mirror or SQL Server.

  2. HADITH — matched via KQUR Ahadees table (fts_hadith FTS5 mirror).
     English text description from knowledge-report.json used as the search key.
     Returns Arabic when matched; leaves status="pending_match" when not.
     NOTE: fts_hadith requires the mirror to be built after confirming Ahadees
     column names via discover_hadith_schema(). Run source_library_mirror.py first.

  3. FULL CHAPTER ARABIC TEXT — extracted from the Arabic OCR file at
     _system/source/multi/ocr/arabic.md, using the line range recorded in
     reconcile-report.json ("arabic-original" spine). This covers all remaining
     Arabic content: hadith prose, poems, closing du'as, author's own words.

Schema: _stages/<ch>/bilingual.json
{
  "slug":                  "ayyuhal-walad",
  "chapter":               "ch01-frame-and-first-counsel",
  "arabic_source_lines":   "13-191",
  "arabic_chapter_text":   "...",   # full Arabic OCR extract
  "quran_verses":  [{ "ref", "surah", "arabic", "phonetic", "confidence", "source" }],
  "hadith":        [{ "text_en", "arabic", "collection", "hadith_num", "confidence", "status" }]
}

USAGE
    python3 scripts/podcast/produce_bilingual.py --slug ayyuhal-walad --chapter ch01-frame-and-first-counsel
    python3 scripts/podcast/produce_bilingual.py --slug ayyuhal-walad --all
    python3 scripts/podcast/produce_bilingual.py --slug ayyuhal-walad --chapter ch01-... --force
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR.parents[1]))  # repo root for tools.*

from _paths import REPO_ROOT, content_dir  # noqa: E402


# ---------------------------------------------------------------------------
# Arabic OCR extraction
# ---------------------------------------------------------------------------

def _parse_line_range(spec: str) -> tuple[int, int] | None:
    """Parse 'lines 13-191' or '13-191' into (start, end) inclusive."""
    m = re.search(r"(\d+)[–\-](\d+)", spec)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def extract_arabic_chapter(book: Path, reconcile: dict) -> tuple[str, str]:
    """Return (arabic_text, line_range_spec) for the chapter's Arabic OCR span.

    Reads _system/source/multi/ocr/arabic.md and slices it using the line range
    stored in reconcile-report.json under the 'spine' field.
    """
    arabic_ocr = book / "_system" / "source" / "multi" / "ocr" / "arabic.md"
    if not arabic_ocr.exists():
        return "", ""

    spine_note = reconcile.get("spine", "")
    line_range = _parse_line_range(spine_note)
    lines = arabic_ocr.read_text(encoding="utf-8").splitlines()

    if line_range:
        start, end = line_range
        # Lines in the spec are 1-indexed, list is 0-indexed
        chunk = lines[max(0, start - 1): end]
    else:
        # No line range — return full file (fallback for chapters without reconcile)
        chunk = lines

    text = "\n".join(chunk).strip()
    range_spec = f"{line_range[0]}-{line_range[1]}" if line_range else "full"
    return text, range_spec


# ---------------------------------------------------------------------------
# Quran verse lookup
# ---------------------------------------------------------------------------

def lookup_quran_verses(quran_refs: list[dict]) -> list[dict]:
    """Look up Arabic text for each verified Quran citation via KQUR.

    Falls back gracefully if the source library is unavailable.
    """
    try:
        from scripts.podcast.source_library_queries import quran_lookup  # noqa: PLC0415
    except ImportError:
        print("[bilingual] source_library_queries not importable — Quran lookup skipped")
        return [
            {"ref": r["key"], "surah": r.get("surah", ""), "arabic": None,
             "phonetic": None, "confidence": 0.0, "status": "import_error", "source": "kqur"}
            for r in quran_refs
        ]

    results = []
    for ref in quran_refs:
        key = ref.get("key", "")
        parts = key.split(":")
        if len(parts) != 2:
            continue
        try:
            surah_n, ayat_n = int(parts[0]), int(parts[1])
        except ValueError:
            continue

        try:
            row = quran_lookup(surah_n, ayat_n)
        except Exception as exc:
            row = {"error": str(exc)}

        if "error" in row:
            results.append({
                "ref": key, "surah": ref.get("surah", ""),
                "arabic": None, "phonetic": None,
                "confidence": 0.0, "status": "lookup_failed", "source": "kqur",
                "error": row["error"],
            })
        else:
            results.append({
                "ref": key,
                "surah": ref.get("surah", row.get("surah", "")),
                "arabic": row.get("arabic", ""),
                "phonetic": row.get("phonetic", ""),
                "confidence": 1.0,
                "status": "verified",
                "source": "kqur",
            })
    return results


# ---------------------------------------------------------------------------
# Hadith lookup
# ---------------------------------------------------------------------------

def lookup_hadith(hadith_refs: list[str]) -> list[dict]:
    """Try to match each hadith text description to a KQUR Ahadees entry.

    Returns Arabic text when matched; status='pending_match' when not.
    Fail-safe: if the mirror is not built yet, returns all as pending.
    """
    try:
        from scripts.podcast.source_library_queries import hadith_lookup  # noqa: PLC0415
    except ImportError:
        return [
            {"text_en": h, "arabic": None, "collection": None, "hadith_num": None,
             "confidence": 0.0, "status": "import_error"}
            for h in hadith_refs
        ]

    results = []
    for text_en in hadith_refs:
        try:
            matches = hadith_lookup(text_en, limit=1)
        except Exception:
            matches = []

        if matches:
            m = matches[0]
            results.append({
                "text_en": text_en,
                "arabic": m.get("arabic") or None,
                "collection": m.get("collection") or None,
                "hadith_num": m.get("hadith_num") or None,
                "confidence": m.get("score", 0.7),
                "status": "matched" if m.get("arabic") else "matched_no_arabic",
                "source": m.get("source", "kqur"),
            })
        else:
            results.append({
                "text_en": text_en,
                "arabic": None,
                "collection": None,
                "hadith_num": None,
                "confidence": 0.0,
                "status": "pending_match",
            })
    return results


# ---------------------------------------------------------------------------
# Main bake
# ---------------------------------------------------------------------------

def bake_chapter(slug: str, chapter: str, *, force: bool = False) -> Path:
    """Produce bilingual.json for one chapter. Returns the output path."""
    book = content_dir(slug)
    stage_dir = book / "_stages" / chapter
    out = stage_dir / "bilingual.json"

    if out.exists() and not force:
        print(f"[skip] {out.relative_to(REPO_ROOT)} already exists — use --force to rebuild.")
        return out

    # Load reconcile report
    reconcile_path = stage_dir / "reconcile-report.json"
    reconcile: dict = {}
    if reconcile_path.exists():
        try:
            reconcile = json.loads(reconcile_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    # Load knowledge report for Quran + hadith refs
    knowledge_path = stage_dir / "knowledge-report.json"
    knowledge: dict = {}
    if knowledge_path.exists():
        try:
            knowledge = json.loads(knowledge_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    # quran_refs may be a list of dicts ({"key":"18:11","status":"verified",...})
    # or a list of plain strings ("79:40") — normalize both to the dict form.
    raw_quran = knowledge.get("quran_refs", [])
    quran_refs = []
    for r in raw_quran:
        if isinstance(r, dict):
            if r.get("status") == "verified":
                quran_refs.append(r)
        elif isinstance(r, str) and re.match(r"^\d+:\d+$", r.strip()):
            quran_refs.append({"key": r.strip(), "surah": "", "status": "verified"})

    # hadith_refs may be strings or dicts — normalize to list of strings
    raw_hadith = knowledge.get("hadith_refs", [])
    hadith_refs = [
        h if isinstance(h, str) else h.get("text", str(h))
        for h in raw_hadith
    ]

    # 1. Full Arabic chapter text from OCR
    arabic_text, arabic_lines = extract_arabic_chapter(book, reconcile)

    # 2. Quran verse Arabic text from KQUR
    quran_verses = lookup_quran_verses(quran_refs)
    verified = sum(1 for v in quran_verses if v.get("status") == "verified")
    print(f"[quran] {verified}/{len(quran_refs)} verses resolved from KQUR")

    # 3. Hadith Arabic text from KQUR Ahadees
    hadith_results = lookup_hadith(hadith_refs)
    matched = sum(1 for h in hadith_results if h.get("status") == "matched")
    print(f"[hadith] {matched}/{len(hadith_refs)} hadith matched in KQUR")

    payload = {
        "slug": slug,
        "chapter": chapter,
        "arabic_source_lines": arabic_lines,
        "arabic_chapter_text": arabic_text,
        "quran_verses": quran_verses,
        "hadith": hadith_results,
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[done] {out.relative_to(REPO_ROOT)}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Produce bilingual.json per chapter")
    ap.add_argument("--slug", required=True)
    ap.add_argument("--chapter", help="single chapter slug (e.g. ch01-frame-and-first-counsel)")
    ap.add_argument("--all", action="store_true", help="process every chapter with a stage dir")
    ap.add_argument("--force", action="store_true", help="overwrite existing bilingual.json")
    ap.add_argument("--discover-hadith-schema", action="store_true",
                    help="print Ahadees column names from KQUR and exit (run before first build)")
    a = ap.parse_args()

    if a.discover_hadith_schema:
        from scripts.podcast.source_library_queries import discover_hadith_schema  # noqa: PLC0415
        cols = discover_hadith_schema()
        print("If any column name differs from the guesses in source_library_mirror._SQL_HADITH,")
        print("update the aliases there and rebuild the mirror.")
        return 0

    if not a.chapter and not a.all:
        ap.error("specify --chapter <slug> or --all")

    book = content_dir(a.slug)
    if a.all:
        stage_root = book / "_stages"
        if not stage_root.is_dir():
            print(f"No _stages directory for {a.slug}")
            return 1
        chapters = sorted(
            d.name for d in stage_root.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )
        print(f"[batch] {len(chapters)} chapters")
        for ch in chapters:
            bake_chapter(a.slug, ch, force=a.force)
    else:
        bake_chapter(a.slug, a.chapter, force=a.force)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
