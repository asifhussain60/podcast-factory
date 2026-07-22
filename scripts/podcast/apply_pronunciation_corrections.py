#!/usr/bin/env python3
"""Apply pronunciation-probe corrections — writes both brains + per-book artifacts.

Ingests a corrections payload (from the /pronunciation view, or a hand-filled
JSON) and propagates each decision so it is never re-made:

  - status "ok"        -> library entry: confirmed @ the intended phonetic
  - status "respell"   -> library entry: confirmed @ the corrected phonetic;
                          the book's _phonetics.md + glossary.yml are updated
  - status "unfixable" -> library entry: unfixable @ gloss; cells annotated
  - status "skip"/none -> ignored

The cross-book library (pronunciation_ledger) means every FUTURE Arabic book
inherits these; the pattern layer (pronunciation_patterns) already pre-fills
unseen same-pattern words so they arrive as confirmable suggestions.

Payload schema:
  {
    "book_slug": "<slug>",
    "confirmed_date": "YYYY-MM-DD",          # optional; CLI defaults to today
    "corrections": [
      {"term": "...", "transliteration": "...", "status": "ok",
       "phonetic": "al-gha-zaa-lee"},
      {"term": "...", "status": "respell", "phonetic": "DAH-wa"},
      {"term": "...", "status": "unfixable", "gloss": "the elite group",
       "mangled_variants": ["al gazali", ...]}
    ]
  }

Usage:
  apply_pronunciation_corrections.py <book_dir> <corrections.json>
  apply_pronunciation_corrections.py <book_dir> -   # read payload from stdin
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

_SCRIPTS_PODCAST = Path(__file__).resolve().parent
if str(_SCRIPTS_PODCAST) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_PODCAST))

from knowledge import pronunciation_ledger as ledger


def _update_phonetics_md(book_dir: Path, term_to_phonetic: dict[str, str]) -> int:
    """Replace the phonetic cell (col 3) for matched terms, in place. Returns count."""
    path = book_dir / "_system" / "source" / "text" / "_phonetics.md"
    if not path.exists():
        return 0
    norm_map = {ledger.normalize_key(k): v for k, v in term_to_phonetic.items()}
    out_lines: list[str] = []
    changed = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and not set(stripped) <= {"|", "-", ":", " "}:
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if len(cells) >= 3 and cells[0].lower() != "term":
                key = ledger.normalize_key(cells[0])
                if key in norm_map and cells[2] != norm_map[key]:
                    cells[2] = norm_map[key]
                    changed += 1
                    out_lines.append("| " + " | ".join(cells) + " |")
                    continue
        out_lines.append(line)
    if changed:
        path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return changed


def _update_glossary_yaml(book_dir: Path, term_to_phonetic: dict[str, str]) -> int:
    """Update audio_phonetic for matched glossary entries. Best-effort YAML edit.

    Edits the ``audio_phonetic:`` line that follows a matching ``phonetic:`` or
    ``transliteration:`` line, preserving formatting (no full YAML round-trip).
    """
    path = book_dir / "_system" / "glossary.yml"
    if not path.exists():
        return 0
    norm_map = {ledger.normalize_key(k): v for k, v in term_to_phonetic.items()}
    lines = path.read_text(encoding="utf-8").splitlines()
    changed = 0
    pending_key: str | None = None
    for i, line in enumerate(lines):
        m = re.match(r"\s*(phonetic|transliteration):\s*\"?(.*?)\"?\s*$", line)
        if m:
            pending_key = ledger.normalize_key(m.group(2))
            continue
        a = re.match(r"(\s*audio_phonetic:\s*)\"?(.*?)\"?\s*$", line)
        if a and pending_key in norm_map:
            new = norm_map[pending_key]
            if a.group(2) != new:
                lines[i] = f'{a.group(1)}"{new}"'
                changed += 1
            pending_key = None
    if changed:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return changed


def _seed_mangle_map(book_dir: Path, term_variants: dict[str, list[str]]) -> int:
    """Append heard misreadings to the book's mangle-map (pre-seed for 0g audit)."""
    variants = {k: v for k, v in term_variants.items() if v}
    if not variants:
        return 0
    path = book_dir / "_system" / "mangle-map.md"
    existing = (
        path.read_text(encoding="utf-8")
        if path.exists()
        else (
            "# Mangle-map — canonical term -> TTS misreadings heard in NotebookLM audio.\n\n"
            "| Canonical | Mangled forms (CSV) |\n|---|---|\n"
        )
    )
    lines = existing.rstrip().splitlines()
    have = {
        ledger.normalize_key(row.split("|")[1])
        for row in lines
        if row.strip().startswith("|") and "Canonical" not in row and len(row.split("|")) > 1
    }
    added = 0
    for term, vs in variants.items():
        if ledger.normalize_key(term) in have:
            continue
        lines.append(f"| {term} | {', '.join(sorted(set(vs)))} |")
        added += 1
    if added:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return added


