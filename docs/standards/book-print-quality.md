# Book Print-Quality Standard (Book Pipeline v2)

Normative requirements for the **rendered** reading-edition PDF
(`content/<Bucket>/<slug>/book/book.pdf`). This is the print counterpart to the
semantic `book-challenger` (which reads `book.md`) and the on-screen
`html-view-quality` standard (which governs the Astro site). It governs what the
reader physically holds: pages, figures, legibility, page-fill.

Applies to every rendered book reading edition (wired into 0book-render).
Enforced by the deterministic probes in `scripts/podcast/_book_render_checks.py`
plus the visual judgment of the `book-render-challenger` agent. Requirements are
cited by `REQ-BR-NNN`.

## Scope

Applies to every book rendered through `render-book-pdf.mjs` with the flag on. It
does NOT re-judge teaching fidelity (that is `book-challenger` BK-P4) or Arabic
accuracy — only the physical rendering. A finding here is about the page, never
the meaning.

## Requirements

### Pagination + page-fill

- **REQ-BR-001 (MUST · P0) — No blank interior page.** Every interior page (all
  but the first and last) carries real content. Blank versos from print-CSS
  page-break interactions are a defect. *Probe: `scan_blank_and_halfempty` →
  `BR-BLANK-PAGE`.*
- **REQ-BR-002 (SHOULD · P1) — No half-empty interior page.** Interior pages fill
  like a professional book; a page whose text is far below the interior median is
  flagged. A chapter still opens on a fresh page — that opener is not "half-empty".
  *Probe: `scan_blank_and_halfempty` → `BR-PAGE-FILL`.*
- **REQ-BR-003 (SHOULD · P1) — Widow/orphan control.** No single line of a
  paragraph stranded alone at a page top or bottom; a chapter heading is never the
  last thing on a page. *CSS: `orphans/widows`, `.chapter-open { break-after:
  avoid }` in `book-print.css` under `body.book-v2`.*
- **REQ-BR-004 (MUST · P1) — The running head names the page's own chapter.** Every
  page's margin-box title matches the chapter the page actually belongs to. Keying
  `@page` rules by position over a chapter list that leads with the preface shifts
  every rule by one, so pages deep in a chapter carry the previous chapter's title
  — a defect no other gate can see, because nothing else reads margin-box text
  against chapter boundaries. *Probe: `scan_running_heads` → `BR-RUNNING-HEAD`.*

### Figures

- **REQ-BR-010 (MUST · P0) — No figure spans a page break.** A standalone figure
  taller than the text column occupies its own page (`page_fit: isolate-plate`)
  rather than splitting. *CSS: `break-inside: avoid` + `page-fit-*`.*
- **REQ-BR-011 (MUST · P0) — No NotebookLM watermark.** No exported-slide
  watermark text survives on any rendered page; slides are watermark-cleaned or
  replaced by a verified vector replica before becoming a candidate.
  *Probe: `scan_watermark` → `BR-WATERMARK`.*
- **REQ-BR-012 (MUST · P1) — No duplicated caption.** A figure's caption is
  printed once. A title baked into the asset is not echoed again as a
  `<figcaption>` (renderer de-dups via `embedded_title`).
  *Probe: `scan_duplicate_captions` → `BR-CAPTION-DUP`.*
- **REQ-BR-013 (MUST · —) — Placement matches the contract.** Each figure renders
  at the `align` / `flow` / `width_pct` / `anchor` the human curated in
  `visual-layout.json`: `flow: wrap` floats with text beside it (`width_pct <= 50`),
  `flow: standalone` is a centered block. *Visual check by the agent.*
- **REQ-BR-014 (SHOULD · —) — Placement after its introduction.** A figure sits at
  or after the passage it illustrates, never marooned before it. *Visual check.*

### Legibility

- **REQ-BR-020 (SHOULD · —) — Legible figures.** No figure is shrunk below
  readability to fit; diagrams stay vertical and uncapped (`_svg_geometry` gate).
  *Visual check.*

### Text integrity + apparatus

- **REQ-BR-030 (MUST · P0) — No unsubstituted placeholder on the page.** No
  `__TOKEN__` reaches print. A placeholder of that shape on a rendered page means a
  substitution silently did not happen, and the reader sees the machinery.
  *Probe: `scan_placeholders` → `BR-PLACEHOLDER`.*
- **REQ-BR-031 (MUST · P0) — A book with a crosswalk prints its crosswalk page.**
  When `source-crosswalk.json` exists, the rendered PDF carries a Source Crosswalk
  apparatus page. Dropping it loses every per-chapter provenance line at once, and
  a translation edition without its crosswalk is unciteable. Books with no
  crosswalk file are out of scope for this requirement.
  *Probe: `scan_crosswalk_present` → `BR-CROSSWALK-MISSING`.*

## Verdicts

`RENDER-CLEAN` (no findings) · `RENDER-CAUTION` (only P1) · `RENDER-BROKEN` (any
P0). Non-blocking for the podcast ship — a broken reading edition is recorded in
`_system/book-render-checks.json` and surfaced, but never stops the audio.

## Relationship to other gates

| Gate | Reads | Judges |
|---|---|---|
| `book-challenger` (BK-*) | `book.md` | teaching fidelity, Arabic accuracy, voice, craft |
| `book-render-challenger` (BR-*) | `book.pdf` | pages, figures, page-fill, legibility |
| `html-view-quality` (REQ-*) | Astro views | on-screen views incl. the Book Composer |

Keep them disjoint: a page-layout defect is BR; a meaning defect is BK; an
on-screen-view defect is REQ.
