# Slide Challenger Report — ch18-sickness-epidemic-and-remembering-death

**Book:** isaf-al-talib
**Run:** 2026-09-18 (slide-deck-challenger v1.0)
**Scope:** per-chapter ch18-sickness-epidemic-and-remembering-death
**Deck source:** `content/Islamic/isaf-al-talib/slide-decks/ch18-deck-sickness-epidemic-and-remembering-death.txt`
**Deck framing:** `content/Islamic/isaf-al-talib/slide-decks/ch18-framing-sickness-epidemic-and-remembering-death.md`
**Audio chapter:** `content/Islamic/isaf-al-talib/chapters/ch18-sickness-epidemic-and-remembering-death.txt`
**Discussion spine:** absent (`_system/episode-drafts/` holds only `.gitkeep` for this book)
**Slide spine (`01-slide-spine.md`):** absent (`_system/slide-decks/ch18-sickness-epidemic-and-remembering-death/` holds only `.validated`)
**Visual registry (`_visual-registry.md`):** absent book-wide
**Iterations:** 2 (of 5 max) — prior ch18 report written 2026-09-18 06:20:51

**Structural moment count:** 39
**Deck word count:** 5,976 (audio 5,991 — 99.7%, inside the 50–100% band, at its ceiling)
**Framing word count:** 239 body words (spec band 150–250 — now in band; was 279 at iteration 1)

**Diagram-type distribution:**

| Type | Count | Share |
|---|---|---|
| Annotated structure | 10 | 25.6% |
| Contrast pair | 9 | 23.1% |
| Process flow | 5 | 12.8% |
| Comparison matrix | 4 | 10.3% |
| Visual metaphor | 4 | 10.3% |
| Named-axis 2x2 | 2 | 5.1% |
| Hierarchy | 2 | 5.1% |
| Timeline | 2 | 5.1% |
| Genealogy chain | 1 | 2.6% |

**Bundle status**: iterate
**Verdict**: BLOCKED

**Pass 1**: fail
**Pass 2**: pass

---

## Iteration 2 — what changed, and what did not

File mtimes settle this without inference:

| File | Modified | Relative to iteration-1 report (06:20:51) |
|---|---|---|
| `ch18-deck-…txt` | 06:12:21 | **before** — deck source untouched since iteration 1 |
| `ch18-framing-…md` | 06:24:11 | after — framing edited |

**The deck source, which carries every P0 and every P1, was not modified.** All 15 P0 findings and both P1 findings were re-derived independently from the file this run and stand unchanged, at unchanged line numbers.

The framing was edited, and the edit addressed exactly one finding: **P2-4 is RESOLVED** (body trimmed 279 → 239 words, inside the 150–250 band). **P2-3 is NOT resolved** — Visual Priority 4 was reworded from "the burial waits on a confirmation, not a presumption" to "burial waits on confirmation, never presumption," but its lead clause still names M22's shape ("Issue Ten as three conditions and one prohibition"), so NotebookLM is still steered toward the deck's weakest treatment of its hardest case.

Iteration 1 closed with: *"A next iteration that touches only P2-4 and P2-5 will be recorded as a non-response."* Touching only P2-4 is that case. **Recorded as a non-response on the P0/P1 set.** This is not a judgement about effort; it is the iteration protocol's rule that the Worker addresses ALL cited failures, not just the easy ones.

---

## The finding in one paragraph

This is a strong deck with one repeating defect, and the defect has a clean boundary. Every **Annotated structure** in this deck that dissects a physical or conceptual *object* supplies spatial positions and does real visual work (M01 the doorway/household/threshold, M11 the house with an illness in it, M16 the two shelves with the reader standing between them). Every Annotated structure that dissects a *sentence* — a question, a definition, a saying — supplies a `Whole:` line, named parts and annotations, but **no positions at all**, and so renders as a labelled bullet list carrying a diagram-type name. Seven of the ten annotated structures are in the second group. Those same seven are also where the deck's restatement problem lives: a sentence dissected into its own clauses is the audio's paragraph with bullet markers. Fix the one pattern and both P0s clear together.

---

## Pass 1 — Per-Structure Probes

