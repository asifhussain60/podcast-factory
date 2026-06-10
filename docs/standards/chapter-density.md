# Chapter Density Standard — Podcast Factory

**Status:** Adopted · **Date:** 2026-06-10  
**Audit tool:** `scripts/podcast/chapter_density_audit.py`  
**Owner:** Pipeline

---

## The Problem

Downloaded NotebookLM Audio Overviews for the master-and-the-disciple, ayyuhal-walad, kitab-al-riyad, and journey-to-the-west-vol-1 were consistently overlong and cognitively exhausting. The root cause is that each chapter was cramming 7–18 distinct concept-level topics into a single podcast episode — 4–6× more than a listener can retain in one sitting.

This document codifies the target, explains the measurement method, presents the audit findings across every book in the pipeline, and describes the remediation strategy.

---

## The Target

**2–3 concept sections per episode.**

One concept section = one `## H2` heading in the rendered chapter `.txt` file (excluding structural frame headings: "Where this episode opens", "What this episode lands", "Closing").

Secondary signal: **~1 500–2 500 words per concept section** (~10–18 minutes of audio at 150 wpm). A chapter of 3 concepts × 1 800 words = 5 400 words ≈ 36 minutes — a natural podcast length.

| Metric | Target | Warning | Fail |
|---|---|---|---|
| Concept sections per chapter | ≤ 3 | 4 | ≥ 5 |
| Words per concept section | 1 500–2 500 | < 800 or > 3 500 | < 400 or > 5 000 |
| Density score (0–10) | ≤ 5 | 5–7 | > 7 |

---

## Audit Findings (2026-06-10)

Run with `python3 scripts/podcast/chapter_density_audit.py`:

```
SUMMARY: 35 chapters total | ✅ 8 PASS | ⚠️ 1 WARN | ❌ 26 FAIL
```

### Per-Book Breakdown

| Book | Chapters | Avg concepts/ch | Max concepts | PASS | WARN | FAIL | Episodes after split | Expansion |
|---|---|---|---|---|---|---|---|---|
| Islamic/the-master-and-the-disciple | 5 | 11.8 | 14 | 0 | 0 | 5 | 20 | **4.0×** |
| Islamic/ayyuhal-walad | 4 | 7.2 | 8 | 0 | 0 | 4 | 12 | **3.0×** |
| Islamic/kitab-al-riyad | 15 | 11.1 | 18 | 3 | 1 | 12 | 60 | **4.0×** |
| Fiction/journey-to-the-west-vol-1 | 5 | 12.4 | 15 | 0 | 0 | 5 | 22 | **4.4×** |
| Guides/healthequity | 3 | 0.7 | 2 | 3 | 0 | 0 | 3 | 1.0× |
| Technical/claude-code-training | 3 | 0 | 0 | 3 | 0 | 0 | 3 | 1.0× |

### Worst offenders

| Chapter | Concepts | Status |
|---|---|---|
| kitab-al-riyad/ch14-tawhid-and-the-critique-of-al-mahsul | 18 | ❌ FAIL |
| kitab-al-riyad/ch03-the-soul-in-time | 17 | ❌ FAIL |
| kitab-al-riyad/ch12-the-shariah-of-adam | 17 | ❌ FAIL |
| journey-to-the-west-vol-1/ch03-four-seas-bow-in-submission | 15 | ❌ FAIL |
| the-master-and-the-disciple/ch04b-the-disciple-becomes-master | 15 | ❌ FAIL |

### Books already within target

Healthequity and Claude Code Training chapters have no `## H2` concept sections (they use different structural conventions). They pass the density gate by default; no remediation needed.

Kitab al-Riyad chapters 1, 4, and 15 (summary chapters) pass on concept count — though note that ch01 has a density score of 10/10 because its 3 concepts average 2 152 words each (very dense prose). This is a secondary signal worth watching but not a gate failure.

---

## The Measurement Algorithm

**File:** `scripts/podcast/chapter_density_audit.py`

**Concept detection** — splits each chapter `.txt` on `## ` headings, classifies each heading as either a _concept section_ or a _frame section_ using a regex:

```python
_FRAME_PATTERNS = re.compile(
    r"^##\s+(where\s+this\s+episode\s+(opens|picks\s+up)"
    r"|what\s+this\s+episode\s+lands"
    r"|closing\s*(turn)?"
    r"|the\s+frame)\s*$",
    re.IGNORECASE,
)
```

