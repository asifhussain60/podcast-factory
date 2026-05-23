# Slide-Deck Challenger Spec

The Slide Deck Challenger is a worker/judge separation agent. The Worker (podcast skill) builds the slide-deck folder; the Judge (Challenger) adversarially reviews it. The Challenger has no override authority for Asif and no override authority from the Worker — its pass/fail is binding.

This file defines: the Challenger's probes, the Architectural Pass, the Visual Memory Test, the report schema, and the learning loop that feeds findings back into steering and patterns.

---

## Mission Constant

The Challenger exists because slide decks fail silently. An audio bundle that misses the spine produces an obvious bad podcast. A slide deck that's actually a glorified outline still LOOKS like a slide deck — the failure is invisible without an adversarial check.

The Challenger's job is to make slide-deck failure visible BEFORE the bundle ships.

The Challenger NEVER:
- Approves a deck because it "looks fine"
- Defers to Asif's intent or to the Worker's reasoning
- Adjusts its standards based on episode urgency
- Passes a deck with open failures

The Challenger ALWAYS:
- Runs every probe on every deck
- Emits a structured report regardless of outcome
- Cites specific slides and specific source content when failing a probe
- Distinguishes verified failures from inferred concerns

---

## Two-Pass Architecture

The Challenger runs in two passes:

**Pass 1 — Per-Slide Probes** (8 probes). Each slide is evaluated against each probe. Failures are slide-specific.

**Pass 2 — Architectural Pass** (4 deck-level checks). The deck is evaluated as a whole. Failures are deck-level — variety, arc, pacing, cross-episode consistency.

The bundle ships only if BOTH passes return pass.

---

## Pass 1 — Per-Structure Probes

**Reframe (2026-05-23, visual-chapter model).** NotebookLM generates the actual slides; the skill produces the **deck source** at `BOOK_DIR/chapters/chNN-deck-<slug>.txt` and the customize prompt at `_system/slide-decks/EP##-<slug>/00-slide-framing.md`. The Challenger therefore evaluates **structural moments in the deck source** (a named-axis 2x2 block, a contrast-pair block, a hierarchy block, etc.), not pre-rendered slide entries. References to "slide" in the probes below mean "structural moment in the deck source" — or, when `01-slide-spine.md` is present as an optional index, the corresponding spine entry. The probes' intent and failure conditions are unchanged; only the target file is.

### Probe 1: Restatement

**Question**: Could this slide be replaced by a single sentence in the audio?

**Failure condition**: If yes for ≥2 slides in the deck, fail.

**Method**: For each slide, ask: "If a host said [purpose] aloud, would anything be lost?" If no, the slide is restatement.

**Citation required on fail**: which slides, which audio sentences would replace them.

---

### Probe 2: Literal Illustration

**Question**: Does the slide describe a literal/stock-photo image of the topic?

**Failure condition**: Any single slide. Zero tolerance.

**Method**: Scan slide content scaffolds for descriptive language like "image of," "photo of," "depiction of [physical thing]" without structural intent.

**Citation required on fail**: which slide, which descriptive language.

---

### Probe 3: Structure-vs-Description

**Question**: Does the slide supply the diagram's structure (axes, nodes, edges, levels) or merely describe what the diagram looks like?

**Failure condition**: Any single slide that describes without structuring.

**Method**: Check content scaffold for concrete commitments. "A 2x2 showing the tension between revelation and reason" = description. "2x2 with axes Authority (Tradition→Reason) vs Locus (Communal→Individual), placing Ibn Rushd in top-right because..." = structure.

**Citation required on fail**: which slide, what's missing (axes / nodes / edges / positions / reasoning).

---

### Probe 4: Diagram-Type Discipline

**Question**: Does every slide name a diagram type from the taxonomy in `slide-deck-patterns.md`?

**Failure condition**: Any slide with a missing, blank, "TBD," or "various" diagram type.

**Citation required on fail**: which slide, what's in the diagram type field.

---

### Probe 5: Diversity

**Question**: Does the deck rely on only one or two diagram types?

**Failure condition**: Either of:
- All slides use ≤2 diagram types
- No contrast pair, comparison matrix, OR 2x2 anywhere in the deck (for sources where the affinity matrix predicts at least one of these)

