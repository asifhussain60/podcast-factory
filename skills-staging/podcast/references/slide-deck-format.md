# Slide-Deck Format Spec

How a slide-deck deliverable is shaped, file-by-file. Revised 2026-05-23 to make the **visual-rewritten chapter file** (the "deck source") the central upload to NotebookLM.

This file governs WHAT each artifact contains and HOW each is shaped. The Slide Deck Challenger validates against this spec.

---

## The two-file deliverable model (revised 2026-05-23 — pair lives together)

NotebookLM produces a slide deck from one **source** upload + one **customize prompt** paste. Both are produced by the podcast skill. Both files for each chapter live adjacent in a single `slide-decks/` folder per book.

| File | Role | NotebookLM action |
|---|---|---|
| `BOOK_DIR/slide-decks/chNN-deck-<slug>.txt` | The visual-rewritten chapter (**SLIDE-DECK SOURCE**) | **Upload** as the single source for the slide-deck notebook |
| `BOOK_DIR/slide-decks/chNN-framing-<slug>.md` | The customize prompt (**SLIDE CUSTOMIZE PROMPT**) | **Paste body** into NotebookLM's *Customize* prompt box (skip the H1 title line) |

Two files, two roles, both at the same flat level using the same `chNN-` prefix (matching the audio chapter prefix). The `-deck-` infix marks the source; the `-framing-` infix marks the customize prompt. `.txt` for source, `.md` for framing.

Optional companion files (NOT uploaded to NotebookLM, used internally by the skill / Challenger):

| File | Role |
|---|---|
| `BOOK_DIR/slide-decks/_visual-registry.md` | Per-book registry of recurring entities + visual conventions. One per book. |
| `BOOK_DIR/_system/slide-decks/chNN-<slug>/01-slide-spine.md` | Internal index — what slides the deck source SHOULD produce. Used by Challenger Coverage check. Optional. |
| `BOOK_DIR/_system/slide-decks/chNN-<slug>/02-visual-glossary.md` | Per-episode entries for cross-episode consistency. References the per-book visual registry. Optional. |

The mental model is simple: **for audio, look in `chapters/` + `episodes/`; for slide decks, look in `slide-decks/`.** Authoring scaffolds live under `_system/`.

---

## The deck source file — `slide-decks/chNN-deck-<slug>.txt`

This is the central new artifact. Lives in `slide-decks/` alongside its framing pair. Same `chNN-` prefix and same `<slug>` as the audio chapter at `chapters/chNN-<slug>.txt`.

**Why a separate file.** NotebookLM's slide-deck output mirrors the STRUCTURE of its source. A prose chapter (the audio source) produces narrative slides — paragraphs collapsed into bullets. A *visually-rewritten* chapter (same concepts, restructured into tables, named axes, hierarchies, contrast columns, etc.) produces diagram slides directly. The deck source is what makes NotebookLM render visuals instead of bullet lists.

**What it is.** A full rewrite of the audio chapter's content, presented as STRUCTURE rather than prose. Same concepts, same depth, same attributions — different rendering optimization.

