# Slide Challenger Report — ch06-bodily-substances-and-disavowal

**Run timestamp**: 2026-09-18T08:05:00Z (slide-deck-challenger v1.0)
**Book**: isaf-al-talib
**Scope**: per-chapter, ch06-bodily-substances-and-disavowal
**Deck source**: `content/Islamic/isaf-al-talib/slide-decks/ch06-deck-bodily-substances-and-disavowal.txt` (5,077 words)
**Slide framing**: `content/Islamic/isaf-al-talib/slide-decks/ch06-framing-bodily-substances-and-disavowal.md` (250 words)
**Audio chapter**: `content/Islamic/isaf-al-talib/chapters/ch06-bodily-substances-and-disavowal.txt` (5,758 words)
**Deck / audio word ratio**: 88% (spec band 50–100%) — pass
**Structural moment count**: 43 (typed blocks; excludes preserved-quote and attribution blocks)
**Iterations**: 1 (of 5 max)

**Bundle status**: iterate
**Verdict**: BLOCKED

---

## Diagram-type distribution

| Type | Count | Share |
|---|---|---|
| Process flow (incl. "with branches" / "with conditions" / "with a branch") | 13 | 30.2% |
| Comparison matrix | 9 | 20.9% |
| Contrast pair | 8 | 18.6% |
| Annotated structure | 6 | 14.0% |
| Genealogy chain | 3 | 7.0% |
| Visual metaphor | 2 | 4.7% |
| Hierarchy | 1 | 2.3% |
| Timeline | 1 | 2.3% |
| **Total** | **43** | **100%** |

Eight distinct taxonomy types. No untyped, "TBD" or "various" moment. No 2x2 and no quadrant map (not required: the source profile is theological argument / comparative study, whose strong fits — contrast pair, hierarchy tree, annotated structure, comparison matrix — are all present).

---

## Pass 1 — Per-Slide Probes

| Probe | Result | Moments flagged | Notes |
|---|---|---|---|
| SL-P1 Restatement | **fail (P0)** | M6 (L77), M12 (L168), M36 (L468) | 3 moments are replaceable by a single audio sentence with no loss; threshold is ≥2 |
| SL-P2 Literal Illustration | pass | — | Zero "image of" / "photo of" / "depiction of" language in the deck. The single word "illustration" (L385) denotes a narrative example (a hadith), not an image. Framing L18 actively prohibits stock photography |
| SL-P3 Structure-vs-Description | pass | — | Every one of the 43 moments commits axes/rows/columns/nodes/levels/positions. Advisory: 2 of 18 cells in M16 and 1 of 4 in M23 defer instead of committing (see P2 findings) |
| SL-P4 Diagram-Type Discipline | pass | — | All 43 moments name a taxonomy type. Advisory: "Genealogy chain" is applied 3x to non-lineage relations (see P2 findings) |
| SL-P5 Diversity | pass | — | 8 types; contrast pairs (8) and comparison matrices (9) both present |
| SL-P6 Audio Redundancy | pass | — | Est. 3–5 of 43 moments (7–12%) are 1:1 bulletifications; threshold is ≥70%. Majority synthesize across non-adjacent audio paragraphs |
| SL-P7 Justified Skip | n/a | — | `slide-deck-status` is not `not-needed`; a deck pair exists |
| SL-P8 Coverage | n/a (vacuous) | — | No `04-discussion-spine.md` exists for this book (`skip_podcast: true` in series-config; `_system/episode-drafts/` holds only `.gitkeep`). Zero `[VISUAL CANDIDATE]` tags exist to cover. Substitute concept-coverage check against the audio chapter: pass (see below) |

### SL-P8 substitute check — audio-chapter concept coverage

Because the canonical Coverage input does not exist for this book, the Challenger ran the `slide-deck-format.md` checklist item 10 instead ("does every concept in the audio chapter appear, restructured, in the deck source"). All 40 identifiable audio concepts are present, including the easily-dropped incidentals: the Eid al-Ghadir make-up ruling (deck L300), the pork reference from the Book of Reports (deck L133), the prohibition on benefiting from a human hide (deck L132), the compiler's admission that he lacked the exact phrase (deck L340-348), and the Prophetic narrative illustration (deck L385-389). No missing-concept finding.

