# Stage 14b — Additional Quality Gates 6 and 7

**Purpose:** Two additional hard gates added by the CORTEX Challenger Framework retrofit. These close silent-failure modes the original five gates do not catch.

These run inside the same convergence loop as Gates 1–5 (max 3 cycles).

## Gate 6 — Implicit Citation Detection (P0)

**Why this gate exists:** Original Gate 3 (Citation Provenance) only catches explicit citations — quoted material with attribution. It misses **implicit citations**: factual claims, biographical assertions, historical statements that are presented as fact in the refined text but came from enrichment sources, not from the source itself.

Without this gate, a refined section could include "Imam Ja'far al-Sadiq lived in the 8th century" — true, but if the source did not include the date, the enrichment added it without being caught by Gate 3 (no quotation marks, no attribution phrase).

**Check:**

For every factual claim, biographical assertion, historical date, place attribution, or quantitative statement in `01-refined/`:

1. Diff the claim against the original `00-source/` content for the same section.
2. If the claim is present in the source → PASS for this claim.
3. If the claim is NOT in the source → it came from enrichment.
4. If from enrichment, verify the editorial notes draft (`_editorial-notes-draft.md`) records:
   - The specific claim.
   - The verifiable source it came from (must be in active tradition's `allowed_enrichment_sources`).
   - The section / location.

**Detection method:**

- Tokenize the refined text into sentences.
- For each sentence containing a date, named figure, place name, or quantitative claim:
  - Extract the claim.
  - Check if a normalized form of the claim appears in source.
  - If not → mark as enrichment-claim → verify in editorial notes.

**Pass criterion:** Every enrichment-claim has a matching editorial notes entry with verifiable source.

**Fail handling:** P0 — halt. Report each unverified claim with location and the source it appears to need. Re-run Stage 10 with stricter enrichment discipline, OR remove the unverified claim, OR add the missing editorial note (with verification).

**Storage:** Append findings to `_quality-gates-report.md` under "Gate 6 — Implicit Citations".

---

## Gate 7 — Per-Section Determinism Check (P1)

**Why this gate exists:** The framework's Determinism Contract (Primitive 6) requires reproducibility. Stages 10 (enrichment) and 11 (analogies) use Haiku-call inference which can produce structurally different output on re-runs even for the same input. A subjective drift in those stages can produce a section that passes Gates 1–5 but is materially different on a second run.

This gate detects that drift by running each section through a deterministic second-pass check.

**Check:**

For each section in `01-refined/`:

1. Compute a structural fingerprint:
   - Word count (must match Stage 14 Gate 5).
   - Sentence count.
   - Paragraph count.
   - Number of substituted phonetic terms.
   - Number of woven analogies (detect by Stage 11's editorial notes count).
   - Number of enrichment bridges (detect by Stage 10's editorial notes count).

2. Re-run Stages 10, 11, 12 on the cleaned input for this section in **dry-run mode** (do not overwrite outputs; produce a parallel `_determinism-check/section-NN.md`).

3. Compute the same fingerprint for the dry-run output.

4. Compare fingerprints:
   - Identical → PASS.
   - Word count differs by > 5% → P1 fail.
   - Sentence/paragraph count differs by > 10% → P1 fail.
   - Substituted phonetic count differs (deterministic check — should be exact match) → P0 fail (Stage 06/12 has a determinism bug).
   - Analogy or enrichment count differs by > 2 → P1 fail (Stage 10/11 non-deterministic beyond tolerance).

**Pass criterion:** All fingerprint deltas within tolerance.

**Fail handling:**
- P0 (phonetic count mismatch) → halt; this is a skill bug.
- P1 (other delta exceeds tolerance) → halt; report which stage drifted; re-run failing stage with seed control, OR mark stage as non-deterministic in editorial notes and proceed only with user acknowledgment.

**Storage:** Append findings to `_quality-gates-report.md` under "Gate 7 — Per-Section Determinism".

**Performance note:** Gate 7 is expensive (re-runs three stages per section). It runs only on the first convergence cycle. If Gates 1–6 fail and trigger re-runs, Gate 7 does not re-run unless explicitly requested (`--strict-determinism` flag), because by definition a re-run is allowed to produce different output if it's correcting a violation.

---

## Integration with Gates 1–5

Gates 6 and 7 sit in the same `playbooks/14-quality-gates.md` execution order, after Gate 5:

| Order | Gate | Severity | Original or framework-added |
|---|---|---|---|
| 1 | No non-Latin script | P0 | Original |
| 2 | No bracketed commentary | P0 | Original |
| 3 | Citation provenance (explicit) | P0 | Original |
| 4 | Section order preserved | P1 | Original |
| 5 | Word count discipline (70-140%) | P1 | Original |
| 6 | Implicit citation detection | P0 | Framework-added |
| 7 | Per-section determinism | P1 | Framework-added |

All gates run on every convergence cycle. The convergence loop in `playbooks/00-cortex-compliance.md` covers them uniformly.

---

## Updated quality-gates-report.md structure

The Stage 14 report now includes Gates 6 and 7:

```markdown
| Gate | Severity | Status | Notes |
|---|---|---|---|
| 1: No non-Latin script | P0 | PASS | 0 violations across 6 files |
| 2: No bracketed commentary | P0 | PASS | 0 forbidden patterns |
| 3: Citation provenance (explicit) | P0 | PASS | 12 explicit citations verified |
| 4: Section order preserved | P1 | PASS | All artifacts consistent |
| 5: Word count discipline | P1 | PASS | All sections within 70-140% (92-118%) |
| 6: Implicit citation detection | P0 | PASS | 8 enrichment-claims, all verified |
| 7: Per-section determinism | P1 | PASS | Fingerprint deltas within tolerance |

## Overall: PASS

Pipeline may proceed to Stage 15 (export).
Convergence: 1 cycle.
```

---

## What this stage does NOT do

- Does not modify the source or the refined output (Gate 6 only verifies; Gate 7 uses a dry-run that gets discarded).
- Does not run on subsequent convergence cycles by default (only first cycle, per performance note above).
- Does not re-run the Stage 14 original gates (those run separately).
