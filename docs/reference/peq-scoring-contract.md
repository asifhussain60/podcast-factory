# PEQ Scoring Contract

## What it is

PEQ (Podcast Episode Quality) is the canonical quality metric for both the podcast pipeline and the wisdom pipeline. It replaces free-form PASS/WARN/FAIL verdicts with a deterministic, reproducible four-axis score that can be trended, regressed against, and used as a hard gate.

## Formula

`PEQ = 0.35 × Fidelity + 0.25 × Voice + 0.20 × Structure + 0.20 × Enrichment`

All four axes are normalised to 0–100. The total is therefore also 0–100.

## Thresholds

| Score | Verdict |
|---|---|
| ≥ 85 | PASS |
| 70–84 | WARN |
| < 70 | FAIL |

## Axes

### Fidelity (weight: 35%)

> Does the adapted chapter contain the citations the source material calls for?

Jaccard similarity between citation IDs listed in the source's TopicAyats and citation IDs found in the adapted extract. Returns 100 when the source declares no citations (no target → no penalty).

### Voice (weight: 25%)

> Does the chapter sound like the established KSessions teaching style?

TF-IDF bigram cosine similarity between the adapted text and a pre-computed voice exemplar vector derived from shipped KSessions chapters. Returns 0 when no exemplar is available; in that case the Voice weight is redistributed to Fidelity so the total still reaches 100.

### Structure (weight: 20%)

> Does the chapter follow the archetype's arc rules?

Proportion of required arc labels (defined in the archetype's `spec.yml arc_rules`) that are present in the chapter. Returns 100 when no arc rules are defined.

### Enrichment (weight: 20%)

> Is the chapter enriched with glossed terms and Quran references?

Weighted combination of two sub-signals:
- Glossing ratio: 70% weight — glossed domain terms ÷ total domain terms
- Quran density: 30% weight — Quran references per 100 words (capped at 1.0)

## Where it is implemented

- **Scoring engine**: `scripts/podcast/_quality.py` — `PEQScore` dataclass and `score()` function
- **Database table**: `scripts/podcast/schema/019_quality_scores.sql`
- **Podcast challenger integration**: `scripts/podcast/intelligence/challenger_scoring.py`
- **Wisdom challenger**: `tools/content_challenger/wisdom/challenge_auto.py` (PEQ section appended to report)
- **Convergence gate**: `scripts/podcast/orchestrate_book.py` — advances only when `peq_total >= 70`
- **Wisdom seal gate**: `tools/content_translator/stages/seal.py` — blocked on `peq_total < 70` unless `--force`
- **Regression tests**: `tests/regression/test_peq_regression.py`
- **Baselines**: `_workspace/test-strategy/baselines/*.json`

## Report format

Every challenger report that runs through the PEQ scorer includes a section in this shape:

```
## PEQ Score

| Axis | Weight | Score | Weighted |
|---|---|---|---|
| Fidelity   | 35% | 87.3 | 30.6 |
| Voice      | 25% | 72.0 | 18.0 |
| Structure  | 20% | 100.0 | 20.0 |
| Enrichment | 20% | 81.5 | 16.3 |
| **Total**  | 100% | — | **84.9** |

**Verdict: WARN** — total 84.9 (threshold 85 for PASS)
```

## Non-negotiable rules

1. The weights in `_quality.py` are the single source of truth. No other file hard-codes `0.35`, `0.25`, `0.20`.
2. The Voice axis never blocks a chapter when no exemplar vector is available (baseline not yet built). It redistributes its weight to Fidelity silently.
3. The scoring function is deterministic — calling `score()` twice with the same inputs returns the same result.
4. A chapter whose total drops more than 5 points below its K1 baseline fails `test_peq_regression.py`.
