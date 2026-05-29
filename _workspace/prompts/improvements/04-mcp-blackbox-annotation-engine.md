# 04 — MCP blackbox as the annotation + silent-marker engine  ✅ CONVERGED

> **STATUS 2026-05-29: design converged with Asif (decisions D10–D13).** Binding outcome below; analysis retained as rationale. No code until the holistic T1+T2+T3 plan entry is written, snapshotted, approved.

## Locked decisions (D10–D13)

| # | Decision |
|---|---|
| **D10** | **Sidecar markers** — `<chapter>.annotations.json`, position-keyed. Prose stays clean, survives re-authoring, matches the glossary-sidecar pattern. **Hard requirement:** markers must render visibly **in the chapter EDITOR** (not just the read view), with distinct per-type visual treatment, so Asif can find + comment on them easily. The editor is a first-class sidecar consumer and integrates with the existing comment/tag UI. |
| **D11** | **Annotation timing** — runs as an automatic **pipeline phase**, regenerated whenever chapter text changes, **plus a manual "refresh markers" action in the editor** for after Asif's own edits. Deterministic, always-present, zero per-read cost. |
| **D12** | **Interpretive scope** — factual reference markers (Quran/hadith/term/topic) are **auto-applied** (corpus-verified). Interpretive tags (esoteric/reality/sharia) are **suggest-only**: surfaced in the editor as dismissible suggestions, applied only on Asif's accept, never auto-applied. Machine owns facts; human owns doctrine. |
| **D13** | **Mechanics + authority** — add a 7th blackbox tool `verify_and_classify(span, context)`; build the corpus FTS/lookup index in **SQLite** (per T1/D4 — no Docker; supersedes the never-built `mirror.db` plan); re-point reader popovers (`QuranPopover`/`TermPopover`) off quran.com/Gemini to the corpus/blackbox. **Corpus is the SOLE authoritative source — no public-source fallback.** Unverifiable spans render `verified=false`, never as authoritative. |

---

**Your intent:** "Explore the MCP blackboxing in detail to come up with a holistic, intelligent plan. I want it to drive as many annotations and silent markers in the chapters so they render with all the visual differentiations I need" (per the reader screenshot).

## Current state (verified)
**The blackbox exists but nothing consumes it.**
- Server: `scripts/podcast/source_library_server.py` — 6 tools, two transports (MCP stdio for agents; HTTP :4390 for the browser). Clean design, zero duplication (both transports call the same 6 query functions).
- Reader popovers do **NOT** call it. `QuranPopover.tsx` → `api/quran/verse.ts` → **quran.com**. `TermPopover.tsx` → `api/ai/define-term` → **Gemini**. So the corpus-of-record (KQUR/KASHKOLE) is bypassed in favour of a public API and an LLM guess.
- Reference detection in the reader is **regex-based** (`lib/reader/ref-categories/builtin/{quran,hadith,arabic-translit}.ts`), applied at render time by `lib/reader/highlight-renderer.ts`. It finds `2:255`-shaped strings and parenthetical glosses — it does not *know* anything; it pattern-matches.

## The vision, made concrete
"Silent markers" = the chapter `.txt`/`.md` is annotated *ahead of render* with stable, invisible markers that carry corpus-verified identity, so the reader renders rich visual differentiation deterministically instead of regex-guessing live.

Two layers, both driven by the blackbox:

### Layer 1 — Build-time silent markers (pipeline writes them)
During the pipeline (or a dedicated annotation pass), every Quran ref / hadith / Arabic term / topic cross-reference is resolved through the MCP blackbox and written into the chapter as a marker the reader understands. Candidate marker syntax (non-destructive, human-readable):
```
The seeker must hold to [[q:2:153]] and practice *sabr*{{term:patience|root:ص-ب-ر}} ...
```
or an out-of-band sidecar `chapter.annotations.json` keyed by character offset (keeps prose clean — preferred; matches how the reader already loads glossary from `_system/glossary.yml`).
Each marker records: type, canonical id, corpus confidence, and a `verified` flag (did the blackbox confirm it exists?).

### Layer 2 — Render-time enrichment (reader reads markers)
The reader stops guessing: it reads the sidecar, renders the exact visual treatment per type (the existing `ref-categories` registry already supports this — it just needs a corpus-backed source instead of regex), and popovers pull verified content from the **MCP HTTP endpoint** (:4390) instead of quran.com/Gemini.

## Why route through the blackbox (not quran.com + Gemini)
1. **Authority** — KQUR/KASHKOLE is your curated, doctrine-aware corpus; quran.com translations and Gemini definitions are neither yours nor verifiable against your tradition.
2. **Determinism** — same chapter renders identically every time; no live LLM variance in the reading surface.
3. **Cost** — term popovers currently cost a Gemini call each; corpus lookups are free and instant.
4. **The "visual differentiation" you want** is only trustworthy if the marker is *corpus-verified* — a regex match on `5:1-3` could be a page number; a blackbox `quran_lookup` confirms it's a real ayah.

## What the blackbox needs to become the engine
- **A 7th tool: `verify_and_classify(span_text, context)`** — returns `{type, canonical_id, confidence, verified}` for an arbitrary span. This is the workhorse the annotation pass calls per candidate. (Today's 6 tools are lookup-by-known-id; the engine needs classify-from-text.)
- **The FTS5 mirror actually built** (`source_library_mirror.py` → `mirror.db`) so the annotation pass and reader don't require Docker/SQL Server running. **It is not built yet** — `CONTENT/knowledge-base/` has no `mirror.db`.
- **Reader popovers re-pointed** from quran.com/Gemini to `:4390` (small, contained change in `QuranPopover.tsx` / `TermPopover.tsx` / `api/quran/verse.ts`).
- **A sidecar annotation format** + a render path in `highlight-renderer.ts` that prefers sidecar markers over regex.

## Visual-differentiation taxonomy (from your screenshot, to confirm)
The reader already shows: Quran / Hadith / Arabic-translit refs (REFS row), `esoteric / reality / sharia` tags, `mark-for-deletion / mark-for-improvement`. Question for discussion: which of these are **machine-derivable** (Quran/Hadith/Arabic/topic-xref → blackbox can mark silently) vs **human-judgment** (esoteric/reality/sharia → stays manual in the workbench)? My read: the blackbox drives the *reference* class automatically; the *interpretive* tags (esoteric/reality/sharia) remain human, but the blackbox can *suggest* them via topic cross-referencing.

## Open questions for our discussion
1. Inline markers in the prose, or out-of-band sidecar JSON? (I recommend sidecar — keeps `.txt` clean, matches glossary pattern, survives re-authoring.)
2. When does annotation run — as a pipeline phase (every book, automatic) or an on-demand pass in the reader? (Relates to doc `05`.)
3. Do you want the blackbox to *auto-apply* interpretive tags (esoteric/reality/sharia) as suggestions, or strictly drive reference markers and leave interpretation to you?
