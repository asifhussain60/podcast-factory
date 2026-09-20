# Slide Challenger Report, ch27-ramadan-foundation-and-obedient-knowledge

**Book**: isaf-al-talib
**Run timestamp**: 2026-09-18T08:31:00Z (slide-deck-challenger v1.0)
**challenger_version**: 1.0
**Scope**: per-chapter, ch27-ramadan-foundation-and-obedient-knowledge
**Iterations**: 2 (of 5 max)
**Deck source**: `content/Islamic/isaf-al-talib/slide-decks/ch27-deck-ramadan-foundation-and-obedient-knowledge.txt`
**Deck framing**: `content/Islamic/isaf-al-talib/slide-decks/ch27-framing-ramadan-foundation-and-obedient-knowledge.md`
**Audio chapter**: `content/Islamic/isaf-al-talib/chapters/ch27-ramadan-foundation-and-obedient-knowledge.txt`
**Discussion spine**: ABSENT (`_system/episode-drafts/` contains only `.gitkeep`)
**Slide spine**: ABSENT (`_system/slide-decks/ch27-ramadan-foundation-and-obedient-knowledge/` holds only `.validated`)
**Visual glossary**: ABSENT
**Visual registry**: ABSENT (no `slide-decks/_visual-registry.md`)
**slide-deck-status**: needed (a deck exists; not skip mode)

**Structural moment count**: 43 typed, zero untyped
**Deck word count**: 5,966 (audio 5,990 = 99.6%, band 50 to 100%)
**Framing body word count**: 250 (band 150 to 250, at the ceiling exactly)

**Bundle status**: iterate
**Verdict**: BLOCKED

---

## This is iteration 2, on a re-authored pair

The deck source (mtime 03:53:49) and the framing (03:54:53) were both rewritten after iteration 1's
report was written (03:37:21). The file under review is materially different from the one that report
describes: 43 typed blocks against 35, eight H2 movements against nine, the `- Row: cellA | cellB`
text scaffold replacing markdown tables throughout, and several of iteration 1's flagged moments
folded into neighbouring structures. Moment IDs below are Challenger-assigned in reading order and do
NOT correspond to iteration 1's IDs; every finding is anchored to a line number instead.

### What the re-authoring fixed, verified

| Iteration 1 finding | Status now |
|---|---|
| SL2, two untyped bullet blocks (P0, SL-P4) | **RESOLVED.** Zero untyped content blocks in the file, verified by walking every non-empty, non-heading, non-blockquote line against its enclosing typed block |
| SL11, M30 typed a timeline and was eight stacked verse blockquotes (P1) | **RESOLVED in type.** The eight verses are now inlined as Parts 1 to 8 of a typed annotated structure at L455, not eight standalone quote slides. Residual defect is flatness, folded into SL7 |
| SL5, M27 external check re-lineated audio:107 (P0) | **RESOLVED.** Folded into L404, a five-row fully matched contrast pair whose "Result in the year four hundred" row carries the Haram slaughter on both calendars |
| SL3, M10 fallback flow re-lineated audio:41 (P0) | **RESOLVED.** Folded into L141 as the concession annotation inside L134 |
| SL4, M34 blessing re-lineated audio:133 (P0) | **RESOLVED.** Absorbed into L519's visual metaphor, which assigns every element |
| SL9, M14 moon's four bare attributes (P0) | **RESOLVED.** Folded into L201 as the standing note on the moon/foundation matrix |
| SL13, M8 declared a test it applied in two of five rows (P1) | **MOSTLY RESOLVED.** Reframed at L123 to "by what makes each fall due"; four of five rows now answer the column. One residual cell at P2, see SL14 |
| SL21, M29's contrast rows did not pair attribute-for-attribute (P2) | **RESOLVED at that moment.** Retyped as L445, a genuinely branching process flow. The pattern recurs elsewhere, see SL19 |
| SL20, framing body 267 words, over the 250 ceiling (P2) | **RESOLVED.** Now 250 exactly |
| Standing observation, markdown tables vs text scaffold | **RESOLVED** in favour of the scaffold. `grep -c '^|'` returns 0 and 31 scaffold rows are present, which is what `slide-deck-steering.md:145` prefers for NotebookLM |

### What it did not fix, and what it broke

| Iteration 1 finding | Status now |
|---|---|
| SL1, annotated structures carry no positions (P0) | **PARTIALLY RESOLVED, and worse in absolute terms.** Five of fourteen now carry a real layout; nine do not. The failing count rose from 8 to 9 and the type's share rose from 22.9% to 32.6% |
| SL6, the arithmetic paragraph as a linear flow (P0) | **UNRESOLVED, near verbatim.** Now L282. The recommended proportion figure was not drawn |
| SL8, licence-into-demand as a linear flow (P0) | **UNRESOLVED, near verbatim.** Now L468. The recommended reuse of the two-pan balance was not taken |
| SL2's second half, the two-figures discrepancy (P0) | **TYPED BUT NOT DRAWN.** Now L366, given an "Annotated structure." label and left as two bullets plus an annotation. The recommended two-mark calendar strip was not drawn |
| SL12, linear process flows with no branch (P1) | **UNRESOLVED.** Four of six, against four of five |
| SL14, Visual Memory Test (P1) | **IMPROVED BUT STILL FAILING.** 40.0% to 30.2% firm / 34.9% inclusive, against a 30% threshold |
| SL17, framing has no figural-depiction prohibition (P2) | **UNRESOLVED.** Fourth occurrence in the book |
| SL18(1), non-canonical rendering instruction in Steering Phrases (P2) | **UNRESOLVED.** Fifth occurrence in the book |
| SL18(2), no Category 4 anti-generic phrase (P2) | **UNRESOLVED.** The added phrase is Category 2, not Category 4 |
| SL19, framing quotation prohibition vs the deck's blockquotes (P2) | **UNRESOLVED**, though materially softer: 24 blockquote lines and no 29-line unattached cascade |
| — | **REGRESSION.** The framing dropped from five steering phrases to three, deleting iteration 1's canonical Category 3 matrix phrase and keeping the non-canonical rendering line. Net canonical phrases: three to two |
| — | **REGRESSION.** Iteration 1's M9, a contrast pair titled "Where the objection dies", is now L134, a four-aspect annotated list |

---

## Diagram-type distribution

| Type | Count | Share |
|---|---|---|
| Annotated structure | 14 | 32.6% |
| Comparison matrix | 7 | 16.3% |
| Process flow | 6 | 14.0% |
| Contrast pair | 5 | 11.6% |
| Visual metaphor | 4 | 9.3% |
| Timeline | 2 | 4.7% |
| Hierarchy | 2 | 4.7% |
| Genealogy chain | 2 | 4.7% |
| Named-axis 2x2 | 1 | 2.3% |