| Probe | Result | Moments flagged | Notes |
|---|---|---|---|
| SL-P1 Restatement | **fail** | M06, M13, M19, M22, M27, M30, M34, M39 | 8 moments replaceable by a single audio sentence with no loss; threshold is 2 |
| SL-P2 Literal Illustration | pass | — | Zero "image of / photo of / photograph / picture of / depiction of / illustration of / stock" language in the deck source (grep-verified, 0 hits). The three `Image 1/2/3` labels at M30 name the source saying's own rhetorical images (herald, imprisonment, thistles), not pictures to be drawn. The only photographic strings in the bundle are the framing's own prohibitions (`No stock-photo imagery`, `no … photographs`), which is steering, not content |
| SL-P3 Structure-vs-Description | **fail** | M02, M06, M19, M22, M27, M30, M34 | 7 annotated structures name the type and supply two of its three required commitments; positions are absent in every one |
| SL-P4 Diagram-Type Discipline | pass | — | All 39 moments name a type drawn from the `slide-deck-patterns.md` taxonomy. No blank, no "TBD", no "various", no "general illustration" (grep-verified, 0 hits) |
| SL-P5 Diversity | pass | — | 9 distinct types. Contrast pair (9), comparison matrix (4) and named-axis 2x2 (2) are all present, which is what the theological-argument row of the affinity matrix predicts |
| SL-P6 Audio Redundancy | pass | — | 11 of 39 moments (28.2%) are 1:1 with an audio paragraph and add no structural value; threshold is 70%. The other 28 commit real axes, rows, levels, arrows, positions or quadrants |
| SL-P7 Justified Skip | n/a | — | Chapter has an authored deck; skip mode does not apply |
| SL-P8 Coverage | n/a (vacuous pass) | — | No `04-discussion-spine.md` and no `01-slide-spine.md` exist, so there are zero `[VISUAL CANDIDATE]` beats to cross-reference and no `[DROPPED: reason]` annotations to read. The probe cannot fail because nothing is registered. Substitute check run instead |

**SL-P6 advisory (does not meet the failure threshold, but is the shape behind SL-P1).** The deck's structural sequence tracks the audio's prose sequence essentially paragraph-for-paragraph, and its word count is 99.7% of the audio's. That parallelism is legitimate where a paragraph is *re-rendered* as a 2x2, a matrix, a bar-with-sliding-boundary or a reverse-direction flow — which is what 28 of the 39 moments do, several of them excellently. It is not legitimate where a paragraph is re-broken into labelled bullets, which is what the 11 flagged moments do. The probe passes on its stated arithmetic; the same evidence fails SL-P1.

**SL-P8 substitute check (concept coverage, `slide-deck-format.md` Common Mistake 6).** Every discrete audio concept appears in the deck in restructured form: the plague-flight permission and its two clauses, the Tafsir al-Arkan definition of the dying state, the four provenance chains, the camera turn from the worshipper to the visitor, the jurisdictional fact, the seventy thousand angels and its three easily-missed details, the refused meal and the polarity reversal, the household's concealed cost, the duty to publish and the transfer of the excuse, the sleep discipline, the prayer for well-being, the lifespan contradiction and its resolution, the animal state and the Hour, Issue Ten with its three conditions and one prohibition, the doorway test of attendance, the command to remember death, the day actually named, the herald/imprisonment/thistles triad, the three sites of calamity, the pressing at death, and the martyr verdict. **One omission:** the audio's three-pass roadmap paragraph (`chapters/ch18-…txt:11`, "It moves in three passes…") has no deck counterpart. This is judged a *correct* omission — a roadmap paragraph rendered as a structure would itself have been an SL-P1 restatement — and is recorded here only so the gap is on the record rather than unnoticed.

---

## Pass 2 — Architectural Pass

| Check | Result | Notes |
|---|---|---|
| SL-A1 Visual Memory Test | pass (narrow) | 10 of 39 moments (25.6%) forgettable against a 30% threshold. The margin is thin and is stated in full below |
| SL-A2 Variety | pass | Largest type share 25.6% (annotated structure) against a 60% threshold for a 10+ moment deck. Comfortable, and the most evenly distributed deck in this book so far |
| SL-A3 Arc | pass | Genuine three-part shape, built on a recurring spine — see below |
| SL-A4 Cross-Episode Consistency | n/a | `slide-decks/_visual-registry.md` does not exist anywhere in the book, so no entity carries a prior convention to violate. Vacuous rather than clean — see P2-1 |

