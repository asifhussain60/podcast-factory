# `content/published/` — reference metadata only (2026-05-28)

> **IMPORTANT:** Content no longer lives here. All book content lives
> exclusively in `content/drafts/<category>/<slug>/`. Publication status
> is tracked via the `publication.status` field in each book's `meta.yml`.
> The `drafts/` path is a pipeline stage name — it holds ALL content
> regardless of whether a book is draft or published.

## Why this directory still exists

This directory retains:
- `_meta/` — auto-generated cross-book catalog index
- `archetypes/` — cross-book archetype reference files

These are NOT per-book content and have no equivalent in `drafts/`.

## How publication status works

Set `publication.status: published` in a book's
`content/drafts/<category>/<slug>/meta.yml` to mark it published.
The astro site badge and all pipeline gates read this field.

`publish_to_library.py` writes this field in place — it does NOT copy
files to this directory. The file-copy model was retired 2026-05-28.

## Legacy note

Prior to 2026-05-28, this directory held full copies of shipped books
under `books/` and `lectures/` subdirectories. Those were deleted as part
of the single-content-source-of-truth refactor (commit 8b16dad3).
Any reference to `content/published/books/` or `content/published/lectures/`
in code or documentation is stale and should be updated to
`content/drafts/<category>/<slug>/`.
└── books/<slug>/
    ├── index.md               ← book metadata (auto-generated; manual edits discouraged)
    ├── cover.{jpg,png}        ← optional manual asset; drop post-ship if curated
    ├── transcript/
    │   └── <NN>-<chapter-slug>.md     ← polished NotebookLM SOURCE, with YAML front-matter
    └── podcasts/
        ├── _series-index.md   ← series list for this book
        └── series-<NN>-<slug>/
            ├── _series.md
            └── EP<NN>-<chapter-slug>/
                ├── source.txt          ← NotebookLM SOURCE upload (TTS-safe)
                ├── framing.md          ← NotebookLM CUSTOMIZE prompt
                ├── challenger-report.md
                └── audio.mp3           ← optional; landed only after audio-archive integration
```

Non-book categories (`articles/`, `documents/`, `interviews/`, `lectures/`,
`letters/`) follow the same hoist-to-top pattern: shipped items land in
`library/<category>/<slug>/`; in-progress drafts live in
`_workspace/<category>/`.

## How to promote

```bash
# Promote one episode (typical case):
python3 scripts/podcast/publish_to_library.py --book kitab-al-riyad --episode EP10

# Promote every chapter in completed_slugs (state-driven bulk ship):
python3 scripts/podcast/publish_to_library.py --book kitab-al-riyad

# Inspect what would happen without touching anything:
python3 scripts/podcast/publish_to_library.py --book kitab-al-riyad --episode EP10 --dry-run
```

Then commit with the `ship: ` prefix:

```
ship: kitab-al-riyad EP10 (motion-stillness-hyle-and-form, SHIP-WITH-CAUTION)
```

## Where in-progress state lives

`_workspace/books/<slug>/` holds the per-book orchestrator state, chapter
drafts, episode customize prompts, intermediate transcripts, raw PDF intake,
challenger reports, and everything else the pipeline reads and writes during
a run. Nothing in `_workspace/` is shippable until the orchestrator (or the
operator, in archetype-driven manual mode) signs off and `publish_to_library.py`
promotes the polished outputs here.
