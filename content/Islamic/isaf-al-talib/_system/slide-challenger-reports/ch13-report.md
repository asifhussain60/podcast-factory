# Slide Challenger Report, ch13-supplication-conduct-and-dress-in-prayer

**Book**: isaf-al-talib
**Run timestamp**: 2026-09-18T16:05:00Z
**challenger_version: 1.0**
**Scope**: per-chapter, ch13-supplication-conduct-and-dress-in-prayer
**Iterations**: 1 this invocation (iteration 4 of the chapter's lifetime)
**Deck source**: `content/Islamic/isaf-al-talib/slide-decks/ch13-deck-supplication-conduct-and-dress-in-prayer.txt`
**Deck framing**: `content/Islamic/isaf-al-talib/slide-decks/ch13-framing-supplication-conduct-and-dress-in-prayer.md`
**Audio chapter**: `content/Islamic/isaf-al-talib/chapters/ch13-supplication-conduct-and-dress-in-prayer.txt`
**Discussion spine**: ABSENT (`_system/episode-drafts/` holds only `.gitkeep`)
**Slide spine**: ABSENT (`_system/slide-decks/ch13-supplication-conduct-and-dress-in-prayer/` holds only `.validated`)
**Visual glossary**: ABSENT
**Visual registry**: ABSENT (no `slide-decks/_visual-registry.md`)

**Structural moment count**: 37
**Deck word count**: 5,729 (audio 5,820 = 98.4%, inside the 50-100% band)
**Framing word count**: 263 by `wc -w` (`.validated` records 252; either figure is over the 150-250 band)

**Bundle status**: iterate
**Verdict**: BLOCKED

---

## Read this first, the deck was rebuilt, not edited

This is not a re-run against an unchanged artifact. Since iteration 3 the deck source was
**fully re-authored**: `git diff --stat` reports 448 insertions and 491 deletions across 915 lines.
The artifact this run judged shares almost no body content with the one iteration 3 judged.

**Every specific finding from iteration 3 is fixed.** Verified mechanically:

| Iteration-3 finding | Status this run | Evidence |
|---|---|---|
| Five single-column comparison matrices (`Columns: the ruling`, no `\|`) | **FIXED** | Zero `Columns:` lines remain. All 10 matrices are real markdown tables; column counts are 4, 3, 5, 4, 4, 5, 4, 4, 4, 3 |
| M18 "positions that are not positions" | **FIXED** | The moment was deleted; the voice rules are now a branched process flow at `:240` |
| M31 duplicating M30's hierarchy | **FIXED** | The duplicate surface matrix was deleted; only the fit/unfit hierarchy at `:425` remains |
| H2 divergence, 8 deck movements against 5 audio | **FIXED** | Deck is now 6 movements; the audio's 5 headings are preserved verbatim plus one split of "Garment And Ground" into a "The Ground Of Prostration" movement |
| Framing over the word band | **NOT FIXED** | 263 words, still over 250 |

That is real, substantial work and it cleared the whole of the prior report's cited catalog.

**The bundle is nevertheless BLOCKED, because SL-P1 fails on different moments.** The rewrite
moved the restatement rather than removing it. Two of the five findings below are a **regression**:
the closing movement's two moments reproduce audio paragraphs 105 and 107 nearly verbatim, and
iteration 1 flagged exactly that content under the signatures
`SL-P1:restatement:ch13-deck:M36-three-living-edges` and `SL-P1:restatement:ch13-deck:M35-third-concept`.
It was removed in iteration 2, and the re-authoring has brought it back.

**This run re-derived every probe from the files.** The moment index, type distribution, table column
counts, word counts, em-dash count and prose-paragraph lengths were all recomputed. The five P0
judgments were argued against the audio chapter from scratch. No prior verdict was inherited.

---

## Diagram-type distribution

Computed from the 37 type-label lines at the head of each structural block.

| Type | Count | Share |
|---|---|---|
| Comparison matrix | 10 | 27.0% |
| Process flow | 6 | 16.2% |
| Contrast pair | 5 | 13.5% |
| Annotated structure | 5 | 13.5% |
| Visual metaphor | 4 | 10.8% |
| Hierarchy | 3 | 8.1% |
| Named-axis 2x2 | 2 | 5.4% |
| Timeline | 1 | 2.7% |
| Genealogy chain | 1 | 2.7% |

Nine distinct taxonomy types across 37 moments. Zero blank, zero "TBD", zero "various".

---

## Moment index

| ID | Line | Type | Subject |
|---|---|---|---|
| M1 | 5 | Annotated structure | The three edges of a completed prayer |
| M2 | 16 | Comparison matrix | The three edges by question, test, failure mode |
| M3 | 24 | Hierarchy | The source's authority stack |
| M4 | 43 | Process flow | The two opening questions and their rulings |
| M5 | 56 | Comparison matrix | Three registers the ruling keeps apart |
| M6 | 64 | Contrast pair | Time-consciousness as the frame for the plea |
| M7 | 80 | Annotated structure | The Mustansiriyya Councils on culmination |
| M8 | 97 | Comparison matrix | The seven forms of supplication |
| M9 | 109 | Visual metaphor | Why the seven are called roots |
| M10 | 121 | Process flow | The twelve foundations, in the source's order |
| M11 | 138 | Annotated structure | The twelve read as four movements |
| M12 | 150 | Genealogy chain | The approach rendered as directed chains |
| M13 | 157 | Contrast pair | What Step 8 presupposes against what it supplies |
| M14 | 173 | Timeline | Six openings of the gates of heaven |
| M15 | 187 | Comparison matrix | The maxims of Amir al-Mu'minin on supplication |
| M16 | 198 | Visual metaphor | The thrower without an arrow |
| M17 | 213 | Comparison matrix | Eight cases of conduct inside the prayer |
| M18 | 226 | Named-axis 2x2 | Chosen/unavoidable against obstructs/does not |
| M19 | 240 | Process flow | The discipline of the voice |
| M20 | 252 | Hierarchy | The fourteen doors of prayer, grouped by function |
| M21 | 277 | Visual metaphor | The doors as a building with thresholds |
| M22 | 293 | Process flow | The image test, with branch conditions |
| M23 | 307 | Comparison matrix | Four registers of judgment on dress |
| M24 | 320 | Named-axis 2x2 | Validity against etiquette in dress |
| M25 | 334 | Comparison matrix | Covering, by the source's own categories |
| M26 | 347 | Contrast pair | Firm rule against recognized exception |
| M27 | 361 | Process flow | Impurity on the garment |
| M28 | 370 | Comparison matrix | Travel, weapons, limits of repetition |
| M29 | 380 | Contrast pair | His own prayer against his fitness to lead |
| M30 | 396 | Annotated structure | Ishtimal al-samma' dissected |
| M31 | 415 | Comparison matrix | Three garment forms side by side |
| M32 | 425 | Hierarchy | Permissible and impermissible surfaces |
| M33 | 448 | Comparison matrix | Closing rulings on material contact and place |
| M34 | 462 | Process flow | The practical test the movement has been building |
| M35 | 474 | Visual metaphor | The praying body inside its material loyalties |
| M36 | 490 | Contrast pair | Severity against mercy |
| M37 | 508 | Annotated structure | The three edges closed |

---

## Pass 1, Per-Structure Probes

| Probe | Result | Moments flagged | Notes |
|---|---|---|---|
| SL-P1 Restatement | **fail (P0)** | M37, M36, M10, M12, M6 | Threshold is 2 moments replaceable by the audio without loss; 5 qualify, 4 VERIFIED and 1 INFERRED |
| SL-P2 Literal Illustration | pass | , | Zero literal or stock-photo language. The single corpus hit is the framing's own prohibition at `:18` |
| SL-P3 Structure-vs-Description | pass | , | Both 2x2s name axis poles and populate four quadrants with reasoning; all three hierarchies name every level with siblings; all six process flows name start, transitions and end; all 10 matrices name rows, columns and concrete cells |
| SL-P4 Diagram-Type Discipline | pass | , | 37 of 37 carry a named taxonomy type. Zero blank, zero TBD, zero "various" |
| SL-P5 Diversity | pass | , | Nine distinct types. Contrast pair, comparison matrix and named-axis 2x2 all present, as the theological-argument affinity profile predicts |
| SL-P6 Audio Redundancy | pass | M6, M10, M12, M33, M36, M37 | 6 of 37 (16.2%) are 1:1 with an audio paragraph and add no structure. Threshold is 70% |
| SL-P7 Justified Skip | n/a | , | Not skip mode; a deck exists |
| SL-P8 Coverage | n/a (unverifiable) | , | No `04-discussion-spine.md` and no `01-slide-spine.md`, so no `[VISUAL CANDIDATE]` tags exist to cross-reference. Recorded as P2 |

**Pass 1**: fail

---

## Pass 2, Architectural Pass

| Check | Result | Notes |
|---|---|---|
| SL-A1 Visual Memory Test | pass | 3 of 37 (8.1%) strictly forgettable, 7 of 37 (18.9%) including four borderline calls. Threshold is 30% |
| SL-A2 Variety | pass | Largest share 27.0% (comparison matrix, 10/37) against a >60% threshold for decks of 10+ |
| SL-A3 Arc | pass | Opening triad establishes the organizing figure, each middle movement terminates on a structural payoff, the close redraws the opening figure |
| SL-A4 Cross-Episode Consistency | n/a | No `_visual-registry.md` exists for this book. Recorded as P2 |

**Pass 2**: pass

---

## Failures requiring Worker iteration

### P0 (blocks ship)

#### SL-P1 Restatement, five moments carry no visual information the audio lacks

The failure condition is two or more moments replaceable by the audio without loss. Five qualify.
Four are VERIFIED by direct textual overlap with the audio chapter; one is INFERRED.

They fall into two clusters, and both clusters are structural rather than incidental:

1. **The entire Closing movement (M36, M37) is audio paragraphs 107 and 105 re-line-broken.** The
   deck's `## Closing` contains exactly two moments, and both are the audio's own closing paragraphs
   with column headers or position prefixes added. Nothing else is in that movement.
2. **The twelve foundations are given three consecutive times (M10, M11, M12).** Only the middle one
   (M11) does structural work the audio lacks. M10 precedes it with the source's flat enumeration and
   M12 follows it with the same sequence as arrows.

M6 is a fifth, weaker case, cited because three of its four attribute rows carry nothing the audio
sentence does not.

---

**M37, deck line 508, "The three edges closed"** , VERIFIED, **REGRESSION**

- **File**: `slide-decks/ch13-deck-supplication-conduct-and-dress-in-prayer.txt:508-516`
- **Deck excerpt**: "- After the salutation, to the right: no dissolving into private wishes. Supplication has roots, foundations, gestures, repentance, praise, blessing, and approach through the imams of the religion. / - Inside the prayer, at the center: devotion is not permission for ordinary behavior. Speech, motion, carrying, eating, drinking, recitation, and gesture are governed by the doors of the act."
- **Audio replaced**: `chapters/ch13-supplication-conduct-and-dress-in-prayer.txt:105`, in full: "After the salutation, the servant does not simply dissolve into private wishes; supplication has roots, foundations, gestures, repentance, praise, blessing, and approach through the imams of the religion. Inside the prayer, the servant does not treat devotion as permission for ordinary behavior; speech, motion, carrying, eating, drinking, recitation, and gesture are governed by the doors of the act. Around the prayer, the servant does not treat clothing, ornaments, images, impurity, and ground as neutral; they either preserve or disturb the dignity of standing before Allah."
- **What is missing**: the three parts are the three clauses of one audio sentence, verbatim but for the negation being turned into a noun phrase ("does not simply dissolve" becomes "no dissolving"). The only added commitment is the position labels right/center/ring, and those are inherited wholesale from M1 at `:5`, which already established that layout 503 lines earlier. A host reading audio 105 aloud loses nothing at all.
- **Regression note**: iteration 1 flagged this same content under `SL-P1:restatement:ch13-deck:M36-three-living-edges`, with an excerpt beginning "Parts: After the salutation. The servant does not dissolve into private wishes..." It was removed at iteration 2. The re-authoring reintroduced it.
- **Suggested Worker re-authoring**: the deck already closes strongly at M35, the concentric rings with "obligations propagate inward." M37 as written adds a second, weaker closing. Either delete it, or make it do the one thing M1 cannot: M1 posed each edge as an open question ("The question is whether the servant may ask"), so a closing figure could place each edge's **answer** against its question on the same three-part layout, which is a comparison the audio never assembles. Do not restate the audio's summary sentence on M1's borrowed positions.

---

**M36, deck line 490, "Severity against mercy"** , VERIFIED

- **File**: `slide-decks/ch13-deck-supplication-conduct-and-dress-in-prayer.txt:490-506`
- **Deck excerpt**: "Column A: Severity / - Prayer cannot be casually interrupted / - It cannot be wrapped in disabling garments / - It cannot be performed knowingly with impurity ... Column B: Mercy / - Unavoidable discomfort is excused / - Constrained travel is recognized / - Hidden objects are tolerated when they do not obstruct the act"
- **Audio replaced**: `chapters/ch13-supplication-conduct-and-dress-in-prayer.txt:107`, sentences 2 and 3: "It is severe because prayer cannot be casually interrupted, wrapped in disabling garments, performed knowingly with impurity, directed toward distracting images, or placed upon unsuitable surfaces. It is merciful because unavoidable discomfort is excused, constrained travel is recognized, hidden objects may be tolerated when they do not obstruct the act, necessity permits a person to pray as he is, and later repair is possible when water or pure clothing becomes available." The Shared row is audio 107's final two sentences verbatim.
- **What is missing**: the whole structural operation is cutting one audio sentence at the words "It is merciful because" and putting each half under a column header. Per `slide-deck-patterns.md`, a contrast pair requires **rows of attributes** with a cell value on each side; these are two independent lists in the audio's own order, and they do not align. Pairing them row by row: A1 interruption against B1 unavoidable discomfort does correspond; A2 disabling garments against B2 constrained travel corresponds weakly; A3 knowing impurity against B3 hidden objects does not (A3's real partner is B5, later repair); A4 distracting images against B4 necessity does not; A5 unsuitable surfaces against B5 later repair does not. One row of five aligns, so there is no attribute-by-attribute reading for a viewer to perform.
- **Suggested Worker re-authoring**: keep the moment, it is the right note to close on, but earn it by aligning the rows. Each severity in this chapter has a specific mercy that answers it, and the chapter supplies every pairing: knowing impurity is answered by later repair when water is found; the disabling wrap is answered by "like the wings of the hook" when no other option exists; the unsuitable surface is answered by fire-purified plaster; casual interruption is answered by excused involuntary discomfort; the distracting image is answered by the pure dirham hidden in a pouch. Five aligned rows turns two lists into a reading, and every cell is already in the deck.

