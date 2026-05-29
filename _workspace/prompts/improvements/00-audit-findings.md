# Holistic Audit — 48-hour work review (Waves A–K + dashboard + MCP + reader)

**Author:** Claude (Opus 4.8)  ·  **Date:** 2026-05-29  ·  **Mode:** research + documentation only, NO code changes
**Scope:** repo, podcast pipeline, intelligence pipeline, MCP blackbox (KQUR/KASHKOLE/KSESSIONS), wisdom corpus, DB schema, Astro site/reader.

> This is the evidence-based system-of-record for the audit. Every claim below is sourced to a file path I read or a command I ran. Documentation in the repo was NOT trusted; this reflects actual code state on `develop` as of 2026-05-29.

---

## 1. What actually got built (verified)

| Area | State | Evidence |
|---|---|---|
| Core layer (Wave A) | Real, in use | `scripts/podcast/_db.py`, `_archetypes.py`, `_paths.py`, `intelligence/_anti_cliche.py`, `_quality.py` |
| Intelligence chain (Wave B) | Built, **orphaned** | `scripts/podcast/intelligence/{extractor,librarian,augmenter,wisdom_ingest_knowledge}.py` |
| Source-library MCP (Wave J) | Real, **not consumed by reader** | `scripts/podcast/source_library_server.py` (6 tools, stdio+HTTP), `source_library_queries.py`, `source_library_mirror.py` |
| PEQ quality scoring (Wave K) | Real, surfaced in reader | `scripts/podcast/_quality.py`, `intelligence/challenger_scoring.py`, schema `019_quality_scores.sql`, `plan-dashboard/src/lib/peq-scores.ts` |
| Phase 06a source-review gate (Wave I) | **Wired + runs** | `scripts/podcast/phases/source_review_gate.py`, called in `phases/initial_driver.py` |
| Phase per-chapter-optimize (Wave I) | **Wired + runs** | `scripts/podcast/phases/per_chapter_optimize.py`, called in `phases/chapter_driver.py` |
| Astro reader + annotation workspace | Real, production-grade | `plan-dashboard/src/pages/library/[slug]/chapter/[chapter].astro`, `components/reader/AnnotationWorkbench.tsx` |
| Reader AI features | Real, **Gemini-backed (not MCP)** | `plan-dashboard/src/pages/api/ai/*`, `lib/reader/gemini-server.ts` |
| DB schema | 20 migrations, applied | `scripts/podcast/schema/001..020*.sql`; live DB `CONTENT/knowledge-base/knowledge.db` (356 KB) |

Books in `CONTENT/drafts/books/`: `asaas-al-taveel`, `ayyuhal-walad`, `islr-mas-i`, `kitab-al-riyad`, `the-master-and-the-disciple`. **No `anwar` book exists** — the screenshot is `ayyuhal-walad` (al-Ghazali, *O Beloved Son*).

---

## 2. The three load-bearing disconnects (the real story)

These are the gaps that matter. Everything the user wants ("intelligence + podcast hand-in-hand", "MCP drives annotations", "wisdom corpus") sits on top of fixing them.

### 2a. The intelligence pipeline is operationally orphaned
`orchestrate_book.py` `CANONICAL_PHASES` (lines ~152-161) is:
`pre-flight, branch, scaffold, 0a, 0b, 0c, 0d, 0e, 06a, 0f, 0g, per-chapter, per-chapter-optimize, per-chapter-slides, finalize, publish, trainer, merge, done`.
There is **no `0h` / extractor / librarian / augmenter phase** in the execution path. The three intelligence scripts only run when invoked manually. The augmenter is gated by `enable_knowledge_augmenter` (default `False` in `_rules.py`, not enabled on any book). Atoms in `knowledge.db` are **write-only** — nothing in a book run reads them back. → topic doc `05`.

### 2b. The MCP blackbox does not feed the reader
The reader's Quran popover calls **quran.com** (`plan-dashboard/src/pages/api/quran/verse.ts`), and term definitions call **Gemini** (`api/ai/define-term`). Neither calls `source_library_server` (port 4390). The 6-tool MCP blackbox exists but **no consumer is wired to it**. The reader's reference-highlighting machinery (`lib/reader/highlight-renderer.ts` + pluggable `ref-categories/`) is regex-based, not corpus-driven. → topic docs `04` + `06`.

### 2c. The "wisdom corpus" is still three separate application databases
`CONTENT/_shared/source-library/` holds three raw SQL Server dumps (KQur 15M, KSessions 29M, Kashkole 724M). They are restored into a Docker container by `infra/setup-wisdom-db.sh`. There is **no unified corpus** — and there is real duplication (two complete Quran representations; see doc `03`). The MCP queries route to these raw DBs. The FTS5 mirror (`mirror.db`) referenced in Wave J **does not exist on disk yet** (`CONTENT/knowledge-base/` has no `mirror.db`). → topic doc `03`.

---

## 3. Smaller findings (straightforward)

- **YNAB MCP is unrelated to this project and leaks a key.** `.vscode/mcp.json` registers `ynab` with a plaintext `YNAB_API_KEY`. Remove. → doc `02`.
- **`loop-intelligence.md` ledger is corrupted with ~100 duplicate log lines** (`_workspace/prompts/loop-intelligence.md` lines 42-131 are the same 7-line block repeated). The H3 autonomous chain driver was looping and appending identical entries. Worth truncating. → doc `02`.
- **Stale memory:** `project_podcast_reader.md` says the reader lives at `podcast-factory/podcast-reader/` — that directory does not exist; the reader is in `plan-dashboard/`. → doc `02`.
- **Plan drift:** the dashboard/SPA and reader are fully built but the refactor plan still lists "Wave D (SPA)" as PLANNED. Plan needs reconciliation. → doc `01`.

---

## 4. What is genuinely healthy (don't touch)

- Phase 06a + per-chapter-optimize are correctly wired (Wave I delivered).
- PEQ scoring is coherent end-to-end: contract in `_quality.py`, computed in `challenger_scoring.py`, stored in `quality_scores`, rendered in the reader header.
- The reader is well-architected: pluggable `ref-categories` registry (matches the "extensibility first" principle), clean `lib/reader/` separation, SQLite-backed annotations (`annotation_tags`, `paragraph_annotations`, `paragraph_notes` in the shared `knowledge.db`).
- Schema migrations are ordered and idempotent (`016_schema_migrations.sql` tracks applied files).

---

## 5. Document index for this review

| Doc | Topic | Disposition |
|---|---|---|
| `01-reader-into-site.md` | Reader folded into main site + advanced features | STRAIGHTFORWARD → plan delta proposed |
| `02-ynab-and-memory-flush.md` | Remove YNAB MCP; flush stale memory; fix loop ledger | STRAIGHTFORWARD → ready to apply |
| `03-wisdom-corpus-merge.md` | Merge KQUR/KASHKOLE/KSESSIONS without duplication | **DISCUSS SEPARATELY** |
| `04-mcp-blackbox-annotation-engine.md` | MCP drives annotations + silent markers | **DISCUSS SEPARATELY** |
| `05-intelligence-podcast-integration.md` | Intelligence + podcast pipeline hand-in-hand | **DISCUSS SEPARATELY** |
| `06-ayyuhal-walad-annotation-prompt.md` | Annotation/visual-differentiation prompt for the book | PROMPT documented |