**SL-A1 detail.** Forgettable set: M02 (L13, a definition shown as text), M06 (L73, question clauses as a list), M13 (L178, four-node linear chain duplicating M12's content), M18 (L255, a two-row matrix restating M17's reading), M19 (L271, question clauses as a list), M22 (L317, conditions as a list), M27 (L392, sentence parts as a list), M30 (L428, three images as a list), M34 (L486, conditions as a list), M39 (L551, a covered/still-ahead summary). **The margin is thin and the Challenger states it rather than hiding it:** adding the two next-weakest moments — M33 (L470, a six-node linear flow with no branch) and M32 (L454, a matrix with two uniform columns) — yields 12/39 = 30.8%, which would fail. Both were judged passes on substantive grounds (M33's remainder-carried-across node is a real conceptual shape; M32's rows genuinely ascend by cost). The check is recorded as a pass, but it is one borderline call away from a P1, and the SL-P1/SL-P3 remedies below would drop the share to roughly 5% and put it beyond argument.

**SL-A3 detail.** The opening establishes the organizing structure three ways over (M01 places the whole chapter at a doorway rather than a grave; M02 defines the crossing every later ruling is measured against; M05 draws the jurisdiction line). The middle builds real pressure: the action-vs-belief 2x2 at M07 with one quadrant deliberately left empty and the emptiness explained, the reward matrix, the food flow that ends in a reversed polarity, the fixed-term bar at M17, the intuition-inverting 2x2 at M21, and Issue Ten's refusal of a near-certain presumption. The close resolves structurally rather than with a takeaway list: M36 runs the whole chapter backwards with upward arrows, then a four-by-four conduct matrix, then a hierarchy nesting three settlements under the opening principle, then a forward-pointing timeline. **The arc's spine is the jurisdiction line**, which recurs by name at M05, at M24 ("third appearance"), inside M30's Consequence of Image 2, and as Level 1 of M38. That is deliberate recurrence tracked in the source itself, and it is the best architectural feature of this deck.

---

## Failures requiring Worker iteration

### P0 (blocks ship)

#### SL-P3: Structure-vs-Description — 7 annotated structures supply no positions

`slide-deck-patterns.md` states that an **Annotated Structure** MUST specify (a) the whole, (b) parts named **with positions**, (c) one annotation per part, and names the anti-pattern explicitly: *"Callouts without spatial relation. Annotated structures need the spatial layout to do work."* Each moment below supplies (a) and mostly (c), and supplies (b) only as far as naming. With no positions, NotebookLM has no layout to draw and will render a bullet list that nonetheless carries a diagram-type label.

The boundary is clean and the Worker should read it as one rule, not seven fixes: **this deck dissects objects well and sentences badly.**

**M02 — the definition of the dying state**
- **File:** `slide-decks/ch18-deck-sickness-epidemic-and-remembering-death.txt:13`
- **Content (≤300 chars):** `Whole: the dying state, as defined / - Part: the presence of death. Annotation: death is placed in the room, already arrived. / - Part: the imminence of transition. Annotation: the crossing has not happened yet and is about to. / - Absent part: any word for ending or termination.`
- **What's missing:** positions. Three parts, no spatial relation between them.
- **Suggested Worker re-authoring:** the content is already spatial and the deck says so ("death is placed in the room", "the crossing has not happened yet"). Make it a one-axis position line — arrived / not-yet-crossed / the terminus the definition refuses to name — and place the absent part where the definition declines to put it. The "Absent part" device is good and should survive.
- **VERIFIED**

**M06 — the first question, as put**
- **File:** `…ch18-deck…txt:73`
- **Content (≤300 chars):** `Whole: the question as put / - Part: people who move out of fear of epidemic and plague. Annotation: the action, described neutrally. / - Part: thinking they can escape it. Annotation: the belief, held as a thought rather than reported as a fact. / - Part: is this permissible or not.`
- **What's missing:** positions. Four parts, all clauses of one sentence, in sentence order only.
- **Suggested Worker re-authoring:** this moment exists to separate action from belief, which is exactly the 2x2 that follows at M07. Fold it in as the 2x2's setup — put the action clause on the horizontal axis label and the belief clause on the vertical — rather than giving it a standalone structure that pre-states the axes in prose.
- **VERIFIED**

**M19 — the questioner's proposed reading**
- **File:** `…ch18-deck…txt:271`
- **Content (≤300 chars):** `Whole: the question, with the answer's brevity as its verdict / - Part: the subject, the wretched and dissolute person, overtaken by the Hour while still alive. / - Part: the proposed reading, that he is more severely punished than those who have already died.`
- **What's missing:** positions, **and** per-part annotations. The only annotation is on the brevity, which is a property of the whole, not of a part. Parts 1–3 carry appositive restatements, not callouts.
- **Suggested Worker re-authoring:** delete the structure and let M20 (the sensory/spiritual contrast pair) and M21 (the inversion 2x2) carry this material, which they already do better. If the brevity-as-verdict observation is worth keeping, it is one annotation line on M21.
- **VERIFIED**

