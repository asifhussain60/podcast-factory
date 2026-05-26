# True Sources Of Knowledge

| | |
|---|---|
| Source database | `KSESSIONS` |
| Group (shelf) | Master and the Disciple (id 12, sort_key 12) |
| Category (this book) | id 31, sort_key -20 |
| Sessions (sections) | 4 (4 with content) |
| Generated | 2026-05-25T19:07:19.646259+00:00 |

## Layout

- `_system/source/true-sources-of-knowledge.html` — audit anchor (concatenated raw HTML; never modified)
- `_system/source/text/raw-extract.md` — Phase 0a output (clean markdown)
- `_system/source/text/_extraction-notes.md` — skipped sections + caveats
- `_manifest.yml` — DB IDs, sort keys, slugs (for traceability)
- `chapters/` — Phase 0d will segment `raw-extract.md` into per-podcast-chapter files here
- `episodes/` — `build_episode_txt.py` will write the customize-prompt episode files here
- `turboscribe/` — human drops post-NotebookLM transcripts here
- `chapter-contracts/` — Phase 0e per-chapter contract YAMLs

## Arabic markers

Every Arabic word, phrase, or quote in `raw-extract.md` is wrapped in `⟪ar:…⟫` (inline)
or `⟪ar-quote:…⟫` (quoted passage). Phase 0c grep these markers to build the per-book
phonetic index — do not strip them during Phase 0b refinement.
