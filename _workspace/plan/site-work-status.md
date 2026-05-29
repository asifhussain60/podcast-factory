<!--
  SINGLE LIVING SOURCE for "where the work stands." The SessionStart hook
  (.claude/hooks/site-work-status.sh) injects this into every new conversation so
  the next session inherits context with zero re-reminding (WC7e). KEEP IT SHORT and
  CURRENT — update the fields at the end of any session. Stale status is worse than none.
-->
# Current work — status

**Last updated:** 2026-05-29

**Active priority: the intelligence + podcast pipeline (Wisdom Corpus Program).**
First step shipped — the corpus-population ENGINE, proven end-to-end on the on-disk
wisdom/teaching material: tradition stamped on every atom (fatimid-ismaili), a
source-agnostic tiered dedup engine (exact + near-duplicate → variants / human-review
queue, non-destructive, idempotent), and a runner. Verified: 122 chapters → 628 atoms,
tradition 628/628, idempotent re-run, 3 borderline review candidates, 0 false merges.
Run `python3 scripts/podcast/intelligence/populate_corpus.py --verify-idempotent` to rebuild.

**Waiting on you:** the other three source databases. The Quran + scholarly DBs aren't
on disk and the teaching-sessions app needs a dump — you said you'll provide them later.
Their per-source importers are deferred until they arrive; the engine already has the
slots (see `SOURCES` in populate_corpus.py).

**RD COMPLETE (awaiting consolidation into a plan):** multi-source intake & reconciliation
+ the chapter-reader redesign. All decisions recorded:
- `09-source-intake-decisions.md` — SI-1..SI-7: spine+layered alignment; hybrid engine-by-strength
  (Gemini bulk / Claude judge / Azure targeted) for the Anwaar two-transcript compare; cheap-signal
  source triage at an early human gate; authority-ranked reconciliation marked in the viewer;
  early-halt placement reusing the gate mechanism; per-book in-context Intake Review panel;
  deterministic spine selection + gate override.
- `10-reader-redesign-decisions.md` — R-1..R-10: two modes (Read audience-grade / Studio review
  cockpit); single contextual inspector; Read = canonical text + subtle verified markers + docked
  audio + Arabic; divergences = inline indicator + side-by-side inspector; persistent synced audio;
  explicit episode↔chapter mapping (Read=episode, Studio=chapter); Studio = the pipeline's single
  human-review cockpit on **TipTap/ProseMirror** (+ jsdiff, floating-ui); FULL capability package
  (minimap/heatmap, marking palette, diff, tracked edits + accept/reject AI, review-queue +
  reviewed-state + one-click stage approval); desktop-only for now.
- Full discussion: `08-source-intake-discussion.md`. Standing prefs: [[ui-max-surfacing]] (richest in-viewer; richer UI is the tiebreaker).

**APPROVED — co-development build on Ayyuhal Walad (plan.yaml WC8).** Walking-skeleton / vertical
slices: each pipeline step built WITH the editor halt that reviews it, run non-destructively on
ayyuhal-walad (own branch, new artifacts only, never re-ship), single-source first. Unification =
common-denominator CORE + attributed ADDITION layers (narrator/explainer/translator), then
noise-strip + enhance (SI-1 refinement). Cadence: **holistic review of ALL completed slices +
pipeline↔UI realignment between every slice** (mandatory gate). Slices: 0 readiness (reconcile
dual phase-naming, install TipTap+jsdiff, ayyuhal branch, editor↔halt write-back) → 1 intake+halt
→ 2 refine+halt → 3 reconcile+halt → 4 knowledge+halt → 5+ deepen.

**SOURCES LANDED (2026-05-29).** Multi-format Ayyuhal set received: 3 PDFs committed (Arabic original,
English superior, scholarly) at `content/drafts/books/ayyuhal-walad/_system/source/multi/` + SOURCES.md;
12 lecture videos (~13GB) + any extracted audio stay LOCAL (transient, deletable after build, restorable
from YouTube) — only pipeline-produced TEXT gets committed. Fixture now exercises the full common-denominator
+ attributed-additions design (Arabic core; English/scholarly/spoken = addition layers). Ready for Slice 0.

