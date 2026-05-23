# Slide-Deck Patterns

Diagram type taxonomy, worked examples, source-type affinity matrix, and anti-patterns. This file is referenced by `01-slide-spine.md` in every episode's slide-deck folder.

When in doubt about which diagram type fits, consult this file. New patterns get added here only after they prove themselves across 2+ episodes.

---

## Diagram Type Taxonomy

Each entry: when to use, what the source MUST specify, worked example, anti-pattern.

### 2x2 Matrix

**When to use**: A central tension that can be organized along two independent axes. Four meaningful regions emerge.

**Source must specify**:
- Both axes (low/high or positive/negative ends)
- Which entities/positions occupy which quadrant
- Reasoning for each placement (1 sentence each)

**Worked example**:
```
Axes:
- Horizontal: Source of authority (Tradition → Reason)
- Vertical: Locus of certainty (Communal → Individual)

Quadrants:
- Top-right (Reason + Individual): Ibn Rushd. Demonstrative knowledge by the philosopher's own intellect.
- Top-left (Tradition + Individual): Ghazali in Munqidh. Personal mystical certitude grounded in scripture.
- Bottom-left (Tradition + Communal): The classical jurist. Authority and certainty rest with the community of scholars.
- Bottom-right (Reason + Communal): The Mu`tazila. Rational consensus as binding authority.
```

**Anti-pattern**: Naming the axes but not assigning entities to quadrants. NotebookLM then produces an empty 2x2 with labels but no content.

---

### Comparison Matrix

**When to use**: Multiple entities (3+) compared across multiple attributes (3+). Audio handles 2-entity comparisons fine; matrices earn their keep at higher dimensions.

**Source must specify**:
- Row entities (named)
- Column attributes (named)
- Cell values (concrete, not "varies" or "depends")

**Worked example**:
```
Rows: Ghazali, Ibn Rushd, Ibn `Arabi
Columns: Source of knowledge | Locus of soul | End state | Method
- Ghazali: revelation+purification | heart (qalb) | unveiling | dhawq
- Ibn Rushd: demonstration | intellect (`aql) | proof | burhan
- Ibn `Arabi: theophany | imaginal faculty | witnessing | kashf
```

**Anti-pattern**: Cells filled with hedges ("could be," "sometimes," "in some interpretations"). The matrix needs commitments; nuance belongs in the audio.

---

### Genealogy / Influence Tree

**When to use**: A lineage of ideas, teachers, traditions. Direction of influence matters.

**Source must specify**:
- Nodes (named individuals or schools)
- Edges (with direction — A influenced B, not just "A and B related")
- Generation/era grouping if relevant

**Worked example**:
```
Generation 1: al-Farabi
  → Generation 2: Ibn Sina (extends metaphysics, narrows logic)
    → Generation 3a: Ghazali (selectively absorbs and refutes)
    → Generation 3b: Ibn Rushd (defends and extends against Ghazali)
      → Generation 4: Latin scholastics (receive Ibn Rushd, often misread)
```

**Anti-pattern**: Bidirectional or unspecified arrows. The whole point of a genealogy is direction.

---

### Process Flow

**When to use**: A sequence of steps, stages, or transformations. Branching is allowed; loops are allowed; the order matters.

**Source must specify**:
- Nodes (steps/stages)
- Transitions (with conditions if branching)
- Start and end states

**Worked example**:
```
Start: Doubt (Ghazali's account of his crisis)
  ↓
Sensory verification fails
  ↓
Rational verification fails
  ↓
Sufi path entered
  ↓
Branch:
  - Path A: Theoretical study → reaches limit of intellect
  - Path B: Practical purification → continues
  ↓
End: Certitude through unveiling (dhawq)
```

**Anti-pattern**: Numbered list pretending to be a flow. A flow needs visible transitions and (often) branches.

---

### Quadrant Map

**When to use**: Entities positioned in 2D conceptual space WITHOUT strict axes. The space is qualitative, not measurable. Useful when relative positions matter but you can't commit to axes.

**Source must specify**:
- The conceptual space (named, even if not axis-bounded)
- Positions of each entity (top, bottom, left, right, center)
- Reasoning for each position relative to the others

**Worked example**:
```
Space: How thinkers relate revelation and reason
- Top-center: Scripture-first traditionalists (al-Hanbali school)
- Right-center: Rationalists with revelation as ratifier (Mu`tazila)
- Bottom-center: Mystical synthesists (Ibn `Arabi)
- Left-center: Reason-first philosophers (Ibn Rushd)
- Center: Ghazali — moves across regions across his career
```

**Anti-pattern**: Forcing this into a 2x2. Quadrant maps work when the space is too qualitative for axes; respect that.

---

### Contrast Pair

**When to use**: Two positions opposed attribute-by-attribute. Stronger than prose comparison; weaker than full matrix.

**Source must specify**:
- Two columns (each headed by the entity name)
- Rows of attributes
- Each cell's value
- Optional: a shared row for points of agreement

**Worked example**: see `slide-deck-format.md` Worked Example.

**Anti-pattern**: Three entities. Use Comparison Matrix instead — contrast pairs lose force with a third party.

---

### Hierarchy Tree

**When to use**: Nested taxonomy. Part-of or kind-of relations. Strict levels.

**Source must specify**:
- Levels (named)
- Parent-child relations
- All siblings at each level

**Worked example**:
```
Level 1: Knowledge (`ilm)
  Level 2: Necessary knowledge (daruri)
    Level 3: Sensory, intellectual, intuitive
  Level 2: Acquired knowledge (nazari)
    Level 3: Demonstrative, dialectical, rhetorical, sophistical, poetic
