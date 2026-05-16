# Stage 09 — Segment Into Sections

**Purpose:** Divide the cleaned source into the sections that become individual podcast episodes. Three-stage approach: auto-detect, heuristic fallback, human review when uncertain.

## Input

- `WORK_DIR/_cleaned/normalized.md`
- `WORK_DIR/_metadata.yml` (content type drives segmentation strategy)

## Output

- `WORK_DIR/_segments/segments.yml` — ordered list of sections with title, start line, end line, word count.
- `WORK_DIR/_segments/section-NN-<slug>.md` — one extracted section per file (input to Stage 12 refinement).
- `WORK_DIR/chapter-segmentation-proposal.md` — only when Stage 3 (human review) is triggered.

## Content-type-aware strategy

The segmentation unit depends on content type from Stage 03:

| Content type | Section = |
|---|---|
| Book | Chapter |
| Memoir | Chapter |
| Academic paper | Named section (Introduction / Methods / Findings / Discussion) |
| Article (multi-section) | Heading-delimited section |
| Article (single piece) | One section = the entire article |
| Lecture series | Part / episode |
| Lecture (single) | Topic break, or one section = the entire lecture |
| Sermon | One section = the entire sermon |
| Document | One section per major heading; if no headings, one section = the entire document |
| Interview | Topic-shift segments |
| Anthology | One section per piece |
| Transcript | Topic-shift segments |

## Shortcut: one-file-per-section

Before running segmentation, check if `00-source/` contains multiple files named with sequential numbers (`ch-01.txt`, `ch-02.txt`, `chapter-1.md`, `part1.md`, etc.).

If yes:
- Treat each file as one section.
- Section number = numeric prefix.
- Section title = filename stem (cleaned), unless the file contains an explicit title line.
- Skip Stages 1–3 below. Write segments.yml and extract section files. Done.

## Stage 1 — Auto-detect explicit markers

Scan `normalized.md` for section markers, in this priority order:

1. **Markdown headings:** `# Heading`, `## Heading`. Use only one level at a time. If both `#` and `##` are present, use the level that produces 2+ matches.
2. **Explicit chapter labels:** `Chapter N`, `Chapter Roman-numeral`, `Ch. N`, `Chapter N — Title`, `Chapter N. Title`.
3. **Numbered headings:** `1.`, `2.`, `3.` at line start with surrounding blank lines.
4. **Roman numeral headings:** `I.`, `II.`, `III.` at line start.
5. **All-caps section titles:** lines of 3+ words in ALL CAPS with surrounding blank lines.
6. **Academic section names:** `Introduction`, `Methods`, `Results`, `Findings`, `Discussion`, `Conclusion`, `Abstract` as standalone lines.

A marker pattern qualifies if:
- It appears at least 2 times.
- The matches are reasonably regularly spaced (no chapter has > 80% of the words).
- The numbering is consistent (1, 2, 3 — not 1, 5, 17).

If a qualifying pattern is found, use it. Section title = the heading line (cleaned). Section content = everything between this marker and the next (or end of document).

**Confidence: high.** Stage 1 succeeds for most well-structured sources. No human review needed unless Stage 09a validation fails (see below).

## Stage 2 — Heuristic fallback

If Stage 1 fails (no qualifying marker pattern), try heuristic detection:

### 2a. Page-break artifacts

Look for form-feed characters `\f`, "Page N", or `\n\n\n\n` (4+ blank lines). These often delimit chapters in OCR'd or scanned material.

### 2b. File-boundary markers

If `_extracted/raw-text.md` preserved file boundary markers (`<!-- FILE: ch-01.txt -->`), treat each file's content as a section.

### 2c. Topic-shift detection

For lecture or interview transcripts where headings are absent:

- Split text into paragraphs.
- Compute embedding (Haiku-call) for each paragraph.
- Compute distance between consecutive paragraph embeddings.
- Mark paragraphs where distance exceeds the 90th percentile as candidate section boundaries.
- Cluster nearby boundaries (within 5 paragraphs) into single break points.
- Generate auto-titles from the first sentence of each section.