**M22 — the ruling of Issue Ten**
- **File:** `…ch18-deck…txt:317`
- **Content (≤300 chars):** `Whole: the ruling, four parts / - Condition 1, WHO. If a woman is available to extract it. / - Condition 2, WHETHER IT CAN BE DONE. If it is possible. / - Condition 3, THE CHILD'S OWN STANDING. Six months or older, showing signs of life. / - Prohibition. The mother should not be buried until the child's death is confirmed.`
- **What's missing:** positions. Annotations are present and good; the structure is a logical list, not a spatial dissection.
- **Suggested Worker re-authoring:** three conditions that must ALL hold before an obligation fires, plus a prohibition that fires independently, is a gate — render as a process flow with three gates in series and the prohibition as a parallel branch that runs whatever the gates decide. That shape shows the thing the annotations are reaching for: the burial prohibition does not depend on whether the extraction was possible.
- **Note:** this moment is still named in the framing's Visual Priority 4 after the iteration-2 framing edit, so NotebookLM is being steered *toward* the deck's weakest treatment of its hardest case. See P2-3.
- **VERIFIED**

**M27 — the first saying on remembering death**
- **File:** `…ch18-deck…txt:392`
- **Content (≤300 chars):** `Whole: a command with a stated purpose attached / - Part, the oath. Annotation: part of the report, marking emphasis rather than doubt. The speaker is insisting. / - Part, the practice. Remember death often. / - Part, the days named. / - Part, the purpose.`
- **What's missing:** positions. Four clauses of one sentence in sentence order.
- **Suggested Worker re-authoring:** M28 (the timeline that shows which day is named and which is conspicuously not) already does this saying's visual work, and does it very well. Reduce M27 to M28's axis caption, or position the four parts on that same axis so the oath, the practice, the two named days and the present-tense purpose sit at their own points on one line.
- **VERIFIED**

**M30 — the second saying, three images**
- **File:** `…ch18-deck…txt:428`
- **Content (≤300 chars):** `Whole: one sentence, three images / - Image 1, the herald. Annotation: a herald arrives before the event, sent by the one whose arrival he announces. / - Image 2, the imprisonment. Annotation: the verb is deliberate and hard. / - Image 3, the thistles. Annotation: the image that carries the argument.`
- **What's missing:** positions. Also, Image 3's annotation is a forward reference rather than a callout ("the image that carries the argument"), so one of the three parts is annotated with a promise.
- **Suggested Worker re-authoring:** the three images are not siblings — they sit at three points on the same passage (notice before, detention during, cleaning throughout). Position them on that passage, which also stops M30 from being a table of contents for M31.
- **VERIFIED**

**M34 — the last sentence**
- **File:** `…ch18-deck…txt:486`
- **Content (≤300 chars):** `Whole: three conditions and one verdict / - Condition 1: believed in our cause. / - Condition 2: loved us. / - Condition 3: allied with us. / Annotation: the three taught from the opening chapters of this book … / - The verdict: he is a martyr.`
- **What's missing:** positions, and per-part annotations on conditions 1–3 (one shared annotation covers all three). The layout is also malformed: the annotation line sits between Condition 3 and The verdict rather than attaching to a part.
- **Suggested Worker re-authoring:** M35 (battlefield against bed) is the memorable treatment of this sentence and needs no preamble. Either delete M34 or make the three conditions a three-step convergence into the single verdict, positioned so the convergence is visible.
- **VERIFIED**

**Contrast — the three annotated structures that pass, cited so the Worker can see the rule:** M01 (`:5`) gives every part a `Position:` (the doorway, the household under strain, the threshold); M11 (`:154`) gives every part a `Position:` (the centre lying ill, the surrounding rooms, the kitchen and the door, the doorway looking in) and is the best annotated structure in the deck; M16 (`:228`) builds a spatial frame (two shelves, with the questioner standing between them) even without an explicit `Position:` field.

#### SL-P1: Restatement — 8 moments are replaceable by one audio sentence

Failure threshold is 2. Each citation pairs the deck moment with the audio sentence that already carries it. The probe's method is applied literally: if a host said this aloud, would anything be lost?