**Slice-0 PoC feel-check — PASSED (2026-05-29).** The throwaway TipTap spike at `/studio-poc`
converged through ~10 feedback rounds (FC-1..FC-12 + panel redesign, recorded in
`_workspace/prompts/improvements/10-reader-redesign-decisions.md`). Now proven: verse refs →
compact chapter:verse chip that REPLACES the phrase non-destructively (NotebookLM-safe) with a
dedicated golden floating-ui popover (Amiri Arabic + serif English, size-capped, hover-persist);
Word-level track changes (jsdiff); per-paragraph icon-tag palette + persistent marks (active ring,
text caret, pointer-on-hover); Arabic-overlay toggle (glossary-driven, compound-word-safe) as a
switch; right panel = Controls card (top) + Inspector card (bordered, scroll). Library policy held:
@tiptap/* + @floating-ui/react + diff(jsdiff), no new JS libs. All verified via Playwright
screenshots; zero console errors. **Still terms-only Arabic** (full verse/hadith/poem swap = FC-9,
waits on the unification slice's Arabic source layer).

**Slice-0 FOUNDATION COMPLETE (2026-05-29, branch `book/ayyuhal-walad`).** Built + verified
(headless, zero errors): (1) stage tabs Source→Denoised→Core→Normalized→Augmented (Augmented live
from the prior run; rest pending until slices produce them); (2) editor↔halt WRITE-BACK LOOP —
per-stage approval at `_system/review/<chapter>.json` via `/api/studio/review`, "Approve <stage>"
button + tab ✓, orchestrator reads it to resume; (3) per-stage METRICS tracking
(`stage-metrics.json` + editor strip) incl. "% noise removed" (Denoised-vs-Source delta, fills
when those stages exist); (4) global HOUSE-VOICE standard `docs/standards/house-voice.md` (WC8.8 /
SN-1..SN-6). Library policy held: @tiptap + @floating-ui + jsdiff, no new JS libs.

**BLOCKER for the intake run:** the new stage-PRODUCERS don't exist yet. `intake_book.py` /
`ingest_source.py` produce the OLD architecture (final chapters), not the new `_stages/<chapter>/`
artifacts the tabs read (no script references `_stages`). So "run Slice 1" = first BUILD the
intake stage-producer (WC8.1: extract the 3 multi-format PDFs → align → common-denominator core →
write `_stages/source.md` + `core.md`), THEN run it. Deterministic extraction = no spend;
multi-source alignment = LLM. Asif approved the run; the producer build is the immediate next step.

**Metric note:** "% noise removed" is a Slice-2 (noise-strip / Denoised) number — not produced by
intake. Tracking is wired; the value lands the first time the noise-strip stage runs.

**INTAKE OCR DONE (2026-05-29).** `journal-docintel` upgraded F0→S0 (Asif ran the command;
shared journal resource, so the tier change was his to make). `scripts/podcast/intake_stage.py`
(Azure-only, NO `claude -p`) OCR'd all three PDFs → `_system/source/multi/ocr/{arabic,english,
scholarly}.md`, cached + cost-tracked in `_system/cost-ledger.json` (**~$0.37 total**). Standing
spend authorization + the NO-`claude -p` rule are in memory.

**SOURCE MISLABELING (resolved, see `SOURCE-MAP-CORRECTION.md`).** Files are mislabeled:
`arabic-original`=Arabic ✓, `english-superior`=**Arabic** (2nd commentary edition),
`scholarly`=**English** (old academic translation, Roman-numeral sections I–XVII). So the set =
two Arabic editions + one English academic translation, all DIFFERENT structures, and a different
scheme from the prior run's 5 chapters.

**FULL 5-STAGE CHAIN DONE for ch01 (2026-05-29, one unified lineage, $0.37 total Azure).**
All agent-inline (no `claude -p`, no Claude tokens). Stage tabs all live at /studio-poc:
- source 6,412w → core 6,398w (−0.2%, page furniture) → **denoised 2,606w (−59.3% = "% noise removed")**
  → normalized 1,777w (−31.8%, re-voiced to house style) → augmented 2,037w (+14.6%, knowledge refs).
- ch01 = treatise opening (invocation + framing letter + first counsel), English academic edition
  lines 1598–2163 (before the Hatim story = ch02). `_stages/ch01-frame-and-first-counsel/{source,
  core,denoised,normalized,augmented}.md` + `knowledge-report.json`. Augmented now DERIVES from
  Normalized (legacy prior-run chapter replaced in the new lineage).
- KNOWLEDGE STAGE honest result: 9 references catalogued, **0 verified** — pending the Quran + hadith
  reference DBs (Asif's deliverable). Tradition filter correctly BLOCKED injection (corpus=fatimid-
  ismaili, chapter=Ghazali Sunni-Sufi) — the safe intended behavior.

**RECONCILE SLICE (Slice 3) DONE for ch01 (2026-05-29).** Tri-source aligned inline: Arabic
original = authoritative SPINE (ch01 = OCR lines 13–191, before the Hatim story); the English
academic edition is FAITHFUL (aligns counsel-by-counsel, each 'أيّها الولد' ↔ academic sections
IV–XVII); the 2nd Arabic edition = attributed ADDITIONS (commentary). The Arabic spine carried
**7 explicit Quran citations** the English prose embedded without numbers (18:11, 18:107, 19:59,
7:179, 7:50, 17:79, 51:18) — all **VERIFIED** against the Quran source. So the knowledge stage
went from 0 → **7 Quran-verified references**. Artifacts: `_stages/ch01.../reconcile-report.json`,
updated `knowledge-report.json` + `augmented.md`. ch01 divergences: none material (clean alignment).

**NUMBERED SLICES 0–4 NOW DONE for the ch01 vertical.** Remaining of the numbered set: **Slice 5+
(Deepen)** — Anwaar engine routing, full Studio capability package, audio + episode↔chapter mapping,
consistency pass. Plus the small Slice-0 phase-naming cleanup.

**HONEST PENDING (not blockers, scoped work):**
- Hadith verification needs a hadith reference DB ingested (Asif providing). Quran now verifiable.
- Reconcile done INLINE for ch01 (I read Arabic); scaling to all chapters/books = Gemini bulk +
  Claude judgment (engine routing), not yet built as a script.
- Only ch01 processed; ch02–ch05 pending (breadth). Slide decks (mandatory output) not yet addressed.
- intake_stage.py only OCRs (committed/tracked). Denoise/normalize/reconcile/augment were inline
  agent transforms (artifacts under content/drafts, local-only) — productionize as scripts when stable.

**Parked (resume anytime):**
- *Site redesign* — 5 of 13 views built, 5 text-only and pending. Full audit + resume
  order: `_workspace/plan/site-view-audit.md`. Discuss each page before changing it.
- *Lint backlog* — `npm run lint:views` → 51 non-blocking warnings toward `--strict`
  (the gate already blocks new MUST violations). Burn-down order in the audit doc.

---
*The HTML-view rules (HOW views are built) live in `docs/standards/html-view-quality-digest.md`
(MUST card) + the full standard. WHAT each view shows is agreed per page.*
