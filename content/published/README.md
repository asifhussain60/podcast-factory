# `library/` — shipped catalog

Top-level read-only catalog of prod-grade podcast artifacts. Every file under
`library/` has either passed a challenger verdict (`SHIP-READY`, or an
operator-approved `SHIP-WITH-CAUTION`) or is curated metadata (catalog,
cover art) added post-ship.

## Invariants

1. **Auto-populated only.** The single supported writer is
   [`scripts/podcast/publish_to_library.py`](../scripts/podcast/publish_to_library.py),
   which promotes shipped episodes from `_workspace/books/<slug>/` into the
   per-book layout below. Pipeline scripts NEVER write directly to `library/`.
2. **CI-enforced.** [`.github/workflows/library-readonly.yml`](../.github/workflows/library-readonly.yml)
   fails any PR commit that touches `library/` unless either:
   - the commit subject starts with `ship: ` (the convention `publish_to_library.py`
     prints in its commit hints), or
   - the commit body contains the literal `[library-manual-edit]` marker (the
     escape hatch for one-off manual overrides — e.g. dropping cover art).
3. **One-way.** Promotion is `_workspace/ → library/`. Nothing flows back.
4. **Idempotent re-ship.** Re-running `publish_to_library.py` adds or updates the
   requested episodes; it does not delete anything from `library/`.

## Layout

```
library/
├── _meta/
│   └── catalog.md             ← auto-generated cross-book index
├── archetypes/                ← cross-book reference (not per-book; hoisted in Phase 9.5)
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
