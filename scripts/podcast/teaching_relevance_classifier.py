#!/usr/bin/env python3
"""teaching_relevance_classifier.py — tag glossary terms by teaching value.

Classifies each `_system/glossary.yml` entry into one of four classes, written
to a `teaching_relevance` field the audio + reader consumers respect:

  teaching     doctrinally load-bearing vocabulary the book TEACHES
               (ta'wil, tanzil, zahir, batin, natiq, asas, hujja, dawr, qa'im).
  name         a personal / transmitter name (al-Nu'man, ibn Hayyun) — referential.
  incidental   a dynasty / place / passing historical reference of no teaching
               value (Fatimid, Mount Tur, a city) — dropped from the pronunciation
               dictionary, never recited.
  referential  any other non-teaching term (safe default).

WHY: the auto-built glossary is a broad net — it scoops up every Arabic token,
teaching terms and historical/referential noise alike. This classifier restores
balance so the SPOKEN audio recites the doctrine (teaching terms in Arabic) and
leaves dynasty names + transmitter fragments in plain speech, and the human
curation review leads with what actually teaches.

Spine (deterministic, auditable — no LLM needed for the load-bearing decision):
  1. concept-glossary.md (the human teaching allow-list) -> teaching
  2. personal-name heuristic (shared _is_proper_name)     -> name
  3. place heuristic (shared _PLACE_HINT)                  -> incidental
  4. the AMBIGUOUS remainder -> one batched Claude-Max judgment from each term's
     first-occurrence snippet (flat-rate Max; --no-llm or a missing `claude`
     binary falls back to `referential`, the conservative default).

Idempotent: an entry that already carries `teaching_relevance` is left alone
unless --reclassify is passed.

Usage:
  python3 scripts/podcast/teaching_relevance_classifier.py <slug|book_dir>
  python3 scripts/podcast/teaching_relevance_classifier.py <slug> --no-llm
  python3 scripts/podcast/teaching_relevance_classifier.py <slug> --reclassify
  python3 scripts/podcast/teaching_relevance_classifier.py <slug> --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fill_glossary_arabic import emit_glossary_yml, parse_glossary_yml
from probe.score_pronunciation_risk import (
    _PLACE_HINT,
    _load_concept_glossary,
    _normalise_translit,
)
from pronunciation_compiler import _is_proper_name

TEACHING = "teaching"
NAME = "name"
INCIDENTAL = "incidental"
REFERENTIAL = "referential"
VALID_CLASSES = frozenset({TEACHING, NAME, INCIDENTAL, REFERENTIAL})

_LLM_BATCH = 60
_CLAUDE_TIMEOUT = 600

# Obvious dynasty / sect markers that carry no teaching weight on their own —
# deterministic pre-LLM catch (the LLM still handles anything not listed here).
_INCIDENTAL_HINT = re.compile(
    r"\b(fatimid|umayyad|abbasid|ayyubid|mamluk|ottoman|safavid|"
    r"dynasty|caliphate|empire)\b",
    re.IGNORECASE,
)


def _deterministic_class(entry: dict, concept: dict[str, str]) -> str | None:
    """Authoritative class when one of the deterministic stages fires, else None
    (ambiguous — handed to the LLM stage). High precision by design."""
    phonetic = str(entry.get("phonetic") or "").strip()
    translit = str(entry.get("transliteration") or "").strip()
    arabic = str(entry.get("arabic_script") or "").strip()
    snippet = str(entry.get("first_seen_snippet") or "")

    # 1. concept-glossary allow-list — the human-authored teaching vocabulary.
    #    Match on Arabic script, on the normalised transliteration, and on the
    #    same with a leading definite article stripped ("al-Natiq" -> "natiq")
    #    so the auto-glossary's article-prefixed forms still hit the allow-list.
    if arabic and arabic in concept:
        return TEACHING
    for raw in (translit, phonetic):
        norm = _normalise_translit(raw)
        if not norm:
            continue
        if norm in concept:
            return TEACHING
        stripped = re.sub(r"^(al|el)(?=.)", "", norm)
        if stripped != norm and stripped in concept:
            return TEACHING
    # 2. personal / transmitter names (ibn, bin, abu, al-yaman ...).
    if _is_proper_name(phonetic):
        return NAME
    # 3. dynasties / places — referential history, not teaching.
    if _INCIDENTAL_HINT.search(f"{phonetic} {translit}"):
        return INCIDENTAL
    if _PLACE_HINT.search(f"{phonetic} {translit} {snippet}"):
        return INCIDENTAL
    return None


def _build_llm_prompt(items: list[tuple[int, dict]]) -> str:
    rows = []
    for i, e in items:
        rows.append(
            f'{i}. term="{e.get("transliteration") or e.get("phonetic")}" '
            f'context="{(e.get("first_seen_snippet") or "").strip()[:200]}"'
        )
    listing = "\n".join(rows)
    return f"""You are classifying Arabic terms pulled from a scholarly Islamic book by how \
much each one carries the book's TEACHING, versus being incidental reference. For each numbered \
term, read the term and the sentence it first appears in, and assign exactly ONE class:

