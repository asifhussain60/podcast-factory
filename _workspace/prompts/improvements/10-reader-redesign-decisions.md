# 10 — Podcast chapter-reader redesign — CONVERGED decisions (2026-05-29)

> Per-view redesign discussion (Asif, 2026-05-29), folded into the intelligence-pipeline
> session. The reader is the convergence surface for the source-intake decisions
> ([09-source-intake-decisions.md](09-source-intake-decisions.md)): the Intake Review /
> source-budget panel (SI-6), divergence markers (SI-4), and corpus-verified annotation
> markers (D10). Current-state map: a mature editorial-modern MVP (external CSS, machine-
> agnostic paths, serif-first, themed) whose core problem is that consumption + editorial
> tooling are fused into one dense surface. Cortex HTML View standard applies to any build.
> Plan-first gate: these become a plan entry + snapshot + approval BEFORE any code.

| # | Decision |
|---|---|
| **R-1 — Two modes on the same chapter: Read + Studio.** | **Read** = clean, audience-grade, distraction-free (the eventual public-facing experience). **Studio** = Asif's editorial cockpit (annotations, AI tools, divergence markers, Intake Review/source-budget, source layers). One-click in-context toggle on the same chapter; nothing removed, just placed in the right mode. Resolves the consumption-vs-editorial tension at the root. |
| **R-2 — Studio uses a single contextual inspector, not stacked rails.** | One right-side panel whose content FOLLOWS FOCUS. Nothing selected → chapter/book context (source budget, section summaries, divergence overview, mini-TOC). Paragraph selected → that paragraph's tags, notes, divergent source renderings, reference markers, AI actions. Replaces the current competing widget stack (workbench + TOC + AI + Q&A + summaries). Makes annotations/divergences prominent; absorbs new surfaces without new rails; surfacing is context-gated, not crammed (honours ui-max-surfacing without clutter). |
| **R-3 — Read mode = reading + subtle verified markers + audio + Arabic; zero editorial chrome.** | Renders only the CANONICAL reconciled text. Corpus-verified Quran/hadith/term markers stay but rendered RESTRAINED + tappable for popovers (not the bright editorial highlight). Inline AUDIO player (NotebookLM/m4a Audio Overview) — the headline missing feature. Arabic toggle stays. Tags, AI, divergence markers, source layers are absent (Studio-only). The audience sees the clean result; Asif reviews divergences in Studio. |

| **R-4 — Divergences: inline indicator + side-by-side inspector.** | Quiet per-paragraph margin glyph ("N sources differ") preserves reading flow; selecting it opens the inspector side-by-side: canonical vs each source version, color-coded by role, span-level diff highlighting, keep/accept/flag controls. Doubles as the Anwaar Urdu-vs-English transcript comparison surface (SI-2). Two jobs (locate / compare) → two treatments. |
| **R-5 — Audio: persistent docked player + sync-when-available.** | Slim player docked to the reading column, persists on scroll, scoped to the chapter's episode; karaoke text-sync when timestamps exist, graceful plain player otherwise; available in both modes. Headline missing feature; degrades cleanly. |
| **R-6 — Chapter/episode: explicit mapping; Read=episode, Studio=chapter.** | Formalize one-episode↔one-or-more-chapters mapping; unify into one reader where Read mode is episode-centric (assembled text + synced audio) and Studio is chapter/source-centric (editorial). Retires the separate pages; makes audio-scoping + listen-along work; models the locked content-aware boundary reconfiguration. |
| **R-7 — Studio = the pipeline's single human-review cockpit.** | Not a reader with edit features bolted on — a purpose-built review workbench where ALL human review happens as raw source flows through the pipeline (source budget, divergence reconciliation, refined-source review, annotation, AI-assisted edits). Maximum tooling for fast scanning / marking / identifying / editing; richest-UI default ([[ui-max-surfacing]]). |
| **R-8 — Engine: TipTap (ProseMirror) for Studio; Read stays static.** | ProseMirror decorations = non-destructive annotations / markers / divergence highlights; mature extensions for comments, suggestions/track-changes, marks, find-replace, keyboard nav; real transactions + undo/redo; collaboration-ready (y.js) later. React-island friendly. Read mode = fast server-rendered prose + audio player. Add `jsdiff` for side-by-side; keep `floating-ui`. Asif authorized installing libraries; prefers richer UI. |

## Still open (reader) — bring next
- **R-9 — Capability set** of the Studio workbench (scan/minimap/find, marking palette, side-by-side diff, tracked AI-suggestions, review-queue + per-paragraph reviewed-state + one-click stage approval). Proposed as a full package.
- **R-10** — Mobile/responsive reflow (three-pane hides rails today).
- (Lower priority from the audit: in-chapter search [partly R-9], citation/export, persistent margin notes, server-side edit history, selectable Quran translation.)

## Also still open (source-intake)
- Spine-selection rule when multiple candidate "authoritative" sources exist (the last item from [09](09-source-intake-decisions.md)).

> After R-9 (+ R-10), consolidate 09 + 10 into a single plan.yaml entry + snapshot for approval (plan-first gate) before any code. This is a real re-platforming of Studio onto TipTap.