```

**Anti-pattern**: Skipping levels (going from Level 1 to Level 3 without naming Level 2). Breaks the hierarchy logic.

---

### Timeline

**When to use**: Events along a temporal axis. Periods/eras can be marked. Order is the point.

**Source must specify**:
- Time axis (years, eras, relative order)
- Events with dates or positions
- Period boundaries if relevant

**Worked example**:
```
1058: Ghazali born
1085: Begins teaching at Nizamiyya in Baghdad
1095: Crisis — abandons post, leaves Baghdad
1095–1106: Wandering — Damascus, Jerusalem, Mecca, Medina
1106: Returns to teaching in Nishapur
1111: Dies in Tus
Period bands: Pre-crisis | Wandering | Post-crisis teaching
```

**Anti-pattern**: Bulleted dates without visible axis. A timeline's force comes from the axis.

---

### Annotated Structure

**When to use**: A single object, concept, or framework dissected into parts. Callouts explain each part.

**Source must specify**:
- The whole (what the structure is)
- Parts (named, with positions)
- Annotation per part (1 sentence)

**Worked example**:
```
Whole: Ghazali's Ihya' (the 40-book structure)
Quadrants of the structure:
- Acts of worship (10 books) — top-left
- Norms of daily life (10 books) — top-right
- Vices leading to destruction (10 books) — bottom-left
- Virtues leading to salvation (10 books) — bottom-right
Annotations:
- TL: external practice
- TR: external action in society
- BL: internal pathology
- BR: internal therapy
Cross-axis: external (top) vs internal (bottom); individual (left) vs social (right)
```

**Anti-pattern**: Callouts without spatial relation. Annotated structures need the spatial layout to do work.

---

### Visual Metaphor

**When to use**: An abstract relation that has no natural diagrammatic form, but can be MADE spatial through metaphor.

**Source must specify**:
- The abstract relation
- The metaphor (concentric circles, spectrum, layers, branches)
- Element assignments

**Worked example**:
```
Abstract relation: nested layers of loyalty in classical Islamic ethics
Metaphor: concentric circles
- Innermost: family
- Next: tribe/clan
- Next: religious community (umma)
- Next: humanity (banu Adam)
- Outermost: creation (khalq)
Reading: obligations propagate outward but intensity decreases.
```

**Anti-pattern**: Inventing a metaphor that doesn't match the relation. If "concentric circles" implies nesting but the relation isn't nested, pick another metaphor.

---

## Source-Type → Diagram-Type Affinity Matrix

When distilling a source, this matrix suggests which diagram types most often fit. NOT prescriptive — overrides are fine — but a strong starting point.

| Source type           | Strong fits                                        | Weak fits                       |
|-----------------------|----------------------------------------------------|----------------------------------|
| Philosophical text    | 2x2, Contrast pair, Hierarchy tree                 | Timeline                         |
| Historical narrative  | Timeline, Genealogy, Process flow                  | 2x2, Visual metaphor             |
| Theological argument  | Contrast pair, Hierarchy tree, Annotated structure | Quadrant map                     |
| Mystical / poetic     | Visual metaphor, Annotated structure, Quadrant map | Comparison matrix, 2x2           |
| Memoir / personal     | Timeline, Process flow, Quadrant map               | Hierarchy tree, Comparison matrix |
| Comparative study     | Comparison matrix, 2x2, Contrast pair              | Visual metaphor                  |
| Polemic / critique    | Contrast pair, 2x2, Annotated structure            | Timeline                         |
| Lineage / tradition   | Genealogy, Timeline, Hierarchy tree                | 2x2 (unless tension is named)    |

A deck of 10 slides should NOT be dominated by one diagram type. Aim for variety — at least 3 distinct diagram types across the deck.

---

## Anti-Patterns the Challenger Catches

1. **Description-not-structure** — "A diagram showing how X relates to Y" without naming the relation.
2. **Bullet-list-as-diagram** — Calling a hierarchy tree what is actually a flat bulleted list.
3. **Monoculture** — Every slide is a comparison matrix, or every slide is a timeline.
4. **Forced 2x2** — Picking a 2x2 because it sounds smart, then inventing axes that don't carve the space.
5. **Generic placement** — "Entity A in the top-right" without reasoning. Reasoning is required; it's what tells NotebookLM how to draw.
6. **Wrong type for source** — Hierarchy tree on memoir, timeline on philosophical argument. The affinity matrix flags these.

---

## Adding New Patterns

A new diagram type joins this file only after:

1. It has been used in 2+ episodes.
2. Both uses passed the Challenger.
3. The type is genuinely distinct from existing types (not a sub-case of another).
4. The "when to use" criterion is concrete enough to avoid overlap with existing types.

Propose new patterns by adding a draft section here and tagging it `[CANDIDATE]`. Promote to permanent after the 2-episode threshold.

---

## Per-Book Visual Registry Hook

For multi-episode series (KaR, future books), recurring entities should have consistent visual treatment across episodes. This is tracked in:

```
slide-decks/_visual-registry.md   (one per book/series)
```

Per entry:
- Entity name (e.g., "Ghazali")
- Standing visual convention (e.g., "deep red, left side of contrasts")
- First defined in: EP##
- Reason: (e.g., "Ghazali is the foil throughout the series; consistent positioning anchors recognition")

Slide-deck `02-visual-glossary.md` files reference the registry rather than redefining conventions per episode.

The Challenger checks new slide decks against the registry — if Ghazali was left-positioned in EP01 but right-positioned in EP05, the Challenger flags the inconsistency.