---

**M10, deck line 121, "The twelve foundations, in the source's own order"** , VERIFIED

- **File**: `slide-decks/ch13-deck-supplication-conduct-and-dress-in-prayer.txt:121-136`
- **Deck excerpt**: "Start: A servant who wants his supplication answered. / - Step 1: He precedes it with repentance from what God has forbidden. / - Step 2: He gives charity. / - Step 3: He fasts. / - Step 4: He prays, because God Almighty says that good words ascend to Him and righteous deeds lift them higher, chapter 35, verse 10."
- **Audio replaced**: `chapters/ch13-supplication-conduct-and-dress-in-prayer.txt:23`, in full: "First, he precedes it with repentance from what God has forbidden. Second, he gives charity. Third, he fasts. Fourth, he prays, because God Almighty says that good words ascend to Him, and righteous deeds lift them higher (chapter 35, verse 10)..." All twelve steps are verbatim; only the ordinal words are swapped for "Step N:".
- **What is missing**: this is a twelve-item enumeration labelled a process flow. There is not one branch, not one condition, and not one transition, so it is precisely the anti-pattern `slide-deck-patterns.md` names under Process Flow: "Numbered list pretending to be a flow. A flow needs visible transitions and (often) branches." It is also superseded seventeen lines later by M11, which groups the same twelve into four positioned movements and adds "personal want is last. It is not diminished, it is positioned." M11 is the moment that earns its keep; M10 is the raw list M11 was built from, left in place.
- **Suggested Worker re-authoring**: delete M10 and let M11 carry the twelve. If a sequential rendering is wanted, it has to become a real flow, which this content supports: the source gates the sequence (praise **before** request, blessings **before** personal need, the imams named **in order** to the imam of the time), so the transitions can carry those conditions and the flow can branch at step 10 into worldly good, otherworldly good, and refuge. A flow with named gates is a different artifact from a numbered list.

