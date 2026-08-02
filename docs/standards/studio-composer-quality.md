# Studio Composer / Preview Standard

Normative requirements for the two Studio authoring surfaces on the **Podcast
Factory Astro Site** (directory `plan-dashboard/`):

1. the **merged Edit canvas** of the Book Composer (`/studio/<slug>/compose`), and
2. the whole-book **Preview** (the "Read" mode).

> **The LIVE Session was retired on 2026-08-01.** It was a third surface —
> `/studio/<slug>/live` — maintaining the same job as the Composer's Read mode.
> Its requirements (REQ-SC-002 and REQ-SC-010..015) are retired below rather than
> re-pointed, because the behaviour they protected already exists elsewhere:
> read-only companion cards, passage tint and follow-the-chapter scroll sync are
> in the Composer's Read mode (locked 2026-07-30 — `GemCompanionPanel` takes
> `readOnly` / `inViewIds` / `anchoredIds` so both surfaces rendered identical
> cards), and the bucket-grouped, volume-nested book picker is `/studio` itself.

This is the on-screen counterpart to the print-side `book-print-quality.md` (which
governs the rendered PDF) and a peer of the cross-cutting `html-view-quality`
standard (which governs Cortex conformance for every view). This standard governs
only what these three surfaces must *do* — their behavioural and structural
invariants. Requirements are cited by `REQ-SC-NNN`.

Enforcement: `book-render-challenger` on the rendered PDF (the Preview shows that
same artifact, so gating the PDF gates both
probes), plus `html-view-challenger` (static Cortex) and `site-health-sentinel`
(runtime + visual) which already exercise these routes.

This document grows per build phase — a requirement is marked `(scaffold)` until the
phase that implements it lands, then the marker is removed.

## Scope

Applies to `src/pages/studio/[slug]/compose.astro` + `src/scripts/book-composer.ts`,
the shared print-HTML module extracted from `render-book-pdf.mjs`, and the
entry-point markup in `src/pages/studio/[slug]/index.astro`. It does NOT re-judge Cortex styling
rules (that is `html-view-quality`), the rendered PDF (that is `book-print-quality`),
or `book.md` meaning (that is `book-challenger`). A finding here is about surface
behaviour, never Cortex conformance and never meaning.

## Requirements

### Entry points (Phase 1)

- **REQ-SC-001 (MUST · P1) — Both authoring entries read as buttons.** The "Chapters"
  and "PDF Generator" entries in the overview tab row are accent-outlined pills
  (`.lib-tab-cta`), visually distinct from the flat `.lib-tab` panel tabs, because
  both leave the page to an authoring surface.
- **REQ-SC-002 — RETIRED 2026-08-01.** Was: "LIVE Session doorway present." The
  route it required no longer exists; the Composer's Read mode is the reading
  surface. Retained as a numbered stub so the identifiers below keep their
  meaning in older reports.
- **REQ-SC-003 (MUST · —) — Routing unchanged.** Restyling "Chapters" as a pill does
  not change where it navigates (`/studio/<slug>/edit`).

### LIVE Session (Phase 2) — RETIRED 2026-08-01

The whole phase is retired with the route. Each clause is listed with where its
behaviour lives now, so a reader of an older report can follow the identifier.
**None of these are re-pointed at the Composer** — a requirement rewritten to
describe what a surface already does is not a gate, and the Composer's Read mode
has its own clauses under Phase 3.

| Was | Required | Where it lives now |
|---|---|---|
| REQ-SC-010 | Read-only reading view | Composer Read mode — `GemCompanionPanel` withholds the write callbacks (`readOnly`) |
| REQ-SC-011 | Scroll-synced explanations | Composer Read mode — the host's scroll sweep feeds `inViewIds` (locked 2026-07-30) |
| REQ-SC-012 | Bucket-filterable book picker | `/studio` (`studio.astro`), which shelves books by bucket |
| REQ-SC-013 | Multi-volume nesting | `/studio` — volumes nest under their container |
| REQ-SC-014 | Own stylesheet | n/a — `live-session.css` deleted |
| REQ-SC-015 | Composed reading column | Composer Read mode renders the composed `book.md`, figures placed |

### Preview (Phase 3)

- **REQ-SC-020 (MUST · P1) — Whole book, paginated.** Preview renders the entire book
  (not a per-chapter dropdown) as discrete page boxes with margins between sheets.
- **REQ-SC-021 (MUST · —) — Print fidelity.** Fonts, figure sizing, and placement
  match the print edition — achieved by styling the preview with `book-print.css`,
  not a hand-copied approximation.
- **REQ-SC-022 (MUST · —) — Single HTML source.** The preview and the PDF consume the
  SAME HTML-assembly module (extracted from `render-book-pdf.mjs`); the web/print
  markdown renderers are not two hand-synced copies for the book body.
- **REQ-SC-023 (MUST · —) — Preview shows the PDF, not a second pagination.** The
  Preview renders the book through `render-book-pdf.mjs` and rasterizes the result;
  it does not paginate the markup itself. Parity is then true by construction and
  there is nothing to verify. *Rewritten 2026-07-20: this requirement previously
  demanded page-for-page parity between two pagination engines, verified by
  `preview-fidelity-check.mjs` and the `preview-fidelity-challenger` agent. There
  was never a second engine — in-browser pagination was abandoned when Paged.js
  hung this environment's Chromium on a two-paragraph document — so the check
  returned DEFERRED unconditionally and the agent never produced a finding. Both
  are deleted. If the Preview ever paginates independently again, this reverts to a
  P0 and the gate comes back with it.*