Nine distinct taxonomy types, largest share 32.6%. SL-P5 and SL-A2 both clear. The composition
shifted the wrong way between iterations: annotated structure, the one type whose taxonomy
requirement this deck does not meet, absorbed the growth (8 of 35 to 14 of 43), while contrast pair
fell from 6 to 5.

---

## Moment index (line anchors in the deck source)

| ID | Line | Type | Subject | P3 layout |
|---|---|---|---|---|
| M1 | 5 | Annotated structure | One chapter, three registers | pass, front/centre/close + seams |
| M2 | 13 | Visual metaphor | The chapter's governing image | pass |
| M3 | 20 | Process flow | The chapter's arc, start to end | n/a, linear |
| M4 | 38 | Contrast pair | Two objectors | pass |
| M5 | 58 | Annotated structure | The damaged manuscript, four places | pass, four named locations |
| M6 | 68 | Named-axis 2x2 | What private judgement costs | pass, deck's best moment |
| M7 | 84 | Process flow | The objection as the objector lays it out | n/a, linear |
| M8 | 94 | Contrast pair | The two causes | pass |
| M9 | 112 | Comparison matrix | Five pillars, the same architecture | pass, 5x4 |
| M10 | 123 | Comparison matrix | The same five, by what makes each fall due | pass, 5x2 |
| M11 | 134 | Annotated structure | Where the objection actually fails | **FAIL** |
| M12 | 145 | Visual metaphor | The great outward testimony, weighed | pass, two pans |
| M13 | 156 | Annotated structure | The damaged clause after the balance | **FAIL** |
| M14 | 162 | Hierarchy | The two callings | pass, 3 levels |
| M15 | 181 | Comparison matrix | The sun and the speaking soul | pass, 4x2 |
| M16 | 192 | Comparison matrix | The moon and the foundation | pass, 4x2 |
| M17 | 203 | Genealogy chain | Light, and what it passes through | pass, 3 directed chains |
| M18 | 209 | Annotated structure | The method, stated openly | **FAIL** |
| M19 | 215 | Timeline | The seven states of the moon | pass, ordered + period bands |
| M20 | 227 | Comparison matrix | The same seven, matched to what they figure | pass, 7x2 |
| M21 | 240 | Visual metaphor | Conjunction, the king and the minister | pass |
| M22 | 251 | Contrast pair | The one day where practice and doubt collide | pass |
| M23 | 273 | Genealogy chain | From the moon to the month | pass |
| M24 | 282 | Process flow | The arithmetic argument | n/a, linear |
| M25 | 296 | Contrast pair | Two perspectives on one sighting | pass, 4 matched rows |
| M26 | 312 | Annotated structure | One passage dissected clause by clause | pass, clause order + mapping |
| M27 | 328 | Comparison matrix | One inference, used twice | pass, 3x3 |
| M28 | 341 | Annotated structure | The exception, carved by function | pass, the cut is the layout |
| M29 | 353 | Timeline | The year four hundred | pass, 8 dated events + bands |
| M30 | 366 | Annotated structure | Two figures the letter does not reconcile | **FAIL** |
| M31 | 375 | Process flow | The counterfactual | pass, real Path A / Path B fork |
| M32 | 395 | Annotated structure | Why the phrase carries the weight | **FAIL** |
| M33 | 404 | Contrast pair | Two sightings, one month | pass, 5 matched rows |
| M34 | 424 | Annotated structure | The final objection and two limbs | **FAIL** |
| M35 | 433 | Hierarchy | Pillars settled by calculation | pass, 3 levels |
| M36 | 445 | Process flow | The prohibition re-read | pass, real Path A / Path B fork |
| M37 | 455 | Annotated structure | The sky read as a text | **FAIL**, 8 flat parts |
| M38 | 468 | Process flow | Licence converted into demand | n/a, linear |
| M39 | 485 | Annotated structure | The result, in three points | **FAIL** |
| M40 | 492 | Annotated structure | The closing address | **FAIL** |
| M41 | 501 | Comparison matrix | Three arrivals the series has not had | pass, 3x3 |
| M42 | 510 | Annotated structure | The figure at the centre, four moments | pass, marginal |
| M43 | 519 | Visual metaphor | The closing formula | pass |

Zero untyped content blocks. Verified programmatically: every non-empty line that is not an H1, an
H2 or a blockquote falls inside a block opened by a taxonomy label.

---

## Pass 1, Per-Structure Probes

| Probe | Result | Moments flagged | Notes |
|---|---|---|---|
| SL-P1 Restatement | **fail (P0)** | M3, M7, M11, M13, M18, M24, M30, M34, M37, M38, M39, M40 | 12 of 43 (27.9%) re-lineate one audio paragraph and commit to no axis, position, column, level, node or edge. Threshold is 2. Three are unresolved verbatim from iteration 1 |
| SL-P2 Literal Illustration | pass | — | Zero "image of / photo / photograph / stock / picture of / depiction of / illustration of / drawing of / painting" hits in the deck, verified by grep. Every visual instruction is a typed structure with content commitments. Two framing-side risks recorded at P2 |
| SL-P3 Structure-vs-Description | **fail (P0)** | M11, M13, M18, M30, M32, M34, M37, M39, M40 | 9 of 14 annotated structures name parts and place none. The taxonomy requires "Parts (named, with positions)" and names the failure outright |
| SL-P4 Diagram-Type Discipline | pass | — | All 43 blocks carry a named taxonomy type. Zero missing, blank, "TBD" or "various". Mis-typings inside declared structures are filed at P1 and P2 below, not against this probe's zero-tolerance condition |
| SL-P5 Diversity | pass | — | Nine distinct types. Contrast pair (5), comparison matrix (7) and named-axis 2x2 (1) all present, as the theological-argument, polemic and comparative-study affinity profiles jointly predict |
| SL-P6 Audio Redundancy | pass | the 12 SL-P1 moments | 12 of 43 (27.9%) are 1:1 with an audio paragraph and add no structure. Threshold is 70%. The remaining 31 cross-tabulate, place on axes, nest, band or fork material the prose never gathers |
| SL-P7 Justified Skip | n/a | — | Chapter is not in skip mode; a deck exists |
| SL-P8 Coverage | n/a (unverifiable) | — | No `04-discussion-spine.md` and no `01-slide-spine.md`, so there are no `[VISUAL CANDIDATE]` tags to cross-reference. Recorded at P2, not as a pass |

**Pass 1**: fail

### Methodology note

Content-word overlap is reported below as corroboration only, never as the test. Measured on this
deck, the seven-states correspondence matrix at M20 scores 83.5% and is one of the strongest moments
in the file, while the 2x2 at M6 scores 42.7%; the metric does not discriminate, because
`slide-deck-format.md` defines the deck source as a re-presentation of the same content at the same
depth rather than a summary. The discriminator used throughout is the spec's own: does the moment
commit to a structure a spoken sentence cannot carry? The Worker should not chase overlap down.

---

## Pass 2, Architectural Pass

