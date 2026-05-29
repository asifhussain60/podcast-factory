# 01 — Reader as part of the podcast-factory site (STRAIGHTFORWARD)

**Assumption (yours):** "Podcast-reader should now be a part of the podcast-factory astro site with advanced features."

## Finding
There is **no separate `podcast-reader/` directory**. The reader already lives **inside** the single Astro app at `plan-dashboard/`:

- Route: `plan-dashboard/src/pages/library/[slug]/chapter/[chapter].astro`
- Nav (per your screenshot): `Architecture · Bookshelf · Wisdom · Quality` — one site, branded "Podcast Factory".
- Annotation workspace: `components/reader/AnnotationWorkbench.tsx` (paragraph/book/global scopes, tags, notes, AI actions).
- Persistence: SQLite `CONTENT/knowledge-base/knowledge.db` (`annotation_tags`, `paragraph_annotations`, `paragraph_notes`) + localStorage queue.

So the merge you want is **already 90% done** — the reader is not a separate app. What remains is (a) naming/plan reconciliation and (b) the "advanced features", which depend on the three DISCUSS topics (MCP-driven annotation, intelligence integration).

## Naming wart to settle
The site is physically called `plan-dashboard/` but now serves end-readers, not just the plan. Options: rename dir to `site/` or `podcast-factory-web/`; or leave it (cosmetic). Low priority — flag only.

## What "advanced features" should mean (depends on DISCUSS docs)
1. Hover popovers backed by the **wisdom corpus MCP** instead of quran.com + Gemini (doc `04`).
2. **Silent markers** auto-injected by the pipeline so refs/terms render pre-classified (docs `04`, `06`).
3. Atoms from the intelligence pipeline surfaced as cross-references in the annotation rail (doc `05`).

## Proposed plan delta (apply after your OK)
- Mark the SPA/reader wave **COMPLETE** in `_workspace/plan/refactor/plan.{md,yaml}` (it is built; plan lists it as PLANNED).
- Add a new wave **"Reader ⇄ Wisdom integration"** whose steps are the outcomes of docs `03/04/05` once we converge.
- Regenerate dashboard snapshots (`cd plan-dashboard && npm run snapshot`) in the same change (per standing Tier-0 rule).

> No plan edits made yet — holding per your "no changes" instruction.
