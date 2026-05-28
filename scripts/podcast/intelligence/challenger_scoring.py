"""challenger_scoring.py — PEQ integration wrapper for the podcast challenger.

Parses a completed challenger report (challenger-report.md) to extract the
inputs needed for PEQ scoring, computes the score, appends a PEQ section to
the report, and returns the PEQScore for the convergence loop to gate on.

USAGE
    from scripts.podcast.intelligence.challenger_scoring import score_report

    peq = score_report(report_path, chapter_txt_path, contract_path)
    if peq.total < 70:
        # FAIL — do not advance convergence loop
        ...

The function is idempotent: if the report already contains a '## PEQ Score'
section, it is replaced (not appended again).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parents[2]
sys.path.insert(0, str(_REPO / "scripts" / "podcast"))

from _quality import score as peq_score, PEQScore  # noqa: E402
from _archetypes import load_exemplar_vector  # noqa: E402


# ---------------------------------------------------------------------------
# Internal helpers
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


def _extract_citations(contract_path: Optional[Path]) -> list[str]:
    if not contract_path or not contract_path.exists():
        return []
    text = contract_path.read_text(encoding="utf-8")
    return re.findall(r'(?:quran|hadith|doctrine):\S+', text)


def _remove_existing_peq_section(report_text: str) -> str:
    """Strip any existing ## PEQ Score section from the report."""
    return re.sub(
        r'\n## PEQ Score\n.*?(?=\n## |\Z)',
        '',
        report_text,
        flags=re.DOTALL,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_report(
    report_path: Path,
    chapter_txt_path: Path,
    contract_path: Optional[Path] = None,
    archetype_slug: Optional[str] = None,
) -> PEQScore:
    """Compute PEQ for a chapter and append the score section to its report.

    Parameters
    ----------
    report_path      : Path to the challenger-report.md to update in-place.
    chapter_txt_path : Path to the chapter .txt (adapted content).
    contract_path    : Path to the chapter-contract .yml (for citation IDs).
    archetype_slug   : Archetype slug for this book (e.g. 'scholarly-deep-dive').
                       When provided, the pre-built voice exemplar vector is
                       loaded and used to score the Voice axis.

    Returns
    -------
    PEQScore with all four axes populated.
    """
    if not chapter_txt_path.exists():
        raise FileNotFoundError(f"Chapter text not found: {chapter_txt_path}")

    chapter_text = chapter_txt_path.read_text(encoding="utf-8")
    words = len(chapter_text.split())
    qrefs = _quran_refs(chapter_text)
    terms_total, terms_glossed = _domain_terms(chapter_text)
    arc_found = _arc_labels(chapter_text)
    citations_source = _extract_citations(contract_path)
    citations_found = re.findall(r'(?:quran|hadith|doctrine):\S+', chapter_text)

    voice_vector = load_exemplar_vector(archetype_slug) if archetype_slug else None

    result = peq_score(
        adapted_text=chapter_text,
        citation_ids_source=citations_source,
        citation_ids_found=citations_found,
        arc_rules=["open_hook", "three_points", "close"],
        arc_labels_found=arc_found,
        term_count=terms_total,
        glossed_count=terms_glossed,
        quran_ref_count=qrefs,
        word_count=words,
        voice_exemplar_vector=voice_vector,
    )

    # Update the report in place.
    if report_path.exists():
        report_text = report_path.read_text(encoding="utf-8")
        report_text = _remove_existing_peq_section(report_text)
        verdict_line = f"**Verdict: {result.verdict}** — total {result.total:.1f}"
        if result.verdict == "PASS":
            verdict_line += " (≥ 85)"
        elif result.verdict == "WARN":
            verdict_line += " (threshold 85 for PASS)"
        else:
            verdict_line += " (threshold 70 for WARN)"
        notes_block = ""
        if result.notes:
            notes_block = "\n\n> " + "; ".join(result.notes)
        peq_section = (
            f"\n\n## PEQ Score\n\n"
            f"{result.markdown_table()}\n\n"
            f"{verdict_line}"
            f"{notes_block}"
        )
        report_path.write_text(report_text.rstrip() + peq_section + "\n",
                               encoding="utf-8")

    return result
