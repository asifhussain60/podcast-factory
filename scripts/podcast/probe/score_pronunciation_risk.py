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
import unicodedata
from collections import defaultdict
from pathlib import Path

_SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_PODCAST) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_PODCAST))

from knowledge import pronunciation_ledger as ledger  # noqa: E402
from knowledge import pronunciation_patterns as patterns  # noqa: E402

DEFAULT_TOP_N = 40

# Matches capitalised proper nouns that are already in English (e.g. "Jesus",
# "Moses", "Torah", "Mahdi").  Used as a last-resort meaning fallback so the
# "Use English translation" checkbox has a pre-fill even without a glossary entry.
_PROPER_NOUN_RE = re.compile(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$")

# Transliteration glyphs that signal phonemes NotebookLM routinely mangles.
_AYN = re.compile(r"[ʿʾ’’’]")                       # hamza / ayn
_EMPHATIC = re.compile(r"[ḥḍṣṭẓḏṯġḫ]")              # emphatics + uncommon fricatives
_QAF = re.compile(r"q", re.IGNORECASE)
_LINEAGE = re.compile(r"\b(ibn|bin|bint|abu|abi|umm|al-| al )", re.IGNORECASE)
_PLACE_HINT = re.compile(r"\b(mount|island|river|valley|city|mosque|masjid|bayt|dwell)", re.IGNORECASE)
_APOST_RE = re.compile(r"[ʿʾ’’ʻ`]")   # ayn / hamza variants


def _normalise_translit(s: str) -> str:
    """Lowercase, strip diacritics and ayn/hamza variants for loose matching."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = _APOST_RE.sub("", s)
    return s.lower()


def _load_concept_glossary(book_dir: Path) -> dict[str, str]:
    """Parse concept-glossary.md -> {arabic_script: meaning, norm_translit: meaning}."""
    path = book_dir / "_system" / "concept-glossary.md"
    if not path.exists():
        return {}
    entry_re = re.compile(r"\*\*([^*]+)\*\*\s*\(([^)]+)\):\s*(.+)")
    meanings: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = entry_re.search(line)
        if not m:
            continue
        translit, arabic, meaning = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        meanings[arabic] = meaning
        meanings[_normalise_translit(translit)] = meaning
    return meanings


_HONORIFIC_RE = re.compile(
    r"^(peace (and blessings )?be upon (him|her|them)|"
    r"alayhis?salam|alayhi (al-)?salam|pbuh|saw|as|ra)$",
    re.IGNORECASE,
)


def _extract_snippet_meaning(snippet: str, transliteration: str = "") -> str:
    """Extract an English gloss from a first-occurrence snippet.

    Only accepts a parenthetical that appears IMMEDIATELY after the normalised
    transliteration in the snippet text.  This avoids false positives where the
    snippet contains a different term's parenthetical (e.g. "wasi (executor)
    appointed for the umma" incorrectly tagging 'umma' as meaning 'executor').
    Also skips honorifics and circular self-references.
    """
    if not snippet or not transliteration:
        return ""
    norm_translit = _normalise_translit(transliteration)
    norm_snippet = _normalise_translit(snippet)
    # Require: <translit> immediately followed by optional space and "(...)".
    # Build pattern as a plain string to avoid f-string brace-escaping pitfalls.
    pattern = re.escape(norm_translit) + r"\s*\(([a-z][^)]{3,80})\)"
    m = re.search(pattern, norm_snippet, re.IGNORECASE)
    if not m:
        return ""
    candidate = m.group(1).strip()
    # Skip if candidate is just the transliteration again or an honorific.
    if _normalise_translit(candidate) == norm_translit:
        return ""
    if _HONORIFIC_RE.match(candidate):
        return ""
    return candidate


def _count_in_text(transliteration: str, text_norm: str) -> int:
    """Count normalised transliteration occurrences in the normalised English text."""
    norm = _normalise_translit(transliteration)
    return text_norm.count(norm) if norm else 0


# Strict: only strip "al-" (with hyphen) so "Allah" / "Ali" are never affected.
_AL_PREFIX_RE = re.compile(r"^al-", re.IGNORECASE)


def _article_root_key(r: dict) -> str:
    """Normalised transliteration with the definite-article al- prefix stripped."""
    norm = _normalise_translit(r.get("transliteration") or r["term"])
    return _AL_PREFIX_RE.sub("", norm)


def _dedup_article_variants(scored: list[dict]) -> list[dict]:
    """Merge entries that differ only by the ال / al- definite article.

    Groups by article-stripped root.  For each group with >1 member:
    - The bare form (transliteration does NOT start with al-) is canonical.
    - Frequencies are summed; the score's freq contribution is recalculated.
    - Meaning falls back to whichever member has one.
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in scored:
        groups[_article_root_key(r)].append(r)

    out: list[dict] = []
    for members in groups.values():
        if len(members) == 1:
            out.append(members[0])
            continue
        # Prefer the bare form (no leading al-) as canonical.
        bare = [
            m for m in members
            if not _normalise_translit(m.get("transliteration") or m["term"]).startswith("al-")
        ]
        primary = max(bare or members, key=lambda m: (m["freq"], m["score"]))
        total_freq = sum(m["freq"] for m in members)

        # Recalculate score's frequency contribution for the merged total.
        score = primary["score"]
        old = primary["freq"]
        if old >= 10:    score -= 3
        elif old >= 4:   score -= 2
        elif old >= 2:   score -= 1
        if total_freq >= 10:   score += 3
        elif total_freq >= 4:  score += 2
        elif total_freq >= 2:  score += 1

        # Build merged reasons: drop the old per-term freq entry, add merged one.
        reasons = [rr for rr in primary["reasons"] if not re.match(r"^x\d+ in text", rr)]
        merged_forms = [m.get("transliteration") or m["term"] for m in members if m is not primary]
        reasons.append(f"x{total_freq} in text (+ {', '.join(merged_forms)})")

        # Use primary's meaning; fall back to any member's meaning.
        merged_meaning = primary.get("meaning") or next(
            (m.get("meaning") for m in members if m.get("meaning")), ""
        )

        out.append({
            **primary,
            "freq": total_freq,
            "score": max(0, score),
            "reasons": reasons,
            "meaning": merged_meaning,
        })
    return out


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


def _body_start_page(book_dir: Path) -> int | None:
    """Return body_starts_at_page from content-range.md, or None if absent."""
    cr_path = book_dir / "_system" / "source" / "text" / "content-range.md"
    if not cr_path.exists():
        return None
    for line in cr_path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*body_starts_at_page\s*:\s*(\d+)", line)
        if m:
            return int(m.group(1))
    return None


def _slice_to_body(raw_text: str, start_page: int) -> str:
    """Return only the text from <!-- page N --> onward, dropping front matter."""
    marker = f"<!-- page {start_page} -->"
    idx = raw_text.find(marker)
    return raw_text[idx:] if idx != -1 else raw_text


def build_probe_terms(book_dir: Path, top_n: int = DEFAULT_TOP_N) -> dict:
    phon_path = book_dir / "_system" / "source" / "text" / "_phonetics.md"
    refined_path = book_dir / "_system" / "source" / "text" / "refined-english.md"
    if not phon_path.exists():
        raise FileNotFoundError(f"phonetics table missing: {phon_path} (run phase 0c first)")

    rows = _parse_phonetics_md(phon_path)
    raw_text = refined_path.read_text(encoding="utf-8") if refined_path.exists() else ""
    body_page = _body_start_page(book_dir)
    if body_page is not None:
        raw_text = _slice_to_body(raw_text, body_page)
    text_norm = _normalise_translit(raw_text)  # normalised once for fast repeated lookup

    meanings = _load_concept_glossary(book_dir)

    lib = ledger.load()
    pat = patterns.load()
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
        # Count by transliteration in the English text (Arabic script never appears there).
        freq = _count_in_text(row["transliteration"], text_norm) if text_norm else 0
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
        # Meaning: concept-glossary first (by Arabic script or normalised translit),
        # then a parenthetical gloss from the first-occurrence snippet, then the
        # transliteration itself when it is already an English proper noun (Jesus,
        # Moses, Torah, Mahdi …) — gives the "Use English translation" checkbox a
        # pre-fill at no extra cost.
        translit_str = row.get("transliteration", "").strip()
        meaning = (
            meanings.get(row["term"])
            or meanings.get(_normalise_translit(translit_str))
            or _extract_snippet_meaning(row.get("snippet", ""), translit_str)
            or (translit_str if _PROPER_NOUN_RE.match(translit_str) else "")
        )

        scored.append({
            "term": row["term"],
            "transliteration": row["transliteration"],
            "phonetic": phon,
            "house_style_ok": house_ok,
            # deterministic pattern baseline — pre-fills a suggestion for unseen /
            # IPA-broken terms so the reviewer confirms instead of types from blank
            "suggested_baseline": pat.baseline_phonetic(row["transliteration"] or row["term"]),
            "signature": patterns.feature_signature(row["term"], row["transliteration"]),
            "segment": _segment_of(row),
            "snippet": snippet,
            "freq": freq,
            "score": score,
            "reasons": reasons,
            # term field IS Arabic script; bake it so the UI pre-fills the Arabic input
            "arabic_script": row.get("arabic_script") or row["term"],
            "meaning": meaning or "",
        })

    # Merge terms that differ only by the ال / al- definite article.
    scored = _dedup_article_variants(scored)

    # Primary sort: frequency desc (most-heard terms first), then risk score desc,
    # then alphabetical.  Terms the listener hears most belong at the top of the list.
    # Segment grouping is NOT applied here — it is the UI's job (or build_probe_bundle's).
    scored.sort(key=lambda r: (-r["freq"], -r["score"], r["term"].lower()))
    top = scored[:top_n]
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