- **REQ-SC-024 (MUST · —) — Inspector hidden in Preview.** The Artifacts/Citations/
  Refinement/Output inspector is not shown in Preview (it belongs to Edit only —
  REQ-SC-031).
- **REQ-SC-025 (SHOULD · —) — Preview stays responsive.** Preview reuses a cached
  render where it can rather than blocking on a fresh Playwright PDF every time.
  *Amended 2026-07-20: previously required in-browser pagination, which this repo
  tried and abandoned — see REQ-SC-023.*

### Merged Edit canvas (Phase 4)

- **REQ-SC-030 (MUST · —) — One authoring surface.** Text editing and figure
  placement/resize happen in the same canvas; there is no separate "Read" mode a user
  must switch to in order to place a figure.
- **REQ-SC-031 (MUST · —) — Inspector Edit-only.** The inspector is present only in
  Edit mode; it is absent in Preview and in the Composer's Read mode.
- **REQ-SC-032 (MUST · P1) — Figures are atomic in the editor.** Placed figures are
  non-editable atomic nodes within the editable document; prose editing never corrupts
  or deletes a figure, and figure drag/resize never corrupts prose.
- **REQ-SC-033 (MUST · —) — Placement mechanics preserved.** Drag-from-palette, the
  `.cx-fig-card` align/flow/width/anchor/position/caption/page-fit controls, and the
  corner resize handle keep working, writing the same `visual-layout.json` contract.
- **REQ-SC-034 (SHOULD · P1) — Autosave with status.** Prose edits autosave (debounced
  `book-md` PUT) with a visible status indicator; the manual "Save layout" for the
  visual layout is retained.

### Formatting toolbar (Phase 5, added 2026-07-26)

- **REQ-SC-035 (MUST · P0) — A control may only produce what a save can write AND a
  reload can read back.** Every formatting control on the Edit canvas must satisfy
  BOTH directions: `docToMarkdown` writes it, and `renderEditSeed` parses it back to
  the same document. One direction is not enough — `~~strike~~` and a fenced code
  block both serialize cleanly and neither has a parse rule, so a click survives one
  save and returns as literal punctuation in the editor, the reader and the printed
  page. A control is not shipped until a round-trip test pins its output.
- **REQ-SC-036 (MUST · P0) — No control may author a chapter boundary.**
  `writeChapterBody` splits `book.md` on `/^##\s+/`, so an H2 typed inside a chapter
  body creates a new chapter on save. The paragraph-format control offers only levels
  below the chapter level, and rejects anything outside its configured set.
- **REQ-SC-037 (MUST · —) — The editor package never owns the schema.** The Composer
  binds `@asifhussain/prose-editor` with `attach()`, never `mount()`:
  `mountChapterEditor` stays the sole owner of `editorExtensions()` (the schema the
  round-trip test parses with), of the `cx-prose` class, and of the `handleDrop` that
  swallows a palette drag. A package release must not be able to widen or restyle any
  of them.
- **REQ-SC-038 (MUST · —) — `covers` is declared, not derived.** The serializer
  coverage list handed to `attach()` is written out by hand. Deriving it from the
  schema makes the assertion agree with itself and check nothing; declared, adding a
  node without teaching the serializer about it makes the editor refuse to open.
- **REQ-SC-039 (MUST · P1) — Toolbar interaction preserves the selection.** Every
  control prevents `mousedown` default. Without it a click blurs the editor, the
  selection collapses, the command runs against nothing, and the AI actions (which
  disable on an empty selection) switch themselves off as the user reaches for the
  bar.

### Cross-cutting

- **REQ-SC-040 (MUST · —) — Cortex + DoD deferral.** All three surfaces obey the
  `html-view-quality` skill/standard: external CSS/JS only, zero inline styling, the
  existing `--c-*` theme unchanged. This standard never overrides that; it adds
  behavioural rules on top.

## Verdicts

`SC-CLEAN` (no findings) · `SC-CAUTION` (only P1/SHOULD) · `SC-BROKEN` (any P0). The
REQ-SC-023 is no longer a P0: the Preview cannot disagree with the PDF, because it
displays the PDF.

## Relationship to other gates

| Gate | Reads | Judges |
|---|---|---|
| `html-view-quality` (REQ-NNN) | Astro view source | Cortex styling/craft/a11y, theme, zero-inline DoD |
| `studio-composer` (REQ-SC-*) | the three Studio surfaces | behavioural invariants: parity, merged canvas, read-only live session, entry points |
| `book-print-quality` (REQ-BR-*) | `book.pdf` | the physical printed page |
| `book-challenger` (BK-*) | `book.md` | meaning, teaching fidelity, Arabic accuracy |

Keep them disjoint: a Cortex/theme defect is REQ; a behavioural-invariant defect is
REQ-SC; a preview-vs-PDF drift is PF; a printed-page defect is BR; a meaning defect is
BK.
