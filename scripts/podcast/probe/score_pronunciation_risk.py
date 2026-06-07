#!/usr/bin/env python3
"""Rank a book's Arabic terms by mispronunciation risk for the 0probe phase.

Reads the book's ``_phonetics.md`` (term + diacritic transliteration + spoken
phonetic), counts each term's frequency in ``refined-english.md``, and scores
risk as ``difficulty + frequency``. Terms the cross-book pronunciation library
already settled (``confirmed`` -> safe; ``unfixable`` -> already glossed) are
DROPPED from the probe — you only re-listen to what is still unproven.

Output: ``_system/probe/probe-terms.json`` — the top-N risk-ranked terms,
bucketed into listen segments (names / places / terms) so the audio maps
cleanly to the checklist.

Risk is a heuristic ON PURPOSE: its only job is to put the worst offenders at
the top of a ~40-item list a human listens to once. It does not need to be
exact, only well-ordered.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_PODCAST) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_PODCAST))

from knowledge import pronunciation_ledger as ledger  # noqa: E402

DEFAULT_TOP_N = 40

# Transliteration glyphs that signal phonemes NotebookLM routinely mangles.
_AYN = re.compile(r"[ʿʾ'‘’]")                       # hamza / ayn
_EMPHATIC = re.compile(r"[ḥḍṣṭẓḏṯġḫ]")              # emphatics + uncommon fricatives
_QAF = re.compile(r"q", re.IGNORECASE)
_LINEAGE = re.compile(r"\b(ibn|bin|bint|abu|abi|umm|al-| al )", re.IGNORECASE)
_PLACE_HINT = re.compile(r"\b(mount|island|river|valley|city|mosque|masjid|bayt|dwell)", re.IGNORECASE)


def _parse_phonetics_md(path: Path) -> list[dict]:
    """Parse the 4-column pipe table into row dicts."""
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        if cells[0].lower() in ("term", "") or set(cells[0]) <= {"-", ":"}:
            continue  # header or divider
        rows.append({
            "term": cells[0],
            "transliteration": cells[1] if len(cells) > 1 else cells[0],
            "phonetic": cells[2] if len(cells) > 2 else "",
            "snippet": cells[3] if len(cells) > 3 else "",
        })
    return rows


def _syllable_count(phonetic: str) -> int:
    if not phonetic:
        return 0
    return max(1, len(re.split(r"[- ]", phonetic.strip())))


def _segment_of(row: dict) -> str:
    term, snippet = row["term"], row.get("snippet", "")
    if _PLACE_HINT.search(snippet) or _PLACE_HINT.search(term):
        return "places"
    # Multi-word capitalised or lineage markers -> proper name.
    if _LINEAGE.search(term) or (term[:1].isupper() and " " in term):
        return "names"
    if term[:1].isupper():
        return "names"
    return "terms"


def score_row(row: dict, freq: int) -> tuple[int, list[str]]:
    """Return (score, reasons)."""
    score = 0
    reasons: list[str] = []
    translit = row.get("transliteration") or row["term"]

    if _AYN.search(translit) or _AYN.search(row["term"]):
        score += 3
        reasons.append("ayn/hamza")
    n_emph = len(_EMPHATIC.findall(translit))
    if n_emph:
        score += min(4, 2 * n_emph)
        reasons.append(f"emphatic x{n_emph}")
    if _QAF.search(row["term"]):
        score += 2
        reasons.append("qaf")

    syl = _syllable_count(row["phonetic"])
    if syl >= 4:
        score += 2
        reasons.append(f"{syl} syllables")
    elif syl >= 3:
        score += 1
        reasons.append(f"{syl} syllables")

    if _LINEAGE.search(row["term"]) or (row["term"][:1].isupper() and " " in row["term"]):
        score += 2
        reasons.append("proper name")

    if len(row["term"]) > 12:
        score += 1
        reasons.append("long")

    # Frequency: log-ish bucketing so a term said 50x doesn't swamp difficulty.
    if freq >= 10:
        score += 3
    elif freq >= 4:
        score += 2
    elif freq >= 2:
        score += 1
    if freq >= 2:
        reasons.append(f"x{freq} in text")

    return score, reasons


def build_probe_terms(book_dir: Path, top_n: int = DEFAULT_TOP_N) -> dict:
    phon_path = book_dir / "_system" / "source" / "text" / "_phonetics.md"
    refined_path = book_dir / "_system" / "source" / "text" / "refined-english.md"
    if not phon_path.exists():
        raise FileNotFoundError(f"phonetics table missing: {phon_path} (run phase 0c first)")

    rows = _parse_phonetics_md(phon_path)
    text = refined_path.read_text(encoding="utf-8").lower() if refined_path.exists() else ""

    lib = ledger.load()
    scored: list[dict] = []
    skipped_confirmed = 0
    skipped_unfixable = 0

    for row in rows:
        hit = lib.lookup(row["term"])
        if hit and hit.status == "confirmed":
            skipped_confirmed += 1
            continue
        if hit and hit.status == "unfixable":
            skipped_unfixable += 1
            continue
        freq = text.count(row["term"].lower()) if text else 0
        score, reasons = score_row(row, freq)
        phon = row["phonetic"]
        house_ok = ledger.is_house_style(phon)
        if not house_ok:
            score += 1  # no valid intended respelling yet — worth authoring + hearing
            reasons.append("non-house-style respelling")
        snippet = row.get("snippet", "")
        # A snippet that just echoes the term/transliteration carries no context.
        if ledger.normalize_key(snippet).find(ledger.normalize_key(row["term"])) != -1:
            snippet = ""
        scored.append({
            "term": row["term"],
            "transliteration": row["transliteration"],
            "phonetic": phon,
            "house_style_ok": house_ok,
            "segment": _segment_of(row),
            "snippet": snippet,
            "freq": freq,
            "score": score,
            "reasons": reasons,
        })

    scored.sort(key=lambda r: (-r["score"], -r["freq"], r["term"].lower()))
    top = scored[:top_n]
    # Stable ordering within the bundle: group by segment, keep score order inside.
    seg_order = {"names": 0, "places": 1, "terms": 2}
    top.sort(key=lambda r: (seg_order.get(r["segment"], 9), -r["score"]))
    for i, r in enumerate(top, 1):
        r["n"] = i

    return {
        "book_slug": book_dir.name,
        "total_terms": len(rows),
        "scored_terms": len(scored),
        "skipped_confirmed": skipped_confirmed,
        "skipped_unfixable": skipped_unfixable,
        "top_n": len(top),
        "terms": top,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Rank Arabic terms by mispronunciation risk")
    ap.add_argument("book_dir", type=Path, help="content/<Bucket>/<slug>/")
    ap.add_argument("--top-n", type=int, default=DEFAULT_TOP_N)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    result = build_probe_terms(args.book_dir, args.top_n)
    out = args.out or (args.book_dir / "_system" / "probe" / "probe-terms.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"probe-terms: {result['top_n']} of {result['scored_terms']} scored "
        f"({result['skipped_confirmed']} confirmed + {result['skipped_unfixable']} unfixable skipped) "
        f"-> {out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