---

**M12, deck line 150, "The approach rendered as directed chains"** , VERIFIED

- **File**: `slide-decks/ch13-deck-supplication-conduct-and-dress-in-prayer.txt:150-155`
- **Deck excerpt**: "Servant to repentance to charity to fasting to prayer to praise of God Almighty / Praise to blessings upon the Prophet, peace be upon him, to the imams of the religion, named one by one / The imams of the religion to the imam of the servant's own time to beseeching him and them before God / Beseeching to the request itself to answer" (arrows in the source are the glyph)
- **Audio replaced**: `chapters/ch13-supplication-conduct-and-dress-in-prayer.txt:23` and `:25`. Audio 25 already states the ordering as a chain: "The supplicant begins by turning away from forbidden acts, then loosens his grip through charity, disciplines appetite through fasting, and stands within prayer... praise must come before request, blessings upon the Prophet must come before personal need, and the imams of the religion are named in order until the imam of the supplicant's own time."
- **What is missing**: three defects compound. (a) The label says "Step 8 rendered as a directed approach", but the chains run from step 1 to step 12; step 8 occupies part of one line. The moment does not do what it announces. (b) It is the third consecutive moment on the twelve foundations, after M10's enumeration and M11's four-movement grouping, and it re-linearizes exactly the sequence M10 already gave. (c) A genealogy chain is for lineage where **direction of influence** matters, per the taxonomy; these arrows encode the temporal order of one servant's own acts, so the type is doing no work that the process-flow arrows at M10 were not already doing. That is the "Wrong type for source" anti-pattern.
- **Suggested Worker re-authoring**: there is a real genealogy in this chapter and this is not it. The chapter's actual directed lineage is the transmission chain the rulings rest on, which M3 currently files as a flat authority hierarchy: Prophet to the pure Imams to Amir al-Mu'minin's Four Hundred Etiquettes, and separately to Ja'far ibn Mansur al-Yaman, to the Musannaf and the Mustansiriyya Councils, to the answers of Idris ibn al-Hasan and the Yemeni and Indian authorities. Drawing that as a directed tree would give the deck its one genuine genealogy, would show the reader why a ruling on turbans and a ruling on plaster carry different weight, and would remove the third pass over the twelve foundations.