The one audio beat that thins in transfer is audio L33-35 ("That repetition is not ornamental… lawful benefit is not simply whatever can be used"), which survives as principle in M1's Part-1 annotation and M14's reading rather than as its own moment. Judged covered in substance. INFERRED.

---

## Pass 2 — Architectural Pass

| Check | Result | Notes |
|---|---|---|
| SL-A1 Visual Memory Test | pass | 4 clearly forgettable (M6, M12, M36, M43) + 2 borderline (M23, M26) = 6/43 = 14%; threshold is ≥30% |
| SL-A2 Variety | pass | Largest type share 30.2% (process flow); threshold is >60% for a 10+ moment deck |
| SL-A3 Arc | pass | Opening establishes the organizing structure; middle builds; close resolves structurally. Advisory on M43 and on templated per-movement cadence |
| SL-A4 Cross-Episode Consistency | n/a | `slide-decks/_visual-registry.md` does not exist. Advisory: the book has 13 decks and verified recurring entities, so a registry would have entries and consistency is currently unverifiable |

### SL-A3 arc trace (verified)

- **Opening** (L5-39): M1 annotated structure names the whole and orders its six parts by "increasing nearness to the person" — an explicit organizing axis, not a list. M2 contrast pair establishes the central tension (what earlier chapters settled vs what this chapter adds: "Earlier chapters read contact, this chapter reads condition").
- **Middle** builds pressure along that stated axis: outer materials (L41-100) → commerce (L102-134) → the repaired body (L135-175) → M13's concentric-circles metaphor at L177, which retroactively renders the opening axis spatial → blood states (L198-381), peaking at M18's threshold hierarchy and M28's banded timeline (the deck's densest structural moment) → speech (L383-472).
- **Close** (L562-599): M44 (six distinctions held apart, two-column) and M45 (before/after contrast pair with a shared row) resolve structurally rather than as takeaways.

The arc holds. Two advisory observations recorded below.

---

## Failures requiring Worker iteration

### P0 (blocks ship)

#### SL-P1: Restatement — M6, "Annotated structure. The goat as the source describes it."

- **File**: `slide-decks/ch06-deck-bodily-substances-and-disavowal.txt:77-86`
- **Content (excerpt)**: "Whole: the animal under discussion, named so the ruling lands on a known creature / Parts: - Classification: a kind of sheep - Defect: beginning from its sin upward - Horns: two - Region: a common type in India"
- **Replaced by which audio sentence**: `chapters/ch06-bodily-substances-and-disavowal.txt:19` — "The source then identifies the goat as a kind of sheep, with a defect beginning from its sin upward and with two horns, a common type in India."
- **What's wrong**: the four "parts" are attributes of one noun with no spatial relation between them, which is the annotated-structure anti-pattern in `slide-deck-patterns.md` ("Callouts without spatial relation"). Nothing is lost if a host says the sentence aloud. Also fails SL-A1 as a labeled list.
- **Suggested Worker re-authoring**: do not delete (concept coverage must hold). Absorb the identification into M4's comparison matrix at L63 as a qualifier on the goat-hair row headers, or as a single source-note line beside the verbatim ruling at L71.
- **Verified | Inferred**: VERIFIED

#### SL-P1: Restatement — M12, "Annotated structure. The quilt made from the dead."

