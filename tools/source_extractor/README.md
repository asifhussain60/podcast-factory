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
python3 -m tools.source_extractor prepare kashkole --binder 1 --chapter 125

# Stage B — in-conversation Claude vision (no command; ask Claude to process
# the vision-tasks.json file under the images/ directory)

# Stage C — substitute placeholders + adapter-specific cleanup + final .md
python3 -m tools.source_extractor finalize kashkole --binder 1 --chapter 125
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
    kashkole.py          ← KAHSKOLE schema + Quran cleanup + curated citations
    ksessions.py         ← KSESSIONS stub
  stages/
    prepare.py           ← Stage A (adapter-generic)
    finalize.py          ← Stage C (adapter-generic)
```

## Output (current — flat shape, matching Phase 1 proof)

```
<extract-root>/<source>/<NN-shelf>/
  <MM-book>.md                ← final markdown (after finalize)
  <MM-book>.meta.yml          ← metadata (source_language, shelf/book, sections, citations)
  <MM-book>-images/
    001.png                    ← decoded image bytes
    001.json                   ← Stage B sidecar (classification + OCR + citation)
    vision-tasks.json
```

The future BOOK_DIR shape (matching `intake_book.py`'s `content/drafts/<slug>/_system/`
layout) lands in Phase B.

## Independence

- No imports from `scripts/podcast/`.
- No external API calls (vision is in-conversation with Claude).
- Sole runtime dependency on `_workspace/kashkole-ksessions/` is the running
  Docker container `kashkole-mssql` that the SQL dumps were restored into.
