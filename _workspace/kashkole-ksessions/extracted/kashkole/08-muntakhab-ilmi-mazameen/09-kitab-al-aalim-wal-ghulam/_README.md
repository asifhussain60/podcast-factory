# کتاب العالم والغلام

Source-extractor bundle for the podcast pipeline.
After intake (`intake_book.py --from-bundle <this-dir>`), the
pipeline picks up at Phase 0b (or 0a-translate if source_language ≠ 'en').

| | |
|---|---|
| Source database | `KASHKOLE` |
| Source language | `ur` |
| Binder (shelf) | منتخب علمی مضامین (id 23, sort_key 5) |
| Chapter (this book) | id 87, sort_key 9 |
| Topics (sections) | 16 (14 with content) |
| Inline images | 13 |

## Layout

- `bundle.yml` — manifest read by intake (slug, source_language, sections list)
- `_system/source/kitab-al-aalim-wal-ghulam.html` — audit anchor (concatenated raw HTML; never modified)
- `_system/source/text/raw-extract.md` — Phase 0a output (clean markdown, source language)
- `_system/source/text/_extraction-notes.md` — skipped sections + caveats
- `_system/source/text/_provenance.json` — `podcast.ingest-source/v1` provenance record
- `_system/source/images/` — decoded PNG + per-image vision sidecar JSON

## Arabic markers

Every Arabic word, phrase, or quote in `raw-extract.md` is wrapped in `⟪ar:…⟫` (inline) or `⟪ar-quote:…⟫` (quoted passage). Phase 0c grep these markers to build the per-book phonetic index — do not strip them during refinement.