---

**M6, deck line 64, "Time-consciousness as the frame for the plea"** , INFERRED

- **File**: `slide-decks/ch13-deck-supplication-conduct-and-dress-in-prayer.txt:64-78`
- **Deck excerpt**: "Column A: Daytime prayer / - Voice: recited silently / - Marker: the noon and afternoon prayers are not audible / - Bodily state: the body prays under open light / - Threshold effect: silence trained by day does not spill into unbounded speech afterward"
- **Audio replaced**: `chapters/ch13-supplication-conduct-and-dress-in-prayer.txt:15`: "daytime prayer is recited silently, night prayer is voiced in the depth of darkness, and dawn is announced like glass catching the light... prayer is never detached from time... The body that prayed silently by day or aloud by night does not then spill into any kind of post-prayer speech it desires. Even the afterword of prayer has a discipline."
- **Why INFERRED**: the moment does commit to a two-column structure with named attribute rows, which is more than the audio sentence carries, so this is a judgment about thin structure rather than absent structure. Of the four rows: **Voice** is genuinely contrastive but duplicates M19's Branch A/B at `:246` ("noon and afternoon: recitation should not be audible" against "night: the prayer is recited aloud"); **Bodily state** is tautological, restating each column header ("Daytime" becomes "under open light", "Night" becomes "under cover of dark"); **Marker** is misaligned, setting a rule about which prayers are audible against an image of dawn; and **Threshold effect** is audio 15's own closing gloss split in half. The Shared row is audio 15 verbatim.
- **Additional structural defect**: dawn is the third term in audio 15 and belongs to neither column, but it has been placed inside Column B (Night) as its Marker. A two-column contrast cannot hold a three-term source without distorting it.
- **Suggested Worker re-authoring**: the source gives three states, not two, so the type is wrong. A short timeline or a three-region spectrum (day, the dawn seam, night) holds all three without forcing dawn into the night column, and it would let M19 keep the silent/aloud rule as the branch inside the act while M6 carries the frame around it. Drop the Bodily state row; it says nothing.

