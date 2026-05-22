---
schema_version: 1
name: blueprint-protocol
authored: 2026-05-20
authored_by: claude-opus-4.7 (P24.1 scaffold for operator review)
status: SCAFFOLD
applies_to: |
  All books processed by the /podcast pipeline. The blueprint protocol activates
  in slot 05.5-blueprint between the P22 transcript-review resume and the
  existing 06-phonetics stage. Books past slot 05.5 at protocol-introduction
  time (asaas-al-taveel mid-0b, kitab-al-riyad at 0d→0e) are NOT replanned.
consumes:
  - <book>/_system/source/text/refined-english.md   # post-P22-approval English transcript
  - <book>/operator-review.md                       # P22 comments (optional)
  - <book>/arc-conventions.md                       # operator-edited; if present, Layer 3 is no-op
consumed_by:
  - scripts/podcast/_blueprint.py                   # three-layer dispatch
  - scripts/podcast/_authoring.py                   # phases 06-phonetics, 07-chapter-design, 08-enrichment, 11-per-chapter
  - scripts/podcast/orchestrate_book.py             # slot 05.5-blueprint integration
related_protocols:
  - P22-transcript-review-gate    # blueprint depends on operator-approved refined-english.md
  - P23-episode-format-contract   # blueprint seeds the audience_profile + source_tradition fields
  - P17.1-source-adapter          # blueprint reads which source adapter produced refined-english.md
locked_decisions:
  - name: "podcast-blueprint (NOT podcast-arc or any synonym)"
  - pipeline_slot: "phase 0b.5 (orchestrator slug 05.5-blueprint)"
  - model_upgrade: "Layer 1 → Layer 2/3 via classification.recommended_model_for_layer_2; --force-model overrides"
  - arc_conventions: "OPTIONAL input; agent-seeded DRAFT on first run; operator-editable; Layer 3 NEVER overwrites"
---

# Blueprint Protocol — operator handbook

A content-aware episode-structure planner. Given a refined English translation (post-P22), `podcast-blueprint` classifies the source — genre, density, narrative mode, structural units, cross-reference load, vocabulary contestedness — and proposes an episode breakdown tailored to that content.

