"""wisdom_quality_snapshot.py — PEQ baseline snapshot generator.

Runs the PEQ scorer against all PASS+WARN chapters of a book and writes
a per-chapter baseline JSON to _workspace/test-strategy/baselines/.
The output is committed and used by test_peq_regression.py to detect
regressions: any chapter whose total drops more than 5 PEQ points
from its baseline will fail the regression test.

USAGE
    python3 scripts/wisdom/wisdom_quality_snapshot.py --book kitab-al-riyad
    python3 scripts/wisdom/wisdom_quality_snapshot.py --book the-master-and-the-disciple
    python3 scripts/wisdom/wisdom_quality_snapshot.py --all-canonical

The script reads chapter contracts from:
    CONTENT/drafts/books/<book>/chapter-contracts/
and chapter text from:
    CONTENT/drafts/books/<book>/chapters/
and writes:
    _workspace/test-strategy/baselines/<book>-peq-baseline.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parents[1]
sys.path.insert(0, str(_REPO / "scripts" / "podcast"))

from _quality import score as peq_score  # noqa: E402

_CANONICAL_BOOKS = ["kitab-al-riyad", "the-master-and-the-disciple"]
_DRAFTS = _REPO / "CONTENT" / "drafts" / "books"
_BASELINES = _REPO / "_workspace" / "test-strategy" / "baselines"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _quran_refs(text: str) -> int:
    """Count Quran citation patterns like Q2:255 or 2:255."""
    return len(re.findall(r'\bQ?\d+:\d+\b', text))


def _domain_terms(text: str) -> tuple[int, int]:
    """Return (total_italicised_terms, glossed_terms).

    Italicised terms (*word*) are treated as domain terms.
    Glossed terms are those followed by an inline definition in parens.
    """
    italics = re.findall(r'\*([^*]+)\*', text)
    total = len(set(italics))
    glossed = len(re.findall(r'\*[^*]+\*\s*\([^)]+\)', text))
    return total, min(glossed, total)


def _arc_labels(text: str) -> list[str]:
    """Heuristic arc label detection from section markers in chapter text."""
    labels: list[str] = []
    if re.search(r'(let us begin|opening|before we dive)', text, re.I):
        labels.append("open_hook")
    if re.search(r'\b(first|second|third|point one|point two)\b', text, re.I):
        labels.append("three_points")
    if re.search(r'(in closing|to close|so as we end|let that sit)', text, re.I):
        labels.append("close")
    return labels


def _extract_citations_from_contract(contract_path: Path) -> list[str]:
    """Parse citation lines from a chapter-contract YAML file."""
    if not contract_path.exists():
        return []
    text = contract_path.read_text(encoding="utf-8")
    # Look for citation_ids: [quran:2:255, ...] or ayat_ids / source_ids
    matches = re.findall(r'(?:quran|hadith|doctrine):\S+', text)
    return matches


def _score_chapter(chapter_txt: Path, contract_path: Path | None) -> dict:
    text = chapter_txt.read_text(encoding="utf-8")
    words = len(text.split())
    qrefs = _quran_refs(text)
    terms_total, terms_glossed = _domain_terms(text)
    arc_found = _arc_labels(text)
    citations_source = _extract_citations_from_contract(contract_path) if contract_path else []
    citations_found = re.findall(r'(?:quran|hadith|doctrine):\S+', text)

    result = peq_score(
        adapted_text=text,
        citation_ids_source=citations_source,
        citation_ids_found=citations_found,
        arc_rules=["open_hook", "three_points", "close"],
        arc_labels_found=arc_found,
        term_count=terms_total,
        glossed_count=terms_glossed,
        quran_ref_count=qrefs,
        word_count=words,
        voice_exemplar_vector=None,
    )
    return result.as_dict()


def snapshot_book(book_slug: str) -> dict:
    book_dir = _DRAFTS / book_slug
    if not book_dir.exists():
        print(f"[SKIP] {book_slug} — not found at {book_dir}", file=sys.stderr)
        return {}

    chapters_dir = book_dir / "chapters"
    contracts_dir = book_dir / "chapter-contracts"
    if not chapters_dir.exists():
        print(f"[SKIP] {book_slug} — no chapters/ directory", file=sys.stderr)
        return {}

    results: dict[str, dict] = {}
    chapter_files = sorted(chapters_dir.glob("*.txt"))
    if not chapter_files:
        print(f"[SKIP] {book_slug} — no .txt files in chapters/", file=sys.stderr)
        return {}

    for ch_file in chapter_files:
        slug = ch_file.stem
        contract = contracts_dir / f"{slug}.yml" if contracts_dir.exists() else None
        result = _score_chapter(ch_file, contract)
        results[slug] = result
        v = result["verdict"]
        print(f"  {slug}: {result['total']:.1f} ({v})")

    return results


def write_baseline(book_slug: str, data: dict) -> Path:
    _BASELINES.mkdir(parents=True, exist_ok=True)
    out = _BASELINES / f"{book_slug}-peq-baseline.json"
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[WRITTEN] {out}")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate PEQ baselines for canonical books")
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--book", help="Single book slug")
    grp.add_argument("--all-canonical", action="store_true",
                     help="Snapshot all canonical books")
    args = parser.parse_args()

    books = _CANONICAL_BOOKS if args.all_canonical else [args.book]
    for book in books:
        print(f"\n=== {book} ===")
        data = snapshot_book(book)
        if data:
            write_baseline(book, data)


if __name__ == "__main__":
    main()
