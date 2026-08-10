# Rearticulation audit — "The Freedom to Disagree" (chapter key: `the freedom to disagree`)

**Date:** 2026-08-10
**Verdict: KEPT** (not reverted). Sidecar entry `saved_at: 2026-08-10T15:43:34.016393+00:00`, `base_fingerprint: 441e14354033c9f5`.

## Why this attempt succeeded where the prior two did not

The two earlier failures were both the abridgement gate firing on a 52% length drop. The
root cause was in the source, not the rewrite: `book/book.md` carried the origin story of
*al-Mahsul*, *al-Islah*, *al-Nusra*, and *al-Riyad* TWICE back to back — a rough six-paragraph
telling followed by the fuller, properly closed nineteen-paragraph telling. Any faithful
rewrite of the deduplicated content necessarily halved the paragraph count relative to the
duplicated source, which the gate correctly read as suspicious.

Before this run, the duplicate six-paragraph telling (~821 words) had already been removed
by hand, leaving only the fuller telling. This run's engine report shows the length delta is
now unremarkable: `base_words: 811`, `output_words: 769` (5% tighter), `status: "adapted"`,
`gates: []`, `warnings: []`. No abridgement flag fired.

## Baseline recorded before the run

- English-prose word count (Arabic block-quote lines excluded): 779 words (811 by the
  engine's own tokenizer).
- 7 Arabic block-quoted name/title citations, each followed by its English rendering.
- No enumerations, no dialogue/speech tags (this chapter is expository narration, not
  reported speech).
- Signature images tracked for survival: (1) disagreement as something that "settles with
  no single party... comes to rest in no single place"; (2) disputes that "spilled beyond"
  oral discussion "into long treatises... across the pages of books and pamphlets";
  (3) intellectual freedom as "a release from the constraints that... bind... to no
  irregularity and no departure from the old inherited plan"; (4) al-Sijistani attacking
  al-Razi "without mercy"; (5) the closing contrast of two books "lost" against two "still
  preserved."

## Judgment against the Book Articulation Standard

- **REQ-BA-010/020 (lucid modern English).** Calqued constructions are gone — "How useful it
  is, then, for the researcher..." became "Any researcher... will find it worthwhile...";
  "It is very strange to me that..." became "What strikes me as remarkable is..." The prose
  now reads as considered English narration rather than a translated Arabic period-phrase
  chain.
- **REQ-BA-040 (quotations intact).** All 7 Arabic block-quote citations are byte-identical
  to the pre-run text, in the same order, each still followed by its correct English
  identification (e.g. `محمد بن احمد النسفي` → "Muhammad ibn Ahmad al-Nasafi"; `قَانُونُ
  الدَّعْوَةِ الْهَادِيَةِ` → "Law of the Guiding Mission"). None was paraphrased away or
  merged into surrounding prose.
- **REQ-BA-050 (signature images survive).** All five tracked images are still images after
  the rewrite: the "settling with no single party... coming to rest in no single place"
  figure survives verbatim; "spilled beyond the oral discussions... growing into long
  treatises that spread across the pages of books and pamphlets" survives near-verbatim;
  the "release from the constraints that hold conservative societies in check, binding them
  to the inherited order" figure survives with tightened but still concrete phrasing;
  "attacked Abu Hatim al-Razi without mercy" is untouched; the closing "lost" / "still
  preserved" contrast is untouched. None was flattened into an abstraction.
- **REQ-BA-070 (terminology consistency).** *al-Mahsul*, *al-Islah*, *al-Nusra*, *al-Riyad*
  are rendered exactly as elsewhere in the book, italicized as the book already italicizes
  them. The English glosses "(The Correction)" / "(The Defense)" attached to *al-Islah* /
  *al-Nusra* were already present in the pre-run text (not introduced by this run) — they
  do differ from "The Reform" / "The Support" used later in the book's translated primary
  text (lines 187/189), but that inconsistency predates this rearticulation and is outside
  this run's scope to fix.
- **REQ-BA-100 (dialogue paragraphing).** Not applicable — the chapter is expository
  narration with embedded name/title citations, not reported speech; no speech turns to
  check.

## What's still open

- The "Correction/Defense" vs. "Reform/Support" gloss mismatch for *al-Islah*/*al-Nusra*
  (chapter 1 vs. the book's later translated primary text) is a pre-existing terminology
  drift, not something this rearticulation introduced or was scoped to fix. Worth a
  dedicated terminology-consistency pass across the whole book if Asif wants it resolved.
