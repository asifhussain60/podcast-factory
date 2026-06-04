# Slide Deck Challenger Report

**Book:** the-master-and-the-disciple
**Chapter:** ch05-father-revealed-and-the-faces-of-seeking
**Run:** 2026-05-26 (challenger v1.0, full deck-authoring path)
**Scope:** per-chapter (deck source + framing both reviewed)
**Iterations:** 1

**Bundle status:** ship
**Verdict:** SHIP-READY

---

## Inputs reviewed

- Deck source: `slide-decks/ch05-deck-father-revealed-and-the-faces-of-seeking.txt` (6,056 words, 19 H2 slides)
- Slide-framing: `slide-decks/ch05-framing-father-revealed-and-the-faces-of-seeking.md` (1,465 words)
- Audio chapter: `chapters/ch05-father-revealed-and-the-faces-of-seeking.txt`
- Episode framing: `_system/episode-drafts/EP05-father-revealed-and-the-faces-of-seeking/00-framing.md`
- Prior Probe-7 finding: `_system/slide-challenger-reports/ch05-report.md` (overwritten by this report)

## Hard-rule verification (slide-deck-format.md, slide-deck-patterns.md)

| Hard rule | Status | Evidence |
|---|---|---|
| Zero em-dashes (U+2014) | ✓ | `grep` count = 0 |
| Zero en-dashes (U+2013) | ✓ | `grep` count = 0 |
| Zero Arabic-script tokens | ✓ | regex sweep over U+0600–U+06FF + Arabic Supplement = 0 hits |
| No inline phonetic parens | ✓ | regex sweep for `(ABC-DEF)` patterns = 0 hits |
| Italicized phonetic Arabic terms only | ✓ | spot-checked *taqiyya*, *zahir*, *batin*, *al-ʿabd al-ṣāliḥ* — all italic, no phonetic guides |
| No surah names in Arabic | ✓ | references read as "chapter on the Cow," "chapter on the Family of Imran," "chapter on Light" |
| Every slide cites chapter prose lines | ✓ | 19 `Anchor: chapter prose, lines N through M` lines, one per slide |
| All cells filled with commitments not hedges | ✓ | cells inspected on each matrix/pair; no "TBD," "various," empty cells |
| Diagram type named on every slide | ✓ | comparison matrix ×6, contrast pair ×6, hierarchy tree ×2, annotated structure ×4, process flow ×1, plus the carry-forward two-row matrix on slide 1 (type-named in framing) |

## Slide-by-slide diagram-type ledger

| # | Slide title (H2) | Diagram type | Source anchor |
|---|---|---|---|
| 1 | Where this chapter picks up | two-row carry-forward matrix | lines 5–7 |
| 2 | The two strands of gratitude | contrast pair | lines 15–21 |
| 3 | The boy's counter-bind on the father | contrast pair (binary trap) | lines 23–35 |
| 4 | The community's three reasons for hesitation | contrast pair | lines 49–53 |
| 5 | The figure of the breach | comparison matrix | lines 57–61 |
| 6 | Abu Malik's three states of the new community | hierarchy tree | lines 63–67 |
| 7 | The tyrants of the previous nations | annotated structure | lines 75–76 |
| 8 | The door of seeking and the sound heart | comparison matrix | lines 79–91 |
| 9 | Reverence before the statement | contrast pair | lines 97–103 |
| 10 | Only this day | process flow | lines 107–111 |
| 11 | The three faces of seeking | comparison matrix | lines 145–157 |
| 12 | Money-seeking and knowledge-seeking | comparison matrix | lines 151–155 |
| 13 | Knowledge by report; knowledge by direct sight | contrast pair | lines 159–167 |
| 14 | The transpositions at the gate | annotated structure | lines 113–123 |
| 15 | Essence-traders and the jewel-or-glass | contrast pair | lines 181–191 |
| 16 | The Maqrub case | comparison matrix | lines 209–217 |
| 17 | What is religion? Salih's collapse argument | hierarchy tree | lines 221–231 |
| 18 | Religion as the unbroken cause | annotated structure | lines 233–249 |
| 19 | The chapter's closing seam | single hanging question (annotated structure) | lines 251–257 |