- **File**: `slide-decks/ch06-deck-bodily-substances-and-disavowal.txt:168-175`
- **Content (excerpt)**: "Whole: a dead-derived covering / Parts: - Dry state: it does not adhere, meaning it does not stick to anything pure - Wet state: one of them is wet, and it therefore becomes a source of impurity / Annotation: the recurring principle returns, moisture matters because moisture carries."
- **Replaced by which audio sentence**: `chapters/ch06-bodily-substances-and-disavowal.txt:45` — "a quilt made from the dead that does not adhere… yet one of them is wet and therefore becomes a source of impurity."
- **What's wrong**: a two-part annotated structure whose two parts are the two halves of one sentence. No axis, no comparison, no hierarchy; the "whole/parts" frame adds no visual information the sentence lacks.
- **Suggested Worker re-authoring**: convert to a dry/wet contrast pair with real attribute rows (status of the object, status of what it touches, required act, instruction to the household) matching the M7 shape at L88-100, OR fold the dry/wet binary into M13's concentric-circles reading as the moisture rule that lets impurity cross a ring.
- **Verified | Inferred**: VERIFIED

#### SL-P1: Restatement — M36, "Genealogy chain. The bridge into the final section."

- **File**: `slide-decks/ch06-deck-bodily-substances-and-disavowal.txt:468-472`
- **Content (excerpt)**: "Hidden state of the body → governs prayer, fasting, touch, speech, and marital approach / Hidden state of the womb → governs marriage, inheritance, sale, and lineage / Shared method → do not proceed as though a concealed bodily fact has no legal force"
- **Replaced by which audio sentences**: `chapters/ch06-bodily-substances-and-disavowal.txt:127` — "In the menstrual section, the hidden state of the body governs prayer, fasting, touch, speech, and marital approach. In the disavowal section, the hidden state of the womb governs marriage, inheritance, sale, and lineage… do not proceed as though a concealed bodily fact has no legal force."
- **What's wrong**: near-verbatim arrow-formatting of one audio paragraph — the cleanest instance of bulletified prose in the deck. Compounding: it is a transitional device whose work M42 (L554-560) already does at greater depth, so the deck spends a structural moment twice.
- **Suggested Worker re-authoring**: either delete and let M42 carry the binding (the audio already speaks the bridge), or promote it into a two-column contrast pair (body vs womb) with attribute rows that M42 does not repeat — what is concealed, who can read it, what instrument reads it, what relation it governs.
- **Verified | Inferred**: VERIFIED

### P1 (ship-with-caution)

None.

### P2 (advisory — does not affect verdict)

#### SL-P4: "Genealogy chain" applied to non-lineage relations (M14, M36, M42)

