# نحج البلاغۃ کے خطبے

Source-extractor bundle for the podcast pipeline.
After intake (`intake_book.py --from-bundle <this-dir>`), the
pipeline picks up at Phase 0b (or 0a-translate if source_language ≠ 'en').

| | |
|---|---|
| Source database | `KASHKOLE` |
| Source language | `ur` |
| Binder (shelf) | علی ابن ابی طالب علیہ السلام (id 6, sort_key 15) |
| Chapter (this book) | id 16, sort_key 5 |
| Topics (sections) | 73 (0 with content) |
| Inline images | 0 |

## Layout

- `bundle.yml` — manifest read by intake (slug, source_language, sections list)
- `_system/source/x4767-x1260-ke-x6495.html` — audit anchor (concatenated raw HTML; never modified)
- `_system/source/text/raw-extract.md` — Phase 0a output (clean markdown, source language)
- `_system/source/text/_extraction-notes.md` — skipped sections + caveats
- `_system/source/text/_provenance.json` — `podcast.ingest-source/v1` provenance record
- `_system/source/images/` — decoded PNG + per-image vision sidecar JSON

## Arabic markers

Every Arabic word, phrase, or quote in `raw-extract.md` is wrapped in `⟪ar:…⟫` (inline) or `⟪ar-quote:…⟫` (quoted passage). Phase 0c grep these markers to build the per-book phonetic index — do not strip them during refinement.
