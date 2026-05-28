# Intelligence Pipeline — Locked Decisions (2026-05-28)

Distilled from the intelligence-pipeline discussion session. Every row is
locked and approved by Asif. This is the authoritative source for Wave I
plan entries and any code that implements them.

---

## Source handling

| # | Decision | Answer |
|---|---|---|
| 1 | Primary source language | Arabic text (when present) is authoritative; Urdu transcript is authoritative when Arabic original is absent |
| 2 | Companion source treatment | All companion sources (English PDFs, YouTube transcripts) are deduplicated in bulk, then evaluated for enrichment value; strict test: "does this teach something the primary does not?" |
| 3 | Historical/biographical content | Strip universally — noise; removed in pre-processing before any LLM cost |
| 4 | Chains of narration / isnads | Strip universally — noise |
| 5 | Incomplete books | Never blocked; pipeline slices what exists; intelligence pipeline supplements depth, not missing content |
| 6 | Original source search | Auto-search at intake (archive.org, IIS catalog, HathiTrust); if missing, logged to `series-config.yaml`, never blocks pipeline |
| 7 | Companion PDF trust calibration | Auto-detect translator at intake (title page scan); metadata-tag fidelity level (literal / interpretive / unknown); dynamic calibration — unknown treated as low-fidelity |

---

## Audio intake (Phase 04 changes)