| Check | Result | Notes |
|---|---|---|
| SL-A1 Visual Memory Test | **fail (P1)** | 13 of 43 firm = 30.2%, 15 of 43 inclusive = 34.9%, against a 30% threshold. Sensitivity stated in SL13 |
| SL-A2 Variety | pass | Largest type share 32.6% (annotated structure, 14 of 43), against a >60% ceiling for decks of 10+. Composition trend recorded at SL22 |
| SL-A3 Arc | pass | Real arc with a genuine bookend, evidenced below |
| SL-A4 Cross-Episode Consistency | n/a (unverifiable) | No `_visual-registry.md` exists for this book. Recorded at P2 |

**Pass 2**: fail

---

## Failures requiring Worker iteration

### P0 (blocks ship)

#### SL1, SL-P3, nine of fourteen annotated structures name parts and place none

- **File**: `content/Islamic/isaf-al-talib/slide-decks/ch27-deck-ramadan-foundation-and-obedient-knowledge.txt`, moments M11 (L134), M13 (156), M18 (209), M30 (366), M32 (395), M34 (424), M37 (455), M39 (485), M40 (492)
- **Deck excerpt (M18, L209 to 213)**: "Annotated structure. The method, stated openly before it is used. / - Premise: the conditions of the sun and moon in the corporeal world correspond to their spiritual counterparts in the world of religion. / - Consequence: the moon's states can be read. / - Constraint: they are read in order, phase by phase, not selected for convenience."
- **What is missing**: positions. `slide-deck-patterns.md` requires of an annotated structure "The whole (what the structure is), Parts (named, with positions), Annotation per part" and names the anti-pattern explicitly: "Callouts without spatial relation. Annotated structures need the spatial layout to do work." Rendered, each of the nine becomes a titled bullet list, which is why all nine are also the core of the Visual Memory Test failure.
- **Verification, and the credit due**: `grep -c 'Position:'` over this book's thirteen decks returns ch02=28, ch06=25, ch13=25, ch09=19, ch07=16, ch08=15, ch11=30, and ch12=0, ch16=0, ch21=0, ch22=0, ch26=0, ch27=2. The two ch27 hits are at L97 and L104 and are contrast-pair row labels ("Position: first, and prior"), not annotated-structure placements. Five of the fourteen nonetheless DO commit to a layout without using the field name, and the Worker should keep them: M1 places its three registers "at the front", "at the centre" and "at the close" and annotates the two seams between them; M5 locates its four manuscript breaks at four named points in the chapter's own sequence; M26 dissects one quoted passage into its clauses in order and maps each to an interpretive counterpart; M28 draws a cut with two functions inside it and everyone else outside; M42 places four moments on the lunar cycle M19 already draws. That is the form the other nine need.
- **Suggested Worker re-authoring**: give all nine an explicit position per part, on the model of `ch11-deck-imamate-in-prayer.txt:9-13`. Four have an obvious layout waiting. M30's two figures are a calendar strip with the people of truth's start mark two days before the common sighting and the stated one-day gap drawn beside it as a shorter measure, so the mismatch the letter refuses to reconcile becomes the visible content. M37's eight scriptural parts are three tiers, the sky as sign (40:57, 41:53), the sky sworn by (25:61, 56:75-76, 81:15-16, 85:1, 91:1) and the sky given for reckoning (10:5 alone), which makes the cascade an argument with a visible peak instead of eight labelled lines and delivers the claim the deck's own annotation at L466 asserts. M32's two costs are a before-and-after on one month strip, a month one day short against a day of obligation flipped into a festival. M34's two limbs are a fork, which M35 and M36 then populate.
- **VERIFIED**. Recurring: filed at P0 against ch11, ch16, ch22 and ch27 iteration 1.

#### SL2, SL-P1, M24 re-lineates the arithmetic paragraph, unresolved from iteration 1

- **File**: deck `:282-294`
- **Audio replaced**: `chapters/ch27-ramadan-foundation-and-obedient-knowledge.txt:83`
- **Deck excerpt**: "Start: the Quran was revealed over twenty-three years / It did not descend all at once in the month of Ramadan / It came down day by day, month by month, and year by year / Therefore the verse on its apparent face points to signs, to the criterion, and to the distinction"
- **Audio excerpt**: "We know the Quran was revealed over twenty-three years. It did not descend all at once in the month of Ramadan; it came down day by day, month by month, and year by year. So the verse, on its apparent face, points to signs, to the criterion, and to the distinction, rather than reporting a single night's delivery of a finished book"
- **What is missing**: six arrows over one audio paragraph, with no branch, no condition and no transition that is not simply the next clause. 87.3% overlap. The argument is a quantity mismatch, twenty-three years of revelation against one named month, and the mismatch is nowhere in the figure. Iteration 1 filed this at `:258-265` and recommended drawing the proportion; the block was re-worded and the shape was kept.
- **Suggested Worker re-authoring**: draw it. A twenty-three-year band with revelation distributed across the whole of it, set against the single Ramadan the verse names, with the gap between the two labelled "what interpretation is needed for". One figure replaces six boxes and shows the conclusion instead of asserting it in a seventh.
- **VERIFIED**. Unresolved from iteration 1.

#### SL3, SL-P1, M38 re-lineates the licence-into-demand paragraph, unresolved from iteration 1

- **File**: deck `:468-480`
- **Audio replaced**: `chapters/ch27-ramadan-foundation-and-obedient-knowledge.txt:119`
- **Deck excerpt**: "Start: the method is permitted / To delay knowledge of the planets' positions, their orbits, their peaks, and their nadirs / Is to delay engagement with the testimony to what Allah has established of His religion / ... / End: the study is a duty, not a permission"
- **What is missing**: 76.5% overlap, six boxes over one audio paragraph, no fork and no loop. The move the moment names, permission converting into obligation, is a change of modal status and is drawn as a straight line like every other step.
- **Suggested Worker re-authoring**: iteration 1's sketch still stands and the deck still owns the right figure. M12 at L145 is a two-pan balance for the great outward testimony, and this is the same testimony. Put "permitted" and "owed" on the two pans and show the natural-order evidence loading the second until it drops. That ties the chapter's licence and its demand into one recurring image.
- **VERIFIED**. Unresolved from iteration 1.

#### SL4, SL-P1, M30 was given a type label rather than a figure, unresolved from iteration 1

- **File**: deck `:366-370`
- **Audio replaced**: `chapters/ch27-ramadan-foundation-and-obedient-knowledge.txt:99`
- **Deck excerpt**: "Annotated structure. Two figures the letter states and does not reconcile. / - Figure 1: the people of truth entered their fast two days before the common sighting of the crescent. / - Figure 2: the discrepancy between the fasting of the people of truth and that of the people of disagreement was no more than one day. / - Annotation: the two sit oddly together, and are left as stated rather than smoothed."
- **What is missing**: 81.8% overlap, two bullets and a comment. Iteration 1 filed this block as untyped at `:344-346` and asked for a two-mark calendar strip. The remediation applied was the label "Annotated structure.", which clears SL-P4 and changes nothing a reader would see. This is the chapter's one open contradiction and it is the single most drawable fact in the movement.
- **Suggested Worker re-authoring**: see SL1's M30 sketch. Two start marks two days apart on one strip, with the asserted one-day discrepancy drawn beside them as a shorter measure that visibly does not span the gap.
- **VERIFIED**. Unresolved in substance from iteration 1.