**M13 — "The warning as a transfer of liability"** (`…ch18-deck…txt:178`)
- Deck: `Start: a man who has never heard the ruling … Status: inside an excuse. He has not been warned. … A scholar warns him. Status changes at the warning, not at the next meal. … End: outside the excuse. The ignorant are covered. The informed are not.`
- Audio (`chapters/ch18-…txt:53`): "The warning transfers the liability. Before he is told, a man who eats at the sick man's table is inside an excuse; afterwards he is not. … The ignorant are covered. The informed are not."
- Near-verbatim, four nodes for one before/after, and M12's hierarchy immediately above already carries the covered/uncovered split as named siblings. **VERIFIED**

**M19 — "The questioner's proposed reading"** (`…ch18-deck…txt:271`)
- Audio (`:85`): "the answer's brevity is a way of saying that the questioner has understood the horror correctly."
- Deck: "Annotation on the brevity: the shortness of the answer says the questioner has understood correctly." Near-verbatim; the four parts above it are the question's own clauses. **VERIFIED** (also cited under SL-P3)

**M06 — "The first question, dissected"** (`…ch18-deck…txt:73`)
- Audio (`:19`): "It does not ask whether flight works. It describes the fleeing party as people who think they can escape, and then asks only about permission. The questioner has separated two things that people under threat almost never separate: whether an action is lawful, and whether it achieves what the person doing it believes it achieves."
- Deck's `Reading:` line is that last sentence compressed; the parts are the rest of it. **VERIFIED** (also cited under SL-P3)

**M22 — "The ruling of Issue Ten"** (`…ch18-deck…txt:317`)
- Audio (`:95`–`:103`): "Three conditions and one prohibition, and they are worth separating. The first condition is who. … The second condition is whether it can be done at all … The third is the child's own standing … Then the prohibition, which is the part that reveals the chapter's mind."
- The deck moment is that passage with bullet markers, down to "the part that reveals the mind behind the ruling." The visual work on Issue Ten is done by M23 and M24, which is precisely why M22 is redundant as a standalone structure. **VERIFIED** (also cited under SL-P3)

**M27 — "The first saying"** (`…ch18-deck…txt:392`)
- Audio (`:117`): "The oath is part of the report, and it marks emphasis rather than doubt: the speaker is insisting. … The benefit is present-tense and it is measured in what a person can carry." Plus `:121`: "Remembrance of death is not commanded here as a preparation for dying. It is commanded as a remedy for living."
- Deck reproduces all three clauses as parts and closes with "remembrance of death is commanded not as preparation for dying but as a remedy for living." **VERIFIED** (also cited under SL-P3)

**M30 — "The second saying, three images"** (`…ch18-deck…txt:428`)
- Audio (`:127`): "A herald arrives before the event, sent by the one whose arrival he announces … Illness, on this reading, is not a random malfunction of the body." And (`:129`): "The verb is deliberate and it is a hard one. To be held in the ground is described as a detention, done by God's will, to whom He wills."
- Deck annotations are these sentences with light compression. **VERIFIED** (also cited under SL-P3)

**M34 — "The last sentence"** (`…ch18-deck…txt:486`)
- Audio (`:145`): "Three conditions, and they are the three this book has been teaching from its opening chapters … What is new is the verdict attached to them. Not that such a person dies well, or is forgiven, or is received kindly. That he is a martyr."
- Deck: "Annotation: this is what is new. Not that he dies well, or is forgiven, or is received kindly. That he is a martyr." Verbatim. **VERIFIED** (also cited under SL-P3)

**M39 — "Where the Book of Funerals stands"** (`…ch18-deck…txt:551`)
- Audio (`:159`): "The Book of Funerals has only just been opened here. It has defined the dying state, regulated the doorway, and taught the reader what to hold in mind while he stands in it; the grave itself, and the rites owed to a body once the transition has actually been made, are still ahead."
- Deck is that sentence split into five axis positions under two period bands, with the first clause repeated verbatim as the annotation. The axis adds no ordering the sentence does not already state, and `slide-deck-patterns.md` names this anti-pattern for Timeline: "Bulleted dates without visible axis. A timeline's force comes from the axis." **VERIFIED**

