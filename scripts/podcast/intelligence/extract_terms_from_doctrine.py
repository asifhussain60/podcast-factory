"""Extract Islamic technical terms from existing doctrine atoms — Wave K.

Scans the text_en of all doctrine atoms in knowledge.db for italicized
Arabic transliterations (* term *).  Two tiers:

  Tier 1 — inline definition: *term* (translation) — uses translation as text_en.
  Tier 2 — context only: captures surrounding sentence (≤160 chars) as text_en.

Deduplicates against existing term atoms (by normalized term name).
Writes new term atoms directly to knowledge.db.
No LLM calls; zero API cost.

Usage:
    python3 scripts/podcast/intelligence/extract_terms_from_doctrine.py
    python3 scripts/podcast/intelligence/extract_terms_from_doctrine.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _db  # noqa: E402
from knowledge._atom_schemas import term_canonical_id, validate_atom  # noqa: E402

# ── regex patterns ────────────────────────────────────────────────────────────

# Tier 1: *term* (inline definition in parens)
_TIER1_RE = re.compile(
    r"\*([a-záéíóúāēīōūʿʾḥḍṭẓṣḳ'\-]{2,35})\*"
    r"\s*\(([^)]{3,100})\)"
)
# Tier 2: *term* with no inline definition
_TIER2_RE = re.compile(
    r"\*([a-záéíóúāēīōūʿʾḥḍṭẓṣḳ'\-]{2,35})\*"
)

# Terms that are common English or markdown fragments — skip
# Also skip plain English adjectives/adverbs that get italicised in the source
# but are NOT Arabic technical terms (e.g. "complete", "content", "without").
# Rule: a valid Islamic term must either (a) contain a diacritic/non-ASCII char,
# (b) begin with "al-", or (c) be in a small explicit allow-set of short terms
# that have no diacritics but are genuine Arabic loanwords.
_SKIP_TERMS = {
    "the", "and", "for", "not", "but", "with", "also", "this", "that",
    "from", "upon", "into", "over", "under", "as", "at", "by", "in",
    "al-", "wa-", "or", "is", "it", "of",
    # Common English words that appear italicised in Kashkole but are not terms
    "complete", "perfect", "defective", "content", "without", "observe",
    "knowledge", "power", "life", "faith", "truth", "heart", "soul",
    "prayer", "fasting", "pilgrimage", "alms", "witness", "light",
    "first", "second", "third", "two", "three", "seven", "eight",
    "good", "evil", "right", "wrong", "great", "small", "high", "low",
    "able", "above", "below", "before", "after", "indeed", "thus",
    "divine", "sacred", "holy", "inner", "outer", "true", "false",
    "special", "general", "natural", "spiritual", "physical", "moral",
}

# Max surrounding context chars (each side) for Tier 2 terms
_CTX_CHARS = 140


def _clean(text: str) -> str:
    return " ".join(text.replace("\n", " ").split())


def _surrounding_sentence(text: str, match_start: int, match_end: int) -> str:
    """Extract context sentence around the match."""
    start = max(0, match_start - _CTX_CHARS)
    end = min(len(text), match_end + _CTX_CHARS)
    snippet = text[start:end]
    # Trim to sentence boundaries if possible
    for sep in (". ", ".\n", "? ", "! "):
        first = snippet.find(sep)
        if 0 < first < (_CTX_CHARS - 10):
            snippet = snippet[first + 2:]
            break
    return _clean(snippet)


def extract_terms(dry_run: bool = False) -> dict:
    """Return a summary dict; writes to DB unless dry_run."""
    conn = _db.get_connection()

    # Load existing term IDs and normalized names for dedup
    existing_ids: set[str] = {
        row[0] for row in conn.execute("SELECT id FROM atoms WHERE type='term'").fetchall()
    }
    existing_names: set[str] = {
        row[0]
        for row in conn.execute(
            "SELECT json_extract(body, '$.term') FROM atoms WHERE type='term'"
        ).fetchall()
        if row[0]
    }
    existing_names_normalized = {n.lower().strip() for n in existing_names}

    # Scan doctrine atoms
    doctrine_rows = conn.execute(
        "SELECT id, body FROM atoms WHERE type='doctrine'"
    ).fetchall()

    tier1: dict[str, dict] = {}  # term_name -> first-seen candidate
    tier2: dict[str, dict] = {}

    for atom_id, body_json in doctrine_rows:
        body = json.loads(body_json)
        text = body.get("text_en", "")
        if not text:
            continue

        for m in _TIER1_RE.finditer(text):
            term = m.group(1).lower().strip()
            defn = m.group(2).strip()
            if len(term) < 3 or term in _SKIP_TERMS:
                continue
            if term in existing_names_normalized:
                continue
            if term not in tier1:
                tier1[term] = {"term": term, "text_en": defn, "source": "doctrine"}

        for m in _TIER2_RE.finditer(text):
            term = m.group(1).lower().strip()
            if len(term) < 3 or term in _SKIP_TERMS:
                continue
            if term in existing_names_normalized or term in tier1:
                continue
            if term not in tier2:
                ctx = _surrounding_sentence(text, m.start(), m.end())
                tier2[term] = {"term": term, "text_en": ctx, "source": "doctrine"}

    # Only use Tier-1 (inline-defined) terms; Tier-2 context sentences are too noisy
    # and frequently capture plain English words that appear italicised in the source.
    candidates = {**tier1}

    # Build atom dicts and validate
    new_atoms: list[dict] = []
    for term_name, data in candidates.items():
        atom_id = term_canonical_id(term_name)
        if atom_id in existing_ids:
            continue
        atom = {
            "id": atom_id,
            "type": "term",
            "body": {
                "term": term_name,
                "text_en": data["text_en"],
                "source": data["source"],
            },
            "tradition": "fatimid-ismaili",
            "confidence": 1.0,
            "needs_review": False,
            "first_seen": {"book": "kashkole", "chapter": "doctrine-scan"},
            "sources": [{"book": "kashkole", "chapter": "doctrine-scan", "locator": ""}],
        }
        try:
            validate_atom(atom)
            new_atoms.append(atom)
        except ValueError:
            continue

    if not dry_run:
        inserted = 0
        for atom in new_atoms:
            try:
                fs = atom.get("first_seen", {})
                conn.execute(
                    "INSERT OR IGNORE INTO atoms "
                    "(id, type, body, first_seen_book, first_seen_chapter, tradition, confidence) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        atom["id"],
                        atom["type"],
                        json.dumps(atom["body"], ensure_ascii=False),
                        fs.get("book", ""),
                        fs.get("chapter", ""),
                        atom["tradition"],
                        atom["confidence"],
                    ),
                )
                inserted += 1
            except Exception:  # noqa: BLE001
                continue
        conn.commit()
    else:
        inserted = len(new_atoms)

    return {
        "scanned_doctrine_atoms": len(doctrine_rows),
        "tier1_with_definition": len(tier1),
        "tier2_context_only": len(tier2),
        "total_candidates": len(candidates),
        "net_new_atoms": inserted,
        "dry_run": dry_run,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Extract term atoms from doctrine text — Wave K.")
    ap.add_argument("--dry-run", action="store_true", help="Report counts without writing to DB")
    args = ap.parse_args()

    summary = extract_terms(dry_run=args.dry_run)
    print("Term extraction from doctrine atoms")
    print(f"  Scanned doctrine atoms:       {summary['scanned_doctrine_atoms']}")
    print(f"  Tier 1 (inline definition):   {summary['tier1_with_definition']}")
    print(f"  Tier 2 (context sentence):    {summary['tier2_context_only']}")
    print(f"  Total candidates:             {summary['total_candidates']}")
    if args.dry_run:
        print(f"  Would insert (dry-run):       {summary['net_new_atoms']}")
    else:
        print(f"  Net new term atoms inserted:  {summary['net_new_atoms']}")


if __name__ == "__main__":
    main()