**Type distribution:** comparison matrix 6 (32%), contrast pair 6 (32%), annotated structure 4 (21%), hierarchy tree 2 (10%), process flow 1 (5%), carry-forward matrix 1 (5%). Five distinct primary types over 19 slides.

---

## Pass 1 — Per-structure probes

| Probe | Result | Slides flagged | Notes |
|---|---|---|---|
| SL-P1 Restatement | pass | — | The two slides flagged as residual risk by the author (slide 1 "where this chapter picks up" and slide 19 "closing seam") both do structural work prose cannot. Slide 1 is a two-row carry-forward matrix that spatializes the seam between chapter four's close and chapter five's opening — a single sentence in audio could state the seam exists, but only a slide can show the dual-axis transformation (chain-naming vs. world-naming) as parallel rows. Slide 19 is the verbatim source question posed as a single hanging frame; the framing explicitly forbids summary and the slide carries the question as visual punctuation, doing what a closing audio line cannot (the reader holds the question on the page after audio ends). |
| SL-P2 Literal Illustration | pass | — | No "image of," "photo of," "depiction of" anywhere. Every slide commits to structure. The transpositions slide (14) explicitly refuses to render divine names as a hierarchy, honoring the chapter's "whiff of perfume" discipline by structuring on the zahir/batin axes only — that is structural restraint, not literal illustration. |
| SL-P3 Structure-vs-Description | pass | — | Each slide names its axes/columns/rows and fills cells with concrete commitments. Slide 5 (breach): 3 domains × {repairability, stake to bearer, cost of haste in judgment}. Slide 11 (three faces): 3 faces × {knowledge state, awareness of lack, action, object pursued}. Slide 12 (money↔knowledge parallel): 3 modes × {money-seeking, knowledge-seeking}. Slide 17 (collapse argument): root → enumeration → conclusion → premises → silence. No slide describes what a diagram would look like; all commit. |
| SL-P4 Diagram-Type Discipline | pass | — | 19/19 slides name a type from the taxonomy. Zero TBDs, zero "various," zero blanks. |
| SL-P5 Diversity | pass | — | Top types tied at 6/19 (32%) — comparison matrix and contrast pair. Both contrast pair and comparison matrix present; a clean 2x2 is absent but the framing explicitly forbids one ("No 2x2 on the boy's counter-bind. The bind is binary; rendering it as four quadrants would invent two cells the chapter does not deliver."). The chapter's affinity-matrix prediction (theological argument + comparative + polemic) calls for contrast pair, comparison matrix, hierarchy tree, annotated structure — all four present and well-distributed. |
| SL-P6 Audio Redundancy | pass | — | Audio chapter is ~6,500 words of dialogue and theological commentary; deck restructures the chapter's *explicit* taxonomies and contrast structures into visual form. Cells contain concrete attribute-by-attribute commitments (e.g., the breach matrix's "repairable; harm easy to remedy and cure near at hand" cell is the chapter's claim *spatialized*, not its prose *bulletified*). The author's flagged residual risk on slides 1 and 19 does not materialize — slide 1 carries dual-axis content the audio enumerates only in prose, and slide 19 carries the question as a held visual object that the audio's ending-in-silence cannot. |
| SL-P7 Justified Skip | n/a | — | Full deck-authoring path; skip not applicable. |
| SL-P8 Coverage | pass | — | No `04-discussion-spine.md` exists for EP05 (verified absent; F30 retirement per prior report). Coverage is checked against the prior finding-only report's 9 candidate structures: candidates 1, 2, 3, 4, 5, 7, 8, 9 all present (slides 11, 12, 6, 2, 3, 14, 5, 18 respectively). Candidate 6 (Abu Malik's three credentials + "heel of the inks") explicitly dropped by the author as decorative — that judgment is acceptable; the credentials annotation would have been a thin annotated-structure with limited deck value next to the heavier structural moments. The framing's `## Visual Priorities` enumerates 19 slides; the deck delivers 19 slides; 1:1 alignment. |

## Pass 2 — Architectural pass