**Suggested Worker approach for SL-P1.** All eight are single sentences, and six of the eight are the same defect as SL-P3. Two structural remedies, no cosmetic ones: **fold** (M06 into the M07 2x2 as its axis setup; M13 into the M12 hierarchy as a state-change annotation; M19 into M21; M27 into the M28 timeline; M34 into M35) or **delete** (M22's content survives in M23 and M24; M39 can become a two-position forward pointer or go). A 39-moment deck built from a 5,976-word source is already 2.6x the 13–15 budget `slide-deck-format.md` sets for a long episode, so deletion is legitimate and probably better.

### P1 (ship-with-caution)

**SL-A1 (secondary): M32's comparison matrix carries two near-uniform columns**
- **File:** `…ch18-deck…txt:454`
- **Content (≤300 chars):** `| His wealth | Property | Lowest | Purges | Sins cleaned | / | His child | A bereavement | Middle | Purges | Sins cleaned | / | His own person | An affliction of the body | Highest | Purges | Sins cleaned |`
- **What's wrong:** the `Verb used` column reads `Purges` in three of four rows and the `Outcome` column reads `Sins cleaned` in the same three. `slide-deck-patterns.md` anti-pattern 4 (decorative structures) applies: a matrix earns its keep only when cells differ. Two of five columns are doing no differentiating work, which dilutes the one genuinely interesting column (`Rank in cost`, where the rows really do ascend).
- **Suggested fix:** drop the two uniform columns into the annotation (the deck already has an "Annotation on the verb" line doing exactly that job), and let the matrix be site / what is lost / rank. Or add a differentiating column that earns its place — what the loss costs the household in each case, which the chapter has material for.
- **VERIFIED**

**SL-A1 (secondary): M18's comparison matrix has only two rows**
- **File:** `…ch18-deck…txt:255`
- **Content (≤300 chars):** `| Deferred lifespans that neither increase nor decrease | A category, the deferred term | The total | The division | Shelf A | / | What decreases from the past portion increases in what remains of the future | A movement, the sliding boundary | The division | The total | Shelf B |`
- **What's wrong:** `slide-deck-patterns.md` sets comparison matrices at 3+ entities and says outright that "audio handles 2-entity comparisons fine; matrices earn their keep at higher dimensions." A two-row matrix is a contrast pair wearing a table, and the deck renders every other two-sided opposition as a contrast pair. Its content also restates the `Reading:` line of M17 immediately above it, which is the deck's best metaphor and needs no table to repeat it.
- **Suggested fix:** re-type as a contrast pair (Column A the total, Column B the division, shared row on the two not measuring the same thing), or fold the two rows into M17 as the two ends of the bar. The `Link back` line about the man who changes his address and not his term is excellent and must survive either way.
- **VERIFIED**

### P2 (advisory, does not affect verdict)

**P2-1: `slide-decks/_visual-registry.md` does not exist**
- This is chapter 18 of a 27-chapter series with every deck authored. Recurring entities in this deck alone — our master Idris ibn Hasan, Sheikh Yusuf ibn Isma'il al-Samati al-Hindi, Arkan al-Islam, our master Ja'far ibn Sayyidina Sulayman, Mawlana the Commander of the Faithful — recur across the ch16–ch19 decks with no standing visual convention recorded. SL-A4 cannot fail because nothing is registered, which makes the check vacuous book-wide rather than satisfied. This chapter also introduces a genuine cross-chapter convention worth registering: the **jurisdiction line** (human action near side, divine outcome far side), used three times inside ch18 and directly relevant to ch19's burial material.
- **INFERRED** (the absence is verified; the judgement that it is a series-level gap rather than a per-chapter defect is heuristic)

**P2-2: no `01-slide-spine.md` and no `04-discussion-spine.md`**
- `_system/episode-drafts/` holds only `.gitkeep`, and `_system/slide-decks/ch18-sickness-epidemic-and-remembering-death/` holds only a `.validated` stamp. SL-P8 therefore has no `[VISUAL CANDIDATE]` beats to check and no `[DROPPED: reason]` annotations to read; only the substitute concept-coverage check could be run. A 39-moment deck against a 13–15 moment budget is exactly the case the slide spine exists to catch.
- **VERIFIED** (both absences confirmed on disk)

**P2-3: the framing's Visual Priority 4 still points at the deck's weakest treatment** *(carried from iteration 1; reworded, not resolved)*
- **File:** `slide-decks/ch18-framing-sickness-epidemic-and-remembering-death.md:13`
- **Content now:** `- Issue Ten as three conditions and one prohibition: burial waits on confirmation, never presumption.`
- **Content at iteration 1:** `- Issue Ten as three conditions and one prohibition: the burial waits on a confirmation, not a presumption.`
- The iteration-2 edit shortened the line (helping P2-4) without changing what it steers toward. The lead clause still names M22, which fails SL-P1 and SL-P3; the trailing clause names M23's content, which is one of the deck's strongest structures. The framing is still steering NotebookLM toward a labelled list when the contrast pair beside it carries the chapter's hardest case. Priorities 1–3 map cleanly to M07, M09+M10 and M17 respectively and are well-chosen.
- **Suggested fix:** lead with the presumption/confirmation contrast and its "nobody standing there may assume what they are almost certainly right about" verdict row; drop the "three conditions and one prohibition" phrasing entirely.
- **VERIFIED**

**P2-4: framing body word count — RESOLVED at iteration 2**
- Body (excluding the H1 label line) now measures **239 words** against the 150–250 band; it was 279 at iteration 1. All five required H2 sections remain present, the audience is named concretely, and there are four steering phrases against the 3–5 band. No further action. Recorded here for the iteration trail; not re-emitted to the ledger.
- **VERIFIED**

**P2-5: three H2 movements added beyond the audio outline**
- Audio has 5 H2s; the deck has 8. All five audio headings are preserved verbatim. The deck adds `## The Refused Meal and the Duty to Publish`, `## The Hour and the Animal State` and `## Issue Ten: The Living Child`, each splitting a long audio movement. `slide-deck-format.md` validation item 3 asks that H2 movement headings be preserved from the audio chapter. The subdivisions are defensible for a deck this dense and they fall on real seams, but they are a deviation from the stated contract and should be a conscious choice rather than a drift.
- **VERIFIED**

**P2-6: the four genealogy chains mix edge semantics inside a single chain**
- **File:** `…ch18-deck…txt:24`
- **Content (≤300 chars):** `Sheikh Yusuf ibn Isma'il al-Samati al-Hindi, compiler → our master Idris ibn Hasan, may Allah be pleased with him, respondent → the volume of questions and answers → the rulings on flight, on lifespans, on the Hour`
- **What's wrong:** the arrows are directed (so the taxonomy's stated anti-pattern, undirected arrows, does not fire), but the *relation* each arrow denotes changes mid-chain: person-asks-person, then persons-produce-artifact, then artifact-contains-content. Chain 2 additionally runs an isnad in reporting order (book → Commander → Messenger) and then hangs "the seventy thousand angels" off the end as a fourth node, though the angels are the hadith's content and not a transmitter. Chain 4 ends on "named here, not re-opened", which is an editorial note rather than a node. A reader of the rendered diagram cannot tell what an arrow means.
- **Suggested fix:** either split each chain at its semantic seam (a transmission chain, then a containment bracket), or label the edge relations. Filed P2 rather than P0 because nodes and direction are both committed and NotebookLM will render a coherent chain; the defect is craft, not absence of structure.
- **VERIFIED**