- **File**: `slide-decks/ch06-deck-bodily-substances-and-disavowal.txt:189-196`, `:468-472`, `:554-560`
- **Content (excerpt)**: "Goat hair → cut during life or taken after slaughter → status follows that act, not the appearance of the hair"
- **What's wrong**: `slide-deck-patterns.md` defines Genealogy / Influence Tree as "a lineage of ideas, teachers, traditions" whose nodes are "named individuals or schools" and whose edges carry direction of influence. All three chains here are material → determining-act → consequence mappings with no descent and no influence. This is anti-pattern 6, "Wrong type for source". SL-P4 still passes because a taxonomy type IS named, which is that probe's stated failure condition.
- **Suggested Worker re-authoring**: re-type M14 and M42 as three-column comparison matrices (Material | Determining act | Consequence) — the content already has exactly that shape — and reserve "Genealogy chain" for transmission lineages (e.g. Qadi al-Nu'man → Hasan bin Noah → the compiler), which this chapter does contain.
- **Verified | Inferred**: VERIFIED

#### SL-P3: Deferring cells in comparison matrices (M16, M23)

- **File**: `slide-decks/ch06-deck-bodily-substances-and-disavowal.txt:216-220`, `:304-307`
- **Content (excerpt)**: "| Nifas, postpartum bleeding | … | Per the rulings below | Distinguished from istihadah as menstrual blood is |" and "| Fasts during a separation period | … | The distinction … has been mentioned with their differences, so one relies on the relevant text |"
- **What's wrong**: `slide-deck-patterns.md` comparison-matrix anti-pattern — "the matrix needs commitments". A cell reading "Per the rulings below" renders literally on the generated slide and points at nothing the slide contains. M16 matters disproportionately: it is the framing's number-one Visual Priority (framing L10), so NotebookLM is explicitly steered to render this exact matrix.
- **Suggested Worker re-authoring**: in M16, fill the nifas "Make-up of prayers" cell with the deck's own answer from M28 ("made up from the end of habit to the two-month mark") and the nifas blood-marker cell with "Thick like postpartum blood until habit ends". In M23, replace the pointer with the operative rule the deck already states at M16/M29.
- **Verified | Inferred**: VERIFIED

#### SL-A3: List-shaped closing moment (M43)

- **File**: `slide-decks/ch06-deck-bodily-substances-and-disavowal.txt:564-576`
- **Content (excerpt)**: "Parts, each a component the chapter has added to the word: - Lawful material - Truthful disclosure - Bodily discernment - Valid worship - Guarded speech - Marital restraint - Lineage clarity"
- **What's wrong**: seven bare labels with no spatial relation and one annotation — an annotated structure in name, a takeaway list in shape, and the exact pattern SL-A3 warns the close against. The arc still passes because M44 and M45 follow it and resolve structurally.
- **Suggested Worker re-authoring**: give the seven components the same ordering principle M1 used ("increasing nearness to the person") so the close visually rhymes with the open, or map them onto M13's rings.
- **Verified | Inferred**: VERIFIED

#### SL-A3: Templated per-movement cadence

- **File**: `slide-decks/ch06-deck-bodily-substances-and-disavowal.txt` (whole)
- **What's wrong**: six of the eight H2 movements run the same rotation (process flow → comparison matrix → … → contrast pair), and three movements close on a "Genealogy chain" binding device (L189, L468, L554). Variety by count is healthy (SL-A2 passes comfortably); variety by *position* is not, which flattens the pressure build SL-A3 looks for.
- **Suggested Worker re-authoring**: vary the entry type per movement; open the blood-states movement on M18's hierarchy rather than a contrast pair, so the deck's densest structural claim lands early in its own movement.
- **Verified | Inferred**: INFERRED (heuristic reading of cadence, not a spec threshold)

#### SL-A4: Per-book visual registry absent

- **File**: `content/Islamic/isaf-al-talib/slide-decks/` (no `_visual-registry.md`)
- **What's wrong**: `slide-deck-format.md` lists `_visual-registry.md` as the per-book companion, and this book has 13 deck pairs with verified recurring entities across them — "Qadi al-Nu'man" appears in 5 decks (ch02, ch06, ch09, ch21, ch22), "Pillars of Islam" in 4, "tayammum" in 5. SL-A4 returns n/a rather than fail because there is no prior convention to contradict, but cross-episode consistency for this series is currently unverifiable by construction.
- **Suggested Worker re-authoring**: create `slide-decks/_visual-registry.md` with entries for at least Qadi al-Nu'man, the *Pillars of Islam*, and the tayammum/ghusl substitution pair, each with a standing visual convention and the deck it was first defined in.
- **Verified | Inferred**: VERIFIED

#### SL-P8: Canonical Coverage input does not exist

- **File**: `content/Islamic/isaf-al-talib/_system/episode-drafts/` (only `.gitkeep`)
- **What's wrong**: this book sets `skip_podcast: true` (series-config L52), so no `04-discussion-spine.md` and no `[VISUAL CANDIDATE]` tags are ever produced, and no `01-slide-spine.md` exists either (`_system/slide-decks/ch06-…/` holds only `.validated`). SL-P8 therefore cannot fail and cannot meaningfully pass. The substitute concept-coverage check above was run in its place and passed, but the spec has no `skip_podcast` branch for Probe 8.
- **Suggested Worker action**: either author `01-slide-spine.md` per chapter so Coverage has a real target for `skip_podcast` books, or record a spec amendment making SL-P8 formally n/a when no episode lane exists.
- **Verified | Inferred**: VERIFIED

#### Format: three H2 movements added beyond the audio chapter's outline

- **File**: `slide-decks/ch06-deck-bodily-substances-and-disavowal.txt:102`, `:311`, `:383`
- **Content (excerpt)**: "## Commerce, Disclosure, and the Human Body", "## Nifas Durations and the Two-Month Precaution", "## Concealment, Recitation, and the Ruling on Speech"
- **What's wrong**: `slide-deck-format.md` says "H2 for movements (same as audio chapter — chapter outline is preserved)" and checklist item 3 asks whether H2 headings are preserved. All 5 audio H2s are present and in order; 3 additional H2s subdivide the two longest movements. The split points are sensible and likely improve NotebookLM's slide titling, so this is recorded as a spec-vs-practice divergence rather than a defect.
- **Suggested Worker action**: if deliberate, amend `slide-deck-format.md` to permit subdivision of long movements; otherwise merge back.
- **Verified | Inferred**: VERIFIED

---

## Slide-framing review

| Requirement | Result | Notes |
|---|---|---|
| All five required H2 sections | pass | Audience, Core Principle, Visual Priorities, Prohibited Patterns, Steering Phrases all present |
| Length 150–250 words | pass | 250 words, at the top of the band |
| Audience named concretely (never "general audience") | pass | "Asif's children, and adult students of Ismaili jurisprudence who know the audio, not the source" |
| Visual Priorities match structures present in the deck | pass | All 4 priorities resolve to real moments: the three-state matrix → M16 (L214, columns match the framing's list exactly); concentric rings → M13 (L177); banded two-month timeline → M28 (L364, "Period bands" line matches verbatim); patched-bone flow → M10 (L135) |
| Prohibited Patterns explicit | pass | 5 prohibitions incl. anti-bullet and anti-stock-photo |
| Steering Phrases 3–5, drawn from `slide-deck-steering.md` | partial | 3 of 4 are verbatim canon (Categories 1, 2, 3). The 4th, "Render every slide as black line art on white: tables, trees, contrast panels, process flows," is not in the canonical file |
| No em dashes (either file) | pass | Zero |
| No inline phonetic parens (R-PHONETICS-OUT) | pass | Zero |
| No prose paragraph >100 words in the deck | pass | Longest prose block is 83 words (L9); the eleven 100+ word blocks are all tables, flows and hierarchies |

---

## Learning-loop proposal

**Candidate steering phrase** for `slide-deck-steering.md` `## Category 7 — Candidates`, tagged `[PROPOSED — needs review]`:

> "Render every slide as black line art on white: tables, trees, contrast panels, process flows."

Grounds: used in 5 of this book's 13 framings (ch06, ch12, ch13, ch21, ch22), which clears the file's own 2-episode threshold for consideration. It is a rendering-medium constraint, distinct from every existing category, and it reinforces Category 2's diagram-type discipline by removing the stock-photo affordance entirely. Promotion still requires the Challenger to pass the decks that used it and an attribution of improvement against a control.

---

## Verified vs Inferred summary

- **VERIFIED — 9**: SL-P1/M6, SL-P1/M12, SL-P1/M36, SL-P4 genealogy misapplication, SL-P3 deferring cells, SL-A3 list-shaped close, SL-A4 registry absent, SL-P8 canonical input absent, format H2 divergence.
- **INFERRED — 2**: SL-A3 templated cadence; the SL-P8 substitute concept-coverage judgment on audio L33-35.

The Worker addresses both categories on iteration.

---

## Overall

**Pass 1**: fail (SL-P1, P0)
**Pass 2**: pass
**Bundle status**: iterate
**Verdict**: BLOCKED

The deck is strong on every structural axis the Challenger measures — 43 typed moments across 8 taxonomy types, no monoculture, no literal illustration, no untyped moment, full concept coverage, a real arc, and a framing whose Visual Priorities each resolve to a real structure. It is blocked on one probe: three moments (M6, M12, M36) restate a single audio sentence apiece, and SL-P1's threshold is ≥2. The remedy is small and local — absorb two of them into adjacent structures and either delete or re-type the third — so this is a fast iterate, not a rebuild. No bundle ships with an open Challenger failure.

## Ledger Hook

11 findings emitted to `_learning/findings.jsonl` this run (source: slide-deck-challenger, version 1.0) — 3 at P0, 8 at P2.
