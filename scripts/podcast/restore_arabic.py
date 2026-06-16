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


def enrich_quran_atoms(*, dry_run: bool = False) -> dict[str, int]:
    """Add canonical Arabic to every Quran atom in knowledge.db (Step 2b — verses).

    Quran atoms carry surah/ayah but (for audio-sourced books) no Arabic. We attach
    the EXACT canonical Arabic from the local Quran corpus — zero LLM, no guessing.
    Idempotent: atoms that already have `arabic` are skipped.
    """
    import json
    import sqlite3
    sys.path.insert(0, str(SCRIPT_DIR))
    from source_library_mirror import quran_ayat_lookup  # noqa: E402

    conn = sqlite3.connect(str(REPO_ROOT / "content" / "knowledge-base" / "knowledge.db"))
    rows = conn.execute("SELECT id, body FROM atoms WHERE type='quran'").fetchall()
    enriched = skipped = unresolved = 0
    for atom_id, raw in rows:
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            continue
        if body.get("arabic"):
            skipped += 1
            continue
        surah, ayah = body.get("surah"), body.get("ayah")
        if not surah or not ayah:
            unresolved += 1
            continue
        hit = quran_ayat_lookup(int(surah), int(ayah))
        if not hit or not hit.get("arabic"):
            unresolved += 1
            continue
        body["arabic"] = hit["arabic"].strip()
        if not dry_run:
            conn.execute(
                "UPDATE atoms SET body=?, updated_at=datetime('now') WHERE id=?",
                (json.dumps(body, ensure_ascii=False), atom_id),
            )
        enriched += 1
    if not dry_run:
        conn.commit()
    conn.close()
    return {"quran_atoms": len(rows), "enriched": enriched,
            "already_had_arabic": skipped, "unresolved": unresolved}


_QUOTE_ARABIC_PROMPT = """You are given transliterated Arabic quotations, hadith, and sayings \
extracted from Urdu/Arabic Islamic lectures (Fatimid/Ismaili tradition). For EACH item, \
provide the ARABIC SCRIPT (fully vowelled, tashkīl).

RULES (quality over coverage):
- If the text is a genuine Arabic quotation / hadith / Qur'anic phrase / saying rendered in \
Latin transliteration, return its accurate Arabic script.
- If the text is actually an ENGLISH paraphrase or translation (NOT Arabic), OR you cannot \
reliably reproduce the exact Arabic, set "arabic": null and "uncertain": true. DO NOT GUESS.
- Conservative bias: a wrong Arabic rendering is worse than none.

Return ONLY a JSON array, one object per item:
[{{"idx": <int>, "arabic": "<arabic script or null>", "uncertain": <true|false>}}]

ITEMS:
{items}
"""


def enrich_quote_atoms_arabic(*, batch_size: int = 12, model: str = "claude-sonnet-4-6",
                              limit: int | None = None, dry_run: bool = False) -> dict[str, int]:
    """Add verified-model Arabic to quote + hadith atoms via the metered Anthropic SDK
    (DR-015: NEVER claude -p in unattended code). Confident Arabic is stored on the atom;
    uncertain items are flagged to _conflicts/arabic-review.jsonl for human review — never
    silently trusted."""
    import json
    import sqlite3
    sys.path.insert(0, str(SCRIPT_DIR))
    from _secrets import get_anthropic_key  # noqa: E402
    from _tighten_helpers import extract_json  # noqa: E402
    import anthropic  # noqa: E402

    db = REPO_ROOT / "content" / "knowledge-base" / "knowledge.db"
    conn = sqlite3.connect(str(db))
    rows = conn.execute("SELECT id, type, body FROM atoms WHERE type IN ('quote','hadith')").fetchall()
    todo = []
    for atom_id, atype, raw in rows:
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            continue
        if body.get("arabic"):
            continue
        text = (body.get("text_en") or body.get("text") or "").strip()
        if not text:
            continue
        todo.append((atom_id, atype, body.get("speaker", ""), text, body))
    if limit:
        todo = todo[:limit]

    client = anthropic.Anthropic(api_key=get_anthropic_key())
    review_path = REPO_ROOT / "content" / "knowledge-base" / "_conflicts" / "arabic-review.jsonl"
    enriched = flagged = failed = 0
    review_lines = []
    for i in range(0, len(todo), batch_size):
        batch = todo[i:i + batch_size]
        items = [{"idx": j, "type": t, "speaker": sp, "text": tx}
                 for j, (aid, t, sp, tx, b) in enumerate(batch)]
        prompt = _QUOTE_ARABIC_PROMPT.format(items=json.dumps(items, ensure_ascii=False, indent=2))
        try:
            resp = client.messages.create(model=model, max_tokens=4096,
                                          messages=[{"role": "user", "content": prompt}])
            out = extract_json(resp.content[0].text)
        except Exception:
            failed += len(batch)
            continue
        by_idx = {o.get("idx"): o for o in out} if isinstance(out, list) else {}
        for j, (atom_id, atype, sp, tx, body) in enumerate(batch):
            o = by_idx.get(j) or {}
            ar = (o.get("arabic") or "").strip() if o.get("arabic") else ""
            if ar and not o.get("uncertain") and _has_arabic(ar):
                body["arabic"] = ar
                body["arabic_source"] = "model-sdk-verified"
                if not dry_run:
                    conn.execute("UPDATE atoms SET body=?, updated_at=datetime('now') WHERE id=?",
                                 (json.dumps(body, ensure_ascii=False), atom_id))
                enriched += 1
            else:
                flagged += 1
                review_lines.append(json.dumps(
                    {"atom_id": atom_id, "type": atype, "text_en": tx,
                     "reason": "uncertain" if o.get("uncertain") else "no-arabic"},
                    ensure_ascii=False))
    if not dry_run:
        conn.commit()
        if review_lines:
            review_path.parent.mkdir(parents=True, exist_ok=True)
            with review_path.open("a", encoding="utf-8") as fh:
                fh.write("\n".join(review_lines) + "\n")
    conn.close()
    return {"candidates": len(todo), "enriched": enriched, "flagged_for_review": flagged,
            "failed_batches_items": failed}


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Restore Arabic script for audio-sourced books.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    rg = sub.add_parser("repair-glossary", help="Fix field-misassignment in glossary.yml (zero LLM).")
    rg.add_argument("slug")
    rg.add_argument("--dry-run", action="store_true")
    ea = sub.add_parser("enrich-atoms", help="Add canonical Arabic to Quran atoms (zero LLM).")
    ea.add_argument("--dry-run", action="store_true")
    eq = sub.add_parser("enrich-quotes", help="Add verified-model Arabic to quote/hadith atoms (metered SDK).")
    eq.add_argument("--limit", type=int, default=None)
    eq.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.cmd == "enrich-atoms":
        r = enrich_quran_atoms(dry_run=args.dry_run)
        tag = " (dry-run)" if args.dry_run else ""
        print(f"enrich-atoms{tag}: {r}")
        return 0
    if args.cmd == "enrich-quotes":
        r = enrich_quote_atoms_arabic(limit=args.limit, dry_run=args.dry_run)
        tag = " (dry-run)" if args.dry_run else ""
        print(f"enrich-quotes{tag}: {r}")
        return 0

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
