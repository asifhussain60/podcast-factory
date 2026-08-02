---
name: studio-composer
description: >
  Execution contract for the two Studio authoring surfaces on the Podcast Factory
  Astro Site (directory plan-dashboard/): the merged Edit canvas of the Book Composer
  (/studio/<slug>/compose) and the whole-book Preview (the "Read" mode). MUST be
  applied to ANY work on those surfaces — building the merged editor, the paginated
  Preview, or their entry points. Encodes the behavioural invariants (Preview↔PDF
  parity, single authoring canvas, read-only Read mode, scroll-synced explanations)
  and defers to the html-view-quality skill for all Cortex styling/theme/DoD rules.
  TRIGGER: "book composer", "compose view", "preview mode", "figure placement", or
  work under compose.astro / book-composer.ts. Canonical rule text:
  docs/standards/studio-composer-quality.md.
---

# Studio Composer / Preview

This skill is the operational contract for building and editing the two Studio
authoring surfaces on the **Podcast Factory Astro Site** (directory `plan-dashboard/`).
(A third, the LIVE Session at `/studio/<slug>/live`, was retired 2026-08-01 — the
Composer's Read mode is the reading surface now.)
The full requirement text lives in
[docs/standards/studio-composer-quality.md](../../docs/standards/studio-composer-quality.md)
(cite findings by `REQ-SC-NNN`, never by section).

> **Hard precedence.** This skill governs the *behaviour* of these surfaces; the
> `html-view-quality` skill governs their *styling*. Both apply, always. A surface is
> not "done" until it passes both gates: `html-view-challenger` (static Cortex) and,
> for Preview work, `book-render-challenger` (the Preview displays the rendered PDF). Do not bypass
> and do not drift.

## 0. Relationship to html-view-quality (do not duplicate)

This skill adds **behavioural** rules; it never restates Cortex styling rules. Every
delivery-mechanics rule — external CSS/JS only, zero inline styling, existing `--c-*`
theme unchanged, shared layout, diagrams vertical/uncapped — comes from the
[html-view-quality skill](../html-view-quality/SKILL.md) and applies here unchanged
(REQ-SC-040). Load that skill alongside this one.

## 1. The verified architecture (read before touching the code)

The current split these surfaces are being redesigned out of:

- **Book Composer** (`src/pages/studio/[slug]/compose.astro` + `src/scripts/book-composer.ts`):
  two columns — left per-chapter preview (dropdown-selected, one chapter visible),
  right sticky inspector with tabs Artifacts / Citations / Refinement / Output. A
  Read/Edit mode toggle; boots into Edit.
- **Edit mode today** = TipTap prose only (`mountChapterEditor` in `book-md-editor.ts`);
  `.cx-body` hidden. No figure placement. Prose saves via `PUT /api/studio/book-md`.
- **Read mode today** = per-chapter WYSIWYG (`render()` re-inlines figures into the
  pristine body). Figure placement = drag from the Artifacts palette; click a figure →
  floating `.cx-fig-card` (align/flow/width/anchor/position/caption/page-fit); corner
  resize handle. Saves the whole-book layout via `PUT /api/studio/visual-layout` →
  `book/visual-layout.json`. "Generate PDF" → `POST /api/studio/generate-book-pdf`.
- **Reader** (`src/pages/studio/[slug]/book.astro` + `loadBook` in `src/lib/reader/book.ts`):
  whole-book continuous scroll + sticky TOC + `CompanionPanel` floating side panel
  (private notes, API-backed, never in the PDF).
- **Print pipeline** (single source of truth for print): `render-book-pdf.mjs`
  (Playwright chromium, A4) + `src/styles/book-print.css` (`@page` 2.2cm×2cm, Source
  Serif 4 + Amiri, drop caps, `body.book-v2` figure system). The markdown→HTML for the
  book body is currently duplicated (mjs `renderMd` vs `lib/reader/markdown.ts`);
  Preview work (Phase 3) unifies it (REQ-SC-022).
- Figure widths ride the `--cx-w` custom property, never inline HTML attributes; the
  layout contract is `scripts/visual-layout.mjs` ↔ `scripts/podcast/_visual_layout.py`.

## 2. The behavioural non-negotiables

Not restated here — they live in one place, the
[standard](../../docs/standards/studio-composer-quality.md), cited by `REQ-SC-NNN`.
The four that are most load-bearing and most easily broken:

- **Preview must equal the PDF (REQ-SC-023, the only P0).** Preview exists solely to
  show how the PDF paginates. Any drift — a figure on a different page, a different
  page count — makes it worse than useless. Unify the HTML source (REQ-SC-022) and
  gate the rendered PDF with `book-render-challenger` every run — the Preview shows it.
- **One authoring canvas (REQ-SC-030).** No mode a user must switch to just to place a
  figure. Text edit + figure place/resize live together; the inspector is Edit-only
  (REQ-SC-031).
- **Read mode is read-only.** It reads book state; it never writes it.
  `GemCompanionPanel` enforces this by withholding the write callbacks
  (`readOnly`), not by rendering a second card style.

## 3. Conformance workflow

1. **Author** per §1–§2 and the html-view-quality skill (shared layout + `theme.css`).
2. **Self-check** against the `REQ-SC-*` list and the Cortex §10/§11 checklist.
3. **Gate.** Run `html-view-challenger` (static) + `site-health-sentinel` (runtime) on
   every touched surface. For any Preview change, ALSO run `book-render-challenger`
   — a `PF-*` parity failure is a P0 block (REQ-SC-023).
4. **MUST/P0 findings block.** P1/SHOULD warn (skip only with a stated code-comment reason).
5. Keep TS↔Python mirrors in sync in the same commit (`content-paths.ts`↔`_paths.py`,
   `visual-layout.mjs`↔`_visual_layout.py`).

## 4. Process guardrails

- **One surface at a time.** Per Asif (2026-05-29), per-view redesigns are agreed page
  by page; this skill governs HOW, not WHAT each surface shows.
- **Risk order.** Ship the additive surfaces (entry points, Preview) before the
  highest-risk full-merge of the Edit canvas.
- **Never change `theme.css` colour values.** Add aliases only (html-view-quality §2).
- **Keep the directory `plan-dashboard/`** in all paths; name the app "the Podcast
  Factory Astro Site" in prose.
