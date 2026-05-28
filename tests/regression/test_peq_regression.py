"""test_peq_regression.py — PEQ regression guard for canonical books.

Fails if any chapter's PEQ total drops more than REGRESSION_THRESHOLD points
below its committed baseline.  Run after every Wave K change to ensure no
regression was introduced.

The test re-scores each chapter on-the-fly using the same inputs as the
baseline snapshot script, then compares against the committed baseline JSON.

To update baselines (after intentional quality improvements):
    python3 scripts/wisdom/wisdom_quality_snapshot.py --all-canonical
    git add _workspace/test-strategy/baselines/
    git commit -m "chore(baselines): update PEQ baselines after Wave K step N"
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "scripts" / "podcast"))

from _quality import score as peq_score  # noqa: E402

_CANONICAL_BOOKS = ["kitab-al-riyad", "the-master-and-the-disciple"]
_DRAFTS = _REPO / "CONTENT" / "drafts" / "books"
_BASELINES = _REPO / "_workspace" / "test-strategy" / "baselines"
REGRESSION_THRESHOLD = 5.0   # points below baseline = regression


# ---------------------------------------------------------------------------
# Helpers (duplicated from wisdom_quality_snapshot.py for test isolation)
# ---------------------------------------------------------------------------

def _quran_refs(text: str) -> int:
    return len(re.findall(r'\bQ?\d+:\d+\b', text))


def _domain_terms(text: str) -> tuple[int, int]:
    italics = re.findall(r'\*([^*]+)\*', text)
    total = len(set(italics))
    glossed = len(re.findall(r'\*[^*]+\*\s*\([^)]+\)', text))
    return total, min(glossed, total)


def _arc_labels(text: str) -> list[str]:
    labels: list[str] = []
    if re.search(r'(let us begin|opening|before we dive)', text, re.I):
        labels.append("open_hook")
    if re.search(r'\b(first|second|third|point one|point two)\b', text, re.I):
        labels.append("three_points")
    if re.search(r'(in closing|to close|so as we end|let that sit)', text, re.I):
        labels.append("close")
    return labels


def _extract_citations(contract_path: Path | None) -> list[str]:
    if not contract_path or not contract_path.exists():
        return []
    text = contract_path.read_text(encoding="utf-8")
    return re.findall(r'(?:quran|hadith|doctrine):\S+', text)


def _score_chapter(chapter_txt: Path, contract_path: Path | None) -> float:
    text = chapter_txt.read_text(encoding="utf-8")
    words = len(text.split())
    qrefs = _quran_refs(text)
    terms_total, terms_glossed = _domain_terms(text)
    arc_found = _arc_labels(text)
    citations_source = _extract_citations(contract_path)
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
    return result.total


# ---------------------------------------------------------------------------
# Test parametrization
# ---------------------------------------------------------------------------

def _collect_cases() -> list[tuple[str, str, float]]:
    """Return list of (book_slug, chapter_slug, baseline_total) tuples."""
    cases: list[tuple[str, str, float]] = []
    for book in _CANONICAL_BOOKS:
        baseline_path = _BASELINES / f"{book}-peq-baseline.json"
        if not baseline_path.exists():
            continue
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        for ch_slug, data in baseline.items():
            cases.append((book, ch_slug, data["total"]))
    return cases


_CASES = _collect_cases()


@pytest.mark.parametrize("book_slug,chapter_slug,baseline_total", _CASES,
                         ids=[f"{b}::{c}" for b, c, _ in _CASES])
def test_no_regression(book_slug: str, chapter_slug: str, baseline_total: float) -> None:
    """Fail if PEQ total drops more than REGRESSION_THRESHOLD points vs baseline."""
    chapter_file = _DRAFTS / book_slug / "chapters" / f"{chapter_slug}.txt"
    if not chapter_file.exists():
        pytest.skip(f"Chapter file not found: {chapter_file}")

    contracts_dir = _DRAFTS / book_slug / "chapter-contracts"
    contract = contracts_dir / f"{chapter_slug}.yml"
    current_total = _score_chapter(chapter_file, contract)

    drop = baseline_total - current_total
    assert drop <= REGRESSION_THRESHOLD, (
        f"{book_slug} :: {chapter_slug} — "
        f"PEQ dropped {drop:.1f} points "
        f"(baseline {baseline_total:.1f} → current {current_total:.1f}). "
        f"Threshold: {REGRESSION_THRESHOLD} points."
    )