---

### P1 (ship-with-caution)

None. SL-P5, SL-P6, SL-A1, SL-A2 and SL-A3 all passed on their own thresholds and produced no
P1 finding.

---

### P2 (advisory, does not affect the verdict)

**Stray Audio Overview instruction in the slide framing** , VERIFIED, **systemic across the book**

- **File**: `slide-decks/ch13-framing-supplication-conduct-and-dress-in-prayer.md:28`
- **Excerpt**: "Do not read this prompt aloud."
- **Detail**: a slide deck has no narration, so the instruction is inert here, and it sits outside the five required H2 sections, which `slide-deck-format.md` enumerates exactly. It is the same finding already logged against ch25 and ch26 (`SL-P4:stray-audio-instruction-in-slide-framing`). **It is present in 21 of this book's 27 framing files**, so it is a template defect, not a ch13 defect. Per the repo's systemic-fixes rule it should be fixed once at the generator, not chapter by chapter.

**Framing exceeds the word band** , VERIFIED

- **File**: `slide-decks/ch13-framing-supplication-conduct-and-dress-in-prayer.md`
- **Detail**: 263 words by `wc -w`, and 252 as recorded in `.validated`, against `slide-deck-format.md`'s 150-250 band. This was flagged at iteration 2, trimmed to 249 at iteration 3, and the current framing has grown back over the limit. The band is not a probe's failure condition, so it stays advisory, but it is now the second regression in this bundle.

