# Stage 05 — Clean and Normalize

**Purpose:** Remove OCR artifacts, broken line breaks, duplicate passages, repeated headers/footers, and other scanning/transcription noise. Preserve all meaningful content.

## Input

- `WORK_DIR/_extracted/raw-text.md`

## Output

- `WORK_DIR/_cleaned/normalized.md` — the cleaned text, ready for foreign-term detection and segmentation.
- `WORK_DIR/_cleaned/cleaning-log.md` — what was removed, what was repaired, what was flagged for review.

## Operations performed

### 1. Encoding normalization
- Convert all text to UTF-8.
- Normalize Unicode (NFC form): combine decomposed characters.
- Replace smart quotes with straight quotes: `"` → `"`, `'` → `'`.
- Replace em-dash variants (`—`, `–`, `––`) with standard em-dash `—`.
- Replace non-breaking spaces with regular spaces.

### 2. Line break repair
- Join lines that end mid-sentence (no terminal punctuation, next line starts lowercase).
- Preserve line breaks at paragraph boundaries (blank line between).
- Preserve line breaks in poetry, scripture verses, or any block with consistent left-aligned structure.

### 3. Header / footer removal
- Detect repeated lines appearing across pages (page numbers, running titles, copyright notices).
- Threshold: line appears in ≥ 30% of detected page boundaries → mark as header/footer, remove.
- Exception: if the line contains substantive content (e.g., a recurring section title that's part of the structure), preserve it.

### 4. OCR artifact repair
- Common OCR errors handled with conservative rules:
  - `rn` → `m` only when not in a known word
  - `cl` → `d` only when not in a known word
  - Stray single characters between words → remove
  - Repeated punctuation like `.,` or `;:` → use only the first
- Preserve `[?word?]` flags from Stage 02 — do not auto-correct these.
- Preserve `<!-- OCR-LOW-CONFIDENCE -->` markers.

### 5. Duplicate passage detection
- Look for paragraphs that appear identically twice within a 100-paragraph window (a common scanning artifact).
- Threshold: ≥ 95% character-level match → flag as duplicate, keep first occurrence, remove second.
- Log every removed duplicate with both positions.

### 6. Page number stripping
- Remove lines containing only a number (1–4 digits).
- Remove lines matching `Page N` or `N of M` patterns.

### 7. Bracket cleanup
- OCR sometimes inserts spurious brackets like `[ ]` around clean words.
- Remove empty brackets `[]`, `( )`, `{ }`.
- Preserve brackets containing content (especially `[?word?]` flags and editorial insertions).

### 8. Quotation mark consistency
- Use straight double quotes `"` for all quoted speech.
- Use single quotes `'` only for nested quotes within doubles.
- Preserve original quotation marks in non-Latin script passages (those get handled at Stage 06).

### 9. Speaker label normalization (for transcripts/dialogues)
- Standardize to `Speaker Name: ` format.
- If multiple variants of the same speaker name appear (e.g., "Dr. Smith", "Dr Smith", "Smith"), pick the most complete form and use consistently.
- Preserve timestamps in HTML comments: `<!-- t=03:42 -->`.

### 10. Whitespace
- Collapse runs of 3+ blank lines to a single paragraph break (one blank line).
- Strip trailing whitespace from every line.
- Strip leading/trailing whitespace from the document.

## Operations explicitly NOT performed

- **No content removal beyond noise.** When in doubt, preserve. Flag for review in `cleaning-log.md`.
- **No grammar correction in source text.** The source's grammar is part of its voice.
- **No rephrasing.** This stage is mechanical cleanup only.
- **No tone changes.** Tone preservation begins here — do nothing that changes voice.
- **No script changes.** Non-Latin script stays as-is until Stage 06/07 processes it.
- **No translation.** Translation happens (via phonetic transcription + meaning gloss) only at Stages 06–08.

## cleaning-log.md format

```
# Cleaning Log — [Source Title]

Run: [YYYY-MM-DD HH:MM:SS]
Input: _extracted/raw-text.md ([N] characters, [N] words)
Output: _cleaned/normalized.md ([N] characters, [N] words)

## Operations summary

| Operation | Count |
|---|---|
| Encoding normalizations | [N] |
| Line breaks repaired | [N] |
| Headers/footers removed | [N] |
| OCR artifacts repaired | [N] |
| Duplicate passages removed | [N] |
| Page numbers stripped | [N] |
| Spurious brackets removed | [N] |
| Quotation marks normalized | [N] |
| Speaker labels normalized | [N] |

## Flagged for review

### [filename / location]
Issue: [description]
Original text: "[snippet]"
Action taken: [what was done or "preserved as-is"]
Recommended user action: [if any]

## Removed content

### Duplicates
- Paragraph at position [N] removed; identical to paragraph at position [M].
- ... (list every removal)

### Headers/footers
- Repeating string "[string]" appeared on [N] pages; removed.
- ...

## Preserved despite uncertainty
[List anything that looked like noise but was preserved because content was ambiguous]
```

## Failure modes

- Aggressive cleaning would change word count by more than 10% → pause and ask user to review the cleaning-log before proceeding.
- All-caps document (likely OCR failure) → flag, ask user to confirm before proceeding.

## What this stage does NOT do

- Does not segment into sections (Stage 09).
- Does not handle non-Latin script (Stage 06).
- Does not refine for audio readability (Stage 12).
