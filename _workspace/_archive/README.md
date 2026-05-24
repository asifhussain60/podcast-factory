# `_workspace/_archive/`

Historical scaffolding moved here so the active `_workspace/` stays focused on the current plan + runbooks. Tracked in git (intentional — preserves provenance), but **outside the working path** for skills, agents, and pipelines.

## Inventory

| Path | Origin | Why archived |
|---|---|---|
| `journal_podcast_processing_package/` | Pre-orchestrator manual source-chapter ingestion package (SRC-001…SRC-012 stubs, source-manifest, OCR tooling recommendations) | Superseded by the orchestrator-driven pipeline under `scripts/podcast/` + per-book `content/drafts/*/_system/` layout. No code reads from this directory. |

## Policy

- **Do not** wire active code or skills to anything under `_archive/`.
- **Do not** delete without team alignment — preserved for repo history and the rare "what did we try before?" question.
- **Do** add new entries with a row in this table when archiving future stale scaffolding.
- If a directory becomes load-bearing again (rare), move it back out of `_archive/` and remove the row.

Last reviewed: 2026-05-19 (plan v2 gap-close pass).
