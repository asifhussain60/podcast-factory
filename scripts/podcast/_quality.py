"""_quality.py — PEQ (Podcast Episode Quality) scoring contract.

Canonical definition of the five-axis PEQ rubric used across both the podcast
pipeline and the wisdom pipeline.  Every challenger, convergence loop, and
quality gate imports from here — there is one formula, one threshold table.

FORMULA (K6 — 5-axis)
    PEQ = 0.30 × Fidelity + 0.20 × Voice + 0.18 × Structure
          + 0.17 × Enrichment + 0.15 × Interest

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
    Interest   — curiosity hooks, challenge-defeat arcs, modern relevance
                 signals, and fair framing (no strawman). (K6)

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

import re
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
# Weights (must sum to 1.0) — K6: 5-axis formula
# ---------------------------------------------------------------------------

WEIGHT_FIDELITY   = 0.30
WEIGHT_VOICE      = 0.20
WEIGHT_STRUCTURE  = 0.18
WEIGHT_ENRICHMENT = 0.17
WEIGHT_INTEREST   = 0.15

assert abs(
    WEIGHT_FIDELITY + WEIGHT_VOICE + WEIGHT_STRUCTURE
    + WEIGHT_ENRICHMENT + WEIGHT_INTEREST - 1.0
) < 1e-9

# ---------------------------------------------------------------------------
# Voice-scorer readiness flag
# ---------------------------------------------------------------------------

# Set to True only when the K2+ shared TF-IDF vocabulary has been built via
# build_exemplar_vector() for at least one KSessions archetype. Until then,
# _voice_score() returns 0.0 regardless of whether an exemplar vector is
# supplied, and score() redistributes the Voice weight to Fidelity so the
# total still reaches 100. Flipping this flag without the vocabulary built
# causes meaningless ratio values to silently corrupt PEQ totals.
_VOICE_SCORER_READY = False


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
    interest:   float   # 0–100  (K6)
    total:      float   # 0–100  (weighted sum)
    verdict:    str     # PASS | WARN | FAIL
    notes:      list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "fidelity":   round(self.fidelity,   1),
            "voice":      round(self.voice,       1),
            "structure":  round(self.structure,   1),
            "enrichment": round(self.enrichment,  1),
            "interest":   round(self.interest,    1),
            "total":      round(self.total,       1),
            "verdict":    self.verdict,
            "notes":      self.notes,
        }

    def markdown_table(self) -> str:
        """Return a compact Markdown table for embedding in challenger reports."""
        lines = [
            "| Axis | Weight | Score | Weighted |",
            "|---|---|---|---|",
            f"| Fidelity   | 30% | {self.fidelity:.1f} | {self.fidelity * WEIGHT_FIDELITY:.1f} |",
            f"| Voice      | 20% | {self.voice:.1f} | {self.voice * WEIGHT_VOICE:.1f} |",
            f"| Structure  | 18% | {self.structure:.1f} | {self.structure * WEIGHT_STRUCTURE:.1f} |",
            f"| Enrichment | 17% | {self.enrichment:.1f} | {self.enrichment * WEIGHT_ENRICHMENT:.1f} |",
            f"| Interest   | 15% | {self.interest:.1f} | {self.interest * WEIGHT_INTEREST:.1f} |",
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

    Returns 0.0 when the scorer is not ready (``_VOICE_SCORER_READY = False``)
    or no exemplar vector is available.  ``score()`` detects this and
    redistributes the Voice weight to Fidelity so the total still reaches 100.

    K2+ full implementation: load the shared TF-IDF vocabulary, build the
    chapter bigram vector in that vocabulary's basis, compute cosine similarity
    against the exemplar vector, then set ``_VOICE_SCORER_READY = True``.
    """
    if voice_exemplar_vector is None or not _VOICE_SCORER_READY:
        return 0.0
    # K2+: cosine similarity with shared vocabulary (not yet built).
    # This branch is unreachable while _VOICE_SCORER_READY = False.
    tokens = adapted_text.lower().split()
    bigrams: dict[str, int] = {}
    for i in range(len(tokens) - 1):
        bg = tokens[i] + "_" + tokens[i + 1]
        bigrams[bg] = bigrams.get(bg, 0) + 1
    # TODO K2+: map bigrams to shared vocabulary positions, then compute dot
    # product and cosine similarity. Until then return 0.0.
    return 0.0


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


