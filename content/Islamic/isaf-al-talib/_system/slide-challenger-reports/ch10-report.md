# Slide Challenger Report — ch10-mosques-and-sacred-space

**Book**: isaf-al-talib
**Run**: 2026-09-18 (challenger_version: 1.0)
**Scope**: per-chapter, ch10-mosques-and-sacred-space
**Deck source**: `content/Islamic/isaf-al-talib/slide-decks/ch10-deck-mosques-and-sacred-space.txt`
**Slide framing**: `content/Islamic/isaf-al-talib/slide-decks/ch10-framing-mosques-and-sacred-space.md`
**Audio chapter**: `content/Islamic/isaf-al-talib/chapters/ch10-mosques-and-sacred-space.txt`
**Discussion spine**: ABSENT (`_system/episode-drafts/` holds only `.gitkeep`)
**Slide spine / visual glossary**: ABSENT (`_system/slide-decks/ch10-mosques-and-sacred-space/` holds only `.validated`)
**Iterations**: 1 (of 5 max)

**Bundle status**: iterate
**Verdict**: BLOCKED

---

## Deck vitals

| Metric | Value | Band | Result |
|---|---|---|---|
| Audio chapter words | 5,570 | — | — |
| Deck source words | 5,568 | 50–100% of audio (2,785–5,570) | pass (100.0%) |
| Framing words | 247 | 150–250 | pass |
| Structural moments | 40 | — | — |
| Prose paragraphs >100 words | 0 | 0 | pass |
| Em dashes (either file) | 0 | 0 | pass |
| Inline phonetic parens (R-PHONETICS-OUT) | 0 | 0 | pass |
| Deck-wide 8-gram overlap with audio | 7.6% | — | low, genuine rewrite |
| Framing required H2 sections | 5 of 5 | 5 | pass |

**Diagram-type distribution** (40 moments, 9 distinct types):

| Type | Count | Share |
|---|---|---|
| Process flow | 8 | 20.0% |
| Contrast pair | 8 | 20.0% |
| Annotated structure | 7 | 17.5% |
| Hierarchy | 6 | 15.0% |
| Comparison matrix | 4 | 10.0% |
| Visual metaphor | 3 | 7.5% |
| Named-axis 2x2 | 2 | 5.0% |
| Quadrant map | 1 | 2.5% |
| Genealogy chain | 1 | 2.5% |

---

## Pass 1 — Per-Structure Probes

| Probe | Result | Moments flagged | Notes |
|---|---|---|---|
| SL-P1 Restatement | **fail (P0)** | M16, M23, M24, M39 | 4 moments replaceable by a single audio sentence; threshold is 2 |
| SL-P2 Literal Illustration | pass | — | Zero "image of"/"photo of"/stock-photo language in the deck. One P2 advisory on the framing's Prohibited Patterns list |
| SL-P3 Structure-vs-Description | **fail (P0)** | M15, M16, M18, M22, M23, M24, M29, M34 | 4 hierarchies assert parent-child edges that are not kind-of/part-of relations; 1 metaphor is non-spatial; 2 process flows have no transitions or branches; 1 annotated structure has no positions |
| SL-P4 Diagram-Type Discipline | pass | — | All 40 moments name a taxonomy type. No blank/TBD/various. 2 P2 advisories on framing steering discipline |
| SL-P5 Diversity | pass | — | 9 distinct types; contrast pair, comparison matrix AND named-axis 2x2 all present, as the theological-argument affinity row predicts |
| SL-P6 Audio Redundancy | pass | — | 4 of 40 moments (10%) mirror an audio paragraph without structural gain; threshold is 70%. One P2 advisory on H2 outline |
| SL-P7 Justified Skip | n/a | — | Chapter is not `slide-deck-status = not-needed`; a deck exists |
| SL-P8 Coverage | **n/a (input absent)** | — | No `04-discussion-spine.md` and no `01-slide-spine.md` exist, so no `[VISUAL CANDIDATE]` beats can be cross-referenced. Fallback concept-coverage check run against the audio chapter: pass (see below) |

### SL-P8 fallback — concept coverage against the audio chapter

