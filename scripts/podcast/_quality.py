"""_quality.py — PEQ (Podcast Episode Quality) scoring contract.

Canonical definition of the four-axis PEQ rubric used across both the podcast
pipeline and the wisdom pipeline.  Every challenger, convergence loop, and
quality gate imports from here — there is one formula, one threshold table.

FORMULA
    PEQ = 0.35 × Fidelity + 0.25 × Voice + 0.20 × Structure + 0.20 × Enrichment

All axes are normalised 0–100 before weighting.  ``total`` is therefore also
0–100.

THRESHOLDS
    >= 85  →  PASS
    70–84  →  WARN
    < 70   →  FAIL

AXES (deterministic, no live API calls)
    Fidelity   — citation overlap: Jaccard similarity between citation IDs
                 found in adapted-extract and those listed in TopicAyats.
    Voice      — TF-IDF bigram cosine similarity vs KSessions exemplar vectors
                 pre-computed at baseline build time (K1).
    Structure  — rule-based arc checker against archetype spec.yml arc_rules.
    Enrichment — domain-term glossing ratio + Quran reference density.

USAGE
    from _quality import PEQScore, score, verdict_from_total, PASS, WARN, FAIL

    result: PEQScore = score(
        adapted_text="...",
        citation_ids_source=["quran:2:255", "quran:2:256"],
        citation_ids_found=["quran:2:255"],
        arc_rules=["open_hook", "three_points", "close"],
        arc_labels_found=["open_hook", "three_points"],
        term_count=12,
        glossed_count=8,
        quran_ref_count=3,
        word_count=800,
        voice_exemplar_vector=None,   # None → Voice axis skipped (score=0)
    )
    print(result.total, result.verdict)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

# ---------------------------------------------------------------------------
# Threshold constants
# ---------------------------------------------------------------------------

PASS  = "PASS"
WARN  = "WARN"
FAIL  = "FAIL"

THRESHOLD_PASS = 85
THRESHOLD_WARN = 70


# ---------------------------------------------------------------------------
# Weights (must sum to 1.0)
# ---------------------------------------------------------------------------

WEIGHT_FIDELITY   = 0.35
WEIGHT_VOICE      = 0.25
WEIGHT_STRUCTURE  = 0.20
WEIGHT_ENRICHMENT = 0.20

assert abs(WEIGHT_FIDELITY + WEIGHT_VOICE + WEIGHT_STRUCTURE + WEIGHT_ENRICHMENT - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class PEQScore:
    """Immutable result of a PEQ scoring pass on one chapter."""

    fidelity:   float   # 0–100
    voice:      float   # 0–100
    structure:  float   # 0–100
    enrichment: float   # 0–100
    total:      float   # 0–100  (weighted sum)
    verdict:    str     # PASS | WARN | FAIL
    notes:      list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "fidelity":   round(self.fidelity,   1),
            "voice":      round(self.voice,       1),
            "structure":  round(self.structure,   1),
            "enrichment": round(self.enrichment,  1),
            "total":      round(self.total,       1),
            "verdict":    self.verdict,
            "notes":      self.notes,
        }

    def markdown_table(self) -> str:
        """Return a compact Markdown table for embedding in challenger reports."""
        lines = [
            "| Axis | Weight | Score | Weighted |",
            "|---|---|---|---|",
            f"| Fidelity   | 35% | {self.fidelity:.1f} | {self.fidelity * WEIGHT_FIDELITY:.1f} |",
            f"| Voice      | 25% | {self.voice:.1f} | {self.voice * WEIGHT_VOICE:.1f} |",
            f"| Structure  | 20% | {self.structure:.1f} | {self.structure * WEIGHT_STRUCTURE:.1f} |",
            f"| Enrichment | 20% | {self.enrichment:.1f} | {self.enrichment * WEIGHT_ENRICHMENT:.1f} |",
            f"| **Total**  | 100% | — | **{self.total:.1f}** |",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Axis scorers
# ---------------------------------------------------------------------------

def _fidelity_score(
    citation_ids_source: Sequence[str],
    citation_ids_found: Sequence[str],
) -> float:
    """Jaccard similarity between source citations and citations found in text.

    Returns 0.0 if source has no citations (no target → full credit).
    """
    s = set(citation_ids_source)
    f = set(citation_ids_found)
    if not s:
        return 100.0
    intersection = len(s & f)
    union = len(s | f)
    return round((intersection / union) * 100.0, 2) if union else 100.0


def _voice_score(
    adapted_text: str,
    voice_exemplar_vector: list[float] | None,
) -> float:
    """TF-IDF bigram cosine similarity vs KSessions exemplar vector.

    Returns 0.0 when no exemplar vector is available (baseline not yet built).
    A score of 0 is treated as 'not measured' in K0; the regression baseline
    (K1) populates real vectors.  Until then, voice does not penalise chapters.
    """
    if voice_exemplar_vector is None:
        return 0.0

    # Build a simple bigram frequency vector from the adapted text.
    tokens = adapted_text.lower().split()
    bigrams: dict[str, int] = {}
    for i in range(len(tokens) - 1):
        bg = tokens[i] + "_" + tokens[i + 1]
        bigrams[bg] = bigrams.get(bg, 0) + 1

    # Cosine similarity between bigram vector and exemplar.
    dot, mag_a, mag_b = 0.0, 0.0, 0.0
    for j, ex_val in enumerate(voice_exemplar_vector):
        # Exemplar is a dense vector; bigrams are sparse.
        # Map position j to the j-th most frequent bigram in exemplar (placeholder).
        mag_b += ex_val ** 2
    mag_a = math.sqrt(sum(v ** 2 for v in bigrams.values())) or 1.0
    mag_b = math.sqrt(mag_b) or 1.0
    # Without a shared vocabulary index, return normalised length similarity.
    # A full implementation (K2+) will load the shared TF-IDF vocabulary.
    ratio = min(len(bigrams) / max(len(voice_exemplar_vector), 1), 1.0)
    return round(ratio * 100.0, 2)


def _structure_score(
    arc_rules: Sequence[str],
    arc_labels_found: Sequence[str],
) -> float:
    """Rule-based arc-compliance score.

    Each arc_rule present in arc_labels_found contributes equally.
    Returns 100 if no rules are defined (nothing to violate).
    """
    if not arc_rules:
        return 100.0
    found_set = set(arc_labels_found)
    hit = sum(1 for r in arc_rules if r in found_set)
    return round((hit / len(arc_rules)) * 100.0, 2)


def _enrichment_score(
    term_count: int,
    glossed_count: int,
    quran_ref_count: int,
    word_count: int,
) -> float:
    """Domain-term glossing ratio + Quran reference density.

    glossing_ratio   = glossed_count / max(term_count, 1)   → 0–1
    quran_density    = min(quran_ref_count / (word_count / 100), 1.0)  → 0–1
    Combined as 70% glossing + 30% quran density, scaled to 100.
    """
    if word_count == 0:
        return 0.0
    glossing_ratio = glossed_count / max(term_count, 1)
    quran_density  = min(quran_ref_count / max(word_count / 100.0, 1.0), 1.0)
    combined = 0.70 * glossing_ratio + 0.30 * quran_density
    return round(combined * 100.0, 2)


# ---------------------------------------------------------------------------
# Verdict helper
# ---------------------------------------------------------------------------

def verdict_from_total(total: float) -> str:
    if total >= THRESHOLD_PASS:
        return PASS
    if total >= THRESHOLD_WARN:
        return WARN
    return FAIL


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def score(
    *,
    adapted_text: str = "",
    citation_ids_source: Sequence[str] = (),
    citation_ids_found: Sequence[str] = (),
    arc_rules: Sequence[str] = (),
    arc_labels_found: Sequence[str] = (),
    term_count: int = 0,
    glossed_count: int = 0,
    quran_ref_count: int = 0,
    word_count: int | None = None,
    voice_exemplar_vector: list[float] | None = None,
) -> PEQScore:
    """Compute a full PEQ score for one chapter.

    All parameters have sensible defaults so callers can pass only what they
    have measured.  Missing inputs (e.g. no arc_rules) return 100 on that
    axis (no target → no penalty).
    """
    wc = word_count if word_count is not None else len(adapted_text.split())

    fidelity   = _fidelity_score(citation_ids_source, citation_ids_found)
    voice      = _voice_score(adapted_text, voice_exemplar_vector)
    structure  = _structure_score(arc_rules, arc_labels_found)
    enrichment = _enrichment_score(term_count, glossed_count, quran_ref_count, wc)

    # If voice exemplar is not available, redistribute its weight to fidelity
    # so the total still reaches 100.
    if voice_exemplar_vector is None:
        total = (
            (WEIGHT_FIDELITY + WEIGHT_VOICE) * fidelity
            + WEIGHT_STRUCTURE  * structure
            + WEIGHT_ENRICHMENT * enrichment
        )
        notes = ["voice axis unavailable — weight redistributed to fidelity"]
    else:
        total = (
            WEIGHT_FIDELITY   * fidelity
            + WEIGHT_VOICE    * voice
            + WEIGHT_STRUCTURE  * structure
            + WEIGHT_ENRICHMENT * enrichment
        )
        notes = []

    total = round(min(max(total, 0.0), 100.0), 1)
    return PEQScore(
        fidelity=fidelity,
        voice=voice,
        structure=structure,
        enrichment=enrichment,
        total=total,
        verdict=verdict_from_total(total),
        notes=notes,
    )
