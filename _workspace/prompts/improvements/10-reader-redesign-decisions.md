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

## Still open (reader)
- **R-4** — How source divergences + competing source renderings visualize in Studio (inline side-by-side vs overlay vs inspector-only).
- **R-5** — Audio integration specifics (player placement, text-sync, per-chapter vs per-episode).
- **R-6** — Mobile/responsive reflow (three-pane hides rails today).
- **R-7** — Chapter/episode unification (today they're separate layouts; chapter doesn't know its episode).
- (Lower priority from the audit: in-chapter search, citation/export, persistent margin notes, server-side edit history, selectable Quran translation.)

## Also still open (source-intake)
- Spine-selection rule when multiple candidate "authoritative" sources exist (the last item from [09](09-source-intake-decisions.md)).
