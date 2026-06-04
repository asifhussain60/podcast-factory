# source_extractor

SQL source database → podcast-pipeline source bundle.

Independent of `scripts/podcast/`. Adapters provide database-specific schema
knowledge; stages run against any adapter. Output is a self-contained bundle
that the podcast pipeline can intake via a forthcoming `--from-bundle` flag.

## Implemented

- **KAHSKOLE adapter** (Urdu): full implementation. Binder → Chapter → Topic
  hierarchy. Inline base64 image extraction. HQAyats-validated Quran citation
  cleanup. TopicAyats curated-citation footers.

## Scaffolded but not implemented

- **KSESSIONS adapter** (English): structural stub. SQL templates preserved
  as reference comments; raises `NotImplementedError` on the required methods.

## Usage

Three-stage pipeline per book (chapter for KAHSKOLE):

```bash
# Stage A — DB → draft markdown + extracted PNG images + vision-tasks.json
python3 -m tools.source_extractor prepare wisdom --binder 1 --chapter 125

# Stage B — in-conversation Claude vision (no command; ask Claude to process
# the vision-tasks.json file under the images/ directory)

# Stage C — substitute placeholders + adapter-specific cleanup + final .md
python3 -m tools.source_extractor finalize wisdom --binder 1 --chapter 125
```

## Layout

```
tools/source_extractor/
  cli.py                 ← entry point
  __main__.py
  db.py                  ← docker-exec sqlcmd wrapper
  html_to_md.py          ← HTML → markdown with KAHSKOLE class-aware semantics
  slugify.py             ← Urdu/Arabic + English slugifiers
  yaml_lite.py           ← minimal YAML emit helpers
  adapters/
    base.py              ← SourceAdapter abstract interface
    wisdom.py          ← KAHSKOLE schema + Quran cleanup + curated citations
    ksessions.py         ← KSESSIONS stub
  stages/
    prepare.py           ← Stage A (adapter-generic)
    finalize.py          ← Stage C (adapter-generic)
```

## Output — BOOK_DIR bundle (Phase B)

```
<extract-root>/<source>/<NN-shelf>/<MM-book>/
  _README.md                              ← human-readable summary
  bundle.yml                              ← manifest read by intake_book.py --from-bundle
  _system/
    source/
      <book-slug>.html                    ← audit anchor: concatenated raw HTML
      text/
        raw-extract.md                    ← Phase 0a output (source language)
        _extraction-notes.md              ← skipped sections + caveats
        _provenance.json                  ← podcast.ingest-source/v1 (source.kind=sql)
      images/
        001.png, 001.json                 ← decoded bytes + Stage B sidecar
        002.png, 002.json
        ...
        vision-tasks.json                 ← Stage B work queue
```

The pipeline-side `intake_book.py --from-bundle <dir>` (Phase D) reads
`bundle.yml`, creates the content branch, copies `_system/source/` into
`content/drafts/<slug>/_system/source/`, and marks Phase 0a complete. If
`source_language != en`, the orchestrator runs the new Phase 0a-translate
step (Phase E, deferred).

## Independence

- No imports from `scripts/podcast/`.
- No external API calls (vision is in-conversation with Claude).
- Sole runtime dependency on `_workspace/source-library/` is the running
  Docker container `wisdom-mssql` that the SQL dumps were restored into.