Frame sections are excluded from the concept count; they are structural bookkeeping present in every chapter regardless of content.

**Density score** — a 0–10 composite:

```
density_score = min(10, (concept_count × words_per_concept) / (max_concepts × 1800) × 10)
```

**Status thresholds:**

```
PASS  = concept_count ≤ 3
WARN  = concept_count == 4
FAIL  = concept_count ≥ 5
```

**Suggested split** — for failing chapters the algorithm groups consecutive concept sections into `ceil(n / max_concepts)` equal-sized sub-episodes, preserving narrative order.

---

## Why Chapters Are So Dense: Root Cause

The density problem originates at Phase 0d (chapter design). The current chapter-design prompt asks the LLM to "cover the chapter comprehensively" without an explicit concept-count ceiling. Given that the source texts are dense scholarly Arabic works with many sub-topics per chapter, the model naturally surfaces every H2-worthy discussion point rather than selecting 2–3 for a single episode.

The secondary amplifier is Phase 0e (enrich), which adds contextual commentary and historical footnotes within each concept section, further expanding word counts without splitting the episode boundary.

---

## Remediation Plan

The remediation operates at three layers: the pipeline's chapter-design phase (fixes new books at source), the chapter-contract schema (adds a density gate), and the existing chapters (retroactive splitting).

### Layer 1 — Phase 0d: Enforce density ceiling in chapter design prompt

In `scripts/podcast/phases/initial_driver.py` (or whichever module generates the chapter design LLM prompt), add an explicit constraint:

> **Density rule (MANDATORY):** Each chapter covers exactly 2–3 concept-level topics. If the source chapter contains more than 3 distinct topics, split it into multiple episodes now. Each episode must be independently coherent — it opens with context and closes with a landing. Never assign more than 3 H2 concept headings to a single episode. This is not a suggestion; it is a hard ceiling enforced by the pre-flight smoke gate.

The word "MANDATORY" and the gate reference are intentional: the model must understand this is a pre-commit check, not style guidance.

Verify by re-running `chapter_density_audit.py --violations-only` after any new book's Phase 0d completes. If violations are present, halt the pipeline before Phase 0e.

### Layer 2 — Pre-flight smoke gate: add density check

In `scripts/podcast/phases/preflight_chapter.py` (the `smoke_check_book` function), add a density gate alongside the existing word-count gate:

```python
from chapter_density_audit import audit_chapter, DEFAULT_MAX_CONCEPTS

density = audit_chapter(chapter_path, slug, bucket)
if density.status == "FAIL":
    failures.append((
        chapter_slug,
        f"density gate: {density.concept_count} concepts "
        f"(max {DEFAULT_MAX_CONCEPTS}) — split required before authoring"
    ))
```

This halts the per-chapter loop at `$0` cost before any framing/convergence LLM spend on an over-dense chapter.

### Layer 3 — Retroactive split for existing chapters

For chapters already authored, the algorithm generates suggested splits (run with `--remediate` flag). The split plan preserves the original concept titles and groups them into coherent sub-episodes. The remediation workflow is:

1. **Audit:** `python3 scripts/podcast/chapter_density_audit.py --slug <slug> --remediate`
2. **Review splits** — confirm groupings make narrative sense. The algorithm groups by count; a human may want to regroup by thematic arc.
3. **Re-run Phase 0d** for the book with the density constraint active, which will produce new chapter contracts with correct episode boundaries.
4. **Regenerate chapters** via `--retry-phase per-chapter` on the book branch.
5. **Re-run Phase 0g** audit.

For the master-and-the-disciple specifically: the 5 existing chapters should produce ~20 episodes after splitting. This is the correct scope for the book — it is a dense tenth-century theological dialogue, not a breezy narrative.

### Suggested split schedules

The following tables are generated by `--remediate` and reviewed manually. Treat concept groupings as starting proposals, not final chapter boundaries.

#### Islamic/the-master-and-the-disciple (5 → 20 episodes)

