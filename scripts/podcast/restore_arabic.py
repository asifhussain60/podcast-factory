"""restore_arabic.py — restore Arabic script for audio-sourced book chapters + glossary.

Audio transcription is transliteration-only, so the reader's "Show Arabic" toggle
has no script to display. This module restores it, **cheapest-source-first**:

  1. repair_glossary  — fix the field-misassignment some audio-era glossaries carry
     (Arabic stored in `phonetic`, the Roman match-token in `transliteration`,
     `arabic_script` empty). The reader matches `phonetic` against the Roman prose,
     so Arabic-in-phonetic never matches AND the overlay is empty. Remap:
         arabic_script <- (Arabic that was in phonetic)   [if arabic_script empty]
         phonetic      <- transliteration (the Roman token in prose)
     ZERO LLM, deterministic, idempotent. Recovers already-present Arabic for free.

  2. (Step 2b — next) fill remaining empty arabic_script: canonical terms + claude -p.
  3. (Step 3 — next) restore multi-word passages (Quran canonical via
     source_library_mirror.quran_ayat_lookup; hadith/poems claude -p) as inline
     ⟪ar|translit|script⟫ markers the reader renders under the toggle.

CLI:
  python3 scripts/podcast/restore_arabic.py repair-glossary <slug> [--dry-run]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from _paths import REPO_ROOT, content_dir, find_content  # noqa: E402

import yaml  # noqa: E402

# Arabic + Arabic-Supplement + Arabic Extended + presentation forms.
_ARABIC_RE = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")


def _has_arabic(s: str | None) -> bool:
    return bool(s) and bool(_ARABIC_RE.search(s))


def _resolve_book_dir(slug: str) -> Path | None:
    hit = find_content(slug)
    if hit:
        return hit[2]
    cand = content_dir(slug)
    return cand if cand.exists() else None


def repair_glossary(book_dir: Path, *, dry_run: bool = False) -> dict[str, int]:
    """Repair field-misassignment in glossary.yml. Returns counts.

    For each entry where `phonetic` holds Arabic script and `transliteration` is a
    Roman token: move the Arabic into `arabic_script` (only if empty) and set
    `phonetic` to the Roman token so the reader's match works. Correctly-shaped
    entries (phonetic already Roman) are left untouched.
    """
    gpath = book_dir / "_system" / "glossary.yml"
    if not gpath.is_file():
        return {"error_no_glossary": 1}

    data = yaml.safe_load(gpath.read_text(encoding="utf-8")) or {}
    entries = data.get("entries") or []
    if not isinstance(entries, list):
        return {"error_bad_schema": 1}

    remapped_script = 0   # arabic_script newly filled from phonetic
    fixed_phonetic = 0    # phonetic match-token corrected to Roman
    skipped_ok = 0        # already correctly shaped

    for e in entries:
        if not isinstance(e, dict):
            continue
        phon = e.get("phonetic") or ""
        translit = e.get("transliteration") or ""
        script = (e.get("arabic_script") or "").strip()

        misassigned = _has_arabic(phon) and translit and not _has_arabic(translit)
        if not misassigned:
            skipped_ok += 1
            continue
        # Recover the Arabic into arabic_script if it isn't already filled.
        if not script:
            e["arabic_script"] = phon.strip()
            remapped_script += 1
        # The match-token the reader greps for in (Roman) prose must be Roman.
        e["phonetic"] = translit
        fixed_phonetic += 1

    if not dry_run and (remapped_script or fixed_phonetic):
        # atomic write
        import os
        import tempfile
        fd, tmp = tempfile.mkstemp(dir=str(gpath.parent), prefix=".glossary.", suffix=".yml.tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            yaml.safe_dump(data, fh, sort_keys=False, allow_unicode=True)
        os.replace(tmp, gpath)

    return {
        "entries": len(entries),
        "arabic_script_recovered": remapped_script,
        "phonetic_corrected": fixed_phonetic,
        "already_ok": skipped_ok,
    }


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Restore Arabic script for audio-sourced books.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    rg = sub.add_parser("repair-glossary", help="Fix field-misassignment in glossary.yml (zero LLM).")
    rg.add_argument("slug")
    rg.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    book_dir = _resolve_book_dir(args.slug)
    if not book_dir:
        print(f"restore_arabic: book not found: {args.slug}", file=sys.stderr)
        return 2

    if args.cmd == "repair-glossary":
        r = repair_glossary(book_dir, dry_run=args.dry_run)
        tag = " (dry-run)" if args.dry_run else ""
        print(f"repair-glossary {args.slug}{tag}: {r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
