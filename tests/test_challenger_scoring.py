"""test_challenger_scoring.py — Unit tests for the challenger report parser and
PEQ scoring integration (scripts/podcast/intelligence/challenger_scoring.py).

Tests cover: parsing the PEQ table from an existing report, in-place report
update, idempotent re-scoring, and the remove-existing-section logic.
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "scripts" / "podcast"))
sys.path.insert(0, str(_REPO))

from scripts.podcast.intelligence.challenger_scoring import (  # noqa: E402
    score_report,
    _remove_existing_peq_section,
    _quran_refs,
    _domain_terms,
    _arc_labels,
    _extract_citations,
)
from _quality import PASS, WARN, FAIL  # noqa: E402


# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------

def _make_chapter_txt(tmp_path: Path, content: str = "") -> Path:
    """Write a chapter .txt file and return its path."""
    p = tmp_path / "ch01-test.txt"
    p.write_text(content, encoding="utf-8")
    return p


def _make_report(tmp_path: Path, content: str = "") -> Path:
    """Write a challenger report and return its path."""
    p = tmp_path / "challenger-report.md"
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Internal parser helpers
# ---------------------------------------------------------------------------

class TestQuranRefs:
    def test_detects_surah_ayat(self):
        assert _quran_refs("See Q2:255 and 3:1 for reference.") == 2

    def test_no_refs(self):
        assert _quran_refs("No citations here.") == 0

    def test_does_not_match_plain_numbers(self):
        assert _quran_refs("100 scholars said 200 things.") == 0


class TestDomainTerms:
    def test_counts_italicised_terms(self):
        total, glossed = _domain_terms("The *tawhid* (unity) and *nubuwwa* (prophethood).")
        assert total == 2
        assert glossed == 2

    def test_unglossed_italics_counted_as_unglosssed(self):
        total, glossed = _domain_terms("The *tawhid* is central.")
        assert total == 1
        assert glossed == 0

    def test_no_terms(self):
        total, glossed = _domain_terms("Plain text with no italics.")
        assert total == 0
        assert glossed == 0

    def test_glossed_capped_at_total(self):
        # Glossed cannot exceed total (degenerate input safety)
        total, glossed = _domain_terms("*tawhid* (unity) *tawhid* (unity)")
        assert glossed <= total


class TestArcLabels:
    def test_detects_open_hook(self):
        labels = _arc_labels("Let us begin our journey.")
        assert "open_hook" in labels

    def test_detects_three_points(self):
        labels = _arc_labels("First, we consider; second, we reflect; third, we act.")
        assert "three_points" in labels

    def test_detects_close(self):
        labels = _arc_labels("In closing, let us remember.")
        assert "close" in labels

    def test_no_labels_empty_text(self):
        assert _arc_labels("") == []

    def test_case_insensitive(self):
        labels = _arc_labels("LET US BEGIN and IN CLOSING.")
        assert "open_hook" in labels
        assert "close" in labels


class TestExtractCitations:
    def test_no_contract(self):
        assert _extract_citations(None) == []

    def test_nonexistent_file(self, tmp_path: Path):
        assert _extract_citations(tmp_path / "missing.yml") == []

    def test_extracts_citation_ids(self, tmp_path: Path):
        contract = tmp_path / "contract.yml"
        contract.write_text("citations:\n  - quran:2:255\n  - hadith:sahih:1234\n", encoding="utf-8")
        ids = _extract_citations(contract)
        assert "quran:2:255" in ids
        assert "hadith:sahih:1234" in ids


# ---------------------------------------------------------------------------
# Remove existing PEQ section
# ---------------------------------------------------------------------------

class TestRemoveExistingPeqSection:
    def test_removes_peq_section(self):
        report = textwrap.dedent("""\
            ## Challenge Report

            Some content.

            ## PEQ Score

            | Axis | Weight | Score | Weighted |
            |---|---|---|---|
            | **Total** | 100% | — | **82.5** |

            **Verdict: WARN**

            ## Next Section

            More content.
        """)
        cleaned = _remove_existing_peq_section(report)
        assert "## PEQ Score" not in cleaned
        assert "## Next Section" in cleaned
        assert "Some content" in cleaned

    def test_no_peq_section_unchanged(self):
        report = "## Challenge Report\n\nSome content.\n"
        assert _remove_existing_peq_section(report) == report


# ---------------------------------------------------------------------------
# score_report integration
# ---------------------------------------------------------------------------

class TestScoreReport:
    def test_missing_chapter_raises(self, tmp_path: Path):
        report = _make_report(tmp_path, "## Report\n\nContent.")
        missing_chapter = tmp_path / "missing.txt"
        with pytest.raises(FileNotFoundError):
            score_report(report, missing_chapter)

    def test_appends_peq_section(self, tmp_path: Path):
        chapter = _make_chapter_txt(
            tmp_path,
            "Let us begin. First point. In closing. *tawhid* (unity). Q2:255.",
        )
        report = _make_report(tmp_path, "## Challenge Report\n\nVerdict: PASS\n")
        result = score_report(report, chapter)
        updated = report.read_text(encoding="utf-8")
        assert "## PEQ Score" in updated
        assert str(round(result.total, 1)) in updated

    def test_idempotent_second_call_replaces_not_appends(self, tmp_path: Path):
        chapter = _make_chapter_txt(tmp_path, "Let us begin. Q2:1. *ilm* (knowledge).")
        report = _make_report(tmp_path, "## Report\n\nContent.\n")
        score_report(report, chapter)
        score_report(report, chapter)
        content = report.read_text(encoding="utf-8")
        assert content.count("## PEQ Score") == 1

    def test_returns_peqscore_with_total(self, tmp_path: Path):
        chapter = _make_chapter_txt(tmp_path, "Some text with no special markers.")
        report = _make_report(tmp_path, "## Report\n")
        result = score_report(report, chapter)
        assert 0.0 <= result.total <= 100.0

    def test_verdict_in_report_file(self, tmp_path: Path):
        chapter = _make_chapter_txt(tmp_path, "Short chapter.")
        report = _make_report(tmp_path, "## Report\n")
        result = score_report(report, chapter)
        content = report.read_text(encoding="utf-8")
        assert result.verdict in content

    def test_report_not_written_when_missing(self, tmp_path: Path):
        """When report_path does not exist, function still returns a valid score."""
        chapter = _make_chapter_txt(tmp_path, "Some chapter text.")
        nonexistent_report = tmp_path / "no-report.md"
        result = score_report(nonexistent_report, chapter)
        assert result.total >= 0.0
        # The nonexistent report should NOT be created if it doesn't exist
        # (score_report only writes if report_path.exists())
        assert not nonexistent_report.exists()

    def test_with_contract_extracts_citations(self, tmp_path: Path):
        contract = tmp_path / "contract.yml"
        contract.write_text("citations:\n  - quran:2:255\n", encoding="utf-8")
        chapter = _make_chapter_txt(tmp_path, "See quran:2:255 for reference.")
        report = _make_report(tmp_path, "## Report\n")
        result = score_report(report, chapter, contract_path=contract)
        # Fidelity should be high since citation is found
        assert result.fidelity > 50.0