**P2-7 (NEW at iteration 2): an unregistered steering phrase is in use across 11 framings in this book**
- **File:** `slide-decks/ch18-framing-sickness-epidemic-and-remembering-death.md:26`
- **Content:** `- "Render every slide as black and white line art on white, never dark or coloured."`
- **What's wrong:** `slide-deck-format.md` requires the `## Steering Phrases` section to draw from `slide-deck-steering.md`. Three of ch18's four phrases do (Category 1 verbatim; Category 2 verbatim-adjacent; Category 3 adapted). This fourth phrase appears nowhere in the steering catalog, and `grep` finds it in **11 of this book's framing files** — so it is a book-wide convention that has never been registered, reviewed, or attributed to an observed improvement. `slide-deck-steering.md`'s own promotion rule requires a draft phrase to sit in `## Category 7 — Candidates` first; **that section does not exist in the file** (it is referenced twice but never defined), so there is currently nowhere for a candidate to land.
- **Learning-loop consequence:** the Challenger's detection rule ("a new failure category emerging in 2+ episodes") is met at 11 episodes. This report proposes the phrase for `## Category 7 — Candidates` tagged `[PROPOSED — needs review]`, together with creating that missing section. Per the boundary contract the Challenger does not write to `skills-staging/`; the proposal is surfaced here and in the ledger for Asif's review.
- **Note on merit, kept separate from the finding:** the phrase is plausibly a *good* one — it is concrete, it targets NotebookLM's stock-photo default, and the framing's `## Prohibited Patterns` backs it with "No colour, gradients, or photographs." The finding is about registration and review, not about the phrase being wrong.
- **VERIFIED**

