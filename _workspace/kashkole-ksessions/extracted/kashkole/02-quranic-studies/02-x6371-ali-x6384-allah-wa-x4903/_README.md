# سلام علی رسول اللہ و آلہ

Source-extractor bundle for the podcast pipeline.
After intake (`intake_book.py --from-bundle <this-dir>`), the
pipeline picks up at Phase 0b (or 0a-translate if source_language ≠ 'en').

| | |
|---|---|
| Source database | `KASHKOLE` |
| Source language | `ur` |
| Binder (shelf) | Quranic Studies (id 34, sort_key 1) |
| Chapter (this book) | id 156, sort_key 2 |
| Topics (sections) | 5 (5 with content) |
| Inline images | 1 |

## Layout

- `bundle.yml` — manifest read by intake (slug, source_language, sections list)
- `_system/source/x6371-ali-x6384-allah-wa-x4903.html` — audit anchor (concatenated raw HTML; never modified)
- `_system/source/text/raw-extract.md` — Phase 0a output (clean markdown, source language)
- `_system/source/text/_extraction-notes.md` — skipped sections + caveats
- `_system/source/text/_provenance.json` — `podcast.ingest-source/v1` provenance record
- `_system/source/images/` — decoded PNG + per-image vision sidecar JSON

## Arabic markers

Every Arabic word, phrase, or quote in `raw-extract.md` is wrapped in `⟪ar:…⟫` (inline) or `⟪ar-quote:…⟫` (quoted passage). Phase 0c grep these markers to build the per-book phonetic index — do not strip them during refinement.