Because the probe's designated input is missing, the Challenger ran the `slide-deck-format.md` Common Mistake 6 check instead (concepts present in the audio chapter absent from the deck source). All 38 audio concepts are represented: the earth-as-mosque grant and its three exceptions, graves and building near them, the mosque above a shop and the demolition fork, the governor's permission, the mosque inside a house and Abu Abd Allah's dislike, jointly owned land, the small mosque, Muhammad ibn al-Fahd on the domed structure, the disliked qiblah framings, the five greeting questions, the dawn latecomer, the Fajr make-up and its blocked windows, the courtyard and precincts, the neighbour defined by audibility, the cited saying, validity against preference, bypassing the nearer mosque, repeated congregations, the roof case, the funeral prayer, the traveller without water, the four qiblah-uncertainty states, the sutrah cases, praying between two rows, camels against cows and sheep, the twelve disliked places, the hudud prohibition, "I did not find it", weapons from Ta'eefil al-Da'a'im, the seven ranks, and the four closing bodily sayings. **No concept gap found.**

This is a fallback, not the probe. SL-P8 remains formally unexecutable for this chapter.

---

## Pass 2 — Architectural Pass

| Check | Result | Notes |
|---|---|---|
| SL-A1 Visual Memory Test | pass (narrow) | 6 firm failures (M12, M15, M16, M23, M24, M39) = 15%; 9 including borderline (M07, M22, M29) = 22.5%. Threshold is 30%. Passes, but the margin is thin and every one of the 6 is already cited under P0 probes |
| SL-A2 Variety | pass | Largest share 20% (Process flow, Contrast pair tied at 8/40). Threshold is >60% for a 10+ moment deck |
| SL-A3 Arc | pass | Opens with the narrowing-bands annotated structure (M01) and front-loads the central 2x2 (M04); middle builds dedication → entry → edges → gathering → direction; closes on the nested-enclosures metaphor (M38) and the thesis-against-misreading contrast (M40). One defect inside the close: M39 is a takeaways list sitting between the two structural closers |
| SL-A4 Cross-Episode Consistency | n/a | No `slide-decks/_visual-registry.md` exists for this 17-deck series, so no conventions can be checked. Recorded as a P2 advisory |

---

## Failures requiring Worker iteration

### P0 — blocks ship

#### SL-P1 Restatement — M16, M23, M24, M39

**SL1 · M16 · `ch10-deck-mosques-and-sacred-space.txt:197` · VERIFIED**
Content: `Reading: these are not construction decisions. They are decisions about promises made to worshippers.`
Audio ¶47 reads: "These are not merely construction decisions. They are decisions about promises made to worshippers." The moment's three elements (promise given / held / absent) are the same paragraph's two if-clauses plus a restatement. A host saying the audio sentence loses nothing.
Suggested re-authoring: drop the moment, or convert it into what the audio cannot carry — a before/after state change on the property itself, e.g. an annotated structure of the same building with the owner's rights redrawn on each side of the dedication act.

**SL2 · M23 · `ch10-deck-mosques-and-sacred-space.txt:288` · VERIFIED**
Content: `Ruling: yes, this is established as permissible, and there is nothing wrong with it` / `End: the obligation to value communal prayer does not trap the worshipper in the nearest building when a more meritorious sacred place is available`
Both lines are verbatim from audio ¶73; every node of the flow is a clause of that one paragraph (27.2% 8-gram overlap, the highest in the deck). The flow has no decision node and no branch — nodes 2 and 3 are facts, not steps.
Suggested re-authoring: delete. M36 (`:460`) already renders this case as a real branching flow read through the rank ladder; M23 is its unbranched precursor.

**SL3 · M24 · `ch10-deck-mosques-and-sacred-space.txt:302` · VERIFIED**
Content: `Rule: two imams should not lead the same prayer simultaneously in the same gathering` / `Exception: unless the first has vacated his place and another has been appointed in his stead`
Every node is a clause of audio ¶75 in the same order (25.3% overlap). "Rule:" and "Exception:" are assertions, not process steps.
Suggested re-authoring: the visual content here is the mosque's *memory of its own prayer* — M25 (`:316`) already carries that spatially. Either fold M24's rule into M25 as a precondition callout, or re-type M24 as a contrast pair (gathering intact against gathering dispersed) where the two columns differ in what the second imam may do.

