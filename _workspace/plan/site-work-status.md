<!--
  SINGLE LIVING SOURCE for "where the work stands." The SessionStart hook
  (.claude/hooks/site-work-status.sh) injects this into every new conversation so
  the next session inherits context with zero re-reminding (WC7e). KEEP IT SHORT and
  CURRENT — update the fields at the end of any session. Stale status is worse than none.
-->
# Current work — status

**Last updated:** 2026-05-30

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

**NUMBERED SLICES 0–4 DONE for the ch01 vertical.**

**SLICE 5+ (Deepen) — PARTIAL (cannot be fully completed; multi-feature bucket).** Status per sub-item:
- ✅ Episode↔chapter mapping (WC8.6 part): `_system/episode-chapter-map.json` (EP01–05 ↔ ch01–05, 1:1).
- ✅ Audio intake (WC8.6) — **FULLY DONE**: ffmpeg + `transcribe_audio.py` + `transcribe_all_lectures.py`
  (Azure Speech fast-transcription, cost-tracked, NO claude -p). **All 12 lectures transcribed** →
  `_system/source/lectures/lec01..lec12.txt` (~730K chars, ~14.4 hours of the Shaykh's spoken
  commentary = the narrator/explainer ADDITIONS layer). Transcription cost $4.31.
- ⬜ Anwaar engine routing (WC8.3): BLOCKED — needs the Anwaar book (two transcripts), a different
  fixture we don't have. Impossible on Ayyuhal.
- ⬜ Full Studio re-platform (WC8.5): MAJOR build (real Read + Studio modes; the throwaway PoC de-risked
  the mechanics). Not a one-shot.
- ⬜ Consistency pass (WC8.7): a sweep to run once the real views exist.

So Slice 5+ is genuinely NOT fully completable now: 2 sub-items advanced, 1 blocked (Anwaar), 2 are
substantial builds (Studio re-platform, full audio job). Total Azure cost to date: **$4.67** ($0.37 OCR + $4.31 transcription, 12 lectures).

**PHASES 6 (Python side) + 8 (output bundle + slides) DONE (2026-05-30):**
- Phase 6 Python side: `_stage_gate.py` (review reader/writer module) + `stage_runner.py` (CLI that checks gate + runs next WC8 stage producer). Status command: `python3 scripts/podcast/stage_runner.py --slug ayyuhal-walad --status`. Copilot's "Run next stage" button calls this via subprocess.
- Phase 8 (output): `assemble_bundle.py` (validates chapters/framings/slides, runs 5-axis PEQ, emits NotebookLM upload table) + `generate_slide_decks.py` (Gemini 2.5 Flash, thinking disabled, maxOutputTokens=8000, line-strip post-processing). All 5 slide decks produced. Total Azure+Gemini cost to date: **$5.75** ($0.37 OCR + $4.31 transcription + ~$0.07 retrofix/narrator + ~$0.03 slides). PEQ: EP1–4 WARN, EP5 FAIL (Interest axis low — closing prayer chapter has no modern-relevance signals). ch04 slide deck thin (260 words); slide challenger would flag.

**PHASES 2-fix RETROFIX + 4 (K6) + 5c DONE (2026-05-30):**
- Phase 2-fix retrofix: all 5 Ayyuhal chapters re-run through denoise+normalize with the SN-7 terminus guard live (~$0.04). Artifacts in `_stages/<ch>/{denoised,normalized}.md` are now guard-protected.
- Phase 4 (K6 interest scoring): 5th PEQ axis added (`_quality.py` — weight 0.15, `_interest_score()` deterministic); weights rebalanced (Fidelity 30%, Voice 20%, Structure 18%, Enrichment 17%, Interest 15%); `R_INTEREST_*` constants + `HOST_ROLE_CONTRACT` + `HOST_ROLE_CONTRACT_DEFAULT` in `_rules.py`; Category V (V1–V5) added to challenger spec; `CHALLENGER_VERSION` bumped 2.2 → 2.3.
- Phase 5c (host roles): `HOST_ROLE_CONTRACT` dict (3 presets: teacher/student, teacher/questioner, scholar/debater) in `_rules.py`; 7th editorial card `host_roles` added to `editorial.ts` (cockpit-visible, debater trigger in notes field).

**AUTONOMOUS EXECUTION PLAN — 8 phases (recorded 2026-05-30, authorized by Asif):**