def _interest_score(adapted_text: str) -> float:
    """Curiosity hooks, challenge-defeat arcs, modern relevance, fair framing. (K6)

    Four sub-signals, each 0–1, averaged and scaled to 100:
      hook       — opening hook: rhetorical question or curiosity-building phrase in
                   the first 20% of the text.
      challenge  — challenge-defeat arc: a problem is raised AND a resolution appears.
      relevance  — modern-relevance signal anywhere in the text.
      fairness   — no strawman markers detected (absence = full credit).
    """
    if not adapted_text.strip():
        return 0.0

    words = adapted_text.split()
    first_20 = " ".join(words[: max(int(len(words) * 0.20), 50)])

    hook_pats = [
        r"what (does|would|if|happens|kind of|makes|drives|compels)",
        r"why (does|would|did|should|is|are|do|must)",
        r"how (does|can|should|is|are|do|did)",
        r"imagine (if|a world|that|for a moment)",
        r"consider (this|the|what|a|that)",
        r"the question (is|was|becomes|facing|at the heart)",
        r"here'?s (the|a|what|why|how|something)",
        r"(let'?s|let us) (begin|start|open|ask|explore|consider)",
    ]
    hook = 1.0 if any(re.search(p, first_20, re.I) for p in hook_pats) else 0.0

    challenge_raise = [
        r"\b(objection|challenge|difficulty|problem|paradox|tension|puzzle|obstacle)\b",
        r"\b(one might (argue|say|object|think|wonder))\b",
        r"\b(it (might|may|could) seem)\b",
        r"\b(but (how|why|what|is this|does this|can))\b",
    ]
    challenge_resolve = [
        r"\b(the answer (is|lies|comes|emerges))\b",
        r"\b(in fact|actually|rather|instead|on the contrary)\b",
        r"\b(resolves?|dissolves?|overcomes?|addresses?|answers? (this|that|the))\b",
    ]
    raised = any(re.search(p, adapted_text, re.I) for p in challenge_raise)
    resolved = any(re.search(p, adapted_text, re.I) for p in challenge_resolve)
    challenge = 1.0 if (raised and resolved) else (0.5 if raised else 0.0)

    relevance_pats = [
        r"\b(today|modern|contemporary|our (time|age|era|world|lives?))\b",
        r"\b(we (find|see|live|face|encounter|grapple))\b",
        r"\b(still (holds?|rings? true|matters?|applies?|speaks?))\b",
        r"\b(resonates?|relevant|speaks? to|timeless)\b",
        r"\b(in (our|this|any|every) (age|era|time|generation|society|context))\b",
    ]
    relevance = 1.0 if any(re.search(p, adapted_text, re.I) for p in relevance_pats) else 0.0

    strawman_deny = [
        r"\bobviously (wrong|false|absurd|incorrect|mistaken)\b",
        r"\bclearly (wrong|mistaken|misguided)\b",
        r"\babsurdly\b",
        r"\b(silly (argument|idea|notion|objection))\b",
        r"\b(no (sane|reasonable|serious) person)\b",
    ]
    fairness = 0.0 if any(re.search(p, adapted_text, re.I) for p in strawman_deny) else 1.0

    combined = (hook + challenge + relevance + fairness) / 4.0
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
    interest   = _interest_score(adapted_text)

    # Redistribute Voice weight to Fidelity when the scorer is not ready or
    # no exemplar vector was supplied, so the total still sums to 100.
    _voice_unavailable = voice_exemplar_vector is None or not _VOICE_SCORER_READY
    if _voice_unavailable:
        total = (
            (WEIGHT_FIDELITY + WEIGHT_VOICE) * fidelity
            + WEIGHT_STRUCTURE  * structure
            + WEIGHT_ENRICHMENT * enrichment
            + WEIGHT_INTEREST   * interest
        )
        notes = ["voice axis unavailable — weight redistributed to fidelity"]
    else:
        total = (
            WEIGHT_FIDELITY   * fidelity
            + WEIGHT_VOICE    * voice
            + WEIGHT_STRUCTURE  * structure
            + WEIGHT_ENRICHMENT * enrichment
            + WEIGHT_INTEREST   * interest
        )
        notes = []

    total = round(min(max(total, 0.0), 100.0), 1)
    return PEQScore(
        fidelity=fidelity,
        voice=voice,
        structure=structure,
        enrichment=enrichment,
        interest=interest,
        total=total,
        verdict=verdict_from_total(total),
        notes=notes,
    )
