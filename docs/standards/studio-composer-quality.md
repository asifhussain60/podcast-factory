# Studio Composer / Preview / LIVE Session Standard

Normative requirements for the three Studio authoring surfaces on the **Podcast
Factory Astro Site** (directory `plan-dashboard/`):

1. the **merged Edit canvas** of the Book Composer (`/studio/<slug>/compose`),
2. the whole-book **Preview** (the renamed "Read" mode), and
3. the **LIVE Session** reading view (`/studio/<slug>/live`).

This is the on-screen counterpart to the print-side `book-print-quality.md` (which
governs the rendered PDF) and a peer of the cross-cutting `html-view-quality`
standard (which governs Cortex conformance for every view). This standard governs
only what these three surfaces must *do* — their behavioural and structural
invariants. Requirements are cited by `REQ-SC-NNN`.

Enforcement: the `preview-fidelity-challenger` agent (Preview↔PDF parity, backed by
the deterministic `plan-dashboard/scripts/preview-fidelity-check.mjs`, `PF-NNN`
probes), plus `html-view-challenger` (static Cortex) and `site-health-sentinel`
(runtime + visual) which already exercise these routes.

This document grows per build phase — a requirement is marked `(scaffold)` until the
phase that implements it lands, then the marker is removed.

## Scope

Applies to `src/pages/studio/[slug]/compose.astro` + `src/scripts/book-composer.ts`,
the new `src/pages/studio/[slug]/live.astro` + `src/styles/live-session.css`, the
shared print-HTML module extracted from `render-book-pdf.mjs`, and the entry-point
markup in `src/pages/studio/[slug]/index.astro`. It does NOT re-judge Cortex styling
rules (that is `html-view-quality`), the rendered PDF (that is `book-print-quality`),
or `book.md` meaning (that is `book-challenger`). A finding here is about surface
behaviour, never Cortex conformance and never meaning.

## Requirements

### Entry points (Phase 1)

- **REQ-SC-001 (MUST · P1) — Both authoring entries read as buttons.** The "Chapters"
  and "PDF Generator" entries in the overview tab row are accent-outlined pills
  (`.lib-tab-cta`), visually distinct from the flat `.lib-tab` panel tabs, because
  both leave the page to an authoring surface.
- **REQ-SC-002 (MUST · P1) — LIVE Session doorway present.** A "LIVE Session" pill
  links to `/studio/<slug>/live` from the overview tab row and is mirrored in the
  composer header's `.lib-title-actions`.
- **REQ-SC-003 (MUST · —) — Routing unchanged.** Restyling "Chapters" as a pill does
  not change where it navigates (`/studio/<slug>/edit`).

### LIVE Session (Phase 2)

- **REQ-SC-010 (MUST · —) — Read-only.** LIVE Session never mutates book state — no
  `book-md` / `visual-layout` writes. Companion notes and citations are surfaced
  read-only; the inspector, if shown, is the read-only projection of the composer's.
- **REQ-SC-011 (MUST · P1) — Scroll-synced explanations.** The explanation panel
  updates to the section currently in view (via `IntersectionObserver` on chapter/
  section anchors), so the reader never hand-syncs the panel to the page.
- **REQ-SC-012 (MUST · P1) — Book picker, bucket-filterable.** A picker lists books
  grouped by content bucket (Islamic / Technical / Fiction / Guides) and filterable
  by bucket, sourced by scanning content buckets via `content-paths.ts` — never a
  hardcoded book list.
- **REQ-SC-013 (MUST · P1) — Multi-volume aware.** A volume series
  (`<container>-vol-NN`) is nested under its container in the picker, not listed as N
  unrelated flat entries.
- **REQ-SC-014 (SHOULD · —) — Own elegant CSS.** LIVE Session has its own stylesheet
  (`live-session.css`) using only existing `--c-*` tokens; it does not overload the
  composer or reader stylesheets.
- **REQ-SC-015 (MUST · —) — Composed reading column.** The reading column shows the
  composed book (prose + placed figures where present), not a bare chapter dump.

