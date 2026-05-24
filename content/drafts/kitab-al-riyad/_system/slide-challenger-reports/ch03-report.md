# Slide Challenger Report — ch03-the-soul-in-time-and-the-rejoinder-to-al-nusra

**Run timestamp**: 2026-05-23T00:00:00Z
**Deck path**: slide-decks/ch03-deck-the-soul-in-time-and-the-rejoinder-to-al-nusra.txt
**Framing path**: slide-decks/ch03-framing-the-soul-in-time-and-the-rejoinder-to-al-nusra.md
**Audio chapter**: chapters/ch03-the-soul-in-time-and-the-rejoinder-to-al-nusra.txt
**Structural-moment count**: 21 H2 sections (≈18 distinct diagrammatic blocks; the remaining 3 are scaffolding: opening contrast pair, anchor-quote dump, "what carries into ch02").
**Slide budget**: KaR is the long tier (25 min+). The deck source far exceeds the 13–15 slide cap, which is expected — NotebookLM compresses, so over-supply at the source level is the correct posture. Caveat noted below.
**Deck-source word count**: 5,832 (61.7% of audio chapter's 9,448). Inside the 50–100% band.

---

## Pass 1 — Per-Slide Probes

| Probe | Result | Slides flagged | Notes |
|-------|--------|----------------|-------|
| 1 Restatement | pass | — | No structural moment is reducible to a single audio sentence; even the short "Foundation cannot be other than perfect" (sub-chapter 26) is a 4-step process flow that earns its place. |
| 2 Literal Illustration | pass | — | No "image of," "photo of," or stock-photo language anywhere. The framing explicitly bans calligraphy, mosques, reed flutes, scholar portraits. |
| 3 Structure-vs-Description | **pass (strong)** | — | This is the deck's biggest strength. The two-Souls 2x2 names both axes (Locus of existence: Creative-world ↔ Natural-world; State at first instant: Already perfect ↔ Hovering in potency), populates all four quadrants with named entities and reasoning, AND explicitly labels two quadrants as "Impossible" with reasoning. Sub-chapter 28's contrast pair commits both columns with 6 attributes each. Sub-chapter 30's branching process flow exhausts Case 1, Case 2a, Case 2b with verdicts. Sub-chapter 37's dispute matrix commits four-claim-by-three-position cells. Every structure supplies axes, nodes, positions, AND placement reasoning. |
| 4 Diagram-Type Discipline | pass | — | Each H2 names its type explicitly: "contrast pair," "named-axis 2x2," "comparison matrix," "process flow," "branching process flow," "hierarchy tree," "annotated structure," "three-row argument," "four-row dispute matrix." All types map to the taxonomy in slide-deck-patterns.md. |
| 5 Diversity | pass | — | Type distribution: contrast pairs ×7, comparison matrices ×4, process flows ×3 (one branching), 2x2 ×1, hierarchy ×1, annotated structure ×1, roster table ×1. Six distinct types present, exceeding the "at least 3" floor. Affinity-matrix expectation (philosophical text → 2x2, contrast, hierarchy) is fully met. |
| 6 Audio Redundancy | pass | — | Walked the deck's 21 H2s against the audio's 17 H2s. The deck preserves the audio's sub-chapter movement headings (required by spec) AND adds three meta-structures the audio lacks: the figures-in-dispute roster, the two-Souls 2x2 promoted upfront, and the anchor-quote bundle. Each sub-chapter body is rendered structurally (axes, columns, branches) not as bulleted prose. Spot check sub-chapter 27: audio runs as continuous prose; deck renders *Samuel's* setup as one 4-column matrix and *the author's* rejoinder as a separate three-step matrix — structural value added. |
| 7 Justified Skip | n/a | — | Deck is not a skip. |
| 8 Coverage | pass | — | Audio chapter does not carry `[VISUAL CANDIDATE]` tags (Phase 2 enrichment is downstream of this draft). Coverage judged by content alignment: every sub-chapter (24–38) has a corresponding structural block, plus the closing prayer and a transition block to ch02. No silently absent beats. |

---

## Pass 2 — Architectural Pass

| Check | Result | Notes |
|-------|--------|-------|
| Visual Memory Test | **pass (strong)** | The two-Souls 2x2 is the deck's signature image — a quadrant grid where two cells are labeled "Impossible" with reasoning, creating a distinctive diagonal that IS the engine of *Samuel's* error. That single slide is memorable on its own. Supporting memorable slides: the four-divisions hierarchy with the deputy-chain Object → Idea → Word → Writing (annotated structure with both spatial layout AND directed chain); the sub-chapter 30 branching process flow with Case 1 / Case 2a / Case 2b verdicts; the sub-chapter 37 four-row dispute matrix scoring *Jonathan* / *Samuel* / *the author* row by row; the three-Quranic-stages spectrum (*ammara* → *lawwama* → *mutma'inna*). Estimated ≥75% of structural moments survive memory test. The few weaker blocks (the closing-prayer reflection, "what carries into ch02") are arc-closing scaffolding, not load-bearing slides. |
| Variety | pass | No single diagram type accounts for >40% of the deck. Contrast pair is the most common (≈33%, 7/21) — well under the 60% near-monoculture threshold and appropriate for a chapter whose entire argument is "Samuel vs the author" pair-by-pair. |
| Arc | pass | Clear shape: opening contrast pair locating where the chapter picks up → roster of disputants → the central 2x2 (the chapter's organizing tension, promoted UP from where it would naturally appear in sub-chapter 28) → fifteen sub-chapter blocks building pressure on *Samuel's* slide between the two souls → closing-chapter contrast pair → closing prayer → ch02 transition. Beginning establishes tension; middle accumulates evidence across analogy ladders; end resolves with structural summary, not a bullet-list takeaway. The promotion of the two-Souls 2x2 from its native position (sub-chapter 28) to the front of the deck is a deliberate arc choice that gives readers the organizing structure before the evidence. |
| Cross-Episode Consistency | n/a | No `_visual-registry.md` exists yet in `slide-decks/`. Cross-episode consistency cannot be evaluated until the registry is created. NOT a fail — the registry is optional per format spec. Flagging as a future-tech-debt observation, not a blocker. |

---

## Overall

**Pass 1**: pass
**Pass 2**: pass
**Bundle status**: **ship**

---

## Failures (if any)

None. No probe failed, no architectural check failed.

---

## Observations (non-blocking)

These are not failures; logged for the learning loop.

1. **Anchor-quote dump at end** — The "Verbatim anchor quotes (preserved for slide use)" H2 collects six already-cited quotes in a flat block. This is internal scaffolding for the Worker, not a slide structure. It does no harm (NotebookLM will likely not produce a slide from it because it lacks structural commitments) but a future pattern could move this to a `## Anchor quote inventory` section flagged "internal — not for slide rendering."

2. **No visual registry yet** — `slide-decks/_visual-registry.md` does not exist. KaR has 15 chapter decks already authored; *Samuel*, *Jonathan*, *the author*, the First Intellect, and the Successor Soul recur across every chapter. A registry would lock conventions (e.g., "Samuel always positioned in the deficient/lower quadrant; the author always in the referee position above"). Recommend creating it before ch04+ to anchor cross-episode recognition. Not a Pass 2 fail today because the check is `n/a` without a registry — but the absence is itself a tech-debt signal.

3. **Sub-chapter title prefixes** — Every body H2 begins "Sub-chapter twenty-X: ...". NotebookLM may produce slides whose only title is "Sub-chapter twenty-X" if it parses the prefix as the title rather than the description. The framing's "no slides whose only content is a sub-chapter title" prohibition catches this downstream, but a deck-source convention of "Sub-chapter twenty-X — <descriptive title>" (em-dash to comma already converted) reads cleanly while subordinating the numeric prefix. Cosmetic only.

---

## Verified vs Inferred

- **VERIFIED**:
  - Word count 5,832 vs 9,448 (61.7%) — measured directly.
  - 21 H2 sections — counted with `grep`.
  - Six diagram types present — read directly from the deck.
  - Two-Souls 2x2 axes named and quadrants populated — read directly (lines 39–57 of deck).
  - Audio chapter has zero `[VISUAL CANDIDATE]` tags — verified with `grep`.
  - No `_visual-registry.md` — verified by directory listing.
  - Em-dash compliance — no `—` in deck (spot-verified; the format-spec prohibition).
- **INFERRED**:
  - Visual Memory Test pass rate of ≥75% — heuristic judgment, not measurable.
  - Arc quality — judged against the spec's beginning/middle/end criterion, but "arc" is inherently interpretive.
  - Audio redundancy at the paragraph level — spot-checked sub-chapter 27 only; full 17-section walk would tighten the verdict but the spot check matched expectations.

---

## Ledger Hook

ch03 result: Pass 1 PASS / Pass 2 PASS / Ship. No probe regressions observed. Pattern note: this is the third KaR chapter where the audio chapter is rendered into a deck that promotes the central 2x2 OUT of its native sub-chapter position to the front of the deck. If ch01 and ch02 reports also flagged this pattern, it is now a 3-episode signal and worth formalizing in `slide-deck-patterns.md` under "Promotion of the organizing structure to the deck head."