**M24 redefines an axis pole inside one quadrant** , VERIFIED

- **File**: `slide-decks/ch13-deck-supplication-conduct-and-dress-in-prayer.txt:320-332`
- **Detail**: the vertical axis is declared as "standing in adab, from Approved at the bottom to Disliked or unfitting at the top". Three quadrants honour it. The fourth is labelled "Bottom-right, Falls though not blameworthy in intent", which substitutes blameworthiness for approval. The cell content is right and the reasoning line is right; the label silently changes what the axis measures, and NotebookLM renders axis labels from exactly these strings. Changing it to "Bottom-right, Falls and Approved: the wearer is not at fault, yet the prayer is void" keeps the axis honest and loses nothing.

**M33's third column is empty in three of seven rows** , INFERRED

- **File**: `slide-decks/ch13-deck-supplication-conduct-and-dress-in-prayer.txt:448-460`
- **Detail**: the Condition column reads "None given" for camel pens, the shirt without a waist-wrapper, and the loosely worn garment. The column is genuine for the other four (small amount, swept and sprinkled, unless no alternative is found, every such prayer), so the matrix is not a disguised list and SL-P3 passes. But `slide-deck-patterns.md` asks matrix cells to be commitments, and a grid that is 43% blank renders as a table with holes in it. The three blank rows are all bare prohibitions; they would sit more naturally as rows in M32's not-permitted branch, leaving M33 as a four-row matrix where every cell says something.

**SL-P8 Coverage is unverifiable, no spine artifacts exist** , VERIFIED

- **Files**: `_system/episode-drafts/` (only `.gitkeep`); `_system/slide-decks/ch13-supplication-conduct-and-dress-in-prayer/` (only `.validated`)
- **Detail**: without `04-discussion-spine.md` there are no `[VISUAL CANDIDATE]` tags, and without `01-slide-spine.md` there are no `Anchor:` fields or `[DROPPED: reason]` annotations. The probe can neither pass nor fail, and a silently dropped visual beat would be undetectable on this book. Unchanged across all four iterations.
- **Independent check performed instead**: coverage against the audio chapter is complete. All five audio movements are represented, all 27 substantive audio paragraphs have a corresponding structural moment, and the deck at 98.4% of audio word count confirms no content was dropped in the rewrite.

**SL-A4 is unenforceable, no visual registry exists** , VERIFIED

- **File**: `content/Islamic/isaf-al-talib/slide-decks/` (no `_visual-registry.md`)
- **Detail**: twenty-seven deck sources exist for this book and several entities recur across them, including the Prophet, Amir al-Mu'minin Ali ibn Abi Talib, Ja'far ibn Mansur al-Yaman, the Musannaf, the Mustansiriyya Councils and the interpretation of the Shari'a. With no registry, positional conventions cannot be held stable across the series. This chapter alone places Amir al-Mu'minin as a matrix row entity at M15 and M33, as a hierarchy leaf at M3 and M32, and as a flow node at M22.

---

## Checks that passed, with evidence

**SL-P2 Literal Illustration.** A case-insensitive scan of both files for "image of", "photo of",
"photograph", "depiction of", "illustration of", "picture of" and "stock" returns exactly one hit,
the framing's own prohibition at `:18` ("No stock-photo imagery, no figurative depiction of
persons"). The chapter's subject includes pictures on rugs and figures at the place of prostration,
and every mention is a ruling being diagrammed, never an instruction to render a picture. The
framing's explicit ban on figural depiction of persons is the stronger form and resolves the
`SL-P2:no-figural-depiction-prohibition` finding logged against ch26.

