# Stage 08 — Build Pronunciation Projection

**Purpose:** Generate the per-source `03-pronunciation.md` file by projecting the master lexicon (with this run's new terms folded in) down to only those terms that appear in this source.

## Input

- `WORK_DIR/_lexicon/detected-terms.yml` (fully populated by Stages 06 and 07)
- `JOURNAL_DIR/reference/translations-glossary.md` (Podcast Pronunciation Lexicon section)

## Output

- `WORK_DIR/03-pronunciation.md` — per the canonical format in `templates/pronunciation-projection.md`.

## Steps

### 1. Load master lexicon

Parse the Podcast Pronunciation Lexicon section of `translations-glossary.md` into an in-memory map:

```
master_lexicon = {
  "Allaah" → { meaning: "God", language: "Arabic" },
  "Imam" → { meaning: "spiritual guide...", language: "Arabic" },
  ...
}
```

### 2. Build projection

For each entry in `detected-terms.yml`:
- If `lexicon_status: matched` → include in projection with the master-lexicon meaning.
- If `lexicon_status: new` AND the term has `proposed_phonetic` filled → include with the proposed values, marked as "(new — pending proposal review)".

### 3. Group by language family

Order in projection:
1. Arabic-origin terms (alphabetical by phonetic).
2. Other Semitic (Hebrew, Aramaic, Syriac).
3. Indo-European (Greek, Sanskrit, Persian-distinct, others).
4. East Asian.
5. Other.
6. Devotional phrases (separate section).

### 4. Add provenance column

Each entry shows where in the source the term first appears:
- "Section 1, line 14"
- For multi-file inputs, include filename: "ch-03.txt section 2, line 41".

### 5. Write to 03-pronunciation.md

Per the canonical format. Header includes generation date, source title, and pointer to master lexicon and proposals file.

### 6. Cross-link new terms to proposals

For any term marked "(new — pending proposal review)", include a footer hint:

```
> 9 of the terms above are new to the master lexicon. They are proposed
> for addition in `06-library-proposals.md` (Section C). To accept them
> into the master, run `/podcast apply <source-slug>`.
```

## Quality checks for this stage

Before writing, verify:
- Every term in the projection has a phonetic (no empty phonetic column).
- Every term has a meaning (no empty meaning).
- No term contains non-Latin script in the phonetic column (regex check).
- No duplicate phonetic spellings within the projection.
- Language-family sections are non-empty (don't write empty section headers).

If any check fails, stop and write `WORK_DIR/PRONUNCIATION-PROJECTION-ERROR.md`.

## What this stage does NOT do

- Does not modify the master lexicon — that's the apply step.
- Does not affect the source text — Stage 12 does substitutions.
- Does not write the proposals — that happens in the library-cross-pollination stage.

## Hand-editing rule

`03-pronunciation.md` is regenerated on every run. The skill writes a warning at the top of the file:

```
<!--
Generated file. Hand-edits will be overwritten on the next run.
To change a term's transcription or meaning, propose against the master
lexicon at `reference/translations-glossary.md` via the staging file
`06-library-proposals.md`, then run `/podcast apply <source-slug>`.
-->
```