| Phase | Name | Key deliverables | Cost |
|---|---|---|---|
| **0.7** | Dual-platform setup | `.vscode/tasks.json` (9 tasks), `.vscode/launch.json` (5 debug configs), `.vscode/extensions.json`; `.github/copilot-instructions.md` (mirrors CLAUDE.md for Copilot); fix 15 `.github/agents/` stubs with Copilot YAML frontmatter; delete 2 broken stubs | $0 |
| **1** | Plan repair + Tier-0 fixes | Register WC8-0-foundation in plan.yaml; fix extractor.py claude-p; set meta.yml tradition_affinity=sunni-sufi for Ayyuhal; fold wave_8_studio into waves: array; fix I0a/I0b status | $0 |
| **2** | K6-pre: terminus protection + retrofix | R_TERMINUS_PRESERVE in _rules.py; TERMINUS guard in gemini_refine.py; SN-7 in house-voice.md; D6 in challenger; re-run denoise+normalize+augmented for 5 chapters | ~$0.07 |
| **3** | B5: MCP corpus enrichment | ingest_mcp_corpus.py (hadith/etymology/poetry from KASHKOLE+KQUR); run ingest; build KSESSIONS voice exemplar vectors | ~$0 |
| **4** | K6: interest + quality scoring | R_INTEREST_* constants; _interest_score() 5th PEQ axis; Category V V1–V5 in challenger; fix Voice axis; INTEREST CONTRACT in _authoring.py | $0 |
| **5** | Studio re-platform (5b + 5c) | @dnd-kit + cmdk packages; 7 editorial cards; StudioLayout.tsx; /studio page; HOST_ROLE_CONTRACT; K1 Debater carve-out | $0 |
| **6** | Pipeline productionization | Orchestrator reads _system/review/<ch>.json approvals; edit-save-back; "Run next stage" button | $0 |
| **7** | New Content intake (6b) | /new-content wizard; intake API; editorial.json pre-fill | $0 |
| **8** | Output: podcast bundle + slides | assemble_bundle.py; per-episode .txt + framings; slide decks; challenger convergence (5-axis); NotebookLM upload table | ~$0.20 |
| **9** | Video visual layer | generate_video_layer.py — per-episode beat→image prompts with estimated timestamps; Gemini text for prompt authoring; Imagen 3 API for image generation; outputs video-prompts.json + video-prompts.md + video-images/*.png per episode | ~$1.50–$2.50 |

**HONEST PENDING (not blockers, scoped work):**
- **Slice 4+ (plan B5) — BUILD:** ingest hadith/etymology/poetry atoms from MCP (KASHKOLE+KQUR). Zero external DB needed — data is in KASHKOLE already (14 hadith topics TypeID 17 + TypeID 23; binder 5 poetry; KQUR Roots etymology). Script: `ingest_mcp_corpus.py`. Also fix `extractor.py` `claude -p` call. Authorized 2026-05-30.
- Reconcile done INLINE for ch01 (I read Arabic); scaling to all chapters/books = Gemini bulk +
  Claude judgment (engine routing), not yet built as a script.
- Only ch01 processed; ch02–ch05 pending (breadth). Slide decks (mandatory output) not yet addressed.
- intake_stage.py only OCRs (committed/tracked). Denoise/normalize/reconcile/augment were inline
  agent transforms (artifacts under content/drafts, local-only) — productionize as scripts when stable.

- **Slice 2-fix / K6-pre — BUILD (FIRST):** retrofix Arabic terminus technicus stripping in gemini_refine.py (tawil/wilaya/batin being replaced by English translations). Add TERMINUS TECHNICUS guard to both prompt blocks; load protect-list from glossary.yml per-run. Add SN-7 to house-voice standard. Add D6 to Challenger. Re-run denoise+normalize for all 5 Ayyuhal chapters (~$0.07). Must land before Slice 7.
- **Wave K step K6 — BUILD:** add 5th PEQ axis (Interest, weight 0.15) + Challenger Category V (curiosity-building, challenge-defeat arcs, opening hook, modern relevance, no strawman). Also fix Voice axis stub (returns 0.0 — build KSESSIONS exemplar vectors). Authorized 2026-05-30. Prerequisite before Slice 7.
- **Slice 5b — BUILD:** full Studio re-platform (replaces /studio-poc). 3-column layout; right panel = 6 stackable editorial cards (Name Resolution, Key Focus, Tone, Forbidden Terms, Required Elements, Audience Calibration). Book-level canonical + per-chapter override. New packages: dnd-kit (sortable), cmdk (corpus search). Authorized 2026-05-30.
- **Slice 5c — BUILD:** Podcaster roles guardrail — Teacher/Student/Debater host dynamics. HOST_ROLE_CONTRACT in framing prompt; debater trigger field in HostRoles card (7th editorial card). Authorized 2026-05-30.
- **Slice 6b — BUILD:** New Content intake page (/new-content) — 3-step wizard: upload content, set book metadata, configure editorial defaults. Tier 2 on submit (triggers Azure intake). Authorized 2026-05-30.

**Parked (resume anytime):**
- *Site redesign* — 5 of 13 views built, 5 text-only and pending. Full audit + resume
  order: `_workspace/plan/site-view-audit.md`. Discuss each page before changing it.
- *Lint backlog* — `npm run lint:views` → 51 non-blocking warnings toward `--strict`
  (the gate already blocks new MUST violations). Burn-down order in the audit doc.

---
*The HTML-view rules (HOW views are built) live in `docs/standards/html-view-quality-digest.md`
(MUST card) + the full standard. WHAT each view shows is agreed per page.*

**WHOLE BOOK STAGED through NORMALIZE (2026-05-29).** All 5 chapters now have Source → Core →
Denoised → Normalized in `_stages/<ch>/`. Denoise+normalize done via the new **Gemini engine**
(`scripts/podcast/gemini_refine.py`, REST, no claude -p, ~$0.013/ch) — replacing the brittle
ch01 regex denoiser (it over-stripped ch02 → 289w; Gemini keeps full text). ch01 also has
augmented + reconcile + knowledge + narrator audio; ch02–05 still need per-chapter knowledge/augmented.
- **20 Quran citations verified** book-wide from the Arabic spine → `_system/quran-citations.json`
  (all ✅ against the Quran source). This is the enrichment substrate for the knowledge stage.
- ch03 ("the path") is THIN from the academic edition (498w core) — that edition is condensed; the
  rich path/stations content lives in the lectures/appendix. Enrich ch03 from the 12 lecture
  transcripts later.
- Total Azure+Gemini cost to date: **$4.71** (OCR $0.37 + transcription $4.31 + Gemini refine ~$0.03).
- Editor PoC still hardcoded to ch01; a chapter switcher would surface ch02–05 stages (small enhancement).

**ALL 5 CHAPTERS — COMPLETE 5-STAGE LINEAGE (2026-05-29).** Every chapter now has Source → Core →
Denoised → Normalized → Augmented in `_stages/<ch>/`. Per-chapter knowledge stage built: the 20
verified Quran citations bucketed by Arabic-spine line-range → ch01 (frame), ch02 (5: the eight
benefits' verses), ch03 (5), ch04 (1), ch05 (0 — closing du'a). Each chapter has augmented.md +
knowledge-report.json. Hadith still await a hadith DB. ch03 remains thin (condensed edition) —
enrich from lectures. Total cost ~$4.71. Reusable scripts: intake_stage, transcribe_audio,
transcribe_all_lectures, gemini_refine (all Azure/Gemini, no claude -p).

**A + B DONE (2026-05-29).** B: chapter switcher in the Studio PoC — all 5 chapters selectable,
each with its 6 tabs (Source→Core→Denoised→Normalized→Augmented→Narrator), metrics, approvals.
A: every chapter now has an attributed NARRATOR-ADDITIONS layer (`additions-narrator.md`),
Gemini-cleaned from the mapped lecture transcripts (`scripts/podcast/narrator_additions.py`,
`lecture-chapter-map.json`): ch01 921w, ch02 2960w, ch03 963w (fixes the thin chapter), ch04
1059w, ch05 1731w. Surfaced via the Narrator tab. Verified headless: all 5 chapters × 6 live tabs,
zero errors. **Total Azure+Gemini cost: $4.80.** All processing Azure/Gemini — zero Claude tokens.

**STATE: Ayyuhal Walad is fully processed + navigable.** 5 chapters × {source, core, denoised,
normalized, augmented, narrator-additions} + 20 verified Quran refs + episode/lecture maps.
Reusable scripts: intake_stage, transcribe_audio, transcribe_all_lectures, gemini_refine,
narrator_additions. NEXT options: hadith DB (pending Asif) for hadith verification; the OUTPUT
track (podcast bundle + mandatory slide decks); productionize the inline stages as orchestrator phases.