- "teaching": a doctrinal / technical / conceptual term the book is actually TEACHING the reader \
(a concept, a method, a rank, a station, a hermeneutic category). Example: ta'wil, batin, natiq, \
hujja, dawr, walaya, qa'im.
- "name": a personal name or name-fragment of a person, author, or transmitter. Example: \
al-Nu'man, ibn Hayyun, al-Tamimi.
- "incidental": a dynasty, sect label, place, tribe, or passing historical reference that bears \
no teaching value on its own. Example: Fatimid, al-Maghrib, a city, a tribe.
- "referential": any other Arabic term that is neither a load-bearing teaching concept nor a \
name nor an incidental reference (a common word, a connective, an ordinary noun).

Judge from CONTEXT, not the surface form. When a term is genuinely borderline between teaching \
and referential, prefer "referential" unless the sentence shows it is being defined or taught.

TERMS:
{listing}

Return ONLY a JSON array, one object per term, no prose:
[{{"i": <number>, "class": "teaching|name|incidental|referential"}}]"""


def _llm_classify(items: list[tuple[int, dict]], book_dir: Path, log) -> dict[int, str]:
    """Batched Claude-Max judgment for the ambiguous remainder. Returns {idx:class};
    missing/failed entries are simply absent (caller defaults them to referential)."""
    try:
        from _authoring._core import _run_claude_p
    except Exception as e:
        log(f"    [classify] claude unavailable ({e}) — ambiguous terms -> referential")
        return {}
    out: dict[int, str] = {}
    for start in range(0, len(items), _LLM_BATCH):
        batch = items[start : start + _LLM_BATCH]
        prompt = _build_llm_prompt(batch)
        rc, text, err = _run_claude_p(
            prompt, timeout=_CLAUDE_TIMEOUT, book_dir=book_dir, phase="audio-script", step="teaching-relevance"
        )
        if rc != 0:
            log(f"    [classify] LLM batch rc={rc}: {err[:120]} — batch -> referential")
            continue
        m = re.search(r"\[.*\]", text or "", re.DOTALL)
        if not m:
            log("    [classify] LLM returned no JSON array — batch -> referential")
            continue
        try:
            for obj in json.loads(m.group(0)):
                idx = int(obj.get("i"))
                cls = str(obj.get("class") or "").strip().lower()
                if cls in VALID_CLASSES:
                    out[idx] = cls
        except Exception as e:
            log(f"    [classify] LLM JSON parse failed ({e}) — batch -> referential")
    return out


def classify_entries(
    entries: list[dict], book_dir: Path, *, use_llm: bool = True, reclassify: bool = False, log=print
) -> dict[str, int]:
    """Mutate entries in place, adding `teaching_relevance`. Returns class counts."""
    concept = _load_concept_glossary(book_dir)
    ambiguous: list[tuple[int, dict]] = []
    for i, e in enumerate(entries):
        if e.get("teaching_relevance") and not reclassify:
            continue
        cls = _deterministic_class(e, concept)
        if cls is not None:
            e["teaching_relevance"] = cls
        else:
            ambiguous.append((i, e))

    if ambiguous and use_llm:
        log(f"    [classify] {len(ambiguous)} ambiguous term(s) -> Claude Max")
        verdicts = _llm_classify(ambiguous, book_dir, log)
        for i, e in ambiguous:
            e["teaching_relevance"] = verdicts.get(i, REFERENTIAL)
    else:
        for _, e in ambiguous:
            e["teaching_relevance"] = REFERENTIAL

    counts: dict[str, int] = {}
    for e in entries:
        counts[e["teaching_relevance"]] = counts.get(e["teaching_relevance"], 0) + 1
    return counts


def _resolve_book_dir(arg: str) -> Path:
    p = Path(arg)
    if p.is_dir() and (p / "_system").is_dir():
        return p.resolve()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _paths import find_content

    bd = find_content(arg)
    if not bd:
        raise SystemExit(f"cannot resolve book dir for {arg!r}")
    return Path(bd).resolve()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("book", help="book slug or BOOK_DIR")
    ap.add_argument("--no-llm", action="store_true", help="deterministic only; ambiguous terms -> referential")
    ap.add_argument("--reclassify", action="store_true", help="overwrite existing teaching_relevance values")
    ap.add_argument("--dry-run", action="store_true", help="classify + print the split; do not write glossary.yml")
    args = ap.parse_args(argv)

    book_dir = _resolve_book_dir(args.book)
    gpath = book_dir / "_system" / "glossary.yml"
    if not gpath.exists():
        print(f"no glossary.yml at {gpath}")
        return 1
    entries, top = parse_glossary_yml(gpath)
    counts = classify_entries(entries, book_dir, use_llm=not args.no_llm, reclassify=args.reclassify, log=print)

    total = sum(counts.values())
    print(f"\n  teaching-relevance split for {book_dir.name} ({total} terms):")
    for cls in (TEACHING, NAME, INCIDENTAL, REFERENTIAL):
        print(f"    {cls:12s} {counts.get(cls, 0)}")
    recited = [e for e in entries if e.get("teaching_relevance") == TEACHING]
    print(f"\n  -> {len(recited)} term(s) will be recited in Arabic (teaching only):")
    for e in recited[:40]:
        print(f"       {e.get('transliteration') or e.get('phonetic')}")

    if args.dry_run:
        print("\n  --dry-run: glossary.yml NOT written")
        return 0
    gpath.write_text(emit_glossary_yml(entries, top), encoding="utf-8")
    print(f"\n  wrote {gpath}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