def apply_corrections(book_dir: Path, payload: dict, *, confirmed_date: str | None = None) -> dict:
    book_slug = payload.get("book_slug") or book_dir.name
    cdate = confirmed_date or payload.get("confirmed_date") or date.today().isoformat()
    corrections = payload.get("corrections", [])

    lib = ledger.load()
    phonetic_updates: dict[str, str] = {}  # term -> phonetic (for _phonetics.md / glossary)
    variant_updates: dict[str, list[str]] = {}
    counts = {"confirmed": 0, "respelled": 0, "unfixable": 0, "skipped": 0}

    for c in corrections:
        term = (c.get("term") or "").strip()
        if not term:
            counts["skipped"] += 1
            continue
        status = (c.get("status") or "").strip().lower()
        translit = c.get("transliteration", "")
        variants = c.get("mangled_variants", []) or []
        if variants:
            variant_updates[term] = variants

        if status == "ok":
            phon = (c.get("phonetic") or "").strip()
            if not phon:
                counts["skipped"] += 1
                continue
            lib.record(
                term,
                phon,
                status="confirmed",
                transliteration=translit,
                arabic_script=c.get("arabic_script", ""),
                mangled_variants=variants,
                source_book=book_slug,
                confirmed_date=cdate,
            )
            counts["confirmed"] += 1
        elif status == "respell":
            phon = (c.get("phonetic") or "").strip()
            if not phon:
                counts["skipped"] += 1
                continue
            lib.record(
                term,
                phon,
                status="confirmed",
                transliteration=translit,
                arabic_script=c.get("arabic_script", ""),
                mangled_variants=variants,
                source_book=book_slug,
                confirmed_date=cdate,
            )
            phonetic_updates[term] = phon
            counts["respelled"] += 1
        elif status == "unfixable":
            gloss = (c.get("gloss") or "").strip()
            if not gloss:
                counts["skipped"] += 1
                continue
            lib.record(
                term,
                "",
                status="unfixable",
                gloss=gloss,
                transliteration=translit,
                mangled_variants=variants,
                source_book=book_slug,
                confirmed_date=cdate,
            )
            counts["unfixable"] += 1
        else:
            counts["skipped"] += 1

    lib.save()
    md_changed = _update_phonetics_md(book_dir, phonetic_updates)
    gloss_changed = _update_glossary_yaml(book_dir, phonetic_updates)
    mangle_added = _seed_mangle_map(book_dir, variant_updates)

    return {
        "book_slug": book_slug,
        "confirmed_date": cdate,
        "counts": counts,
        "library_size": len(lib),
        "phonetics_md_updated": md_changed,
        "glossary_updated": gloss_changed,
        "mangle_map_added": mangle_added,
    }


def _load_payload(arg: str) -> dict:
    if arg == "-":
        return json.loads(sys.stdin.read())
    return json.loads(Path(arg).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Apply pronunciation-probe corrections.")
    ap.add_argument("book_dir", type=Path, help="content/<Bucket>/<slug>/")
    ap.add_argument("payload", help="corrections JSON file, or '-' for stdin")
    ap.add_argument("--date", default=None, help="confirmed_date (YYYY-MM-DD); default today")
    args = ap.parse_args(argv)

    payload = _load_payload(args.payload)
    result = apply_corrections(args.book_dir, payload, confirmed_date=args.date)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
