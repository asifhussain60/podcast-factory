# Continuation prompt — Wave 8, AUTONOMOUS build — Ayyuhal Walad

**Branch:** `book/ayyuhal-walad` (pushed). **Read this + `site-work-status.md` first** (the latter is
auto-injected at session start).

## ★ North-star goal
Build an **automated pipeline that converts ANY content — regardless of form or format — into the
structures NotebookLM needs to generate an audio-overview podcast.** Ayyuhal Walad is the **TEST
CASE**: by the end of Wave 8, **Ayyuhal Walad must be a fully transformed, production-ready book** —
every chapter processed through every layer, the editor able to review/drive it, and the final
NotebookLM podcast bundle + slide decks produced.

## ★ Autonomy mandate (Asif, 2026-05-30)
**Build Wave 8 as far as possible AUTONOMOUSLY — do NOT stop for per-step authorization.** Use your
best judgment and recommend/decide based on the north-star goal and project needs. Azure + Gemini
spend is pre-authorized (track cost in `_system/cost-ledger.json`). Chain through the work; commit +
push descriptively as you go; keep `site-work-status.md` current.

**STOP and present to Asif ONLY when:**
1. **A major-dent decision on the EDITOR** — e.g. designing the full Studio re-platform (Read + Studio
   modes, the capability package). Bring options + a recommendation; let him steer the big shape.
2. **A major-dent decision on the PIPELINE architecture** — e.g. how the new stage-producers
   (intake_stage/gemini_refine/narrator_additions) consolidate with the existing `orchestrate_book`
   phases; the productionization design (how approvals drive advancement). Bring options; let him steer.
