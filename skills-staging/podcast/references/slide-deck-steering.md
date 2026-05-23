# Slide-Deck Steering Patterns

Phrases that bend NotebookLM's Slide Deck output toward intelligent diagrams instead of bullet-list slides. Mirrors `two-host-framing.md` for the audio side.

Unlike Audio Overview steering (well battle-tested), Slide Deck steering is **early-stage**. The seed list below is the starting point. Phrases prove themselves across episodes; failures get cataloged and avoided.

This file grows with use. The Challenger learning loop proposes additions when recurring failures suggest a new steering phrase would help.

---

## How to Use

In each episode's `00-slide-framing.md`, the `## Steering Phrases` section pulls 3–5 phrases from this file. Pick phrases that target THIS episode's risk — if the source naturally tempts NotebookLM toward bullet lists, lean on anti-bullet phrases; if the source has rich genealogy, lean on relationship-emphasis phrases.

Do NOT include all phrases. Density dilutes steering force.

---

## Category 1 — Anti-Restatement (Prevent Audio Echo)

These prevent NotebookLM from producing slides that just bullet-point the audio.

- "Each slide must add visual information not present in the audio."
- "If a slide could be a single bullet in a list, omit it."
- "Do not produce slides whose only content is the discussion-spine beat title."
- "A slide that summarizes a section of audio is not a slide — it is a transcript fragment. Omit it."
- "Treat the audio as the linear track. Slides exist only to capture what cannot be linear."

**Use when**: source has dense conceptual content that audio handles well, and the risk is the deck duplicates the audio's outline.

---

## Category 2 — Diagram-Type Discipline

These force NotebookLM to commit to specific diagram types rather than producing generic visuals.

- "Use [diagram type] for [concept] — show the structure, not the label."
- "For [the central tension], use a 2x2 with [axis X] vs [axis Y]. Specify both axes explicitly."
- "For [the lineage of ideas], use a directed genealogy tree. Show edges, not just nodes."
- "Do not produce 'general illustration' slides. Every slide must have a named diagram type."
- "Avoid stock-photo-style imagery. Every slide is a diagram or it does not exist."

**Use when**: source has clear visual moments and the risk is NotebookLM defaults to bland title-with-image slides.

---

## Category 3 — Relationship Emphasis (Show, Don't List)

These push NotebookLM from listing entities to showing how they relate.

- "Show the relationships between [entities], not a list of them."
- "Place [entity A] in the top-right because [reason]; place [entity B] in the bottom-left because [reason]."
- "When two positions are contrasted, show them side by side as columns, attribute by attribute."
- "When three or more positions are compared, use a matrix with rows for entities and columns for attributes."
- "When influence flows from A to B, show a directed arrow from A to B. Bidirectional unless source establishes mutuality."

**Use when**: source has multiple entities that naturally compare, contrast, or influence each other.

---

## Category 4 — Anti-Generic (Block Filler Slides)

These block NotebookLM from producing throat-clearing or wrap-up slides.

- "Do not produce an opening slide that says [Episode Title]. Begin with content."
- "Do not produce a closing slide that says 'Thank you' or 'Questions?' Slides end on the last content moment."
- "Do not produce a slide titled 'Key Takeaways' — takeaways belong to the audio."
- "Do not produce a slide titled 'Overview' or 'Agenda.' The deck has no agenda; it has visual moments."
- "Avoid summarizing the obvious."

**Use when**: every episode. These are evergreen.

---

## Category 5 — Pacing and Depth

These shape how slowly or quickly the deck moves.

- "Slow down on [the central tension] — give it at least two slides showing different angles."
- "Each slide must be readable in 30 seconds. If it requires more reading time, break into two slides or remove detail."
- "Front-load the strongest visual moment. The first content slide should be the most structurally demanding."
- "Do not produce more than two slides on background context. Context belongs in the audio."

**Use when**: source has uneven density — risk of either over-slowing on light beats or rushing the central tension.

---

## Category 6 — Per-Book Visual Consistency

These maintain cross-episode visual conventions for multi-episode series.

- "[Entity X] is positioned [direction] across all episodes of this series. Maintain that convention."
- "[Color/treatment] is reserved for [tradition/entity] across this series. Do not reuse for unrelated entities."
- "When [recurring theme] appears, show it using [specific diagram type] for visual recognition across episodes."

**Use when**: episode is part of a series that has a `_visual-registry.md`. Cross-reference the registry in the framing.

---

## Phrases That DID NOT Work

A growing catalog of steering phrases that proved weak. Documented so we don't try them again expecting different results.

| Phrase | Why it failed | First observed |
|--------|---------------|----------------|
| "Make slides visually compelling" | Too vague. NotebookLM defaulted to stock-photo aesthetic. | — |
| "Use beautiful design" | No traction. Aesthetic adjectives don't steer structure. | — |
| "Avoid bullet points" | Surface-only. NotebookLM produced numbered lists instead. The fix is the anti-restatement category, not the surface format. | — |
| "Be creative" | Anti-signal. Produced more random imagery, not more structural visuals. | — |

(Entries added as failures are observed and Challenger reports identify them.)

---

## Adding New Phrases

A phrase joins the seed list above only after:

1. It was used in 2+ episodes.
2. The Challenger passed both decks.
3. The phrase can be attributed to a specific improvement (compared to a control episode where it was absent).

Drafted phrases go into a `## Category 7 — Candidates` section at the bottom of this file, tagged `[CANDIDATE]`. They get promoted to a numbered category after the 2-episode threshold.

---

## Challenger Learning Loop Hook

The Slide Deck Challenger writes findings to `_workspace/EP##-[slug]/slide-challenger-report.md`. The run-tracking ledger aggregates findings across episodes.

When the ledger detects:
- Same probe failure occurring in 3+ consecutive episodes
- A new failure category emerging in 2+ episodes

…it proposes a new steering phrase or a new probe. Proposals land in the `## Category 7 — Candidates` section of this file (for steering phrases) or in `slide-deck-challenger.md` (for new probes), tagged `[PROPOSED — needs review]`.

Asif reviews proposals and either promotes them, rejects them, or marks them as `[FAILED PHRASES]` if they're attempted and don't work.

---

## Notes on NotebookLM Behavior (Observed, Subject to Change)

- NotebookLM's Slide Deck output is sensitive to the structure of the source, not just its content. A source written as prose produces narrative slides; a source written as structured headings with explicit content scaffolds produces diagram-oriented slides.
- Specificity beats abstraction. "Place Ghazali in the top-left" works; "Position Ghazali appropriately" does not.
- NotebookLM does not reliably parse complex Markdown tables for visual layout. Prefer explicit text scaffolds (`- Column A: X | Column B: Y`) over Markdown tables for content scaffolds.
- Headings in source files appear to influence slide titles. Use H2 for slide entries in `01-slide-spine.md` so NotebookLM picks up the titles cleanly.

These observations are heuristic and will evolve as NotebookLM evolves.