### Preview (Phase 3)

- **REQ-SC-020 (MUST · P1) — Whole book, paginated.** Preview renders the entire book
  (not a per-chapter dropdown) as discrete page boxes with margins between sheets.
- **REQ-SC-021 (MUST · —) — Print fidelity.** Fonts, figure sizing, and placement
  match the print edition — achieved by styling the preview with `book-print.css`,
  not a hand-copied approximation.
- **REQ-SC-022 (MUST · —) — Single HTML source.** The preview and the PDF consume the
  SAME HTML-assembly module (extracted from `render-book-pdf.mjs`); the web/print
  markdown renderers are not two hand-synced copies for the book body.
- **REQ-SC-023 (MUST · P0) — Preview↔PDF page parity.** The on-screen pagination
  matches the rendered PDF: same page count, same figure-to-page assignment, same
  per-page text-flow boundaries. *Verified by `preview-fidelity-check.mjs`
  (`PF-001..PF-004`) + the `preview-fidelity-challenger` agent.*
- **REQ-SC-024 (MUST · —) — Inspector hidden in Preview.** The Artifacts/Citations/
  Refinement/Output inspector is not shown in Preview (it belongs to Edit only —
  REQ-SC-031).
- **REQ-SC-025 (SHOULD · —) — Live, no render wait.** Preview paginates in-browser and
  does not block on a Playwright PDF render.

### Merged Edit canvas (Phase 4)

- **REQ-SC-030 (MUST · —) — One authoring surface.** Text editing and figure
  placement/resize happen in the same canvas; there is no separate "Read" mode a user
  must switch to in order to place a figure.
- **REQ-SC-031 (MUST · —) — Inspector Edit-only.** The inspector is present only in
  Edit mode; it is absent in Preview and read-only in LIVE Session.
- **REQ-SC-032 (MUST · P1) — Figures are atomic in the editor.** Placed figures are
  non-editable atomic nodes within the editable document; prose editing never corrupts
  or deletes a figure, and figure drag/resize never corrupts prose.
- **REQ-SC-033 (MUST · —) — Placement mechanics preserved.** Drag-from-palette, the
  `.cx-fig-card` align/flow/width/anchor/position/caption/page-fit controls, and the
  corner resize handle keep working, writing the same `visual-layout.json` contract.
- **REQ-SC-034 (SHOULD · P1) — Autosave with status.** Prose edits autosave (debounced
  `book-md` PUT) with a visible status indicator; the manual "Save layout" for the
  visual layout is retained.

### Cross-cutting

- **REQ-SC-040 (MUST · —) — Cortex + DoD deferral.** All three surfaces obey the
  `html-view-quality` skill/standard: external CSS/JS only, zero inline styling, the
  existing `--c-*` theme unchanged. This standard never overrides that; it adds
  behavioural rules on top.

## Verdicts

`SC-CLEAN` (no findings) · `SC-CAUTION` (only P1/SHOULD) · `SC-BROKEN` (any P0). The
sole P0 today is REQ-SC-023 (Preview↔PDF parity) — a Preview that disagrees with the
PDF is broken by definition.

## Relationship to other gates

| Gate | Reads | Judges |
|---|---|---|
| `html-view-quality` (REQ-NNN) | Astro view source | Cortex styling/craft/a11y, theme, zero-inline DoD |
| `studio-composer` (REQ-SC-*) | the three Studio surfaces | behavioural invariants: parity, merged canvas, read-only live session, entry points |
| `preview-fidelity-challenger` (PF-*) | preview + `book.pdf` | Preview↔PDF page parity (the REQ-SC-023 probe) |
| `book-print-quality` (REQ-BR-*) | `book.pdf` | the physical printed page |
| `book-challenger` (BK-*) | `book.md` | meaning, teaching fidelity, Arabic accuracy |

Keep them disjoint: a Cortex/theme defect is REQ; a behavioural-invariant defect is
REQ-SC; a preview-vs-PDF drift is PF; a printed-page defect is BR; a meaning defect is
BK.
