# Continuation prompt — Ayyuhal Walad pipeline (WC8 walking skeleton)

**For:** the next Claude session. **Branch:** `book/ayyuhal-walad`. **Read** this + `site-work-status.md`
first. **Standing rules:** never run `claude -p` from scripts (it drains Asif's Max tokens — Claude
reasoning is the AGENT inline; bulk = Gemini; OCR/transcribe = Azure). Azure + Gemini spend is
pre-authorized — track cost in `_system/cost-ledger.json`, never gate on asking.

---

## 1. What this is

We're building the intelligence + podcast pipeline as a **walking skeleton** on **Ayyuhal Walad**
(al-Ghazali's "O Beloved Son") — the **primary test case**. Three things mature in lockstep:
**pipeline** (processing) + **editor** (the Studio review cockpit) + **intelligence** (the wisdom
corpus). Each pipeline step is built with the editor halt that reviews it. Run non-destructively
(new artifacts only; never re-ship the prior run).

## 2. The plan structure — waves & slices

**8 waves total (WC1–WC8).** WC1 (corpus engine) is done — 628 atoms, fatimid-ismaili tradition.
**WC8 is the active wave**: multi-source intake + reconciliation + the Studio cockpit. WC2–WC7 are
the surrounding intelligence/site waves (verify seam, knowledge-read, corpus view, audio, HTML-view
standard) — interleaved into WC8's slices.

**WC8 has 6 slices (0–5):**
| Slice | Name | What it does |
|---|---|---|
| 0 | Foundation | editor, stage tabs, write-back loop, metrics, (phase-naming cleanup) |
| 1 | Intake | OCR the sources → common-denominator Core + attributed additions |
| 2 | Refine / noise-strip | strip apparatus/filler → Denoised (the "% noise removed") |
| 3 | Reconciliation | align sources, pick authoritative rendering, mark divergences |
| 4 | Knowledge | verify references vs the corpus + enrich → Augmented |
| 5+ | Deepen | Anwaar engine (separate fixture), full Studio re-platform, audio+episode map, consistency |

**Plus an interleaved Normalize stage** (house voice, `docs/standards/house-voice.md`).
**The per-chapter layer chain (6 layers):** Source → Core → Denoised → Normalized → Augmented → Narrator(additions).

## 3. COMPLETED (as of 2026-05-30, ~$4.80 Azure+Gemini, zero Claude tokens)

- **Slice 0** ✅ — TipTap Studio editor at `/studio-poc`: chapter switcher (all 5 chapters), 6 stage
  tabs, write-back loop (`/api/studio/review` → `_system/review/<ch>.json`), per-stage metrics,
  golden verse popover, icon tagging, Arabic toggle. (Loose end: phase-naming cleanup.)
- **Slice 1 (Intake)** ✅ — `intake_stage.py` OCR'd all 3 PDFs via Azure Doc Intelligence (S0).
  Found the files are MISLABELED (2 Arabic + 1 English academic — see `SOURCE-MAP-CORRECTION.md`).
- **Slice 2 (Noise-strip)** ✅ — via `gemini_refine.py` (robust; the regex denoiser was brittle).
- **Slice 3 (Reconcile)** ✅ — Arabic original = spine; English academic = faithful; **20 Quran
  citations recovered from the spine + ALL verified** (`quran-citations.json`).
- **Normalize** ✅ — house voice via `gemini_refine.py`, all 5 chapters.
- **Slice 4 (Knowledge)** ✅ — per-chapter Augmented + the 20 verified Quran refs bucketed to chapters.
- **Slice 5 (partial)** ✅ episode↔chapter map; ✅ **all 12 lectures transcribed** (~14.4 h via Azure
  Speech); ✅ **narrator-additions layer on all 5 chapters** (Gemini-cleaned, `narrator_additions.py`).
- **Net:** all 5 chapters fully staged through 6 layers; navigable in the editor.
- **Reusable scripts:** intake_stage, transcribe_audio, transcribe_all_lectures, gemini_refine,
  narrator_additions (all Azure/Gemini, no claude -p).

## 4. REMAINING

- **Hadith verification** — blocked on the hadith reference DB (Asif providing). Quran already verifiable.
- **Slice 5 leftovers:** full Studio RE-PLATFORM (WC8.5 — the real Read+Studio modes; the `/studio-poc`
  is a throwaway spike), consistency pass (WC8.7), Anwaar engine (WC8.3 — a DIFFERENT book, not Ayyuhal).
- **Productionization** — fold the inline/script stages into the orchestrator as proper phases so a
  book runs end-to-end and the editor's approvals actually DRIVE advancement (see §6).
- **Output track** — assemble the processed text into the NotebookLM podcast bundle + the MANDATORY
  slide decks.
- **Slice-0 phase-naming cleanup** (small).

## 5. Mandatory human-review steps

The design has these mandatory human gates:
1. **PoC feel-check** (WC8.0) — ✅ DONE (converged over ~12 rounds).
2. **Holistic-review-per-wave** — between every slice, realign pipeline+editor+intelligence (gate).
3. **Per-stage approval in the editor** (the write-back loop) — the recurring operational review:
   approve each chapter's stage to release the pipeline. (5 chapters × the reviewable stages.)
4. **Finalize halt** — review the clean version before publish.
5. **Publish gate** (Tier 2 — always ask) and **develop→main** production gate (Tier 2).

So: ~2 standing design gates (2,3) recur per book; 1 was one-time (1); 2 are at ship time (4,5).
The one you'll touch repeatedly to move a book forward is **#3 — per-stage approval in the editor.**

## 6. Is the editor ready for you to progress the book? — HONEST ANSWER

**Ready now (you can do these today at `/studio-poc`):**
- Switch between all 5 chapters; view all 6 layers (Source→…→Narrator) and the diffs/metrics between them.
- Read the house-voice Normalized text, the Augmented references, and the Shaykh's Narrator commentary.
- Edit (TipTap), tag paragraphs (icon palette), toggle Arabic, hover verses (golden popover).
- **Mark each stage "approved"** — this writes `_system/review/<chapter>.json`.

**NOT ready yet (the gaps that stop true editor-driven pipeline progression):**
1. **No orchestrator is watching the approvals.** This session's stages were produced by standalone
   scripts, not an automated orchestrator loop. So "approve a stage → the book advances to the next
   stage automatically" is **not closed**. The approval is recorded; nothing consumes it yet.
2. **Editor edits don't save back** to the stage artifacts (edits are in-memory in the throwaway PoC).
3. It's the **throwaway PoC**, not the real Studio (WC8.5) with the full capability package
   (minimap/heatmap, side-by-side divergence diff, tracked edits + accept/reject AI, review-queue).

**Bottom line:** the editor is ready for **review, markup, and approval of every layer of every
chapter** — but to actually *drive the book forward through the pipeline from the editor*, two
things must be built next: **(a) save editor edits back to the stage files, and (b) an orchestrator
that watches `_system/review/<ch>.json` and runs the next stage when you approve.** That is the
"productionization" item, and it is the single highest-leverage next step for editor-driven progress.

## 7. Where to pick up (recommended order)

1. **Productionize** the chain into the orchestrator + close the approve→advance + edit-save-back loop
   (makes the editor actually drive the pipeline — answers the question above).
2. **Output track** — podcast bundle + mandatory slide decks from the processed chapters.
3. Ingest the **hadith DB** when Asif provides it → hadith verification.
4. The **real Studio re-platform** (WC8.5) when ready.

*Cost ledger: `content/drafts/books/ayyuhal-walad/_system/cost-ledger.json`. Editor: `cd plan-dashboard && npm run dev` → `/studio-poc`.*