**SL4 · M39 · `ch10-deck-mosques-and-sacred-space.txt:497` · VERIFIED**
Content: `- Level 1: A mosque is not merely a building` / `  - Level 2: It is property transformed by permission, dedication and communal claim`
Audio ¶131: "First, a mosque is not merely a building; it is property transformed by permission, dedication, and communal claim. Second, entering a mosque places the worshipper inside an ordered field of greeting, Sunnah, obligation, congregation, time, and rank. Third, sacred space trains the whole body..." The Level 1 and Level 2 lines are that paragraph split at its semicolons. This is a Key-Takeaways slide in hierarchy clothing — barred by the deck's own framing ("No bullet list masquerading as a diagram") and by `slide-deck-steering.md` Category 4 ("Do not produce a slide titled 'Key Takeaways' — takeaways belong to the audio").
Suggested re-authoring: delete. M38 (three nested enclosures) and M40 (thesis against misreading) already close the deck structurally; M39 sits between them and weakens both.

#### SL-P3 Structure-vs-Description — M15, M16, M18, M22, M23, M24, M29, M34

**SL5 · M22 · `ch10-deck-mosques-and-sacred-space.txt:276` · VERIFIED**
Content: `- Level 1: Forbidden` / `  - Level 2: Disliked` / `  - Level 2: Permissible` / `  - Level 2: Obligatory`
`slide-deck-patterns.md` Hierarchy Tree requires parent-child relations that are part-of or kind-of. Disliked, Permissible and Obligatory are not kinds of Forbidden — they are points on a graded register. Rendered as a tree, this deck will put "Permissible" inside "Forbidden" in a jurisprudence deck. What is missing: a true root, or the right type.
Suggested re-authoring: re-type as a visual metaphor on a spectrum (forbidden → disliked → permissible → commendable → obligatory) with the chapter's cases pinned at their points, which is what the moment's own lead-in ("cannot be flattened into yes and no") is reaching for.

