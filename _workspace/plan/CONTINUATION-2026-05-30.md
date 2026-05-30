# Continuation prompt — Ayyuhal Walad pipeline (WC8) — for the next session

**Branch:** `book/ayyuhal-walad` (pushed to origin). **Read this + `site-work-status.md` first**
(the SessionStart hook injects the latter automatically).

---

## 0. START HERE — holistic + systematic architectural review (DO THIS FIRST, before building)

Before writing any new code, put on a **senior architect + engineer** hat and review ALL work done
so far — across the earlier waves (WC1–WC7) AND the Wave 8 slices already shipped (0–5) — and answer,
honestly and concretely:

1. **Is everything up to par?** Does each shipped slice actually meet its goal at production quality,
   or did we accept "walking-skeleton" shortcuts that now need hardening?
2. **Any regression?** Did later slices break or weaken earlier ones? (e.g. did the multi-chapter
   refactor weaken the ch01 path; did the Gemini engine change outputs vs the inline ch01 pass; are
   the editor's earlier features — verse popover, tagging, Arabic toggle, write-back — still intact
   across the chapter switcher?) Run the headless checks; re-read the committed artifacts.
3. **Refactoring opportunities?** Five one-off scripts (intake_stage, transcribe_audio,
   transcribe_all_lectures, gemini_refine, narrator_additions) + inline transforms now exist parallel
   to the OLD orchestrate_book phases. Where is the duplication? What should consolidate? Is the
   `_stages/` convention the right seam, or should it merge with the existing phase outputs?