| Check | Result | Notes |
|---|---|---|
| SL-A1 Visual Memory Test | pass | Distinctive shapes throughout: the boy's binary-trap contrast (slide 3) with both columns vindicating the boy; the breach 3×4 matrix (slide 5) with religion as the irreparable apex; the three-faces taxonomy (slide 11) with the first face naming students (not knowledge) as the object pursued; the money↔knowledge parallel (slide 12) as a 2-domain × 3-mode register-shift; the transpositions (slide 14) on the explicit zahir/batin axes; the religion-as-cause (slide 18) as a single whole with named figures anchored to revelation; the Only-this-day process flow (slide 10) as a 3→2→1 collapse. Zero slides are "summary slide" or "definition shown as text." Memory test: well below the 30% forgettable threshold. |
| SL-A2 Variety | pass | Top type 32% (under the 60% cap for 10+ decks). Five distinct types meaningfully represented. No near-monoculture. |
| SL-A3 Arc | pass | Opening (slide 1) establishes the seam from chapter four — continuity anchor. Build phase (slides 2–10) develops the father-resolution → community-arrival → breach-doctrine → three-states → tyrants → seeking-discipline → reverence → urgency. Central pivot (slides 11–13) is the three-faces taxonomy plus its money↔knowledge mirror plus its report-vs-sight sub-pair — the deck's deepest structural moment. Post-pivot phase (slides 14–17) carries the gate-transpositions → essence-test → Maqrub case → what-is-religion collapse (the zero-point). Resolution (slide 18) holds religion-as-cause as the positive doctrine; closing (slide 19) holds the question open. The arc has shape: opening seam → build → taxonomic pivot → indictment → zero point → positive doctrine → unresolved question. The chapter's narrative discipline is honored. |
| SL-A4 Cross-Episode Visual Consistency | n/a | This is the book's sole authored deck (the other four chapters are correctly skipped via verified justified-skips per the prior reports). `slide-decks/_visual-registry.md` does not exist for this book. Per the spec, SL-A4 returns n/a when no registry entries exist. Not penalized — internal arc and variety hold up independently. |

---

## Failures requiring Worker iteration

None.

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

None.

### P2 (advisory)

None.

---

## Author's claims, verified

| Claim | Verified? | Evidence |
|---|---|---|
| Zero em-dashes | ✓ | grep |
| No inline phonetic parens | ✓ | regex sweep |
| All slides have chapter-prose line citations | ✓ | 19/19 `Anchor:` lines |
| All cells filled with commitments not hedges | ✓ | manual inspection across all matrices/pairs |
| Closing seam is a single hanging question, NOT a summary | ✓ | slide 19 frames the verbatim source question (`how is it described?`) and ends; no takeaways, no thanks; framing's prohibited patterns honored |
| Probe-5 residual risk on slides 1 and 19 cleared | ✓ | slide 1 is a dual-axis carry-forward matrix doing work prose cannot; slide 19 is visual punctuation holding the question after audio ends |

---

## Verified vs Inferred

- **VERIFIED:** the 19 H2 slide count; the 19 anchor citations; the zero em-dashes / en-dashes / Arabic-script tokens / inline phonetic parens; the diagram-type distribution; the audio chapter's structural taxonomies and the deck's 1:1 coverage of them; the framing's enumeration of 19 priorities and the deck's 19 slides; the absence of a discussion spine (so Coverage is checked against the prior finding's 9 candidates and the framing's priorities, both satisfied); the absence of `_visual-registry.md` (so SL-A4 is n/a).
- **INFERRED:** the "visual memory test" judgment that each slide will survive recall — based on structural distinctiveness, not on actual recall testing; the arc judgment that the deck builds coherent narrative pressure from open to close — based on slide titles and content shape, not on an external reader's experience.

---

## Surface to operator

The deck clears all 8 Pass-1 probes and all 4 Pass-2 architectural checks. The author's flagged residual concern on slides 1 and 19 does not materialize: slide 1 spatializes the seam in a way prose cannot (dual-axis carry-forward), and slide 19 holds the verbatim source question as visual punctuation after audio ends — explicitly NOT a summary or takeaway slide, which the framing's prohibited-patterns section forbids. The book's single-deck status is structurally fine; cross-episode consistency is n/a in the absence of a registry, and the chapter's internal arc and variety carry the corpus-level slide-deck mandate cleanly. SHIP-READY.
