# Stage 14 — Quality Gates

**Purpose:** Five hard automated gates. All must pass before the skill writes the export ZIP, before the editorial notes are finalized, and before any apply step can run. If any gate fails, the skill reports which gate failed, what triggered it, and what to fix.

## Input

All artifacts produced by Stages 1–13:
- `WORK_DIR/01-refined/section-NN-<slug>.md` (refined section files)
- `WORK_DIR/02-instructions/podcast-instructions.md` (instruction file)
- `WORK_DIR/03-pronunciation.md` (pronunciation guide)
- `WORK_DIR/_editorial-notes-draft.md` (draft editorial notes from Stages 10–11)
- `WORK_DIR/_segments/segments.yml` (section ordering)
- `WORK_DIR/00-source/` (original)

## Output

- `WORK_DIR/_quality-gates-report.md` — per-gate pass/fail with details.
- If all gates pass → unlocks Stage 15 (export).
- If any gate fails → halts pipeline.

## The five gates

### Gate 1 — No non-Latin script in podcast-ready output

**Check:** Run a regex scan for any character in non-Latin Unicode blocks across:
- Every file in `01-refined/`
- `02-instructions/podcast-instructions.md`

**Allowed exceptions:** 
- ASCII characters
- Latin-1 Supplement (for diacritics in names like "Tomás" or "Müller" used in transliteration)
- General punctuation
- Currency symbols if the source uses them

**Pass:** Zero matches outside the allowed exceptions.
**Fail:** Report file, line number, and the offending character/term. Likely cause: Stage 12 missed a substitution.

### Gate 2 — No bracketed commentary headings

**Check:** Regex scan refined output for bracketed markers that indicate study-note style:

Forbidden patterns in `01-refined/` files:
- `\[Modern Example\]`
- `\[Note\]`
- `\[Commentary\]`
- `\[Explanation\]`
- `\[Background\]`
- `\[Integrated Clarification\]`
- `\[Narrator'?s? Note\]`
- `\[Editorial\]`
- `\[Aside\]`
- `\[Context\]`

**Allowed brackets:**
- `[?word?]` from OCR/transcription confidence flags (Stage 02) — these should have been resolved by Stage 05 but may persist as flags for user review.

**Pass:** Zero forbidden patterns in `01-refined/` content body.
**Fail:** Report file, line, and matched pattern. Likely cause: Stage 10 or 11 used a labeled bridge instead of a woven one.

### Gate 2b — No frontmatter or metadata block in refined files

**Check:** Per Stage 12 Hard Rule, refined section files contain **only** the `# Section [N] — [Title]` heading and the refined body. Scan each file in `01-refined/` for:

- Leading `---` block (YAML frontmatter).
- HTML comments containing audit fields (`<!-- word_count_refined: ... -->`).
- Any block that looks like per-file metadata (lines matching `section_number:`, `tone_preserved:`, `phonetic_substitutions:`, `paraphrasing_notes:`, etc.).

**Pass:** Each refined file starts with `# Section` heading. No YAML, no comments, no metadata block anywhere in the file.
**Fail:** Report file and offending content. Likely cause: Stage 12 emitted metadata into the deliverable instead of routing it to `_meta/sections-metadata.yml`.

### Gate 3 — Citation provenance

**Check:** For every external quote or attributed claim in `01-refined/` files, verify there is a matching entry in `_editorial-notes-draft.md` that:
- Cites the source.
- Cites the section in the source from which the enrichment came.
- Names the translator (if applicable).
- The source is listed in the active tradition's `allowed_enrichment_sources`.

**Detection of external quotes:**
- Look for quotation marks containing material that is attributed to a figure not in the section's original text (cross-reference with `00-source/` content for the section).
- Look for parenthetical attributions like "(Nasir-i Khusraw, _Wajh-i Din_)".

**Pass:** Every detected external attribution has a corresponding editorial note with verifiable source.
**Fail:** Report the quote, the attribution, and what's missing from editorial notes. Likely cause: Stage 10 added enrichment without recording it.

### Gate 4 — Section order preserved

**Check:** Compare the section order in `_segments/segments.yml` with the order in `02-instructions/podcast-instructions.md`. The Nth section block in the instructions file must correspond to the Nth section in segments.yml.

Also check: section numbers in `01-refined/` filenames match the section numbers in `_segments/segments.yml`.

**Pass:** Identical order across all artifacts.
**Fail:** Report which file is out of order. Likely cause: Stage 13 reordered.

### Gate 5 — Word count discipline

**Check:** For each section, compare refined word count vs. source word count:

```
ratio = refined_section_word_count / source_section_word_count
```

**Pass:** Every section has `0.70 ≤ ratio ≤ 1.40`.
**Fail:** Report section, source words, refined words, ratio. Diagnose:
- Ratio < 0.70 → Stage 12 over-summarized; rerun Stage 12 with less compression.
- Ratio > 1.40 → Stage 10 + 11 over-enriched; reduce enrichment density and rerun.

## quality-gates-report.md format

```markdown
# Quality Gates Report — [Source Title]

Run: [YYYY-MM-DD HH:MM:SS]
Source: [Source Title] by [Author]
Sections: [N]

## Gate results

| Gate | Status | Notes |
|---|---|---|
| 1: No non-Latin script | PASS | 0 violations across 6 files |
| 2: No bracketed commentary | PASS | 0 forbidden patterns |
| 3: Citation provenance | PASS | 12 external citations verified |
| 4: Section order preserved | PASS | All artifacts consistent |
| 5: Word count discipline | PASS | All sections within 70-140% (range: 92-118%) |

## Overall: PASS

Pipeline may proceed to Stage 15 (export).

---

## (If any fail, replace "Overall: PASS" with:)

## Overall: FAIL

Halting pipeline. Address the following before re-running:

### Gate [N] failure details
[Details of what failed, where, and remediation guidance]
```

## Failure handling

When a gate fails:

1. Write the report to `_quality-gates-report.md`.
2. Do not write `05-export.zip`.
3. Do not write `06-library-proposals.md` for library cross-pollination (those proposals were drafted earlier but should not be exposed until gates pass — they remain as `_draft-library-proposals.md` until then).
4. Print a clear summary to the user with the gate that failed and the remediation step.
5. The user can re-run the failing stage(s) and then re-run gates without re-running the whole pipeline.

## Gate independence

Gates are independent and run in parallel where possible. A failure in Gate 1 does not skip Gates 2–5 — all gates run, all results are reported. This gives the user complete diagnostic information in one pass.

## What this stage does NOT do

- Does not modify any output files.
- Does not run the apply step.
- Does not generate proposals — only validates what was generated.