> **Anti-requirement.** There is NO global episode template. NO one-size-fits-all defaults. Every book is classified, every book gets its own [arc-conventions.md](../../../#per-book-arc-conventions), every book's planning mode is genre-appropriate.

## 1. Why this exists

The pipeline today applies the same episode-shape assumptions to every book — a tribunal-arc polemic, a chronological memoir, a problem/solution self-help book, and a vignette essay collection all flow through `06-phonetics` → `07-chapter-design` → `08-enrichment` → `11-per-chapter` framing with no upstream classification. The chapter-design phase reverse-engineers structure from `refined-english.md` without ever asking "what kind of book is this?"

P24 inserts that question — and answers it — BEFORE the downstream phases bake assumptions in. The answer becomes:

- A `classification.json` (Layer 1)
- An `episode-plan.md` (Layer 2)
- A DRAFT `arc-conventions.md` (Layer 3, first run only)

## 2. The three layers

| Layer | Model | Reads | Writes | Operator gate |
|---|---|---|---|---|
| **1 — scan/classify** | Haiku (default; classifier may self-upgrade if signals warrant) | `refined-english.md`, `operator-review.md` (if present), `arc-conventions.md` (if present) | `_system/blueprint/classification.json`, `_system/blueprint/proposed-config.yaml` | Halts rc=3 unless `--auto-approve-blueprint` |
| **2 — episode planner** | Per Layer 1's `recommended_model_for_layer_2`; `--force-model` overrides | `classification.json`, `refined-english.md`, `arc-conventions.md` (if present) | `_system/blueprint/episode-plan.md` | No halt |
| **3 — convention emitter** | Same as Layer 2 | `classification.json` only | `<book>/arc-conventions.md` (DRAFT, first run only) | No halt; merges `proposed-config.yaml` into `series-config.yaml` |

Cost ledger records `agent_id=podcast-blueprint, layer={1|2|3}, model_used=<actual>, model_recommended=<from-layer-1>, model_overridden_by_operator=<bool>` for every layer call.

## 3. The planning modes

| Mode | Best for genre | Episode shape |
|---|---|---|
| `tribunal_arc` | `polemic_tribunal` | Accuser → defense → verdict cycles; recap recalls last verdict |
| `chronological` | `memoir`, `exegesis`, `epistle` (when linear) | Time-anchored events; recap restates the last event chain |
| `problem_solution` | `self_help` | Each episode states a problem + arrives at a tactic; recap restates last tactic |
| `vignette_grid` | `essay_collection`, `exegesis` (non-linear) | Self-contained essays; recap is light; preview is curiosity-anchored |
| `dialectical_pairs` | `didactic_dialogue` | Thesis paired with response; recap restates the prior dialogue's arc |

Layer 1 selects the mode; operator can override before `--approve-blueprint`.

## 4. The P23 synergy (load-bearing)

P23's [Episode Format Contract](./episode-format-contract.md) activates only when `series-config.yaml` declares an `audience_profile`. Without P24, the operator types that field by hand before any content has been read. **With P24**, Layer 1 emits `recommended_audience_profile` (one of `traditional | modern-secular | clinical-wellness | academic`) AND `recommended_source_tradition` (a tradition-slug or `null`) AND writes them into `proposed-config.yaml`. On `--approve-blueprint`, the orchestrator merges that patch into `<book>/series-config.yaml`, activating P23's `ContractView` for Phase 0e + Phase 11 framing.

Net effect:
1. Operator approves the P22 transcript.
2. Blueprint Layer 1 reads it (Haiku, <$0.05 typical), proposes profile + tradition.
3. Operator reviews `classification.json` and the proposed patch.
4. Operator approves → series-config.yaml gains the field → P23 activates → downstream phases automatically apply the right honorifics density, citation form, source-language preservation, etc.

If the operator REJECTS Layer 1's recommendation (clears the `audience_profile` field in the patch), P23 stays inactive — that book runs with pre-P23 behavior. Zero regression.

## 5. The arc-conventions.md lifecycle

```
First blueprint run for <book>:
  Layer 1 → classification.json (proposes audience_profile + source_tradition)
  Operator: review, edit, approve
  Layer 2 → episode-plan.md
  Layer 3 → arc-conventions.md DRAFT  ← here
  Orchestrator → series-config.yaml merged from proposed-config.yaml
  Hands off to 06-phonetics

Operator-editing window (between runs):
  Operator edits <book>/arc-conventions.md freely
  Operator may delete it to force a re-seed on the next blueprint run

Subsequent blueprint run for <book>:
  Layer 1 → classification.json (recomputes if source_signature changed)
  Layer 2 → episode-plan.md (reads arc-conventions.md as additional context)
  Layer 3 → SKIPS (file exists; logs skip_reason=arc-conventions-already-present)
```

The invariant is hard: Layer 3 **never** overwrites an existing `arc-conventions.md`. To force a re-seed, delete or rename the file.

## 6. CLI cheat-sheet

```bash
# Initial run — halts at Layer 1 for operator review
blueprint-book <book-slug>

# Resume after operator review — runs Layers 2 + 3, merges series-config
blueprint-book <book-slug> --resume --approve-blueprint

# Resume + override model upgrade (use Opus for a contested-vocabulary source)
blueprint-book <book-slug> --resume --approve-blueprint --force-model opus

# Run end-to-end without halt (for batch / CI / regression)
blueprint-book <book-slug> --auto-approve-blueprint

# Status check (never modifies)
blueprint-book --status <book-slug>

# Skip the blueprint slot entirely (zero-regression for legacy books)
orchestrate-book --resume <book-slug> --approve-transcript --skip-blueprint-gate
```

## 7. When to override the classification

Layer 1's output is a recommendation, not a verdict. Operator should override when:

| Signal | Override |
|---|---|
| Classifier picks `chronological` but the book is a Festschrift (multiple authors, no continuity) | Set `recommended_episode_planning_mode: vignette_grid` |
| Classifier picks `traditional` audience profile but the series is for a wellness podcast | Set `recommended_audience_profile: clinical-wellness` |
| Classifier picks Haiku for Layer 2 but the book has dense unattributed Quranic citations | Set `recommended_model_for_layer_2: opus` (or pass `--force-model opus` on resume) |
| Classifier returns `recommended_source_tradition: null` but the operator knows the tradition | Set the slug; verify [content/_shared/traditions/](../../../_shared/traditions/) has the supplement |

Edit `classification.json` or `proposed-config.yaml` directly before `--approve-blueprint`. Both are JSON/YAML and validate on resume — typos fail loud.

## 8. Anti-patterns (don't do these)

| Anti-pattern | Why it breaks |
|---|---|
| Running blueprint on a book past slot 05.5 (asaas-al-taveel mid-0b, kitab-al-riyad at 0d→0e) | Orchestrator detects past-slot state and skips; reclassifying would invalidate downstream artifacts |
| Hand-editing `<book>/arc-conventions.md` AFTER 06-phonetics has started | Phonetics already consumed an earlier version; recap discipline would drift mid-pipeline |
| Setting `--force-model haiku` for a book classified as `vocabulary_contestedness: high` | Layer 2 will under-plan cross-episode anti-repetition; high-stakes esoteric-concept framing degrades |
| Approving a Layer 1 classification with `rationale` that doesn't cite specific signals | Means the classifier hallucinated; re-run with `--force-model sonnet` |
| Deleting `proposed-config.yaml` before `--approve-blueprint` | P23 will not activate; downstream phases run with pre-P23 behavior. Zero regression but loses the synergy. |

## 9. Debugging

- Layer 1 emitted nonsense rationale? Force Sonnet: `blueprint-book <slug> --force-model sonnet`.
- Layer 2 produced too few / too many episodes? Edit `arc-conventions.md` `episode_count_target`, then re-run `blueprint-book <slug> --resume --approve-blueprint`.
- Layer 3 didn't write `arc-conventions.md`? Check whether the file already exists (it's no-op when present); check cost-ledger for `skip_reason`.
- `--approve-blueprint` failed to merge series-config? Check that `proposed-config.yaml` is valid YAML and that `series-config.yaml` doesn't already declare the conflicting fields.

## 10. Pending — Air handoff

Layer 1 / Layer 2 / Layer 3 prompt skeletons (the actual instructions sent to claude -p) are gated on receipt of the truncated three-layer architecture body from Air session 7768a31c (2026-05-20). Until that text arrives:

- This handbook documents the **contract** (schemas, slot, model-upgrade behavior, P23 synergy).
- The agent spec at [infra/claude-agents/podcast-blueprint.md](../../../../infra/claude-agents/podcast-blueprint.md) documents the **agent boundaries**.
- The orchestrator slot is **reserved** but [scripts/podcast/_blueprint.py](../../../../scripts/podcast/_blueprint.py) raises `NotImplementedError("AWAITING_AIR_HANDOFF — P24.2/P24.3 blocked")` for the layer dispatchers.
- The halt-with-DoR runner at [scripts/podcast/phases/p24_1.py](../../../../scripts/podcast/phases/p24_1.py) prints the gate every launchd tick.

When the handoff arrives, P24.2 + P24.3 unblock and the layer prompts can be authored against this handbook.
