"""test_peq_engine.py — Unit tests for the PEQ scoring engine (_quality.py).

Covers edge cases in each of the four axes: Fidelity, Voice, Structure,
Enrichment — plus weight redistribution logic and the verdict thresholds.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "scripts" / "podcast"))

from _quality import (  # noqa: E402
    FAIL,
    PASS,
    WARN,
    PEQScore,
    score,
    verdict_from_total,
    THRESHOLD_PASS,
    THRESHOLD_WARN,
)


# ---------------------------------------------------------------------------
# Verdict thresholds
# ---------------------------------------------------------------------------

class TestVerdictThresholds:
    def test_pass_at_exactly_85(self):
        assert verdict_from_total(85.0) == PASS

    def test_pass_above_85(self):
        assert verdict_from_total(99.9) == PASS

    def test_warn_at_exactly_70(self):
        assert verdict_from_total(70.0) == WARN

    def test_warn_at_84(self):
        assert verdict_from_total(84.9) == WARN

    def test_fail_below_70(self):
        assert verdict_from_total(69.9) == FAIL

    def test_fail_at_zero(self):
        assert verdict_from_total(0.0) == FAIL

    def test_threshold_constants(self):
        assert THRESHOLD_PASS == 85
        assert THRESHOLD_WARN == 70


# ---------------------------------------------------------------------------
# Fidelity axis
# ---------------------------------------------------------------------------

class TestFidelityAxis:
    def test_perfect_match(self):
        result = score(
            citation_ids_source=["quran:2:255", "quran:2:256"],
            citation_ids_found=["quran:2:255", "quran:2:256"],
        )
        assert result.fidelity == 100.0

    def test_zero_overlap(self):
        result = score(
            citation_ids_source=["quran:2:255"],
            citation_ids_found=["quran:3:1"],
        )
        assert result.fidelity == 0.0

    def test_partial_overlap(self):
        result = score(
            citation_ids_source=["quran:2:255", "quran:2:256"],
            citation_ids_found=["quran:2:255"],
        )
        # Jaccard: source={2:255, 2:256}, found={2:255}
        # intersection=1, union=2 → 1/2=50.0
        assert result.fidelity == pytest.approx(50.0, abs=1.0)

    def test_no_source_citations_returns_full_credit(self):
        result = score(
            citation_ids_source=[],
            citation_ids_found=["quran:2:255"],
        )
        assert result.fidelity == 100.0

    def test_extra_citations_in_chapter_penalised(self):
        # Source has 1 citation, chapter has 2 (1 match + 1 extra)
        result = score(
            citation_ids_source=["quran:2:255"],
            citation_ids_found=["quran:2:255", "quran:99:1"],
        )
        # Jaccard: 1/2 = 50.0
        assert result.fidelity == pytest.approx(50.0, abs=1.0)


# ---------------------------------------------------------------------------
# Voice axis
# ---------------------------------------------------------------------------

class TestVoiceAxis:
    def test_no_exemplar_returns_zero(self):
        result = score(adapted_text="some text", voice_exemplar_vector=None)
        assert result.voice == 0.0

    def test_no_exemplar_note_present(self):
        result = score(adapted_text="some text", voice_exemplar_vector=None)
        assert any("voice" in n.lower() for n in result.notes)

    def test_no_exemplar_weight_redistributed_to_fidelity(self):
        # With no exemplar and perfect fidelity + structure, but no enrichment:
        # total = (0.35+0.25)×100 + 0.20×100 + 0.20×0 = 60 + 20 + 0 = 80
        result = score(
            citation_ids_source=[],
            citation_ids_found=[],
            arc_rules=[],
            term_count=0,
            glossed_count=0,
            quran_ref_count=0,
            word_count=100,
            voice_exemplar_vector=None,
        )
        assert result.total == pytest.approx(80.0, abs=1.0)

    def test_exemplar_provided_returns_nonzero(self):
        result = score(
            adapted_text="the quick brown fox jumps over the lazy dog",
            voice_exemplar_vector=[1.0] * 8,
        )
        assert result.voice > 0.0


# ---------------------------------------------------------------------------
# Structure axis
# ---------------------------------------------------------------------------

class TestStructureAxis:
    def test_no_arc_rules_returns_100(self):
        result = score(arc_rules=[], arc_labels_found=[])
        assert result.structure == 100.0

    def test_all_rules_met(self):
        result = score(
            arc_rules=["open_hook", "three_points", "close"],
            arc_labels_found=["open_hook", "three_points", "close"],
        )
        assert result.structure == 100.0

    def test_no_rules_met(self):
        result = score(
            arc_rules=["open_hook", "three_points", "close"],
            arc_labels_found=[],
        )
        assert result.structure == 0.0

    def test_partial_rules_met(self):
        result = score(
            arc_rules=["open_hook", "three_points", "close"],
            arc_labels_found=["open_hook"],
        )
        assert result.structure == pytest.approx(33.33, abs=1.0)

    def test_extra_labels_not_penalised(self):
        result = score(
            arc_rules=["open_hook"],
            arc_labels_found=["open_hook", "extra_label_not_in_rules"],
        )
        assert result.structure == 100.0


# ---------------------------------------------------------------------------
# Enrichment axis
# ---------------------------------------------------------------------------

class TestEnrichmentAxis:
    def test_zero_words_returns_zero(self):
        result = score(word_count=0)
        assert result.enrichment == 0.0

    def test_fully_glossed_no_quran(self):
        result = score(
            term_count=10, glossed_count=10,
            quran_ref_count=0, word_count=500,
        )
        # glossing=1.0, quran_density=0 → combined=0.70 → 70.0
        assert result.enrichment == pytest.approx(70.0, abs=1.0)

    def test_quran_density_capped_at_one(self):
        # 50 refs per 100 words would normally exceed 1.0 — must be capped
        result = score(
            term_count=0, glossed_count=0,
            quran_ref_count=500, word_count=100,
        )
        # glossing=0, quran_density=1.0 (capped) → 0.30 × 100 = 30
        assert result.enrichment == pytest.approx(30.0, abs=1.0)

    def test_perfect_enrichment(self):
        result = score(
            term_count=10, glossed_count=10,
            quran_ref_count=100, word_count=100,
        )
        # glossing=1.0 (×0.70) + quran_density=1.0 (×0.30) = 1.0 → 100
        assert result.enrichment == pytest.approx(100.0, abs=1.0)


# ---------------------------------------------------------------------------
# Full score integration
# ---------------------------------------------------------------------------

class TestFullScore:
    def test_result_is_peqscore_instance(self):
        result = score()
        assert isinstance(result, PEQScore)

    def test_total_clamped_to_100(self):
        result = score(
            citation_ids_source=[], citation_ids_found=[],
            arc_rules=[], arc_labels_found=[],
            term_count=10, glossed_count=10,
            quran_ref_count=100, word_count=100,
        )
        assert result.total <= 100.0

    def test_total_clamped_to_zero(self):
        result = score(
            citation_ids_source=["quran:2:255"],
            citation_ids_found=[],
            arc_rules=["open_hook", "close"],
            arc_labels_found=[],
            term_count=10, glossed_count=0,
            quran_ref_count=0, word_count=500,
        )
        assert result.total >= 0.0

    def test_deterministic(self):
        """Calling score() twice with the same inputs returns the same result."""
        kwargs = dict(
            adapted_text="In the name of God",
            citation_ids_source=["quran:1:1"],
            citation_ids_found=["quran:1:1"],
            arc_rules=["open_hook"],
            arc_labels_found=["open_hook"],
            term_count=5, glossed_count=3,
            quran_ref_count=1, word_count=200,
        )
        r1 = score(**kwargs)
        r2 = score(**kwargs)
        assert r1.total == r2.total
        assert r1.verdict == r2.verdict

    def test_word_count_defaults_to_text_length(self):
        """If word_count is None, it should be derived from adapted_text."""
        text = "word " * 100
        result_explicit = score(adapted_text=text, word_count=100)
        result_implicit = score(adapted_text=text, word_count=None)
        assert result_explicit.total == result_implicit.total

    def test_as_dict_keys(self):
        result = score()
        d = result.as_dict()
        for key in ("fidelity", "voice", "structure", "enrichment", "total", "verdict", "notes"):
            assert key in d

    def test_markdown_table_contains_total(self):
        result = score()
        table = result.markdown_table()
        assert "**Total**" in table
        assert str(round(result.total, 1)) in table