**What it is NOT:**
- NOT a slide-by-slide outline (that's `01-slide-spine.md`).
- NOT a summary or condensed version (it preserves chapter depth).
- NOT prose with a few tables sprinkled in (it's structured throughout).
- NOT decorative — every structure earns its place.

### Length

- 50–100% of the audio chapter's word count. Some prose loses density when restructured (a paragraph becomes a 4-row table); some structures expand (a one-line lineage becomes a multi-row chain). Both are expected.
- For KaR's extended tier: 5,500–9,500 audio chapter words → 4,000–9,500 deck chapter words.
- Hard floor 2,000 words (below that, the source is too thin for a useful slide deck and the density-gauge skip flow should be triggered instead).

### Structure types it uses

Drawn from the [`slide-deck-patterns.md`](slide-deck-patterns.md) taxonomy. Every meaningful structural moment in the source becomes one of:

- **Named-axis 2x2** — axes named, four quadrants populated with entity + reasoning
- **Comparison matrix** — rows = entities, columns = attributes, cells = concrete commitments
- **Contrast pair** — two columns attribute-by-attribute, plus optional shared row
- **Hierarchy** — explicit indentation showing nesting, every level named
- **Genealogy chain** — directed arrows in text, generations grouped
- **Process flow** — branching and looping permitted; nodes + transitions specified
- **Timeline** — events ordered, eras marked
- **Annotated structure** — a single whole dissected into parts with one-sentence callouts
- **Visual metaphor** — abstract relations made spatial via concentric circles / spectrum / layers
- **Quadrant map** — when conceptual space is qualitative (no axis commitment possible)

The Challenger's Pass 1 Probe 3 (Structure-vs-Description) catches structures that DESCRIBE without supplying commitments.

### Format rules

- Plain text file (`.txt`), markdown-friendly content (so NotebookLM can parse it but the file is upload-clean).
- H1 once: the chapter title (same as audio chapter).
- H2 for movements (same as audio chapter — chapter outline is preserved).
- Within each H2, the body is structures — NOT prose paragraphs.
- Paragraphs of >100 words are a Challenger fail (rewrite as structure).
- Tables: explicit markdown tables with row headers and cell content (not "...").
- Hierarchies: `- Level 1` / `  - Level 2` indentation that NotebookLM reliably parses.
- Genealogies: explicit arrows `→` in text, one chain per line where possible.
- Contrast columns: use `Column A:` / `Column B:` prefix lines, NOT side-by-side markdown columns (NotebookLM parses sequential text better than columnar tables for this).
- Citations and verbatim quotes preserved from the audio chapter, but presented in blockquote with attribution — no prose surrounding them.
- No em dashes (use commas or restructure).
- No emojis unless the audio chapter uses them.
- Arabic transliterations retain the audio chapter's R-PHONETICS-OUT discipline: no inline `(pho-ne-tic)` parens; phonetics live in the customize prompt.

### Worked example — a paragraph transformed

**Audio chapter (prose):**
> Ghazali locates the soul's faculty in the heart (qalb), reaching certitude through unveiling (kashf) once purification is achieved. Ibn Rushd, opposing, places the faculty in the intellect (`aql) and reaches certitude through demonstrative proof (burhan). Both claim certitude as the goal, but the path and the locus differ entirely.

**Deck source (same content, contrast-pair structure):**
```
## Two readings of the soul's faculty

Contrast pair — Ghazali vs Ibn Rushd, attribute-by-attribute.

Column A: Ghazali
- Faculty location: heart (qalb)
- Knowledge source: revelation + purification
- Method: unveiling (kashf)
- End state: certitude through inner vision

Column B: Ibn Rushd
- Faculty location: intellect (`aql)
- Knowledge source: demonstrative proof
- Method: syllogism (burhan)
- End state: certitude through formal reasoning

Shared row: Both claim certitude as the goal. The path and locus differ entirely.
```

Same content, different rendering optimization. NotebookLM reading this produces a 2-column contrast slide; reading the prose version produces a bulleted summary slide.

### Slug + filename convention

- Slug matches the audio chapter slug EXACTLY: `<slug>` is whatever appears between `chNN-` and `.txt` in the audio chapter filename.
- Two files per chapter, both in `slide-decks/`, both using the `chNN-` prefix:
  - Source: `slide-decks/chNN-deck-<slug>.txt`
  - Framing: `slide-decks/chNN-framing-<slug>.md`
- Example pair for chapter 02:
  - Audio chapter (stays in `chapters/`): `chapters/ch02-soul-intellect-and-the-power-of-emanation.txt`
  - Deck source: `slide-decks/ch02-deck-soul-intellect-and-the-power-of-emanation.txt`
  - Deck framing: `slide-decks/ch02-framing-soul-intellect-and-the-power-of-emanation.md`

The `validate_registry.py` chapter-existence check (R5) only looks for the audio chapter file under `chapters/`; the `slide-decks/` folder is invisible to the validator. The slide-deck-status column in the registry tracks deck readiness instead.

---

## The customize prompt — `slide-decks/chNN-framing-<slug>.md`

Sibling of the deck source in the same `slide-decks/` folder. Markdown extension because it is never built or transformed; you copy-paste its body into NotebookLM's Customize prompt box during slide-deck generation. Skip the H1 line when pasting (the H1 is a file label).

**Length**: 150–250 words.

**Required H2 sections:**

- `## Audience` — named concretely (Asif's children, a specific person, scholars of X, general thoughtful adult). NEVER "general audience."
- `## Core Principle` — restate the audio-vs-slide division of labor in 1–2 sentences. Tells NotebookLM what slides are FOR.
- `## Visual Priorities` — 2–4 specific visual moments to emphasize (e.g., "the contrast between [A] and [B]," "the lineage from [X] to [Y]"). These should match the structures present in the deck source.
- `## Prohibited Patterns` — explicit list: no literal-text slides, no slides that restate audio, no stock-photo descriptions, no bullet-list slides masquerading as diagrams.
- `## Steering Phrases` — 3–5 phrases drawn from [`slide-deck-steering.md`](slide-deck-steering.md).

**Example skeleton:**

```markdown
# Slide Deck Framing — EP##-[slug]

## Audience
Asif's children — thoughtful young adults familiar with the audio but not the source.

## Core Principle
Each slide must add visual information the audio cannot carry. If a slide could be a single audio sentence, omit it.

## Visual Priorities
- The contrast between Ghazali and Ibn Rushd on the soul's faculty — render as side-by-side columns.
- The genealogy from al-Farabi through Ibn Sina to Ghazali and Ibn Rushd — render as a directed tree.
- The 2x2 of authority-source vs locus-of-certainty organizing the central tension.

## Prohibited Patterns
- No slides that bullet-point the audio.
- No literal illustrations of source quotes.
- No stock-photo-style imagery.
- No slides whose only content is the discussion-spine beat title.

## Steering Phrases
- "Each slide must add visual information not present in the audio."
- "Show the relationships between entities, not a list of them."
- "Use a 2x2 matrix for the central tension — specify both axes."
```

---

## Optional: `01-slide-spine.md`

A per-episode index of what slides the deck source SHOULD produce. Used by the Challenger's Pass 1 Probe 8 (Coverage) — every `[VISUAL CANDIDATE]` beat in `04-discussion-spine.md` should map to a structure in the deck source, and the spine names that mapping.

This file is NOT uploaded to NotebookLM. It's an internal index, useful for:
- Pre-generation: sanity-check that all visual beats are reflected in the deck source.
- Post-generation: compare NotebookLM's actual output against expected slide count + types.
- Multi-episode tracking: the spine accumulates the deck's diagram-type distribution, feeding the Variety architectural check.

**Per-slide schema** when present:
- **H2 heading**: `## Slide N: [title]` (zero-padded slide number)
- **Diagram type** — one from the [`slide-deck-patterns.md`](slide-deck-patterns.md) taxonomy
- **Anchor** — beat ID `B##` from `04-discussion-spine.md`, or `[STANDALONE]`
- **Deck-source reference** — the H2 in `chNN-deck-<slug>.txt` where this structure lives

Slide count budget when this file is present:

| Audio length     | Slide budget | Notes                                         |
|------------------|--------------|-----------------------------------------------|
| ~8 min (tight)   | 6–8          | One slide every ~75 seconds                   |
| ~12–15 min (std) | 9–12         | One slide every ~75–90 seconds                |
| ~25 min+ (long)  | 13–15        | Hard cap at 15 even for very long episodes    |

---

## Beat Anchor IDs (Cross-File Convention)

Discussion-spine beats in `_system/episode-drafts/EP##-<slug>/04-discussion-spine.md` MUST be tagged with monotonic IDs: `B01`, `B02`, … in order of appearance.

`01-slide-spine.md`'s `Anchor:` fields and the Challenger's Coverage check both reference these IDs.

If existing episodes lack beat IDs (pre-enhancement audio bundles), they're added as part of Stage B of the slide-deck enhancement rollout per the SKILL.md Phase 3 overlay.

---

## Common Mistakes the Challenger Catches

1. **Prose hiding in a deck source** — paragraph > 100 words inside `chNN-deck-<slug>.txt` is a Challenger fail. Structure or rewrite.
2. **Description instead of structure** — "A 2x2 showing the contrast" without naming the axes or which entity goes in which quadrant.
3. **Untyped diagram** — a structural moment in the deck source that doesn't match a diagram-type from the taxonomy.
4. **Decorative structures** — a contrast pair where Column A and Column B say roughly the same thing (no actual contrast).
5. **Audio-restatement** — deck source structures echo the audio chapter beat-for-beat with no structural advantage.
6. **Missing concepts** — concepts present in the audio chapter that are absent from the deck source (the deck is a *re-presentation*, not a *summary*).
7. **Beat ID gaps** — discussion-spine beats are unlabeled, breaking coverage checks.

---

## Validation Checklist (Self-Check Before Challenger)

1. Does `chapters/chNN-deck-<slug>.txt` exist with the correct `deck-` infix?
2. Is its word count within 50–100% of the audio chapter's word count?
3. Are H1 and H2 movement headings preserved from the audio chapter?
4. Are there ANY prose paragraphs > 100 words inside it? (Should be zero.)
5. Does every structural moment match a named diagram type from `slide-deck-patterns.md`?
6. Does `00-slide-framing.md` have all five required H2 sections?
7. Does `00-slide-framing.md` name the audience concretely?
8. Are there NO em dashes anywhere in either file?
9. Are Arabic transliterations free of inline phonetic parens (R-PHONETICS-OUT)?
10. Does every concept in the audio chapter appear (restructured) in the deck source?
