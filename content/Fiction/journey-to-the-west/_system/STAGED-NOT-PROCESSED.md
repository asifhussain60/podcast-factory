# Journey to the West (西遊記) — STAGED, NOT PROCESSED

Staged 2026-06-04 as the first occupant of the **Fiction** bucket.

- **Source:** `_system/source/journey-to-the-west-zh.gutenberg.html` — Project
  Gutenberg eBook #23962, 《西遊記》by Wu Cheng'en, **original Classical Chinese**.
- **Status:** `draft`. The pipeline has **not** been run on this book.

## Before this can be processed (separate future effort)

1. **Fiction end-to-end wiring** — Fiction is a first-class content type in the
   registry (`_rules.CONTENT_TYPE_REGISTRY`) with a literary "narrative" voice and
   phonetics/enrichment switched off, but its 0d chapter-design + challenger
   behaviour are not yet built.
2. **Chinese → English translation path** — the pipeline's ingest is built for
   Arabic→English; this book is the first `source_language: zh`.
3. **Chapter scope** — the novel is 100 chapters. Pick a defined slice (e.g. the
   opening Monkey-King arc) rather than the whole work.

Do **not** `orchestrate_book.py --resume journey-to-the-west` until the above land.