4. **Enhancements?** What's the highest-leverage improvement to quality or reviewer experience?
5. **Unseen risks** — be specific about:
   - **Scalability:** does this survive a 30-chapter book? 50 books? (OCR page caps, Gemini context
     limits, the inline-agent reconcile that doesn't scale, the editor loading ALL chapters server-side.)
   - **Extensibility:** adding a new source type, a new stage, a new tradition — one-file change or
     search-and-replace? (Check against the locked `extensibility-first` rule.)
   - **Cost:** what's the per-book cost at scale (audio transcription dominated at $4.31/book)? Where
     can engine-routing cut it? Is cost tracked end-to-end?
   - **Correctness/doctrine:** the auto-applied normalize is interpretive on doctrinal text — are the
     drift guards real? Is scripture truly verbatim? Did Gemini ever paraphrase a quote?
6. **Cross-session memory:** is `site-work-status.md` + this doc enough for a cold start, or is state
   leaking only into commit messages / local-only artifacts?

Produce a short ranked findings list (severity-tagged) BEFORE proposing the next build. Use the
`podcast-auditor` agent if helpful. Do NOT skip this — it is the explicit ask.

---

## 1. Standing rules (non-negotiable)
- **NEVER** run `claude -p` from scripts (drained Asif's Max tokens once). Claude reasoning = the
  AGENT inline; bulk = Gemini (keychain `gemini_api_key`); OCR/transcribe/translate = Azure.
- Azure + Gemini spend pre-authorized; **track cost** in `_system/cost-ledger.json`, don't gate on asking.
- Plan-first: nothing executes without a plan entry + snapshot + approval. No PRs (push to branch directly).
- Response format: plain English, H2/H3, blockquote callouts, tables for tabular, alphabetized Next.

## 2. Structure: 8 waves; Wave 8 active; now 8 slices (0–7)
WC1 (corpus engine) ✅. The podcast pipeline CORE pre-existed. **Wave 8** builds the EDITOR + multi-source
intake/reconciliation and threads intelligence through each slice. Slices: 0 foundation · 1 intake ·
2 noise-strip · 3 reconcile · 4 knowledge · 5 deepen · **6 productionization (NEW)** · **7 output (NEW)**.
Per-chapter layer chain: Source → Core → Denoised → Normalized → Augmented → Narrator(additions).

## 3. Completed (Ayyuhal Walad, ~$4.80, zero Claude tokens) — all committed + pushed
Slices 0–4 + Normalize DONE for all 5 chapters; Slice 5 partial (episode map ✅, 12 lectures
transcribed ✅, narrator-additions ✅; Studio re-platform/consistency/Anwaar remain). 20 Quran refs
verified. Whole book navigable in `/studio-poc` (chapter switcher + 6 tabs). Artifacts in
`content/drafts/books/ayyuhal-walad/_stages|_system`. Scripts in `scripts/podcast/`.

## 4. Remaining
Slice 5 leftovers (Studio re-platform WC8.5, consistency WC8.7, Anwaar WC8.3=different book);
**Slice 6 productionization** (edit-save-back + orchestrator-watches-approvals — the thing that makes
the editor actually DRIVE the pipeline); **Slice 7 output** (NotebookLM bundle + mandatory slide decks);
hadith verification (awaiting Asif's hadith DB); Slice-0 phase-naming cleanup.

## 5. Mandatory human-review steps
(1) PoC feel-check — ✅ done one-time. (2) Holistic-review-per-wave (between slices). (3) **Per-stage
approval in the editor** — the recurring operational gate. (4) Finalize halt before publish. (5) Publish
+ develop→main gates (Tier 2). The one touched repeatedly to move a book forward is **#3**.

## 6. Editor readiness (honest)
READY: switch all 5 chapters; view all 6 layers + diffs/metrics; edit/tag/Arabic/verse-popover; MARK
stages approved (writes `_system/review/<ch>.json`). NOT YET: (a) no orchestrator consumes approvals →
"approve → advance" not closed; (b) editor edits don't save back to the stage files; (c) it's the
throwaway PoC, not the real Studio (WC8.5). → **Slice 6 closes (a) and (b).**

---

## 7. Wave-8 completion view — FINALIZED RESPONSE TEMPLATE (Asif's target end-state)
_This is the exact table format to render at Wave 8 completion. Columns:
{completion} Status | Slice | Description | Service | Est Cost | Actual Cost | Goal._

### WAVE 8 of 8 — Multi-source Intake, Reconciliation & the Studio Cockpit  *(ACTIVE)*
**Description:** Process a book from multiple raw sources into clean, normalized, reference-verified
chapters, reviewed in the Studio editor — the walking skeleton on Ayyuhal Walad.

**Overall progress:** `███████░░░` ~68%  (slices 0–4 + Normalize done; Slice 5 partial; 6–7 not started)

| Status | Slice | Description | Service | Est Cost | Actual Cost | Goal |
|---|---|---|---|---|---|---|
| ✅ 100% | 0 | Foundation — editor, tabs, write-back, metrics | copilot | $0 | $0 | review cockpit every halt flows into |
| ✅ 100% | 1 | Intake — OCR sources → Source + Core | azure | ~$0.40 | $0.37 | extract raw text + build the spine |
| ✅ 100% | 2 | Noise-strip → Denoised | gemini | ~$0.05 | $0.02 | remove apparatus + filler |
| ✅ 100% | 3 | Reconcile — align editions, mark divergences | claude · azure | ~$0.05 | $0 | authoritative core + 20 verified refs |
| ✅ 100% | — | Normalize (house voice) | gemini | ~$0.05 | $0.03 | one editorial-modern voice |
| ✅ 100% | 4 | Knowledge — verify refs + enrich → Augmented | claude | $0 | $0 | corpus/Quran-verified chapter |
| ◐ 60% | 5 | Deepen — audio+narrator ✅ · Studio re-platform ⬜ · consistency ⬜ | azure · gemini · copilot | ~$5.00 | $4.40 | full layers + final cockpit |
| ⬜ 0% | 6 | Productionization — edit-save-back + orchestrator watches approvals | copilot | ~$0 | — | approving a stage DRIVES the book forward |
| ⬜ 0% | 7 | Output — NotebookLM podcast bundle + mandatory slide decks | gemini · claude | ~$0.20 | — | the audience deliverables |

**Wave 8 total — Est ~$5.60 · Actual $4.80 to date.**
**Service legend:** azure = OCR/transcribe/translate · gemini = bulk LLM · claude = agent reasoning inline · copilot = code/UI by the dev agent.

---
*Editor: `cd plan-dashboard && npm run dev` → `/studio-poc`. Cost ledger:
`content/drafts/books/ayyuhal-walad/_system/cost-ledger.json`.*