#### SL5, SL-P1, M3 and M7 are narration with arrows, not flows

- **File**: deck `:20-36` (M3) and `:84-92` (M7)
- **Audio replaced**: `chapters/...:5`, `:7`, `:9` (M3) and `:19`, `:21` (M7)
- **Deck excerpt (M3)**: "Start: every pillar deposited with the community under the leader standing in the Prophet's place... / Objection 1: a single entry day forces some to fast a day belonging to Sha'ban / Reply: every obligation stands on two causes, demonstrated across five pillars / Register change: the call divides into outward practice and interpretation"
- **What is missing**: M3's nodes are "Objection 1", "Reply", "Register change", "Objection 2", which are the chapter's table of contents with arrows between the entries, at 76.4% overlap with the audio's three orientation paragraphs. It also duplicates M1 directly above it, which states the same three-register shape and does it with positions. M7 at 72.5% chops the objector's single quoted sentence at its two "therefore"s, and that sentence is already quoted in full inside M4's Column A four lines earlier, so the moment restates the deck as well as the audio.
- **Suggested Worker re-authoring**: delete M3; M1 carries the chapter's shape better and the narration belongs to the audio. Fold M7 into M4 as a fourth Column A row, or rebuild it as the one thing the objection actually is, a rule turning on itself, with the letter's own principle and the fault it charges drawn as the same arrow arriving back at its origin.
- **VERIFIED**. New moments, same habit iteration 1 filed at SL10 and SL12.

#### SL6, SL-P1, M34 is a prose preamble to the two structures beneath it

- **File**: deck `:424-431`
- **Audio replaced**: `chapters/...:109`, `:111`, `:113`
- **Deck excerpt**: "- The objection: what you have mentioned of the report of the sun and the moon, and the degrees, the distances, and the hours, making all of this your guide, is something the Prophet forbade... / - Limb 1, consistency: the same inference settles the direction of prayer and the times of prayer, by calculation. / - Limb 2, re-reading the prohibition: the Prophet prohibited that pursuit only for the risk that a student might chase astronomical knowledge without first grounding himself in the divine sciences."
- **What is missing**: 88.5% overlap, the highest in the deck. Both limbs are then drawn properly, Limb 1 as M35's hierarchy and Limb 2 as M36's branching flow, so this moment announces in bullets what the next two moments show. No position, no fork, no relation between the objection and either limb.
- **Suggested Worker re-authoring**: keep the objection, which is load-bearing and belongs as the movement's opening statement, and cut the two limb bullets, whose content is M35 and M36. If the moment is kept whole, draw it as the fork it describes: one charge arriving, two replies departing, each landing on the structure that answers it.
- **VERIFIED**. New.

#### SL7, SL-P1, M37's scriptural cascade is eight labelled lines

- **File**: deck `:455-466`
- **Audio replaced**: `chapters/...:115`, `:117`
- **Deck excerpt**: "- Part 3, the constellations: Blessed is He who placed constellations in the heavens and set therein a lamp, at chapter 25, verse 61. / - Part 4, the oath by positions: And I swear by the positions of the stars... / - Part 8, the purpose clause, which carries the weight: It is He who made the sun a light and the moon a light and determined its phases, so that you might know the number of years and the reckoning, at chapter 10, verse 5."
- **What is missing**: 82.3% overlap across 124 content words, the largest single block in the deck. Retyping it from "Timeline of citation" to "Annotated structure" removed iteration 1's mis-typing and the eight standalone blockquotes, which is real progress and fixes the framing conflict at SL18 for this moment. What it did not do is supply the shape: eight parts in document order, one annotation noting that the eighth "carries the weight". The three-tier structure iteration 1 recommended is the argument.
- **Suggested Worker re-authoring**: see SL1's M37 sketch.
- **VERIFIED**. Type resolved from iteration 1, structure unresolved.

#### SL8, SL-P1, M39 restates the result and duplicates M33's rows

- **File**: deck `:485-490`
- **Audio replaced**: `chapters/...:121`
- **Deck excerpt**: "- Point 1: the sighting is of two kinds. / - Point 2: acting upon the superior of the two in fulfilling one's obligations takes precedence. / - Point 3: the Prophet's intention in his use of the letter lam was to direct the people's fasting to the sighting of the crescent with their eyes and nothing else. / - Annotation: point 3 is a limit on the audience of a rule, not a refutation of it."
- **What is missing**: 66.7% overlap, and the content is already drawn. M33 at L404 is a five-row contrast pair whose "Standing in the final ruling" rows carry points 2 and 3 verbatim ("the superior of the two, and acting upon it in one's obligations takes precedence"; "what the Prophet directed the people to, in his use of the letter lam") and whose shared row at L420 carries the annotation. Three numbered bullets, no positions.
- **Suggested Worker re-authoring**: delete it. M33 states all three points as a figure eighty lines earlier, which is where the movement's argument lands.
- **VERIFIED**. New.

#### SL9, SL-P1, M40 re-lineates the closing address

- **File**: deck `:492-497`
- **Audio replaced**: `chapters/...:123`
- **Deck excerpt**: "- Part 1, the greeting: know, then, and may Allah grant you success in obeying Him and obeying His guardians, the meanings of what we have set forth. / - Part 2, the instruction: seek Allah's help in all your affairs, draw near with sincere intention, and exert yourself in worshipping Him and obeying His guardians. / - Part 3, the ground: He is the best of helpers in attaining the realities. / - Part 4, the thanks: I thank Allah for the blessings He has bestowed through His trustees."
- **What is missing**: 72.9% overlap; the audio paragraph split at its own sentence boundaries and labelled. No position, no relation between the four parts, nothing a reader carries away. Iteration 1 filed the same habit at its M34, the closing blessing; that moment was properly absorbed into M43's visual metaphor and this one took its place.
- **Suggested Worker re-authoring**: delete it, or quote it. `slide-deck-format.md` permits verbatim material "in blockquote with attribution, no prose surrounding them", which is the honest treatment of a four-sentence address that has no figure in it. The movement already closes on M43, the borrowed-light metaphor, which is the strongest close the deck could have.
- **VERIFIED**. New moment, iteration 1's habit.

#### SL10, SL-P1, M11 regressed from a contrast pair to a four-aspect list