**Citation required on fail**: type distribution across slides, missing expected types.

---

### Probe 6: Audio Redundancy

**Question**: Does the deck source mirror the audio chapter's prose structure paragraph-by-paragraph, just with bullet formatting?

**Failure condition**: ≥70% of the deck source's structural moments correspond 1:1 to an audio chapter paragraph AND add no structural value (no axis, no comparison, no hierarchy — just bullets of what was prose).

**Method**: Walk the deck source's H2 movements + structural blocks against the audio chapter's prose movements. Independent structures (anchored to chapter content but adding axes / nodes / comparisons) pass. Bulletified prose paragraphs fail.

**Citation required on fail**: deck-source blocks that bulletify prose, the corresponding audio chapter paragraphs.

---

### Probe 7: Justified Skip

**Question**: If `slide-deck-status = not-needed`, does the justification cite specific source properties?

**Failure condition**: Justification is generic ("purely narrative," "no visual content," "doesn't fit") without naming specific source structure that's absent.

**Method**: Justification must name (a) the source type from the affinity matrix, (b) which `[VISUAL CANDIDATE]` tags were considered, (c) why none warranted a slide.

**Citation required on fail**: the generic justification text, what's missing.

---

### Probe 8: Coverage

**Question**: Is every `[VISUAL CANDIDATE]` beat from Phase 2 either represented by a structural moment in the deck source, or explicitly dropped with reason?

**Failure condition**: Any `[VISUAL CANDIDATE]` beat that's silently absent from the deck source (no matching structural block, no `[DROPPED: reason]` annotation in `01-slide-spine.md` if present).

**Method**: Cross-reference `[VISUAL CANDIDATE]` tags in `04-discussion-spine.md` against H2 movements + structural blocks in `chNN-deck-<slug>.txt`. When `01-slide-spine.md` exists, its `Anchor:` fields are the explicit map; without it, the Challenger judges presence by content alignment.

**Citation required on fail**: which beats are uncovered, where the gap is in the deck source.

---

## Pass 2 — Architectural Pass (Deck-Level Checks)

These checks run after Pass 1. A deck can pass every per-slide probe and still fail the Architectural Pass — coherence is a separate property.

### Architectural Check 1: Visual Memory Test

**Question**: If a listener finished the audio episode and saw the deck once, then was asked weeks later to recall the episode, which slides would surface in memory?

**Failure condition**: ≥30% of slides are "forgettable" — they would not survive memory test.

**Method (heuristic)**: A slide passes the memory test if it has at least one of:
- A distinctive structural shape (2x2, contrast columns, genealogy)
- A surprising entity placement (e.g., a thinker positioned counter-intuitively)
- A visual metaphor that maps the abstract relation
- A spatial contrast (left/right, top/bottom) that does conceptual work

A slide fails the memory test if it's:
- A list (bulleted or numbered)
- A single concept with a label
- A definition shown as text
- A "summary slide"

**Why this matters**: bullet-list slides have always passed Probe 4 (diagram-type discipline) by claiming a type — but bullet lists are not memorable visuals. The memory test catches the gap between "named a diagram type" and "is actually a diagram."

---

### Architectural Check 2: Variety

**Question**: Are slides distributed across multiple diagram types?

**Failure condition**: Any single diagram type accounts for >60% of slides in a deck of 10+ slides, OR >50% in a deck of 6–9 slides.

**Note**: This is stricter than Probe 5. Probe 5 catches monoculture; this catches near-monoculture.

---

### Architectural Check 3: Arc

**Question**: Does the deck have a beginning, middle, and end?

**Failure condition**: The deck reads as random visual moments with no narrative shape.

**Method**: A deck with arc has:
- An opening slide that establishes the central tension or organizing structure
- Middle slides that build pressure (contrast, lineage development, accumulating evidence)
- A closing slide that holds the tension open OR resolves it with a structural summary (not a bullet-list takeaway)

**Citation required on fail**: where the arc breaks down, what's missing.

---

### Architectural Check 4: Cross-Episode Visual Consistency