### 2d. Length-based fallback

If 2a–2c all fail and the document is long (> 3,000 words), propose breaking into ~1,500-word chunks at paragraph boundaries. Each chunk gets an auto-title from its first sentence. Mark all boundaries as low-confidence.

**Confidence: medium.** Stage 2 succeeds for transcripts and unstructured documents but produces lower-quality boundaries.

## Stage 3 — Human review

Triggered when:
- Stage 1 failed.
- Stage 2 produced any boundary with confidence < 0.7.
- The document is a single section but the user asked for chaptering.
- Stage 09a validation fails.

Write `WORK_DIR/chapter-segmentation-proposal.md`:

```markdown
# Chapter Segmentation — Proposal for Review

⚠ REVIEW BEFORE PROCEEDING ⚠

Auto-segmentation could not produce high-confidence boundaries for this
source. Below is the best proposal. To proceed:

1. Review each proposed section below.
2. Edit titles, boundaries, or split/merge sections as needed.
3. When the boundaries are correct, save this file and run:
   `/podcast continue <source-slug>`

The skill will not generate refined text or instructions until you sign off.

---

## Proposed sections

### Section 1
Auto-title: "[generated title]"
Start: line [N] ("[opening sentence]")
End: line [N]
Word count: [N]
Confidence: [N]
Reason for boundary: [heuristic that produced this]

### Section 2
...

---

## To accept all proposed sections as-is

Add this line at the top of the file:
SEGMENTATION_DECISION: accept_all

## To override with custom boundaries

Add this YAML at the top of the file:

```yaml
SEGMENTATION_DECISION: custom
custom_sections:
  - title: "Your title"
    start_line: 1
    end_line: 487
  - title: "Your next title"
    start_line: 488
    end_line: 1042
```

Save and re-run.
```

The skill pauses until the user sets `SEGMENTATION_DECISION`.

## Stage 09a — Validation after segmentation

Once segmentation is determined (any of the three stages or the shortcut), validate:

1. **Coverage:** every line of the source is in exactly one section. No gaps, no overlaps.
2. **Minimum length:** no section is shorter than 100 words. If one is, propose merging with neighbor and ask the user.
3. **Maximum length:** no section exceeds 30,000 words. If one does, propose splitting and ask the user.
4. **Ordering:** section numbers are consecutive starting from 1.
5. **Titles:** every section has a non-empty title.

If any validation fails, trigger Stage 3 (human review).

## Extract section files

For each validated section, write `WORK_DIR/_segments/section-NN-<slug>.md`:

```markdown
---
section_number: N
section_title: "[Title]"
source: "[Source Title]"
start_line: [N]
end_line: [N]
word_count: [N]
---

[Section content, cleaned, ready for Stage 10–12 processing]
```

These files are the inputs to Stages 10 (enrichment), 11 (analogies), and 12 (audio refinement).

## segments.yml format

```yaml
source: "[Source Title]"
total_sections: [N]
total_words: [N]
segmentation_method: "stage1_markdown_headings" | "stage1_chapter_labels" | "stage2_topic_shift" | "shortcut_one_file_per_section" | "human_review"

sections:
  - number: 1
    title: "Scholar and Seeker"
    slug: "scholar-and-seeker"
    start_line: 12
    end_line: 487
    word_count: 1432
    file: "section-01-scholar-and-seeker.md"
  - number: 2
    title: "Oath and Cosmic Origins"
    slug: "oath-and-cosmic-origins"
    start_line: 488
    end_line: 1041
    word_count: 1607
    file: "section-02-oath-and-cosmic-origins.md"
```

## What this stage does NOT do

- Does not refine text (Stage 12).
- Does not generate instructions (Stage 13).
- Does not enrich with context (Stage 10) or analogies (Stage 11).