---

## What passes, stated plainly

This deck is not a bulletified mirror of the audio, and its ceiling is the highest in this book so far. Twenty-eight of thirty-nine moments commit to real structure: two named-axis 2x2s that populate every quadrant with an entity and a reason, one of them deliberately leaving a quadrant empty and explaining the emptiness, and the other inverting ordinary intuition by emptying the two quadrants intuition would fill; a fixed-length bar with a single sliding boundary that resolves the lifespan contradiction in one image; a jurisdiction line drawn three separate times in three different rooms and then installed as Level 1 of the closing hierarchy; a burrs-in-camel-fur metaphor with the pain correctly assigned as the cleaning rather than incidental to it; a branching process flow whose second path ends in a reversed polarity; a reverse-direction flow that reads the whole chapter backwards with upward arrows; a house with an illness in it whose four parts are placed in four rooms; and a timeline whose force comes from the position it conspicuously declines to name.

Diversity and variety both pass comfortably, and the type distribution is the most even in the book. The arc is genuine and spined by a recurring metaphor the source tracks by name. Length is in band on both files as of iteration 2, all five required framing H2 sections are present with a concretely named audience, there are no em dashes anywhere in either file (grep-verified, 0 in each), no inline phonetic parens, no prose paragraph over 100 words (the ten blocks over 100 words are all structured scaffolds — tables, element-assignment lists, level trees — not prose), and no literal-illustration language anywhere.

What blocks the bundle is a single habit applied seven times: reaching for "Annotated structure" to dissect a *sentence*, where the parts are that sentence's own clauses, no positions are supplied, and the result is the audio paragraph with bullet markers. Fix that one habit and both P0s clear, the SL-A1 margin stops being narrow, and this deck ships.

---

## Verified vs Inferred summary

- **VERIFIED (21 findings):** SL-P3 ×7, SL-P1 ×8, SL-A1 secondary ×2 (M32 uniform columns, M18 two-row matrix), P2-2, P2-3, P2-5, P2-6, P2-7. Each carries evidence quoted from the deck source, the audio chapter, the framing, or a file absence confirmed on disk.
- **INFERRED (1):** P2-1 (registry absence judged a series-level gap rather than a per-chapter defect).
- **RESOLVED since iteration 1 (1):** P2-4 (framing word count), verified by re-measurement.

Six moments are cited under both SL-P3 and SL-P1 (M06, M19, M22, M27, M30, M34). That overlap is not double-counting: they are two distinct defects with a common cause, and a fix that supplies positions without removing the audio-verbatim wording would clear one and leave the other standing.

The Worker addresses BOTH categories on iteration.

---

## Iteration note

Two iterations run. Early-break taken after iteration 2: the deck source — the sole carrier of all 15 P0 and both P1 findings — was not modified between iterations (mtime 06:12:21, prior report 06:20:51), so the (p0, p1) counts are identical to iteration 1 by construction and a third pass inside this invocation cannot produce new information. Three iterations remain in the budget for the next invocation.

Re-invoke after the Worker re-authors or folds the seven SL-P3 moments and resolves the eight SL-P1 restatements. Expected effect: SL-P3 and SL-P1 clear, the SL-A1 forgettable share drops from 25.6% to roughly 5%, and the chapter reaches SHIP-READY once the two P1 matrix defects are also addressed.

Per the iteration protocol, the Worker addresses ALL cited failures, not just the easy ones. Iteration 2 touched only P2-4 and is recorded as a **non-response** on the P0/P1 set. There is no Worker-overrides-Challenger path; a disagreement with any finding above is logged in this report and escalated to Asif, but the bundle still does not ship while the finding is open.

## Ledger emission summary

23 findings emitted to `_learning/findings.jsonl` this run (source: slide-deck-challenger, version: 1.0). Breakdown: **P0 15** (SL-P3 ×7, SL-P1 ×8), **P1 2** (SL-A1 M32 decorative columns, SL-A1 M18 two-row matrix), **P2 6** (SL-A4 registry absent, SL-P8 spine absent, SL-P3 framing priority mis-point, SL-P4 added H2 movements, SL-P3 genealogy edge semantics, SL-P5 unregistered steering phrase). All 23 signatures unique within the run, and every carried-forward signature is byte-identical to its iteration-1 emission so the aggregator dedups correctly across runs. `SL-P4:framing-wordcount-above-band:ch18-framing` is deliberately NOT re-emitted — the finding is resolved.