3. **The mandatory finalize/publish gate (review [D], Tier-2)** — never auto-publish.
4. **A genuine blocker** — e.g. needs the hadith DB (Asif's deliverable) or an external resource.

Otherwise: **keep going.** Small/mechanical/clearly-correct work needs no check-in.

---

## 0. START HERE — senior-architect review FIRST (before building)
Put on a senior architect + engineer hat and review ALL work so far (WC1–WC7 + Wave 8 slices 0–5).
Answer concretely, produce a short severity-ranked findings list, THEN build:
1. **Up to par?** Does each shipped slice meet its goal at production quality, or are there
   walking-skeleton shortcuts to harden?
2. **Regressions?** Did later work break earlier (multi-chapter vs ch01; Gemini engine vs inline ch01;
   editor features intact across the chapter switcher)? Run the headless checks; re-read artifacts.
3. **Refactoring?** Five one-off scripts + inline transforms now run parallel to the OLD
   `orchestrate_book` phases — consolidate? Is `_stages/` the right seam?
4. **Enhancements?** Highest-leverage quality / reviewer-experience win.
5. **Risks (be specific):** scalability (30-chapter book? 50 books? OCR/Gemini limits; inline-agent
   reconcile doesn't scale; editor loads all chapters server-side), extensibility (new source/stage/
   tradition = one-file change?), cost (per-book at scale — audio dominated at $4.31; engine-routing),
   correctness/doctrine (auto-applied normalize is interpretive — drift guards real? scripture verbatim?).
6. **Cross-session memory** sufficient for a cold start?
Use the `podcast-auditor` agent if helpful.

## 1. Standing rules (non-negotiable)
- **NEVER** `claude -p` from scripts (drained Asif's Max tokens). Claude = agent inline; bulk = Gemini
  (`gemini_api_key`); OCR/transcribe/translate = Azure.
- Plan-first: new work → plan.yaml entry + `cd plan-dashboard && npm run snapshot` + commit. No PRs (push the branch).
- Response format: plain English, H2/H3, blockquote callouts, tables for tabular, alphabetized Next.

## 2. Structure: 8 waves; Wave 8 active; slices 0–7
WC1 (corpus engine) ✅; podcast pipeline CORE pre-existed; **Wave 8 builds the EDITOR + multi-source
intake/reconciliation and threads intelligence through each slice.** Per-chapter layers:
Source → Core → Denoised → Normalized → Augmented → Narrator(additions).

## 3. Done (Ayyuhal, ~$4.80, zero Claude tokens; committed + pushed)
Slices 0–4 + Normalize on all 5 chapters; Slice 5 partial (episode map ✅, 12 lectures transcribed ✅,
narrator layer ✅; Studio re-platform/consistency remain). 20 Quran refs verified. Whole book navigable
in `/studio-poc` (chapter switcher + 6 tabs). Scripts: intake_stage, transcribe_audio,
transcribe_all_lectures, gemini_refine, narrator_additions.

## 4. Remaining to reach "Ayyuhal production-ready" (Wave 8 definition of done)
- **Slice 5 leftovers** — full Studio re-platform (WC8.5 — major-dent EDITOR decision → STOP & present),
  consistency pass (WC8.7). (Anwaar WC8.3 = a different book, out of scope here.)
- **Slice 6 (productionization)** — edit-save-back + an orchestrator that watches
  `_system/review/<ch>.json` and advances on approval; consolidate the new producers with
  `orchestrate_book` (major-dent PIPELINE decision → STOP & present the design).
- **Slice 7 (output)** — the NotebookLM podcast bundle (per-episode .txt + framings, per
  `feedback_notebooklm_instructions_format`) + the MANDATORY slide decks (`feedback_slide_decks_required`).
- **Hadith verification** — Slice 4+ (plan.yaml B5) extracts from KASHKOLE+KQUR via MCP; no external DB needed. Runs before Slice 7.
- **[D] finalize + publish** — Tier-2, STOP & present.

**Done = every chapter through every layer (done) + pipeline productionized + output (podcast bundle +
slide decks) produced + Ayyuhal ready to publish.**

## 5. Mandatory human review — exception-driven, not a gate per step
Per book it collapses to: **[D] finalize/publish (mandatory)**; **[B]/[C] exception-only** (surface only
when a divergence conflict or low-confidence/interpretive item is flagged — were CLEAN on Ayyuhal);
**[A] optional** source-budget cost check. Everything else flows automatically. (Per-slice checks during
the build are temporary 🔧 build-time scaffolding.)

## 6. Editor readiness (honest)
READY: switch all 5 chapters; view all 6 layers + diffs/metrics; edit/tag/Arabic/verse-popover; MARK
stages approved. NOT YET (→ Slice 6): no orchestrator consumes approvals; edits don't save back; it's
the throwaway PoC, not the real Studio.

---

## 7. Wave-8 completion view — CANONICAL TEMPLATE (render Wave 8 like this)
**Review legend:** 🔒 mandatory · ⚠ exception-only · ◽ optional · 🔧 build-time. Slices = numbers, reviews = letters A–D.

| Status | Slice | Description | Service | Est | Actual |
|---|:--:|---|---|--:|--:|
| ✅ | 0 | Build the Studio editor — the review cockpit every halt flows into: stage tabs, approve/write-back loop, per-stage metrics. | Copilot | $0 | $0 |
| ✅ | 1 | OCR the raw source PDFs and build the authoritative spine — the Source and Core layers. | Azure | ~$0.40 | $0.37 |
| ◽ | A | **Optional — source-budget: skip a redundant/expensive source before spending (cost call, multi-source books).** | | | |
| ✅ | 2 | Strip the apparatus and filler from the Core into a clean Denoised layer (auto; spot-check via diff). | Gemini | ~$0.05 | $0.02 |
| ✅ | 3 | Align the editions, pick the authoritative rendering, flag divergences, recover 20 verified Quran citations. | Claude · Azure | ~$0.05 | $0 |
| ⚠ | B | **Exception — adjudicate flagged divergence conflicts (only when sources genuinely disagree; none on ch01).** | | | |
| ✅ | — | Re-voice into one editorial-modern house style (auto-applied; spot-check via diff). | Gemini | ~$0.05 | $0.03 |
| ✅ | 4 | Verify the chapter's references against the corpus and enrich it into the Augmented layer. | Claude | $0 | $0 |
| ⚠ | C | **Exception — only low-confidence references or suggested interpretive enrichments surface for your call.** | | | |
| ✅ | 2-fix | **Retrofix DONE:** SN-7 terminus-technicus guard — `gemini_refine.sn7_guard`+`load_protect_terms` (protect-list from per-book `glossary.yml`, tradition-agnostic), house-voice §2b SN-7, `_rules.R_TERMINUS_PRESERVE`, challenger D6, 9 tests green. Re-ran denoise+normalize on all 5 chapters. Honest finding: Ayyuhal body has NO terminus technicus (clean English translation; all Arabic was footnote apparatus, correctly stripped) — guard is forward-looking for body-Arabic books. augmented.md regen deferred to Slice 4+. | Gemini | ~$0.07 | $0.12 |
| ⬜ | 4+ | Ingest hadith, etymology, and poetry atoms from the wisdom corpus MCP (KASHKOLE+KQUR) — removes the hadith-DB blocker, no external source needed. Fix `extractor.py` `claude -p` violation. | source-library MCP | ~$0 | — |
| ◐ | 5 | Transcribe the 12 lectures and fold the Shaykh's commentary in as the Narrator layer (auto-clean). Pending: Studio re-platform (editorial cockpit), consistency pass. | Azure · Gemini · Copilot | ~$5.00 | $4.40 |
| ⬜ | 5b | Full Studio re-platform — replace the throwaway PoC with a real editorial cockpit. Right panel = stackable editorial cards (Name Resolution, Key Focus, Tone & Register, Forbidden Terms, Required Elements, Audience Calibration). Book-level canonical decisions + per-chapter override. dnd-kit (sortable) + cmdk (corpus search) added. | Copilot | ~$0 | — |
| ⬜ | 5c | Podcaster roles guardrail — bake Teacher/Student/Debater host role dynamics into framing prompts and K6 scoring. host_b switches from Student→Debater on contested claims; debater trigger field in editorial card. | Copilot | ~$0 | — |
| ⬜ | 6 | Close the loop so approving a stage in the editor advances the book — edits save back, orchestrator runs the next stage. | Copilot | ~$0 | — |
| ⬜ | 6b | New Content intake page — upload raw content (PDF / audio / links), set book metadata and editorial defaults (tradition, archetype, audience, initial focus priorities), trigger the intake pipeline from the UI. | Copilot | ~$0 | — |
| ⬜ | 7 | Assemble the chapters into the NotebookLM podcast bundle and the mandatory slide decks. Requires K6 (interest scoring) + 5b/5c (editorial cockpit + roles) before running. | Gemini · Claude | ~$0.20 | — |
| ⬜ | 7b | Generate the video visual layer — per-episode timed image prompts (beat→visual_type→prompt→estimated_timestamp) + auto-generated images via Imagen 3. Outputs: video-prompts.json, video-prompts.md, video-images/*.png. Visual types: scenery, quran_verse, hadith_text, flowchart, concept, portrait. | Gemini text + Imagen 3 | ~$2.50 | — |
| 🔒 | D | **Mandatory — finalize halt + publish gate: review the clean assembled book once before it ships.** | | | |
| | **Total** | **Wave 8 cost** | | **~$8.30** | **$4.80** |

---
*Editor: `cd plan-dashboard && npm run dev` → `/studio-poc`. Cost ledger:
`content/drafts/books/ayyuhal-walad/_system/cost-ledger.json`. Goal restated: ANY content → NotebookLM-ready
structures → audio podcast; Ayyuhal Walad must end Wave 8 production-ready.*
