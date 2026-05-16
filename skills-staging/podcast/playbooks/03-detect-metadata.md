# Stage 03 — Detect Metadata

**Purpose:** Identify the source's title, author/speaker, period, intended audience, and content type. These drive the opening template and the tradition detection.

## Input

- `WORK_DIR/_extracted/raw-text.md`

## Output

- `WORK_DIR/_metadata.yml` — structured metadata with confidence scores.
- `WORK_DIR/missing-metadata.md` — only created if any required field cannot be determined and user input is needed.

## Required fields

| Field | What to detect | If unknown |
|---|---|---|
| `title` | The work's title | Stop and ask user. Do not fabricate. |
| `author` (or `speaker` / `editor` / `translator`) | The primary creator | Stop and ask user. |
| `content_type` | book / article / paper / lecture / sermon / document / transcript / interview / anthology / memoir | Auto-classify; ask user only if confidence < 0.6. |
| `period` | Historical/intellectual era (e.g., "10th century Fatimid", "21st century American", "Classical Antiquity") | Best-effort inference; flag as "approximate" if uncertain. |
| `genre` | Theological / philosophical / scientific / literary / historical / biographical / instructional | Auto-classify; multi-label allowed. |
| `audience` | Original intended audience (e.g., "advanced theological students", "general lay readers", "professional peers") | Best-effort inference. |
| `tradition` | Detected at Stage 04 / tradition-detection step (not here) | N/A this stage |

## Detection logic

**Title:**
1. Look for explicit title in document frontmatter, title tag, or first all-caps or title-case line within first 50 lines.
2. Look for "Title:" or "Subject:" labels.
3. If multiple candidates, prefer the shortest non-trivial one.
4. If filename is informative and content has no internal title, use filename stem (slugified back to title-case).
5. If none of the above produces a confident result, write `WORK_DIR/missing-metadata.md` and pause.

**Author:**
1. Look for "by [Name]", "Author:", "Written by", "Translated by" patterns within first 100 lines.
2. Check filename for author hints (e.g., "smith-2024-paper.pdf").
3. For transcripts/interviews, identify speakers explicitly.
4. If unknown, pause — do not fabricate.

**Content type — classification rubric:**

| Signal | Type |
|---|---|
| Has explicit "Chapter N" markers and a table of contents | book or memoir |
| Has abstract, introduction, methods, results, discussion | academic paper |
| Has section headings but no chapter structure; under 10,000 words; single argument | article |
| Has timestamped speaker labels | transcript (interview if 2+ speakers; lecture if 1) |
| Has "In the name of God" style invocation, oral cadence, audience address | sermon |
| Has "Q:" / "A:" patterns or explicit interviewer turns | interview |
| Has multiple short titled pieces by different authors | anthology |
| Has narrative arc focused on a single life and uses first person | memoir |
| Lacks any of the above markers | document |

For ambiguous cases (two types are plausible), record both with confidence scores. If neither exceeds 0.6, write `WORK_DIR/missing-metadata.md` and ask the user.

**Period:**
- Look for explicit dates in frontmatter, copyright notice, or first/last pages.
- Look for figures named (cross-reference with known historical periods).
- Look for language register (early modern English, classical Arabic, modern academic prose).
- If uncertain, record range with confidence (e.g., "10th–11th century, confidence 0.7").

**Audience:**
- Lexicon density (technical terms per 1000 words) → academic vs. lay.
- Address style ("Brethren," "the reader," "students of...") → original audience signal.
- If the source explicitly names its audience, use that.

**Genre:**
- Multi-label allowed (a work can be "theological + philosophical").
- Use vocabulary distribution + named figures + structural patterns.

## metadata.yml format

```yaml
title:
  value: "[Detected Title]"
  confidence: 0.95
  source: "frontmatter"

author:
  value: "[Detected Author Name]"
  confidence: 0.90
  source: "title page line 3"

translator:
  value: "[Detected Translator Name]"
  confidence: 0.85
  source: "frontmatter"

content_type:
  value: "book"
  confidence: 0.92
  alternatives: []

period:
  value: "[Detected period, e.g., 'early 20th century, modernist']"
  confidence: 0.80
  source: "author date + content references"

genre:
  - value: "[primary-genre]"
    confidence: 0.95
  - value: "[secondary-genre]"
    confidence: 0.80

audience:
  value: "[Detected audience]"
  confidence: 0.75
  source: "vocabulary density + explicit address"
```

(Bracketed placeholders illustrate where detection results go. The skill stores nothing about any specific work — every metadata.yml is derived from the user's actual input.)

## Failure modes

- Title or author unknown → `WORK_DIR/missing-metadata.md` with specific questions, pause.
- Content type ambiguous (no candidate > 0.6) → ask user.
- Period genuinely unknown → record as "unknown" with confidence 0; proceed. Period is not strictly required for the pipeline.

## What this stage does NOT do

- Does not detect tradition — that's done at the tradition-detection step (between Stage 04 and 05).
- Does not segment into sections — that's Stage 09.
- Does not analyze tone — that's Stage 04.