- **File**: deck `:134-141`
- **Audio replaced**: `chapters/...:39` and `:41`
- **Deck excerpt**: "- What the objector assumed: the conjunction is the obligation. / - What the conjunction actually is: the general half of a cause... / - What obliges a person to fast: the arrival of dawn. / - Property of dawn that settles the case: it is local, and universally available."
- **What is missing**: 82.1% overlap, no position, no columns. Iteration 1's deck drew this same material as a contrast pair ("Where the objection dies", its M9 at line 105), and that moment was not flagged by any probe. The re-authoring turned a passing structure into a list. The content is inherently two-sided: what the objector assumed against what the letter establishes, attribute by attribute.
- **Suggested Worker re-authoring**: restore the contrast pair. Column A the objector's reading, Column B the letter's, on matched rows (what causes the duty, what the conjunction does, what dawn does, who can reach it), with the concession annotation at L141 as the shared row. Nothing new needs writing; the rows are already on the page as bullets.
- **VERIFIED**. Regression against iteration 1.

#### SL11, SL-P1, M13 and M18 are three-bullet asides under a structural label

- **File**: deck `:156-160` (M13) and `:209-213` (M18)
- **Audio replaced**: `chapters/...:45` (M13) and `:61` (M18)
- **Deck excerpt (M13)**: "Annotated structure. The damaged clause that follows the balance. / - What survives: no human being could imitate the Prophet in his actions except one uniquely prepared. / - What the preparation is: one set apart by his attribute and his readiness to receive the revelation of Allah as a gift. / - What is broken: a barn where the sense requires the sanctuary of Jerusalem. Left as it stands."
- **What is missing**: M13 is 87.5% overlap on 32 content words, M18 62.1% on 29, the two thinnest moments in the file. Neither has a position and neither has a whole that a layout could carry; both are single paragraphs of the audio with three labels attached.
- **Suggested Worker re-authoring**: fold M13's damage note into M5, which is already the deck's damage register and already places its four breaks, as a fifth entry; that removes a moment and strengthens the one that survives. Fold M18's premise-consequence-constraint into M19's timeline as its stated reading rule, where the constraint ("read in order, phase by phase, not selected for convenience") is a property of the axis rather than a separate slide.
- **VERIFIED**. New.

### P1 (ship-with-caution)

#### SL12, SL-P4, four of six process flows are linear chains with no branch, gate or loop

- **File**: deck `:20` (M3), `:84` (M7), `:282` (M24), `:468` (M38)
- **What is wrong**: `slide-deck-patterns.md` requires a process flow to specify "Nodes (steps/stages), Transitions (with conditions if branching), Start and end states" and names the anti-pattern "Numbered list pretending to be a flow. A flow needs visible transitions and (often) branches." All four are Start / step / step / End with no condition, fork or loop, and in all four the steps are narration rather than states. All four are independently VERIFIED at SL2, SL3 and SL5 as re-lineations of one audio paragraph each. The exception proves the point twice over: M31 at L375 and M36 at L445 both carry a genuine Path A / Path B fork and are among the strongest moments in the deck.
- **Suggested Worker re-authoring**: per-moment sketches at SL2, SL3 and SL5. The general rule this deck needs, unchanged from iteration 1: if the block's steps are narration rather than states, it is not a flow.
- **VERIFIED**. Unresolved from iteration 1 (four of six, against four of five).

#### SL13, SL-A1, the Visual Memory Test fails at 30.2% firm

