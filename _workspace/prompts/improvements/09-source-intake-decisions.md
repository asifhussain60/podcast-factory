# 09 — Multi-source intake & reconciliation — CONVERGED decisions (2026-05-29, session 2)

> Binding outcomes of the discussion on Asif's two questions: (Q1) how to unify
> multiple sources/formats of the SAME work early, before noise removal, without
> losing key concepts; (Q2) how to compare the two Anwaar transcription routes and
> which engine does it. Full discussion: [08-source-intake-discussion.md](08-source-intake-discussion.md).
> Surrounding decisions already locked: [03-wisdom-corpus-merge.md](03-wisdom-corpus-merge.md) (D1–D9),
> [05-intelligence-podcast-integration.md](05-intelligence-podcast-integration.md) (D10–D18).
> Plan-first gate: these become a plan.yaml entry + snapshot + approval BEFORE any code.

| # | Decision |
|---|---|
| **SI-1 — Unify via canonical spine + layered alignment.** | Don't merge sources into one text. Pick the AUTHORITATIVE source as the structural spine; attach every other source as a ROLE-TAGGED layer (authoritative-text / translation-aid / commentary) keyed to the spine's chapters/sections. Align cheaply first — headings → embeddings → timestamps — and spend the (free, Max-plan) Claude reasoning ONLY on gap-detection + divergence reconciliation. Lives in Phase 04 intake (the locked `pdf \| audio-transcript \| mixed` branch), BEFORE the Phase 05 noise-strip. Nothing is discarded; each source survives as a layer. |
| **SI-2 — Anwaar transcript comparison = hybrid by engine strength.** | Timestamps let the Urdu-native (AI-enhanced) and direct-English transcripts align segment-by-segment for FREE. Then: **Gemini** does the cheap long-context bulk divergence + technical-term-loss scan (taveel/haqaiq/daqaiq); **Claude** (free on Max) adjudicates doctrinal fidelity on the flagged segments only; **Azure** Translator re-translates just the corrupted segments — never the judge. Outcome: the **Urdu-native transcript is the authoritative spine**, direct-English is a fluency cross-check layer (SI-1). Direct-audio-to-English mangles specialized vocabulary; Urdu-native preserves it. |
| **SI-3 — Token guardrail = cheap-signal source triage at the human gate.** | Right after alignment (cheap/structural), compute per source: overlap %, unique passages (gaps filled), divergence count. Recommend a processing TIER per source — **full** / **gap-fill-only** / **skip-as-confirmatory** — and present a one-screen "source budget" at the whole-book human review gate, approved BEFORE any costly pass. Captures the gap-fill upside of multiple sources without paying to fully process redundant material. This IS the "stop me from bad decisions that waste tokens" gate. |
| **SI-4 — Reconciliation = authority-ranked, preserve-all, marked in the viewer.** | The authoritative source wins the CANONICAL rendering; every divergent version is PRESERVED as a tagged annotation (never discarded); routine variation = enrichment. Genuine (esp. doctrinal) conflicts surface as **review markers in the Podcast Factory Astro Site viewer** for Asif to review/resolve — never auto-resolved. Ties directly into the annotation/marker engine (D10) + Wisdom Corpus view (D9). One clean canonical text + a full preserved, reviewable trail. |

## Engine-routing principle (cross-cutting, from Asif's stated priorities)
- **Free first:** timestamps + structural alignment + Claude (Max) reasoning carry the bulk; no metered cost.
- **Gemini** for cheap long-context bulk work (divergence scans, term-loss detection).
- **Azure** (the only metered cost) used sparingly — targeted re-translation only.
- **Never a fixed script** for noise/divergence — the pipeline decides per-content when to invoke LLM vs Azure vs Gemini (Asif: "NEVER use any kind of fixed script… intelligent to know when to use" each).

## Open items — resolutions

- **SI-5 — Halt placement (RESOLVED).** Unify (spine+layer alignment) runs as the last step of intake; the source-budget triage fires at a NEW EARLY approval halt right after it (before cleaning/enrichment), REUSING the existing approval-flag + astro-viewer gate mechanism. Three checkpoints, one mechanism, each a distinct question: (1) early source-budget gate — *what/how much to process*; (2) existing refined-source review — *is the cleaned English faithful before chapter design*; (3) existing finalize — *is the finished book shippable*. Resolves the audit's "two halts" contradiction (each halt has one non-overlapping job). Token gate sits where it has leverage (before spend).
- **SI-6 — Source-budget UI (RESOLVED).** A per-book "Intake Review" panel INSIDE the book's workspace/reader view in the Podcast Factory Astro Site: one row per source (role, overlap %, unique passages, divergences, recommended tier, approve/override) + click-through to preview each layer; writes the gate flag; co-located with the SI-4 divergence markers. Mirrors the planned Wisdom Corpus curation view. Standing preference confirmed: **surface everything possible in the viewer** (memory: ui-max-surfacing) — default to the richest in-viewer option for any pipeline output/decision.

- **SI-7 — Spine selection = deterministic priority + gate override (RESOLVED).** Auto-pick the canonical spine by: (1) original-language primary text if present → (2) most-complete source-language primary transcript → (3) authoritative published translation → (4) commentary/derived. Chosen spine is shown and overridable at the source-budget halt (SI-5/SI-6). Obvious cases resolve automatically (Ayyuhal=Arabic, Anwaar=Urdu-native); genuine ties surface for human choice. Principle: authority = closest to the original work, in its original language, most complete, least derived.

## All source-intake points RESOLVED (SI-1..SI-7).
Reader-redesign thread (the convergence UI for SI-4/SI-6) resolved separately in [10-reader-redesign-decisions.md](10-reader-redesign-decisions.md) (R-1..R-10).

> **Next: consolidate 09 + 10 into one plan.yaml entry + snapshot for approval (plan-first gate) before any code.**
