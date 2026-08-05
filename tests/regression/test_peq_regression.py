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

from _quality import score as peq_score

_CANONICAL_BOOKS = ["kitab-al-riyad", "the-master-and-the-disciple"]


def _book_dir(slug: str) -> Path | None:
    """Where this book lives today — resolved, never composed.

    This pointed at `CONTENT/drafts/books/`: a layout retired on 2026-06-04, and
    with a capital that only resolves on a case-insensitive filesystem besides.
    Together with an absent baselines directory it meant `_CASES` was empty, so
    this suite reported as a handful of skips and could never fail. A gate that
    cannot fail is not coverage; it is the appearance of it.
    """
    from _paths import find_content

    found = find_content(slug)
    return found[2] if found else None


# `_workspace/tests/baselines/`, which is where the tracked baselines actually
# live. This read `_workspace/test-strategy/baselines` — a folder renamed on
# 2026-05-30 when `_workspace` was compressed to five directories, and the
# retired half of the same stale-path bug as `_DRAFTS` above. Correcting only
# one of the two would have written a fresh, UNTRACKED baseline set beside the
# tracked one: green here, and zero cases on any other clone, which is verbatim
# the vacuous gate this was all meant to end.
_BASELINES = _REPO / "_workspace" / "tests" / "baselines"
REGRESSION_THRESHOLD = 5.0  # points below baseline = regression


# ---------------------------------------------------------------------------
# Helpers (duplicated from wisdom_quality_snapshot.py for test isolation)
# ---------------------------------------------------------------------------


def _quran_refs(text: str) -> int:
    return len(re.findall(r"\bQ?\d+:\d+\b", text))


def _domain_terms(text: str) -> tuple[int, int]:
    italics = re.findall(r"\*([^*]+)\*", text)
    total = len(set(italics))
    glossed = len(re.findall(r"\*[^*]+\*\s*\([^)]+\)", text))
    return total, min(glossed, total)


def _arc_labels(text: str) -> list[str]:
    labels: list[str] = []
    if re.search(r"(let us begin|opening|before we dive)", text, re.I):
        labels.append("open_hook")
    if re.search(r"\b(first|second|third|point one|point two)\b", text, re.I):
        labels.append("three_points")
    if re.search(r"(in closing|to close|so as we end|let that sit)", text, re.I):
        labels.append("close")
    return labels


def _extract_citations(contract_path: Path | None) -> list[str]:
    if not contract_path or not contract_path.exists():
        return []
    text = contract_path.read_text(encoding="utf-8")
    return re.findall(r"(?:quran|hadith|doctrine):\S+", text)


def _score_chapter(chapter_txt: Path, contract_path: Path | None) -> float:
    text = chapter_txt.read_text(encoding="utf-8")
    words = len(text.split())
    qrefs = _quran_refs(text)
    terms_total, terms_glossed = _domain_terms(text)
    arc_found = _arc_labels(text)
    citations_source = _extract_citations(contract_path)
    citations_found = re.findall(r"(?:quran|hadith|doctrine):\S+", text)
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
            # Underscore-prefixed keys are provenance, not chapters — a baseline
            # that was deliberately reset says so in the file it resets, where
            # the next person to see an unexpected floor will actually look.
            if ch_slug.startswith("_"):
                continue
            cases.append((book, ch_slug, data["total"]))
    return cases


_CASES = _collect_cases()


@pytest.mark.parametrize("book_slug,chapter_slug,baseline_total", _CASES, ids=[f"{b}::{c}" for b, c, _ in _CASES])
def test_no_regression(book_slug: str, chapter_slug: str, baseline_total: float) -> None:
    """Fail if PEQ total drops more than REGRESSION_THRESHOLD points vs baseline."""
    book_dir = _book_dir(book_slug)
    assert book_dir is not None, (
        f"{book_slug} has a committed PEQ baseline but no content directory. "
        "A baseline without a book is a stale baseline — delete it or restore the book."
    )

    chapter_file = book_dir / "chapters" / f"{chapter_slug}.txt"
    assert chapter_file.exists(), (
        f"{book_slug} :: {chapter_slug} has a baseline but no chapter at {chapter_file}. "
        "This used to skip, which is how the whole suite reported green while measuring nothing."
    )

    contracts_dir = book_dir / "chapter-contracts"
    contract = contracts_dir / f"{chapter_slug}.yml"
    current_total = _score_chapter(chapter_file, contract)

    drop = baseline_total - current_total
    assert drop <= REGRESSION_THRESHOLD, (
        f"{book_slug} :: {chapter_slug} — "
        f"PEQ dropped {drop:.1f} points "
        f"(baseline {baseline_total:.1f} → current {current_total:.1f}). "
        f"Threshold: {REGRESSION_THRESHOLD} points."
    )