- **File**: deck, moments M3, M7, M11, M13, M18, M24, M30, M32, M34, M37, M38, M39, M40 firm; M41 and M42 marginal
- **What is wrong**: the check's own auto-fail categories account for every entry. Nine are lists with a title, and they are exactly the nine SL-P3 failures. Four are the linear flows of SL12, which are numbered lists with arrows inserted. That is 13 of 43 = 30.2%, against a threshold of 12.9 moments.
- **Sensitivity, stated because the margin is one moment**: counting only the nine lists gives 20.9%, which passes. Counting the nine plus the two summary moments (M41, a three-arrival matrix in a movement titled "What this episode lands", and M42, a four-moment recap of the chapter's central figure) gives 25.6%, which also passes. The failure therefore depends on counting the four linear flows, and that call is solid rather than borderline: each is independently VERIFIED as a re-lineation of one audio paragraph at 72.5% to 87.3% overlap, and a moment already established as adding nothing the audio carries cannot survive a memory test weeks later. Including the two marginals gives 15 of 43 = 34.9%.
- **Suggested Worker re-authoring**: the check clears automatically on the SL1 and SL12 remediations. Nine annotated structures given real positions plus four flows rebuilt or deleted moves the deck to 2 of 43 (4.7%) before any other change.
- **VERIFIED**. Unresolved from iteration 1, improved from 40.0%.

### P2 (advisory, does not affect the verdict)

#### SL14, SL-P4, M10's Prayer row does not answer its declared column

- **File**: deck `:123-132`
- **Deck excerpt**: "Comparison matrix. The same five, recapitulated from the other side, by what makes each fall due. / Columns: Falls due when | What is explicitly not enough / - Prayer: its time falls due | even if wealth is withheld"
- **What is wrong**: withheld wealth is not something insufficient for prayer; it is another pillar's cause, carried over from the audio's own loose clause at `:37`. The other four rows perform the declared operation correctly (Zakat "the mere presence of wealth", Hajj "bare ability", Jihad "discord and defiance alone", Fasting "the moon existing at dawn"), which produces the visible stripe the movement's argument needs. One cell of ten. This is the residual of iteration 1's SL13, downgraded from P1 because the frame was fixed and four of five rows now work.
- **Suggested Worker re-authoring**: the Prayer row's second cell is "the day arriving", which is the general cause named in M9 one block earlier and makes the stripe read consistently across all five rows.
- **VERIFIED**

#### SL15, SL-P4, M32 is a two-term contrast typed as an annotated structure

- **File**: deck `:395-399`
- **Deck excerpt**: "Annotated structure. Why the phrase carries the weight it does. / - The phrase: the day of the forbidden Eid. / - What a miscount ordinarily costs: a month left a day short. / - What this miscount costs: a day of obligation converted into a day of festival."
- **What is wrong**: the moment's content is one opposition on one attribute, which the taxonomy assigns to a contrast pair ("Two positions opposed attribute-by-attribute"). Typed as an annotated structure it inherits the positions requirement it does not meet, which is why it also appears at SL1.
- **Suggested Worker re-authoring**: retype as a contrast pair on one month strip, an ordinary miscount against this one, with "the day of the forbidden Eid" as the shared row. That clears SL1 and SL15 in one edit.
- **VERIFIED**

#### SL16, SL-P4, the framing's Steering Phrases regressed to two canonical phrases

- **File**: `slide-decks/ch27-framing-ramadan-foundation-and-obedient-knowledge.md:22-25`
- **What is wrong**: three problems, one of them new. (1) Only three phrases are present, at the floor of the spec's 3 to 5, and one of them, "Render everything as black line art on a white background. No colour fills, no gradients, no photographs.", appears in no category of `slide-deck-steering.md`; the same defect is on record for ch06, ch07, ch08 and ch27 iteration 1, making this the fifth occurrence in the book. Net canonical phrases: two. (2) No Category 4 anti-generic phrase is present. The second phrase, "Do not produce 'general illustration' slides. Every slide must have a named diagram type.", is Category 2 (Diagram-Type Discipline), not Category 4, and the deck ships two summary moments (M41, M42) in a movement titled "What this episode lands", which is exactly what Category 4 exists to suppress. (3) **Regression**: iteration 1's framing carried a canonical Category 3 phrase ("When three or more positions are compared, use a matrix with rows for entities and columns for attributes"), and the rewrite deleted it to come in under the word cap while keeping the non-canonical rendering line. The deck's dominant real work is seven comparison matrices and five contrast pairs, so Category 3 is the single most load-bearing steering category for this pair.
- **Suggested Worker re-authoring**: one edit does all three. Drop the rendering line from Steering Phrases, where it is non-canonical and duplicates Prohibited Patterns `:20` almost word for word, which recovers roughly seventeen words in a file at the 250 ceiling. Restore the Category 3 matrix phrase and add the Category 4 phrase "Do not produce a slide titled 'Key Takeaways', takeaways belong to the audio." That lands four canonical phrases inside the band. Routing the rendering instruction through a `## Category 7 — Candidates` entry in `slide-deck-steering.md` is the durable fix and is past the learning-loop threshold; the Challenger does not write that file.
- **VERIFIED**. Recurring, with a new regression.

#### SL17, SL-P2, the framing carries no figural-depiction prohibition while the deck supplies a royal-court scene and names sacred persons

- **File**: `slide-decks/ch27-framing-ramadan-foundation-and-obedient-knowledge.md:15-20` against deck `:240-249` and `:523`
- **Deck excerpt**: "Metaphor: a minister admitted to the king. / Element assignment, the king: the one who commands and signs. / Element assignment, the minister: the one commanded, who then commands the kingdom to carry out whatever the king signs." followed four lines later by "> I am the city of knowledge and he is its gate... / > Attribution: the Prophet, pointing to Ali ibn Abi Talib."
- **What is wrong**: the deck source does not fail SL-P2, correctly, because M21 is a typed visual metaphor with both elements assigned. The gap is in the pair. The framing bans stock photography of crescents, night skies and mosques, and then instructs "Render everything as black line art on a white background", so a line-art king receiving a line-art minister is squarely permitted, and the adjacent blockquote assigns those two figures to the Prophet and to Ali ibn Abi Talib by name. L523 additionally names Muhammad al-Mustafa, the guardian Ali al-Murtada, the pure Imams and the Imam of the age inside a visual metaphor. Fourth occurrence (ch16, ch22, ch27 iteration 1, here), and the highest-stakes of the four: this is a named sacred person in a described posture in a religious text.
- **Suggested Worker re-authoring**: add one line to Prohibited Patterns: "No figural depiction of the Prophet, the Imams, or any named person; render a person as a labelled node or an abstract outline, never as a drawn figure." Recommend escalating this to Asif rather than carrying it a fifth time at P2.
- **VERIFIED** on the framing gap. **INFERRED** on the rendering outcome, since NotebookLM's output is downstream and not inspected by this Challenger.

#### SL18, SL-P2, the framing's quotation prohibition contradicts the deck's 24 blockquote lines

- **File**: `slide-decks/ch27-framing-ramadan-foundation-and-obedient-knowledge.md:17` against deck `:81`, `:153`, `:176`, `:248`, `:279`, `:319-326`, `:338`, `:372`, `:401`, `:482`
- **Framing excerpt**: "No literal text slides reprinting a verse or a saying."
- **What is wrong**: the deck source carries 24 blockquote lines, including three consecutive standalone verses at `:319-326` and the woven chain of questions at `:482`. The deck is compliant with `slide-deck-format.md`, which requires quotes to be "preserved from the audio chapter, but presented in blockquote with attribution, no prose surrounding them". The two deliverable files therefore instruct NotebookLM in opposite directions. Materially softer than iteration 1, which had 39 blockquote lines including an unattached 29-line cascade; M37 absorbing the eight-verse cascade is what improved it.
- **Suggested Worker re-authoring**: soften to "No slide whose only content is a quotation; where scripture is quoted it must annotate a structure rather than stand alone", and attach the three verses at `:319-326` explicitly to M26 directly above, which already reads all three clause by clause.
- **VERIFIED**. Recurring.

#### SL19, SL-P4, two contrast pairs carry unmatched rows

- **File**: deck `:251-269` (M22, two of six rows) and `:38-56` (M4, one of six)
- **What is wrong**: the taxonomy requires "rows of attributes" and a contrast pair's force comes from the eye running across matched rows. M22 pairs "What they have seen" against "What they require" and "What they recognised" against "What follows"; M4 pairs "Fallback offered" against "Concedes". Rendered as two columns, the unmatched rows read as two unrelated lists. Recorded rather than charged because M22 is otherwise one of the deck's best moments, M25 and M33 are perfectly matched on four and five rows, and iteration 1's instance of this defect (its M29) was resolved.
- **Suggested Worker re-authoring**: M22's row 3 is one attribute, "What they have of the crescent": nothing, and the sight of it; row 6 is "What follows from the recognition": the obedience owed before it was stipulated, and its violation out of ignorance. M4's row 5 is "What he grants": the Ramadan portion, and every figure on the page.
- **VERIFIED**

#### SL20, SL-P8 Coverage is unverifiable, no spine artifacts exist

- **File**: `content/Islamic/isaf-al-talib/_system/episode-drafts/` (only `.gitkeep`); `_system/slide-decks/ch27-ramadan-foundation-and-obedient-knowledge/` (only `.validated`)
- **What is missing**: without `04-discussion-spine.md` there are no `[VISUAL CANDIDATE]` tags, and without `01-slide-spine.md` there are no `Anchor:` fields or `[DROPPED: reason]` annotations. The probe can neither pass nor fail, and a silently dropped visual beat would be undetectable on this book. Now recorded on ch06, ch07, ch08, ch09, ch11, ch13, ch16, ch22 and ch27.
- **Note**: coverage against the audio chapter is nonetheless complete by content alignment. All five audio H2 movements are present and in order; both objectors, all four damaged places, all five pillars in both directions, all eight correspondences, all seven lunar states, every date of the year four hundred, and all eight scripture citations (40:57, 41:53, 25:61, 56:75-76, 81:15-16, 85:1, 91:1, 10:5) are carried into a structure or a blockquote. Verified by walking the audio's substantive paragraphs against the moment index above.
- **INFERRED**. Recurring.

#### SL21, SL-A4 is unenforceable, no visual registry exists on a thirteen-deck book

- **File**: `content/Islamic/isaf-al-talib/slide-decks/` (no `_visual-registry.md`)
- **What is missing**: thirteen deck sources now exist for this book and this chapter carries its controlling figure. The sun as the Prophet above and the moon as the foundation below (M15, M16, M17) is a positional convention that later decks will either honour or contradict with nothing to check against, and the borrowed-light close at M43 depends on it. The `Position:` split named at SL1, present in seven decks and absent in six, is exactly the kind of convention a registry would own.
- **INFERRED**. Recurring.

#### SL22, SL-A2, the annotated-structure share grew into the deck's one failing type

- **File**: deck, type distribution above
- **What is wrong**: annotated structure went from 8 of 35 (22.9%) to 14 of 43 (32.6%) between iterations, while contrast pair fell from 6 to 5. It is a strong affinity fit for a theological argument, so the growth is not wrong in itself, but it is the only type in this deck that does not meet its taxonomy requirement, it carries all nine SL-P3 failures and nine of the thirteen memory-test failures, and two of the additions (M11, M32) are moments that were a contrast pair and a contrast in iteration 1. SL-A2 passes comfortably on the 60% ceiling; this is recorded so the next re-authoring does not add a fifteenth.
- **VERIFIED**

---

## Checks that passed with evidence

**SL-P2 Literal Illustration.** Grep over the deck for "image of, photo, photograph, stock, picture
of, depiction of, illustration of, drawing of, painting" returns zero hits. Every visual instruction
in the file is a typed structure with content commitments. The four visual metaphors all assign their
elements: M2 (the moon's monthly performance as a biography), M12 (the balance with two named pans),
M21 (king and minister) and M43 (moons amid the darkness, with source, reflector and beneficiary
assigned). The two framing-side risks are filed at P2 and neither is a deck defect.

**SL-P4 Diagram-Type Discipline.** All 43 structural blocks carry a named taxonomy type, and zero
untyped content blocks exist anywhere in the file, which is the single cleanest result any deck in
this book has produced against this probe and a direct fix of iteration 1's P0. Verified
programmatically rather than by eye.

**M6, the deck's best moment.** The named-axis 2x2 at L68 meets the taxonomy's full requirement.
Both axes are named with directions ("what the ruling does to duty, from Adds an obligation that is
not owed to Removes an obligation that is owed"; "what name the result is given, from Called by its
own name to Dressed in the Prophet's name"), all four quadrants are populated with an entity and a
reason, and the reasoning line at L79 makes the counter-intuitive claim the memory test rewards,
that private reasoning lands in two opposite quadrants at once rather than sliding one step. Overlap
with the audio is 42.7%, the lowest in the deck, because the grid is the deck's own work: the audio
at `:17` says only that private judgement "counterfeits obligations in both directions at once" and
never draws the space.

**SL-P5 Diversity and SL-A2 Variety.** Nine distinct taxonomy types, the most of any deck in this
book, with a largest share of 32.6% against a 60% ceiling. Contrast pair, comparison matrix and
named-axis 2x2 are all present, which is what the affinity matrix predicts for a source that is
simultaneously a theological argument, a polemic against two named objectors, and a comparative
study of five pillars.

**SL-P6 Audio Redundancy.** The deck is a rewrite in the large majority, and the evidence is the work
with no audio counterpart. M9 (L112) turns five sequential pillar paragraphs into a five-row,
four-column grid whose "Why it is general" and "What the second cause fixes" columns are entirely
the deck's addition. M20 (L227) sets the seven celestial states against their counterparts in one
authority's history, seven rows the audio runs as seven separate paragraphs. M22 (L251)
cross-tabulates the day of doubt against the unrecognised authority on six attributes where the
audio at `:77` runs them as one long paragraph, and its shared row names the chapter's hinge. M29
(L353) places eight dated events on a real axis with three period bands. M31 (L375) and M36 (L445)
both fork properly, and M31 carries the counterfactual that gives the year-four-hundred case its
force. M33 (L404) absorbs iteration 1's restated external check into five matched rows. M17 (L203)
and M23 (L273) build directed chains from material the audio scatters. Twelve of forty-three moments
are 1:1 restatement, against a 70% threshold.

**SL-A3 Arc.** The deck opens on its organizing structure rather than its topic: M1 places the
chapter's three registers with positions and annotates both seams, and M2 states the governing image
before it is argued. Pressure builds through movements that each terminate in a structural payoff
rather than a recap: M6's 2x2 and M9's grid close the legal movement, M19's seven-station timeline
climaxes at M20's correspondence and M22's hinge contrast pair, M29's dated timeline and M31's
branching counterfactual close the calculation movement, M33 resolves the two sightings, and M35
plus M36 answer the prohibition. The close is a genuine structural image, M43's borrowed light with
every element assigned, and it reaches back to M2's opening metaphor and to the sun-and-moon
correspondences at M15 and M16, so the final moment is the deck's own argument compressed into the
formula the community already recites. The bookend between M2 and M43 is the strongest arc feature
in any deck in this book. M41 and M40 are blemishes inside the closing movement, filed at SL9 and
SL13, but neither is the final moment and the arc survives them.

**Format rules (`slide-deck-format.md`).** Zero em dashes in either file, verified by grep. Zero
inline phonetic parens, so R-PHONETICS-OUT holds. H1 appears once. No authored line exceeds 100
words; the longest is 62 (L316). Deck at 99.6% of the audio word count, inside the 50 to 100% band,
though with only 24 words of headroom for the SL1 remediation, so the deletions recommended at SL5,
SL8, SL9 and SL11 should be taken before positions are added. All five required framing H2 sections
are present, the audience is named concretely ("Asif's children and adult students of Ismaili
fiqh"), the framing body is 250 words exactly, and all four Visual Priorities map 1:1 onto real deck
structures: the two causes across five pillars onto M9, the sun-and-moon correspondences onto M15
and M16, the seven states each paired with its counterpart onto M19 and M20, and the year four
hundred onto M29. Contrast columns use the `Column A:` / `Column B:` prefix form the spec requires,
and all seven matrices use the `- Row: cellA | cellB` scaffold rather than markdown tables, which
resolves iteration 1's standing observation in favour of `slide-deck-steering.md:145`.

---

## Verified vs Inferred

**VERIFIED (20)**: the nine position-less annotated structures (SL1), corroborated by grep counts
across all thirteen decks in this book and by the Worker's own correct form in seven of them and in
five moments of this same deck; the twelve SL-P1 restatement findings (SL2 to SL11), each cited to a
deck line range and a matching audio chapter line with both excerpts quoted and a measured overlap;
the four linear process flows (SL12); the Visual Memory Test count with its sensitivity (SL13);
M10's off-frame cell (SL14); M32's mis-typing (SL15); the Steering Phrases regression (SL16),
corroborated against iteration 1's recorded five phrases; the framing half of the figural-depiction
gap (SL17); the quotation-prohibition conflict (SL18); the two unmatched contrast pairs (SL19); and
the annotated-structure share growth (SL22).

**INFERRED (2)**: the SL-P8 coverage-unverifiable advisory (SL20) and the SL-A4 registry-absent
advisory (SL21), both absence-of-artifact judgments rather than defects found in authored content.
The rendering-outcome half of SL17 is likewise inferred, since NotebookLM's output is downstream and
not inspected by this Challenger.

The Worker addresses both categories on iteration. The INFERRED items do not gate the ship on their
own.

---

## Standing observations, not findings

**Re-segmentation of the H2 outline.** The deck carries eight H2 movements against the audio's five,
adding "The balance of testimony and the two callings", "The month, the verse, and the council of
silence" and "The charge of a prohibited science". All five audio movement titles survive verbatim
and in order. `slide-deck-format.md` says the chapter outline is preserved, and it is; the split is
in the direction of more structure, it gives NotebookLM clean section boundaries at roughly 50-line
intervals, and it is part of why SL-P6 passes. Iteration 1 carried nine, so the deck consolidated.

**The scaffold-versus-tables conflict is now resolved in practice, not in the specs.**
`slide-deck-format.md` calls for "explicit markdown tables" while `slide-deck-steering.md:145` says
NotebookLM "does not reliably parse complex Markdown tables for visual layout" and prefers
`- Column A: X | Column B: Y`. This deck has now shipped both forms across two iterations and has
settled on the scaffold. Named for the third time so the conflict is resolved once, in the format
spec, rather than re-decided per deck.

**An inference counted twice in the audio and twice in the deck.** Iteration 1 recorded the deck
saying "used three times" where the audio says "twice"; the current M27 at L328 reads "One
inference, used twice, plus the case that names it" and tabulates three rows, which reconciles the
count with the audio while keeping the third row. Recorded as a fidelity improvement.

**Where the restatement clusters.** All twelve SL-P1 moments are annotated structures or linear
process flows. Not one contrast pair, comparison matrix, genealogy, timeline, hierarchy, visual
metaphor or 2x2 in this deck is a restatement, and the two forking flows are among its best moments.
As in both prior iterations and in ch22, the failure mode is confined to two diagram types, which is
why the remediation is mechanical rather than a rethink of the deck.

---

## Learning loop

Five patterns meet the spec's recurrence thresholds. The Challenger does not write
`slide-deck-steering.md` or `slide-deck-patterns.md` under its v1.0 boundary contract, so these are
surfaced here for the Worker or Asif to place.

1. **Annotated structures shipped without positions** is a P0 on ch11, ch16, ch22 (both iterations)
   and ch27 (both iterations), and the field is absent from six of this book's thirteen decks.
   Proposed Category 7 candidate: "Every part of an annotated structure must carry an explicit
   position. A part without a position is a bullet."
2. **Process flows used to put arrows between the clauses of one audio paragraph** is now filed on
   ch22 (3 of 3) and ch27 (4 of 5, then 4 of 6). Proposed `slide-deck-patterns.md` anti-pattern
   refinement: a flow whose steps are narration ("a question is put", "an objection is raised",
   "register change") rather than states is a list, whatever the arrows say.
3. **A framing with no figural-depiction prohibition** is now filed on ch16, ch22 and ch27 twice,
   and ch27 names sacred persons in described postures. Recommend escalating to Asif rather than
   carrying it at P2 a fifth time. Proposed Category 4 candidate: "No figural depiction of the
   Prophet, the Imams, or any named person; render a person as a labelled node or an abstract
   outline."
4. **A non-canonical rendering instruction inside Steering Phrases** is now filed on ch06, ch07,
   ch08 and ch27 twice, five occurrences. Either promote a rendering-discipline category to
   `slide-deck-steering.md` or have the framing generator reject phrases absent from the canon.
5. **New this run: the word cap is being paid for out of the canonical steering phrases.** ch27's
   framing came into the 250-word band between iterations by deleting two canonical phrases,
   including the Category 3 phrase that matches this deck's dominant structures, while keeping the
   non-canonical rendering line that duplicates Prohibited Patterns. Proposed generator rule: when
   the framing exceeds the band, trim Prohibited Patterns duplicates and non-canonical phrases
   first, and never reduce the canonical steering set below three.

---

## Overall

**Pass 1**: fail (SL-P1 and SL-P3, both P0)
**Pass 2**: fail (SL-A1, P1)

**Bundle status**: iterate
**Verdict**: BLOCKED

Eleven P0 findings, two P1, nine P2. Per the iteration protocol the Worker addresses all of them, not
a subset, and re-runs the Challenger. There is no override path.

The re-authoring was a real net improvement and most of it should not be undone. The two untyped
bullet blocks are gone and the file is now the only deck in this book with zero untyped content;
iteration 1's eight-verse quotation cascade, its restated external check, its restated closing
blessing, its four bare moon adjectives and its unapplied five-pillar test are all resolved, four of
them by folding into a neighbouring structure that got stronger for it; the matrices moved to the
text scaffold NotebookLM actually parses; the framing came inside its word band; and the arc now has
a genuine bookend between the opening metaphor at M2 and the closing one at M43. Thirty-one of
forty-three moments do real visual work, nine taxonomy types are in play, and the 2x2 at M6 remains
the best single moment this book has produced.

What blocks the ship is that the deck's two known habits were not broken, and in two places they
absorbed the growth. Nine annotated structures still name parts and place none, which is one more
than iteration 1 even though five of the fourteen now show the Worker knows the form; four of six
process flows are still one audio paragraph with arrows inserted, two of them near verbatim from
iteration 1 after the report named the figure to draw in each case; and one moment that passed every
probe in iteration 1, the contrast pair at "where the objection dies", came back as a four-aspect
list. Together those account for all eleven P0s and for the architectural failure. The work is
narrow and almost entirely mechanical: give nine structures a position, rebuild or delete four flows,
delete M39 and M40 (whose content M33 and M43 already carry better), fold M13 into M5 and M18 into
M19, and restore M11 to the contrast pair it was. Take the deletions before adding positions; the
deck has only 24 words of headroom. On the framing, one edit fixes three findings: drop the
non-canonical rendering line, restore the Category 3 matrix phrase, add a Category 4 phrase, and add
the figural-depiction prohibition.

---

## Ledger Hook

22 findings emitted to `_learning/findings.jsonl` (source: slide-deck-challenger, version: 1.0):
11 P0 (10 SL-P1, 1 SL-P3), 2 P1 (1 SL-P4, 1 SL-A1), 9 P2 (4 SL-P4, 2 SL-P2, 1 SL-P8, 1 SL-A4,
1 SL-A2). All 22 signatures unique within the run, every excerpt inside the 300-char cap, every
record `resolution: flagged` per the v1.0 no-auto-fix scope.

Signatures for the three findings unresolved verbatim from iteration 1 are keyed to the audio line
being restated (`SL-P1:restates-audio-83`, `-119`, `-99`) rather than to a moment number, so the
aggregator folds them as recurrences across the re-authoring that renumbered every moment in the
file. The SL-P8 and SL-A4 signatures are book-scoped and recur by design.