**SL6 · M29 · `ch10-deck-mosques-and-sacred-space.txt:370` · VERIFIED**
Content: `- Level 1: Praying in open ground with a barrier available` / `  - Level 2: Praying in open ground with nothing to use`
The Level 2 node is the negation of its Level 1 parent, not a sub-case of it; the second Level 2 node (a stranger's sword) is not a sub-case either. The Level 1 node carries no ruling of its own. The lead-in says "from ordinary provision down to constraint", which names a scale, not a nesting.
Suggested re-authoring: process flow or spectrum ordered by decreasing provision, with the sandals prohibition and the sword rulings as terminal states.

**SL7 · M34 · `ch10-deck-mosques-and-sacred-space.txt:434` · VERIFIED**
Content: `- Level 1: Prayer in one's house, counting as one prayer` / `  - Level 2: Prayer in the market mosque, counting as twelve` (nesting continues to Level 7)
Seven merit ranks nested seven deep. Prayer in the market mosque is not part-of or kind-of prayer in one's house. The framing's own Visual Priority 3 asks for "one ascending ladder, rungs labelled from one to one hundred thousand" — a ladder, which a hierarchy tree does not draw.
Suggested re-authoring: re-type as a visual metaphor (ascending ladder / ranked scale) with the seven rungs and their multipliers, satisfying the framing as written.

**SL8 · M16 · `ch10-deck-mosques-and-sacred-space.txt:197` · VERIFIED**
Content: `Metaphor: a promise made, then held.`
`slide-deck-patterns.md` Visual Metaphor requires an abstract relation MADE SPATIAL — concentric circles, spectrum, layers, branches. "A promise made, then held" is temporal and verbal; nothing in it can be drawn. The three elements are propositions, not element assignments to a spatial figure.
Suggested re-authoring: see SL1. If the moment survives at all, it needs a spatial figure.

**SL9 · M23, M24 · `ch10-deck-mosques-and-sacred-space.txt:288, :302` · VERIFIED**
Content: `Rule: two imams should not lead the same prayer simultaneously in the same gathering` (M24); `A farther mosque is of greater rank` (M23)
`slide-deck-patterns.md` Process Flow requires nodes, transitions and start/end states, and names as its anti-pattern "Numbered list pretending to be a flow. A flow needs visible transitions and (often) branches." Neither moment has a decision node or a branch; the arrows connect assertions, not state changes. Six of the deck's eight process flows (M09, M19, M27, M36, M06, M07) do carry real branches or ordered transitions, which makes these two the outliers rather than a house style.
Suggested re-authoring: as in SL2 and SL3.

**SL10 · M18 · `ch10-deck-mosques-and-sacred-space.txt:218` · INFERRED**
Content: `- Level 1: Sacred time governs the whole field` / `  - Level 2: Obligation before devotion` / `  - Level 2: Congregation before private devotion`
Only the first Level 2 branch ("What the hour permits") is genuinely governed by sacred time. The other two are independent ordering principles, so the root reads as a banner rather than a parent. Marked INFERRED because the root is at least defensible as a governing claim, unlike SL5 and SL6.
Suggested re-authoring: either re-root at "the ordered field at the door" with sacred time as one of three co-equal branches, or re-type as a priority ladder.

**SL11 · M15 · `ch10-deck-mosques-and-sacred-space.txt:187` · VERIFIED**
Content: `Parts, each with what it compromises:` / `- A bathroom. Annotation: purity and dignity.`
`slide-deck-patterns.md` Annotated Structure requires "Parts (named, with positions)" and names as its anti-pattern "Callouts without spatial relation. Annotated structures need the spatial layout to do work." This moment gives four parts and four annotations and no positions at all — it is a labelled list. Every other annotated structure in this deck (M01, M08, M12, M25, M33, M37) does commit positions, so this is a local lapse, not the deck's pattern.
Suggested re-authoring: position the four compromising objects around the qiblah line the worshipper faces, so the diagram shows the field of sight the moment's own Reading line describes.

### P1 — ship-with-caution

None. Both P1-tier probes (SL-P5, SL-P6) and all four architectural checks pass.

### P2 — advisory

**SL12 · SL-P6 · `ch10-deck-mosques-and-sacred-space.txt:3` · VERIFIED**
The deck carries 9 H2 movements against the audio chapter's 5. All five audio movements are preserved; four are added (`The Edges of the Mosque` :247, `Order Inside the Gathering` :300, `The Ladder of Ranked Places` :432, `The Body at the Mosque Door` :474). `slide-deck-format.md` says "H2 for movements (same as audio chapter — chapter outline is preserved)." The subdivisions are defensible on a 5,568-word deck and they improve the arc, but the outline is a superset, not a mirror. Same signature was raised on the prior ch10 run and remains open.

**SL13 · SL-P8 · `_system/episode-drafts/` · VERIFIED**
No `04-discussion-spine.md` for this chapter and no `01-slide-spine.md` under `_system/slide-decks/ch10-mosques-and-sacred-space/` (the folder holds only `.validated`). Probe 8 cannot execute as specified. The fallback concept check passes, but coverage against `[VISUAL CANDIDATE]` beats is unverifiable for this chapter and for the book.

**SL14 · SL-A4 · `slide-decks/` · VERIFIED**
No `slide-decks/_visual-registry.md` exists. This book ships 17 decks with recurring entities (the Prophet, Amir al-Mu'minin Ali ibn Abi Talib, Muhammad ibn al-Fahd, the questioner) and no cross-episode visual convention is recorded, so SL-A4 cannot fire for any chapter in the series.

**SL15 · SL-P4 · `ch10-framing-mosques-and-sacred-space.md:22` · VERIFIED**
Content: `- "Render everything in black and white line art on a white background."`
`slide-deck-format.md` requires Steering Phrases to be "drawn from `slide-deck-steering.md`". This phrase is in none of Categories 1–6. It now appears in 7 of this book's 17 framings. See the learning-loop proposal below.

**SL16 · SL-P4 · `ch10-framing-mosques-and-sacred-space.md:27` · VERIFIED**
Content: `Do not read this prompt aloud.`
An Audio Overview idiom. A slide deck has no narration, so the instruction is inert, and it sits outside the five required H2 sections.

**SL17 · SL-P3 · `ch10-framing-mosques-and-sacred-space.md:12` · VERIFIED**
Content: `- The seven levels of prayer by place as one ascending ladder, rungs labelled from one to one hundred thousand.`
The framing asks for a ladder; deck M34 (`:434`) supplies a seven-deep hierarchy tree. The two deliverables disagree about how the same moment renders. Resolving SL7 resolves this.

**SL18 · SL-A1 · `ch10-deck-mosques-and-sacred-space.txt` · INFERRED**
Six moments fail the memory test outright (M12 front/behind/beneath layering that is rhetorical rather than spatial; M15 labelled list; M16 non-spatial metaphor; M23 and M24 unbranched flows; M39 takeaways list) and three are borderline (M07 linear opening flow, M22 and M29 false hierarchies). 15% firm, 22.5% inclusive, against a 30% threshold. The check passes; it is recorded because every firm failure is already a P0 citation and fixing the P0s lifts this margin rather than leaving it at the edge.

**SL19 · SL-P2 · `ch10-framing-mosques-and-sacred-space.md:15` · VERIFIED**
The Prohibited Patterns section bans photographs, stock imagery and decorative ornament but does not bar figural depiction of persons. The deck names and quotes the Prophet, peace and blessings be upon him and his family, and Amir al-Mu'minin Ali ibn Abi Talib repeatedly. For an `islamic_scholarly` profile this prohibition belongs in the list explicitly. Consistent with the same finding on ch22 and ch25.

---

## Verified vs Inferred

| Category | Count | Findings |
|---|---|---|
| VERIFIED | 17 | SL1–SL9, SL11–SL17, SL19 |
| INFERRED | 2 | SL10 (M18 hierarchy root defensible as a governing claim), SL18 (memory-test judgment, heuristic by construction) |

The Worker addresses both categories on iteration.

---

## What the deck does well

Recorded so re-authoring does not damage it. The two named-axis 2x2s (M04 `:32`, M35 `:446`) name both axis poles and populate all four quadrants with a named case and its reasoning — they are the strongest moments in the deck and M04 is correctly front-loaded. The concentric-rings metaphor (M20 `:249`) and the three-nested-enclosures metaphor (M38 `:488`) are genuinely spatial and carry the chapter's thesis. The quadrant map (M31 `:398`) places all twelve disliked places by the reason each is disliked rather than lumping them as impure, which is exactly the "surprising entity placement" the memory test rewards. The necessity-against-choice contrast pair (M30 `:382`) has four parallel attribute rows and a shared row. Deck-wide overlap with the audio is 7.6%, so this is a real visual rewrite, not a bulletified mirror — the P0 findings are eight local moments in a deck of forty.

---

## Learning-loop proposals

Not written to the reference files by this agent (v1.0 is read-only over all bundle and reference artifacts). Surfaced for the Worker and for Asif.

1. **Steering phrase, Category 7 candidate.** `"Render everything in black and white line art on a white background."` appears in 7 of this book's 17 framings and has now been flagged 4 times across chapters as off-canon. It has cleared the 2-episode threshold in `slide-deck-steering.md`'s promotion rule. Propose adding it to that file, most naturally as a new house-style category, so the framings stop drifting from the canon they cite.
2. **Anti-pattern candidate for `slide-deck-patterns.md`.** *Rank-scale-as-hierarchy-tree*: a graded scale (merit ranks, legal registers, degrees of constraint) rendered with nested indentation, which a renderer draws as containment. Four instances in this deck alone (M18, M22, M29, M34) and a matching `wrong-type-hierarchy-for-sequence` signature already recorded twice elsewhere in this book. The existing Hierarchy Tree anti-pattern covers skipped levels but not false nesting.
3. **Infrastructure.** `slide-decks/_visual-registry.md` is absent book-wide (11 findings), and no chapter in this book has a `04-discussion-spine.md` or `01-slide-spine.md` (SL-P8 unexecutable everywhere). Two of the twelve checks cannot run on any chapter of this book until those artifacts exist.

---

## Ledger emission

19 findings emitted to `_learning/findings.jsonl` this run (`source: slide-deck-challenger`, `source_version: 1.0`). Finding IDs SL1–SL19 are run-scoped; the aggregator dedups across runs by `signature`. Signatures for SL12, SL13 and SL14 are deliberately identical to those raised on the prior ch10 run — those findings remain open against the re-authored deck.

**Bundle status**: iterate
**Verdict**: BLOCKED
