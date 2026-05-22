<!-- DRAFT — operator-editable; subsequent blueprint runs read this as-is and DO NOT overwrite.

  Layer 3 of podcast-blueprint emits this template populated with Layer 1's
  classification.json values. After this file ships, the operator may:
    - accept as-is by leaving it untouched + running --approve-blueprint
    - edit any field (planning_mode, episode_count, recap discipline, etc.)
      before --approve-blueprint
    - replace wholesale with a hand-authored arc-conventions.md

  Once Layer 3 has written this file, subsequent blueprint runs treat it as
  immutable input. To force re-seeding, delete or rename the file.
-->

---
schema_version: 1
book_slug: <BOOK_SLUG>
seeded_at: <ISO_8601_TIMESTAMP>
seeded_by: podcast-blueprint Layer 3
source_signature: <SHA256_OF_REFINED_ENGLISH_MD>

# === Inherited from Layer 1 classification.json ===
genre_primary: <GENRE_PRIMARY>                      # one of: polemic_tribunal | memoir | self_help | essay_collection | didactic_dialogue | exegesis | epistle
narrative_mode: <NARRATIVE_MODE>                    # one of: first_person | third_person_omniscient | dialectical | epistolary | vignette
structural_units: <STRUCTURAL_UNITS_YAML_LIST>      # e.g. ["babs", "fasls"]
density_score: <DENSITY_SCORE>                      # 0.0–1.0
cross_reference_load: <CROSS_REFERENCE_LOAD>        # low | medium | high
vocabulary_contestedness: <VOCABULARY_CONTESTEDNESS> # low | medium | high

# === Operator-confirmable (these become series-config.yaml on --approve-blueprint) ===
audience_profile: <RECOMMENDED_AUDIENCE_PROFILE>    # traditional | modern-secular | clinical-wellness | academic
source_tradition: <RECOMMENDED_SOURCE_TRADITION>    # tradition-slug | null
episode_planning_mode: <RECOMMENDED_EPISODE_PLANNING_MODE>  # tribunal_arc | chronological | problem_solution | vignette_grid | dialectical_pairs

# === Episode planning conventions (Layer 2 consumes these) ===
episode_count_target: <RECOMMENDED_EPISODE_COUNT>   # integer; Layer 2 uses as anchor
target_words_per_episode: <RECOMMENDED_WORD_COUNT>  # integer; ±15% tolerance
recap_discipline:                                   # how each episode opens
  pattern: <RECAP_PATTERN>                          # recursive_scaffold | problem_restatement | character_anchor | vignette_callback | none
  density: <RECAP_DENSITY>                          # one-line | paragraph | full-restatement
preview_discipline:                                 # how each episode closes
  pattern: <PREVIEW_PATTERN>                        # next-question | next-character | next-vignette | none
cross_episode_anti_repetition:
  enabled: true                                     # operator may flip to false
  seeds_per_episode: <CROSS_EP_SEED_COUNT>          # integer
---

# Arc Conventions — <BOOK_SLUG>

> *Seeded by `podcast-blueprint` Layer 3 on <ISO_8601_TIMESTAMP>. This file is the per-book episode-planning convention. Operator is the editor of record after the seed; subsequent blueprint runs read it as-is.*

## Why this book gets this planning mode

<RATIONALE_FROM_CLASSIFICATION_JSON>

## Planning-mode rules (for `<RECOMMENDED_EPISODE_PLANNING_MODE>`)

<!-- Layer 3 inserts the rule set for the chosen planning_mode here. Reference:
     - tribunal_arc: episodes follow accuser → defense → verdict cycles; recap recalls last verdict
     - chronological: episodes anchored to time-marked events; recap restates last event chain
     - problem_solution: each episode states a problem + arrives at a tactic; recap restates last tactic
     - vignette_grid: episodes are self-contained essays; recap is light, preview is curiosity-anchored
     - dialectical_pairs: episodes pair a thesis with a response; recap restates the prior dialogue's arc
-->

## Audience profile alignment

This book uses `<RECOMMENDED_AUDIENCE_PROFILE>` per Layer 1 recommendation. Per [episode-format-contract.md](../episode-format-contract.md):

<!-- Layer 3 inserts the audience-profile row from P23's contract here -->

## Source-tradition data

<!-- If recommended_source_tradition is non-null, Layer 3 inserts a one-line
     pointer to content/_shared/traditions/<slug>.md and any tradition-specific
     planning notes (honorifics density, citation-form preferences, etc.). If
     null, this section reads: "No tradition supplement; generic defaults
     apply per episode-format-contract.md §3.1."
-->

## Operator notes

<!-- Free-form. Operator may add per-book quirks here (e.g., "Bāb numbering
     restarts at §17 — treat as anthology break", "footnote density is so high
     that episodes should split footnotes into a per-episode supplement").
     Layer 2 reads this section as additional planning context.
-->

## Anti-patterns to avoid (book-specific)

<!-- Operator-authored. Examples:
     - "Do not group the proof-text section with the rebuttal section; they
       belong in separate episodes (recursive_scaffold breaks otherwise)."
     - "Do not allow Layer 2 to merge Bāb 3 + Bāb 4 — the second-author
       voice shift requires an episode boundary."
-->