**SL-P3 Structure-vs-Description.** Both 2x2s meet the taxonomy's full requirement. M18 (`:226`)
names horizontal "origin of the act, from Unavoidable on the left to Chosen on the right" and
vertical "effect on the required form, from Does not obstruct at the bottom to Obstructs or replaces
at the top", populates all four quadrants with named cases, and closes with a reason for the axes.
M24 (`:320`) does the same on validity against adab (see the P2 on its fourth quadrant label). All
three hierarchies name every level with its siblings; M20's fourteen doors reproduce the source's
count exactly, including the doubled Praise, while adding a six-group functional sort the audio does
not have. All ten matrices are real tables with 3 to 5 columns and concrete cells.

**SL-P4 Diagram-Type Discipline.** 37 of 37 structural blocks open with a named taxonomy type. One
line does not belong to a labelled block, `:472` ("End state, all tests passed..."), and it is the
terminal state of M34's flow rather than an untyped moment.

**SL-P6 Audio Redundancy.** The deck is a rewrite, not a mirror. M3 builds an authority stack that
exists nowhere in the audio. M11 regroups the twelve foundations under four movements the source
does not name. M18 and M24 are 2x2s synthesised from case law scattered across many audio
paragraphs. M32 sorts prostration surfaces into a fit/unfit hierarchy the audio distributes across
paragraphs 87 to 91. M34 converts audio 83's rhetorical question list into a seven-test cascade with
a verdict per test. M35 assigns five concentric rings to material categories the audio only gestures
at as "material loyalties". Six of 37 moments (16.2%) are 1:1 with no structure added, against a
70% threshold.

**SL-A1 Visual Memory Test.** Strictly forgettable, three: M10 (a twelve-item enumeration), M12
(four lines of arrows duplicating a sequence), M33 (a grid 43% blank). Borderline, four: M6 (thin
rows, duplicated axis), M16 (the audio's own thrower metaphor with the audio's own element mapping),
M21 (the audio's own building metaphor, though more spatially committed than audio 53), M36 (contrast
columns that do not align). Strict 8.1%, inclusive 18.9%, threshold 30%. Passes on either count.
Thirty of 37 moments carry a distinctive shape: a populated quadrant grid, a multi-column matrix, a
nested hierarchy, a branched flow, or a metaphor with committed element assignments. M30's
dissection of ishtimal al-samma' remains the strongest moment in the deck, pairing each part of the
wrap to the specific act it disables.

**SL-A3 Arc.** The opening does real work: M1 sets the tension (the public form is complete, the
test begins) as a three-part spatial figure, M2 gives each edge its governing question and decisive
test, M3 supplies the authority the rulings will lean on. The middle traverses the edges in order and
each movement terminates on a structural payoff rather than a recap: M18's 2x2 closes Speech And
Motion, M24's 2x2 anchors the dress rulings, M32's fit/unfit hierarchy closes the ground, M34's
seven-test cascade converts the whole movement into a procedure. M35 then redraws the opening figure
as concentric rings with "obligations propagate inward", which is the deck's best moment of arc
closure. The Closing movement that follows it is where the P0s sit, but the arc's shape is present
and this check is about shape.

**Deck format compliance.** Zero em dashes in either file, mechanically confirmed. Zero prose
paragraphs over 100 words; the only non-tabular block over 60 words is M12's arrow chain, which is
structure. No inline phonetic parens, R-PHONETICS-OUT clean. H1 present once. The audio's five H2
movement headings are preserved verbatim, with one additional split.

