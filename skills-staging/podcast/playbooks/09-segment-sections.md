# Stage 09 — Segment Into Episodes (Content-Driven)

**REQUIRED READING BEFORE THIS STAGE:** `journal/reference/notebooklm-best-practices.md`. Do not segment a source until that file has been read in the current run. The episode word-count band, the format selection, and the per-episode coherence rule all come from there.

**Purpose:** Re-segment the cleaned source into episodes optimized for NotebookLM Audio Overview, not into the source's native chapter or section structure. A book's chapters were designed for a reader. An Audio Overview episode is a different unit and needs a different shape.

## Core principle: content-driven, not structure-honoring

**The source's table of contents is a hint, not a constraint.** Do not produce one episode per source chapter unless that segmentation happens to satisfy all four content-driven criteria. The skill's deliverable is a series of evenly-paced, thematically coherent episodes — not a 1:1 mirror of the source structure.

Four criteria every episode must satisfy:

1. **Thematic coherence.** One sentence summarizes the episode. If a host can't answer "what is this episode about?" in one clause, the segmentation is wrong.
2. **Word-count band.** Each refined episode lands in the **1,800-2,800 word band** (Default Deep Dive sweet spot). Hard floor 1,200, hard ceiling 4,500. See `notebooklm-best-practices.md` §3.
3. **Approximate balance across the series.** Episode lengths should fall within ±30% of the series mean. A 600-word episode next to a 4,000-word episode is a defect.
4. **Forward-only narrative arc.** Episodes follow the source's logical flow even when they don't follow physical chapters. Each episode has a beginning, middle, and end the hosts can develop.

Source chapters that are too short get **merged with neighboring chapters of related theme**. Source chapters that are too long get **split at internal topic shifts**. This re-segmentation is the central work of Stage 09 — it is not optional.

## Input

- `WORK_DIR/_cleaned/normalized.md`
- `WORK_DIR/_metadata.yml` (content type, tone, target audience)
- `journal/reference/notebooklm-best-practices.md` (authoritative reference, MUST be read)

## Output

- `WORK_DIR/_segments/segments.yml` — the **redesigned** episode list. Each entry has: `episode_number`, `slug`, `title`, `theme` (one-sentence summary), `source_chapters` (the original source sections this episode covers), `start_line`/`end_line` ranges into normalized.md, `target_word_count_refined`, `notebooklm_format` (deep-dive / brief / critique / debate), `length_setting` (shorter / default / longer).
- `WORK_DIR/_segments/episode-NN-<slug>.raw.md` — extracted source content for the episode (concatenation if it spans multiple source chapters).
- `WORK_DIR/_segments/segmentation-rationale.md` — explanation of why the source structure was preserved, merged, or split for each episode.
- `WORK_DIR/chapter-segmentation-proposal.md` — only when the auto-design has low confidence and needs human review.

## Re-segmentation algorithm

### Step 1 — Inventory the source as it stands

Run the old structural detector (heading scan, chapter labels, numeric markers) to produce a **raw section inventory** with word counts. This is now an intermediate artifact, not the final segmentation. Write it to `_segments/raw-inventory.yml`.

### Step 2 — Compute series geometry

Given the source's total refined word count (estimated as 0.95-1.05× the source word count, since paraphrasing is approximately ratio-neutral):

```
total_words = source_word_count
target_episode_count = round(total_words / 2,300)   # mid of 1,800-2,800 band
target_episode_size = total_words / target_episode_count
```

For *Ayyuhal Walad* (16,464 source words): `round(16,464 / 2,300) = 7` episodes, target size ~2,350 words each.

### Step 3 — Group raw sections into thematic episodes

For each raw section in source order, decide:

- **Standalone episode** — if word count is within the band (1,800-2,800) and the section presents a coherent theme.
- **Merge with following sections** — if word count is under the floor (1,200) and adjacent sections share theme. Merge across the smallest reasonable thematic boundary, not greedily until the band is hit.
- **Split at internal topic shifts** — if word count exceeds the ceiling (4,500). Detect topic shifts via paragraph-level cues: explicit transition phrases ("Now I will turn to…", "Next, consider…"), shifts in pronoun or addressee, shifts in tense, the entry of a new named entity or proper noun.

Document every merge and split in `segmentation-rationale.md` with one sentence of reasoning per decision.

### Step 4 — Verify the four criteria

For each proposed episode, check:

1. Can you write its theme in one sentence? Write it down and put it in `segments.yml` as the `theme` field.
2. Is its target refined word count between 1,800 and 2,800? (Hard floor 1,200, hard ceiling 4,500.) If not, halt — return to Step 3.
3. Are all episodes within ±30% of the series mean? Compute the mean across the proposal; flag outliers.
4. Does it have a beginning, middle, end? If it's a flat list or a single argument with no development, consider merging or splitting.

### Step 5 — Assign NotebookLM format per episode

Default: **Deep Dive** with Length=Default. Use the other formats only when the content explicitly invites them:

- **The Brief** for a closing prayer, a single supplication, or a one-page summary — episodes well under the word floor where the brevity is the point.
- **The Critique** for an essay, design doc, or position piece that explicitly invites evaluation. Rare in spiritual/literary work.
- **The Debate** for a source presenting a claim with a real opposing view. Almost never used for monologic devotional content.

See `notebooklm-best-practices.md` §1.

### Step 6 — Confidence check

If the auto-design produces episodes inside the band, balanced, and thematically clean: proceed.

If any episode is outside the band even after merging/splitting, or the rationale is forced, write `chapter-segmentation-proposal.md` with the proposed design and the issues, and pause for the user.

## Content-type defaults (initial groupings, then refined by Steps 3-4)

These are starting hints for Step 1, not the final shape:

| Content type | Typical episode | Re-segmentation pressure |
|---|---|---|
| Book | One thematic chunk crossing chapter boundaries | High — book chapters are usually too short or too long |
| Memoir | One chapter or one tightly themed multi-chapter arc | Medium — memoir chapters often map cleanly but watch for short ones |
| Spiritual treatise | One coherent argument or one parable cluster | High — treatises like *Ayyuhal Walad* have many micro-sections that must be merged |
| Academic paper | One named section, sometimes merged | Low — academic sections are usually already band-sized |
| Article (multi-section) | One heading-delimited theme | Medium |
| Lecture series | One lecture, sometimes split | Medium — long lectures need splitting |
| Sermon | The entire sermon if under 2,800 words; split if longer | Low |
| Anthology | One piece, or grouped pieces by theme | High — short pieces must be bundled |
| Transcript | Topic-shift segments rebuilt | High — raw transcripts have no useful structure |

## Shortcut: one-file-per-section (revised)

If `00-source/` contains multiple files with sequential numbers, run Steps 1-6 anyway. The numeric ordering is preserved, but the file-per-episode default is **not** assumed — multiple files may merge into a single episode if their combined refined word count fits the band. The shortcut is just a hint about ordering, not a free pass to skip the re-segmentation work.

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