| Current chapter | Concepts | Sub-episodes | Suggested groupings |
|---|---|---|---|
| ch01a-true-sources-of-knowledge | 11 | 4 | Opening scene + warnings + Persian scholar story ∣ Search for disciple + test of speech ∣ Glorification + hearing/sight/heart ∣ Five conditions + covenant |
| ch02b-spiritual-symbols | 14 | 5 | Originator/inheritor + 3 primordial words ∣ Light & seven + heavens & twelves ∣ Bismillah + chosen ranks + heavenly mirror ∣ Seven nutaqa' + zahir/batin ∣ Worldly symbols + Air + al-Awan |
| ch03a-knowledge-versus-action | 13 | 5 | Inner within inner + 3 creatures + angelic level ∣ Strategy/strength + dream of Joseph ∣ King's vision + union of inner/outer ∣ Why scholars look pale + divine justice ∣ Ranks of religion + five-portion division |
| ch04b-the-disciple-becomes-master | 15 | 5 | Sheikh address + name dialogue + seven days ∣ Returning home + forty-years syllogism ∣ Opposing scholar arrival + fairness + proper seeking ∣ Triad at door + receiving guest + kasra ∣ Jewels/forged glass + moon-sighting + description of religion |
| ch05-unity-justice-and-living-witness | 14 | 5 | Who is Allah + from name or attribute ∣ Syllogism of divine justice + hierarchy of witnesses ∣ Conspiracy formula + same formula across communities ∣ Turning consensus argument + unbroken chain + no fatra ∣ Friends in concealment + scholars who serve oppressors + path of return |

#### Islamic/ayyuhal-walad (4 → 12 episodes)

| Current chapter | Concepts | Sub-episodes |
|---|---|---|
| ch01-knowledge-without-action | 8 | 3 |
| ch02-the-path-of-obedience-and-struggle | 7 | 3 |
| ch03-the-shaykh-and-the-disciples-rule-of-life | 7 | 3 |
| ch04-eight-admonitions-and-a-closing-prayer | 7 | 3 |

#### Islamic/kitab-al-riyad (15 → 60 episodes)

Kitab al-Riyad is the most severely affected. Its 15 source chapters map to 60 episodes after splitting, with the densest chapters (ch03, ch12, ch14 at 17–18 concepts each) requiring 6 sub-episodes. The summary chapters (ch01 with 3 concepts, ch04 with 3 concepts, ch15 with 4 concepts) are already close to target; ch01 and ch04 pass; ch15 is WARN and needs one split.

Run `chapter_density_audit.py --slug kitab-al-riyad --remediate` for the full per-chapter split plan.

#### Fiction/journey-to-the-west-vol-1 (5 → 22 episodes)

Each chapter averages 12.4 concepts and needs 4–5 sub-episodes. The chapters follow a strong scene-by-scene narrative arc, which makes concept-grouping by scene boundary natural and clean. Run `--remediate` for the full plan.

---

## Integration with Pipeline Phases

```
Phase 0d (chapter design)
  └─ ENFORCE: max 3 concepts per episode in LLM prompt
  └─ OUTPUT: chapter contracts with bounded concept count

Phase 0e (enrich)
  └─ RESPECT: do not add new H2 sections; only deepen existing ones

Pre-flight smoke gate (preflight_chapter.py)
  └─ GATE: chapter_density_audit.audit_chapter() — halt if FAIL

Per-chapter authoring loop
  └─ INPUT: chapter .txt already within density target
  └─ NO CHANGE needed here

Phase 0g (bundle audit)
  └─ ADD: run chapter_density_audit in post-authoring check as advisory signal

chapter_density_audit.py --violations-only (session start check)
  └─ RECOMMEND: run on any branch before per-chapter loop begins
```

---

## Running the Auditor

```bash
# Full audit, all books
python3 scripts/podcast/chapter_density_audit.py

# One book with remediation plan
python3 scripts/podcast/chapter_density_audit.py --slug the-master-and-the-disciple --remediate

# Only show violations
python3 scripts/podcast/chapter_density_audit.py --violations-only

# JSON output for CI or downstream tooling
python3 scripts/podcast/chapter_density_audit.py --json

# Raise the target (e.g., allow 4 concepts during a transition period)
python3 scripts/podcast/chapter_density_audit.py --max-concepts 4
```

Exit codes: `0` = all pass, `1` = at least one FAIL, `2` = no chapters found.

---

## Open Questions

1. **Kitab al-Riyad summary chapters** (ch01, ch04, ch15): they pass the concept-count gate but have very high word counts per concept. Should a secondary `words_per_concept > 3500` gate be added? Decision deferred to next pipeline review.

2. **Technical and Guides chapters**: currently use prose without `## H2` headings, so they pass the density gate vacuously. When these books get headings, re-run the auditor.

3. **Split boundary quality**: the algorithm groups by count, not by thematic arc. For the master-and-the-disciple, manual review of the split groupings is recommended before re-running Phase 0d.