**Framing file.** All five required H2 sections present in order. Audience named concretely ("Asif's
children and adult students of the Ismaili tradition who heard this episode, not the source"), not
"general audience". Four steering phrases, inside the 3-5 band. All four Visual Priorities map to
real deck structures, checked individually: the seven forms to M8 (and its columns match the priority
line's "hand position, direction, setting"), the twelve foundations to M10 and M11 (whose four
movements carry the priority's exact names, turning away, gathering, approaching, asking), the two
hierarchy trees to M20 and M32, and the validity-against-etiquette 2x2 to M24, whose quadrants place
all four named entities (silk, rings, exposed covering, ishtimal al-samma'). The no-colour constraint
is stated in both Prohibited Patterns and Steering Phrases, consistently.

---

## Verified vs Inferred

**VERIFIED (9)**: SL-P1 at M37, M36, M10 and M12, each cited to a deck line range and a matching
audio paragraph with both excerpts quoted and the overlap shown; the M37 regression, confirmed
against iteration 1's ledger signature; the stray-audio-instruction advisory, confirmed by grep
across all 27 framings; the framing word-count advisory; the M24 axis-pole advisory; the SL-P8
spine-absent advisory; the SL-A4 registry-absent advisory.

**INFERRED (2)**: SL-P1 at M6, a judgment about thin-but-present structure rather than absent
structure; the M33 sparse-column advisory.

The Worker addresses both categories on iteration. The P2 items do not gate the ship.

---

## Learning loop

**Pattern detection triggers.** The ledger now carries SL-P1 P0 findings for **23 of 23 chapters**
with a reviewed deck in this book (ch13 alone has 16 across four runs). The spec's threshold is "same
probe failure occurring in 3+ consecutive episodes", so this is triggered by a wide margin and is no
longer a per-chapter authoring problem.

**Proposal, routed to `slide-deck-steering.md` Category 7 as `[PROPOSED , needs review]`.** The
recurring shape is specific and therefore addressable: the deck's opening and closing movements
restate the audio chapter's opening and closing paragraphs, because those audio paragraphs are
already summaries, and a summary restructured is still a summary. Two candidate phrases:

- "The audio chapter's first and last paragraphs are summaries. Never build a structural moment from a summary paragraph; build it from the cases the summary is summarising."
- "A closing moment must compare something the deck has not yet compared. Re-labelling the opening figure is not a close."

**Second proposal, to `slide-deck-format.md`'s Common Mistakes.** Add: "An enumeration is not a
process flow. If the block has no branch and no condition, it is a list wearing a type name." This
run's M10 and the prior run's five single-column matrices are the same error at different surfaces,
and the current per-structure probes only catch it through SL-P1 and SL-A1 rather than directly.

**Systemic item for the Worker's generator, not this chapter.** "Do not read this prompt aloud."
appears in 21 of 27 framing files. Per the repo's systemic-fixes rule, fix the framing template once.

---

## Overall

**Pass 1**: fail (SL-P1, P0)
**Pass 2**: pass

**Bundle status**: iterate
**Verdict**: BLOCKED

The rewrite was a real improvement and should be acknowledged as one. Every iteration-3 finding is
resolved: the single-column matrices are gone, all ten matrices now carry 3 to 5 real columns, the
duplicated surface matrix and the non-spatial positions were deleted, and the H2 outline is back
within one movement of the audio's. Type diversity went from eight to nine types with no type over
27%. Thirty of 37 moments do genuine visual work.

What blocks the ship is that the restatement moved rather than left. The deck's entire Closing
movement, both of its moments, is the audio's two closing paragraphs with column headers and
position prefixes added, and M37 is a verbatim reinstatement of content iteration 1 already flagged
and iteration 2 already removed. Separately, the twelve foundations are presented three times in
thirty lines, where only the middle presentation adds anything.

The required work is small and subtractive. Deleting M10 and M12 and rebuilding M36's five rows so
each mercy sits opposite the severity it answers clears three of the five findings; M37 should be
deleted outright, since M35 already closes the deck on its strongest figure. Only M6 needs new
authoring, and the fix there is a type change from a two-column contrast to a three-region figure
that can hold dawn.

The iteration protocol requires all five to be addressed, not a subset, and requires a re-run. There
is no override path, and the bundle does not ship on this deck.

---

## Ledger Hook

11 findings emitted to `_learning/findings.jsonl` (source: slide-deck-challenger,
source_version 1.0): 5 P0 (SL-P1 at M37, M36, M10, M12, M6) and 6 P2 (stray audio instruction in the
framing, framing word count over band, M24 axis-pole slippage, M33 sparse column, SL-P8 spine
absent, SL-A4 registry absent). Signatures are content-distinguishing, so the two carried-over
advisories (SL-P8, SL-A4) deduplicate against prior runs, while the five P0s carry new signatures
because they cite different moments than iteration 3's did. The M37 record's excerpt names the
iteration-1 signature it regresses against, so the aggregator can read it as a reopened finding
rather than a new one.