| # | Decision | Answer |
|---|---|---|
| 8 | Audio intake path | `meta.yml.input_type` branch inside Phase 04 (no new phase number); values: `pdf`, `audio-transcript`, `mixed` |
| 9 | Turboscribe strategy | Urdu mode only for Ismaili lectures; Azure Translator (Urdu → English) + custom terminology glossary |
| 10 | Terminology glossary location | `content/_shared/islam/ismaili-glossary.yml` |
| 11 | Mixed sources | Both paths run and merge before Phase 05; upstream phases are unaffected |
| 12 | Urdu-on-absent-Arabic rule | Urdu transcript is the working authority; Arabic-origin technical terms (ta'wil, haqaiq, daqaiq, etc.) preserved verbatim in Arabic script; phonetics coverage mandatory for every preserved term |

---

## Noise detection (Phase 05 changes)

| # | Decision | Answer |
|---|---|---|
| 13 | Noise detection architecture | Model-driven routing, not fixed regex patterns; routing layer selects cheapest capable model by `input_type` + `tradition` + content complexity |
| 14 | Routing logic | Haiku for structurally obvious noise (lecture openers, repetitive sentence fragments); Sonnet for contextually ambiguous cases; Gemini for tradition-specific patterns it handles well |
| 15 | Audit output | Phase 05 sub-step 1 writes `_system/noise-stripped.jsonl` so Asif can audit what was removed |
| 16 | Execution position | Phase 05 sub-step 1 (before the LLM refinement call); universal — fires for all `input_type` values |

---

## Source Review Gate (Phase 06a — NEW)

| # | Decision | Answer |
|---|---|---|
| 17 | Gate name | "Source Review Gate" |
| 18 | Gate position | After Phase 06 (phonetics), before Phase 07 (chapter-design) |
| 19 | Gate scope | Per-book freeze; other books in the factory run normally |
| 20 | Pre-gate analysis | Phase 06a: Claude Haiku, ~$0.50–1.00/book; checks: teachable core present per chapter, Ismaili/Arabic terms in phonetics glossary, structural noise the automated pass may have missed |
| 21 | Phase 06a output | `_system/review-gate.json` with `warnings[]` array |
| 22 | Approval mechanism | Button in the astro site (always-on at port 4322); CLI fallback `approve_book.py <slug>` |
| 23 | Approval flag storage | `_system/review-gate.json` field `"approved": true` + `approved_at` + `approved_by: "asif"` |
| 24 | Orchestrator guard | `phase_status: awaiting_human_review` must be explicitly handled: orchestrator skips book on every tick until flag is set |
| 25 | Resume mechanism | Orchestrator resumes on next hourly tick after flag is set (no manual restart) |

---

## Phase 11g — per-chapter optimization (NEW)

| # | Decision | Answer |
|---|---|---|
| 26 | Phase name | Phase 11g (following existing `11b` precedent; "per-chapter-optimize") |
| 27 | Position | After Phase 11 (chapter authoring), before Phase 0g (dual-auditor) |
| 28 | Model | Claude Sonnet — NOT Gemini; preserves Phase 0g Gemini independence as second-opinion auditor |
| 29 | Jobs | (1) NotebookLM format hygiene; (2) host-role consistency across episode; (3) teaching-arc check (hook → core teaching → example → application → bridge) |
| 30 | What it does NOT do | Does not change meaning, add knowledge, or regenerate content |

---

## Book Review unified view (Astro site — NEW)

| # | Decision | Answer |
|---|---|---|
| 31 | View name | "Book Review" |
| 32 | Location | Single unified view in the astro site (always-on port 4322) |
| 33 | Two gates in one view | "Source Review Gate" (Phase 06a) and "Publish Review Gate" (Phase 13) both surface here; view shows which gate is currently active |
| 34 | Source Review Gate view content | Chapter list, Phase 06a warnings, word counts, noise-stripped log summary, approve button |
| 35 | Publish Review Gate view content | Episode list, challenger findings, Phase 11g optimization summary, NotebookLM upload checklist, approve button |
| 36 | Edit surface | Podcast-reader (separate; Asif edits source files there); astro site is read-approve only |

---

## Tradition-aware knowledge base (Wave B patch + Wave I)

| # | Decision | Answer |
|---|---|---|
| 37 | Tradition field | Add `tradition` field to ALL atom types (not just `doctrine`); requires schema migration 019+ |
| 38 | Tradition taxonomy v1 | Three values: `sunni`, `ismaili`, `universal` |
| 39 | `meta.yml` field | `tradition_affinity` in each book's `meta.yml` |
| 40 | Augmenter filtering | Augmenter filters by `tradition_affinity` before injecting atoms; `tradition: universal` atoms injectable into any book |
| 41 | Universal atom governance | `universal` atoms contain ONLY the raw source text with no interpretive note; any interpretive content requires an explicit tradition tag |
| 42 | Cross-tradition injection | Not supported in v1; any atom with a tradition-specific interpretive note requires the matching tradition tag — never tagged `universal` to bypass the firewall |
| 43 | Migration requirement | B2.1 patch must land before any new book runs extraction; existing atoms require backfill migration |

---

## Audit findings (to be resolved in plan)

| ID | Severity | Finding |
|---|---|---|
| R1 | 🔴 | Wave B execution state is contradictory in plan.yaml |
| R2 | 🔴 | H2 marked "PENDING APPROVAL" but partially executed |
| R3 | 🔴 | Wave I I3 tradition schema is a Wave B regression — needs B2.1 patch |
| R4 | 🔴 | Orchestrator has no `awaiting_human_review` guard — hourly tick will re-enter halted books |
| R5 | 🔴 | `content/published/README.md` contradicts the new single-source layout |
| R6 | 🔴 | `publish_to_library.py` still physically copies files; conflicts with meta.yml status model |
| G1 | 🟡 | Wave I has zero plan entries |
| G2 | 🟡 | "Phase 11" doesn't exist in PHASE_ORDER — needs phase naming decision |
| G3 | 🟡 | Batches API optimization not applied to podcast orchestrator (only KASHKOLE) |
| G4 | 🟡 | No Gemini API fallback/degradation path in Phase 0g |
| G5 | 🟡 | No prompt-change tracking per chapter |
| P2 | 🟢 | Model version not tracked per chapter output |
| P3 | 🟢 | GSAP ScrollTrigger needs commercial licence for public site |
| P4 | 🟢 | Manual-review queue has no SLA/aging policy |
| P5 | 🟢 | Archetype not validated at intake (before LLM spend) |
| P6 | 🟢 | No structured rollback path for mid-Rasāʾil failures |
| P7 | 🟢 | `tradition: universal` atoms have no governance policy (→ resolved above in row 41/42) |

---

## Phase naming resolution (G2)

"Phase 11" does not exist in the current phase backbone. The per-chapter
authoring phase is `per-chapter` (letter-suffix: `11a`, `11b` are used).
The optimization phase created in this session maps to the existing
convention as a sub-step of the per-chapter authoring handler:

- **Phase 11g** → rename to **`per-chapter-optimize`** in PHASE_ORDER and
  orchestrator-state.json schema; internal sub-step suffix `11g` preserved
  in code for backward-compat with any existing state files.

This resolution must be reflected in Wave I I6 plan entry.