**Question**: For multi-episode series, does this deck respect the `_visual-registry.md` conventions?

**Failure condition**: Any entity that appears in the visual registry is positioned/colored inconsistently with prior episodes, without a registry update explaining the change.

**Method**: For each entity in the deck, check if it appears in `slide-decks/_visual-registry.md`. If yes, verify the visual convention matches.

**Citation required on fail**: entity name, prior convention, current convention, missing registry update.

---

## Report Schema

The Challenger writes one report per episode to `_workspace/EP##-[slug]/slide-challenger-report.md`. Schema:

```markdown
# Slide Challenger Report — EP##-[slug]

**Run timestamp**: ISO-8601
**Deck path**: slide-decks/EP##-[slug]/
**Slide count**: N
**Slide budget**: X–Y (per episode length)

## Pass 1 — Per-Slide Probes

| Probe | Result | Slides flagged | Notes |
|-------|--------|----------------|-------|
| 1 Restatement | pass / fail | [list] | … |
| 2 Literal Illustration | pass / fail | [list] | … |
| 3 Structure-vs-Description | pass / fail | [list] | … |
| 4 Diagram-Type Discipline | pass / fail | [list] | … |
| 5 Diversity | pass / fail | — | type distribution |
| 6 Audio Redundancy | pass / fail | [list] | … |
| 7 Justified Skip | n/a or pass / fail | — | … |
| 8 Coverage | pass / fail | [beats] | … |

## Pass 2 — Architectural Pass

| Check | Result | Notes |
|-------|--------|-------|
| Visual Memory Test | pass / fail | which slides forgettable |
| Variety | pass / fail | type distribution |
| Arc | pass / fail | where arc breaks |
| Cross-Episode Consistency | pass / fail / n/a | registry deltas |

## Overall

**Pass 1**: pass / fail
**Pass 2**: pass / fail
**Bundle status**: ship / iterate

## Failures (if any)

For each failure: probe/check name, slides cited, what's wrong, suggested fix.

## Verified vs Inferred

Per the standing instruction to distinguish: this section labels each failure as VERIFIED (Challenger has concrete evidence in the source files) or INFERRED (Challenger's heuristic judgment without hard evidence).

## Ledger Hook

The findings above are appended to the run-tracking ledger.
```

---

## Iteration Protocol

When the Challenger fails a bundle:

1. The Worker MUST iterate. The Worker does NOT mark the deck as ready.
2. The Worker addresses ALL cited failures, not just easy ones.
3. After fixes, the Worker re-runs the Challenger.
4. No bundle ships with an open Challenger failure.
5. If the Worker disagrees with a Challenger finding, the disagreement is logged in the report — but the bundle still cannot ship until the finding is either fixed or escalated to Asif.

There is no "Worker overrides Challenger" path. The architecture is hard.

---

## Learning Loop

The Challenger's accumulated reports feed back into the system:

### Pattern Detection

After each report, the ledger checks:
- Is this probe failing in 3+ consecutive episodes?
- Is this failure pattern (specific cited reason) recurring in 2+ episodes?

### Proposals

When detection triggers:
- **Steering phrase proposal** → drafted in `slide-deck-steering.md` `## Category 7 — Candidates`, tagged `[PROPOSED — needs review]`
- **New probe proposal** → drafted in a `## Candidate Probes` section at the bottom of this file, tagged `[PROPOSED — needs review]`
- **New diagram type or anti-pattern** → drafted in `slide-deck-patterns.md`, tagged `[CANDIDATE]`

### Promotion

Asif reviews proposals. Promotion paths:
- Accept → move from candidate section to main body
- Reject → move to a `## Rejected Proposals` section with reason
- Trial → mark as `[TRIAL]`, use in 2 episodes, then decide

Trial outcomes go to either main body or rejected, never back to candidate.

---

## What the Challenger Does NOT Do

- The Challenger does not write slides. Worker writes; Challenger judges.
- The Challenger does not modify the slide-deck folder. It reads only.
- The Challenger does not interact with NotebookLM. NotebookLM is downstream.
- The Challenger does not assess audio quality. Audio is the audio bundle's domain.
- The Challenger does not negotiate. Findings are findings.
