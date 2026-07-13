# Book Pipeline v2 — Phase 0 spike findings

Read-only investigation that de-risks the two architectural moves before any
producer/consumer code lands. Recorded here so later phases (esp. Phase 4, the
Astro Book Composer) reuse the established mechanism instead of inventing one.

## Finding 1 — the Astro reader is NOT read-only

The Podcast Factory Astro Site (`plan-dashboard/`) is a full SSR Node server, not
a static reader:

- `plan-dashboard/astro.config.mjs`: `output: 'server'` + `@astrojs/node`
  (`mode: 'standalone'`). Dev server on `localhost:4322`.
- ~50 API routes under `plan-dashboard/src/pages/api/`; ~10 already **write files
  to disk on POST**, each with `export const prerender = false`.
- Content is read at request time via `node:fs` through the canonical resolver
  `plan-dashboard/src/lib/content-paths.ts` (TS mirror of `scripts/podcast/_paths.py`).

## Finding 2 — the write-back template to reuse (Phase 4)

`plan-dashboard/src/pages/api/studio/save-stage.ts` is the closest precedent for
"Book Composer writes `visual-layout.json`":

- `export const prerender = false`
- `SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/` slug validation
- `findContentDirSync(slug)` to resolve the book dir (mirrors the read path)
- `.bak` backup before overwrite, then `writeFileSync`
- side-file JSON write under `_system/` via `mkdirSync({recursive:true})` +
  `writeFileSync(JSON.stringify(...))`
- shared `apiOk` / `apiError` / `apiServerError` helpers from
  `src/lib/api-responses.ts`

Editorial convention (`src/lib/reader/editorial.ts`): **TS writes JSON, Python
reads the same JSON** — deliberately JSON (not YAML) so the orchestrator's stdlib
`json` consumes it. `book/visual-layout.json` MUST follow this so both the Astro
Composer (writer) and the Python renderer (reader) share one contract file.

## Finding 3 — where the Composer view + endpoint live (Phase 4)

- Book reader today: `plan-dashboard/src/pages/studio/[slug]/book.astro` →
  `loadBook(slug)` in `src/lib/reader/book.ts` (reads `book/book.md`, builds TOC
  from `##` headings).
- New sibling view: `plan-dashboard/src/pages/studio/[slug]/compose.astro`.
- New write endpoint: `plan-dashboard/src/pages/api/studio/visual-layout.ts`
  (near-copy of `save-stage.ts`).
- Artifact home: `content/<Bucket>/<slug>/book/visual-layout.json`, sibling of
  `book-toc.json`. No `visual-layout.json` exists anywhere yet — the name is free.

## Finding 4 — current book route dispatch (Phase 1)

- `scripts/podcast/phases/book_driver.py::_drive_book_branch` runs the book
  phases `0book-design → 0book-compose → 0book-illustrate → 0book-slide-import →
  0book-render`.
- Route split happens at `0book-compose`: `is_translation_edition(book_dir)` →
  `author_translation_edition_compose` (faithful translation, from
  `_system/source/text/refined-english.md`) vs `author_phase_book_compose` (the
  legacy author-companion revoice). This branch is where the two knobs replace
  the single `deliverable_mode` selector under the `book_pipeline_v2` flag.

## Phase 0 scaffold

`scripts/podcast/_pipeline_flags.py` — the single source of truth for the
`book_pipeline_v2` flag (default OFF, env override `BOOK_PIPELINE_V2` for CI) and
the two knob readers with the zero-regression default map
(`translation_edition → {none, faithful}`; else `{source_only, author_companion}`).
Tested in `scripts/podcast/tests/test_pipeline_flags.py`. **Flag-OFF invariant:
no pipeline code imports this module yet** — it is inert scaffold, so output is
byte-for-byte identical to today.
