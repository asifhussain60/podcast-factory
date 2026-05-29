# Architecture Redesign — Cross-Session Work Ledger

**Canonical source of truth. Read this FIRST on any session resume.**
Owner: Asif + Claude  ·  Started: 2026-05-29  ·  Mode: design convergence (NO code changes until a topic is settled → planned → approved)

Working agreement (locked 2026-05-29):
- Work each topic individually, in dependency order. Claude extracts requirements, challenges weak assumptions, recommends toward clean/robust/DRY/SOLID/scalable/extensible architecture balancing accuracy with efficiency.
- One question at a time; max 3 before proceeding on best assumption; interactive buttons when available.
- Nothing executes until: design settled → plan.yaml/plan.md entry → dashboard snapshot regen → Asif approval.

---

## Prior art — READ before opening any topic (added 2026-05-29)

A large prior convergence exists at `_workspace/prompts/intelligence-pipepine-discussion.md` (1667 lines, authored in the Copilot interregnum). It is NOT stale — it locks a "Wave I" requirements definition that overlaps T2/T3 and cross-cuts T1. Key locked decisions to honour, not re-litigate:
- **Tradition firewall**: every atom carries a `tradition` field; `tradition_affinity` in `meta.yml`; Augmenter filters by it; `tradition: universal` atoms freely injectable (governance rule P7 still open). → **This is a NEW hard requirement on T1**: the corpus must carry per-record tradition provenance, else atoms can't be filtered downstream.
- **Source Review Gate at 06a** (Haiku, ~$0.50–1/book, writes `warnings[]` to `review-gate.json`) + **Publish Review Gate at 13**, both in one Astro view. This is the gate doc 05's proposed `0h-knowledge` phase must feed.
- **Gemini role locked**: consistency/teaching-quality gate, does NOT change meaning; Phase 11g runs Claude Sonnet to preserve Gemini independence in 0g.
- **Audio intake**: `input_type` branch; Turboscribe Urdu → Azure Translator + `ismaili-glossary.yml`; Urdu-on-absent-Arabic = Urdu is working authority, Arabic terms preserved verbatim.
- **Incomplete books**: slice from what exists; the intelligence pipeline supplements depth, never blocks on completeness.

⚠ **Phase-numbering discrepancy (audit G2, unresolved)**: the doc references Phase 04/05/06/06a/11g/13, which do NOT match the real `CANONICAL_PHASES` (0a–0g, per-chapter, per-chapter-optimize, finalize, publish, trainer, merge). Any T3 plan entry MUST translate the doc's phase labels to the real ones before writing plan.yaml.

The doc's closing **Plan Audit** lists 6 regression risks (R1–R6), 5 structural gaps (G1–G5), 7 pattern gaps (P1–P7). Several (R5 README contradiction, R6 publish-script-vs-UI-model) are live regressions from the Copilot content refactor — captured as findings only; NO fixes under the current no-code mandate. Folded into the audit doc `00`.

---

## Topic queue (dependency order)

### T1 — Wisdom corpus merge  ·  STATUS: ✅ CONVERGED 2026-05-29 (D1–D9)
Doc: `03-wisdom-corpus-merge.md`. Decide how KQUR/KASHKOLE/KSESSIONS become ONE deduplicated corpus.
- [x] Q1.1 Source-app lifecycle — **ANSWERED 2026-05-29**: KQUR **frozen**, KASHKOLE **frozen**, KSESSIONS **ACTIVE / needs sync**. → one-time canonical import for KQUR + KASHKOLE; idempotent re-ingest (sync) path required for KSESSIONS only.
- [x] Q1.2 Query logic — **ANSWERED via D4 2026-05-29**: re-express the ~6 useful queries in Python (no T-SQL stored procs carried forward); implied by SQLite choice. Blackbox already does this.
- [x] Q1.3 Transcript scope — **ANSWERED 2026-05-29**: everything injectable, BUT intelligently filtered (exclude content irrelevant to podcast/intelligence needs). No privacy-tier split requested. Dedup is paramount: 40%+ overlap across KASHKOLE↔KSESSIONS and even within books.
- [~] Q1.4 Disambiguate look-alike tables — **BUILD-TIME, no user decision needed**: resolve TopicData/TopicDataUnicode/TopicSimple, SessionDoctrines vs TopicDoctrines, canvas.* by inspecting the dumps during extraction-mapping; canvas.* is app-plumbing → excluded. Documented in doc 03 extraction map.
- [x] Q1.5 Tradition provenance — **ANSWERED 2026-05-29 (D5)**: single tradition. Auto-stamp by source/content-type: teaching+commentary → `fatimid-ismaili`; raw Quran+hadith text → `universal`. No per-record hand-labeling. Honours P7 (universal = raw text only, no interpretive note).
- [x] DECISION: corpus architecture — **Option A CONFIRMED & strengthened (D2, 2026-05-29)**: build a NEW purpose-built Wisdom-corpus database, intelligently extract only podcast/intelligence-relevant content from the 3 sources with aggressive cross- and intra-source dedup, then retire the originals. Designed specifically for podcast-factory, not a lift-and-shift.
- [x] D3 (2026-05-29): KSESSIONS KEPT as the live session-authoring system of record; corpus re-syncs (deduplicated, on-demand) the changed parts from it. KQUR + KASHKOLE deleted after one-time extraction. Retiring KSESSIONS into a single home is a deferred future option, not now (would require building session-authoring tooling into the corpus first).
- [x] D4 (2026-05-29): corpus DB = **SQLite** (server-less, in-repo, machine-agnostic; matches pipeline + reader + blackbox mirror). SQL Server dropped. KSESSIONS stays SQL Server only as the external authoring source we read at sync time; corpus is SQLite. Useful queries re-expressed in Python.
- [x] Canonical Quran — **KQUR (D6, derived 2026-05-29)**: KASHKOLE deleted → its HQ* duplicate Quran removed automatically; KQUR is the single Quran of record, stamped `universal`.
- [x] DECISION: corpus schema carries `tradition` provenance — **YES (D5)**: every record/atom has a `tradition` field; values from auto-stamp. Hard dependency of the locked firewall, satisfied by design.

**T1 STATUS: ✅ CONVERGED 2026-05-29.** Decisions D1–D6 locked. Remaining before plan entry: extraction-map detail (Q1.4, build-time) + dedup-strategy spec (40%+ overlap — to be detailed in doc 03, not a user decision). Plan.yaml/plan.md entry deferred until T2/T3 converge (they may add corpus requirements e.g. verify_and_classify / FTS index) — write all three plan entries holistically to avoid plan churn.

### T2 — MCP blackbox → annotation + silent-marker engine  ·  STATUS: ✅ CONVERGED 2026-05-29 (D10–D13)
Doc: `04-mcp-blackbox-annotation-engine.md`. Make the blackbox drive corpus-verified annotations into the reader.
- [x] Q2.1 Marker storage — **ANSWERED (D10, 2026-05-29)**: SIDECAR (`<chapter>.annotations.json`, position-keyed). **Hard requirement**: markers must render visually IN the chapter EDITOR (already built) with distinct per-type visual treatment, so Asif can visually identify + comment on them easily. Editor is a first-class sidecar consumer, not just the read view; integrates with the existing comment/tag workflow.
- [x] Q2.2 When annotation runs — **ANSWERED (D11, 2026-05-29)**: pipeline phase (auto, deterministic), regenerated on chapter-text change, PLUS a manual "refresh markers" action in the editor for after Asif's edits. Always-present, instant open, no per-read cost.
- [x] Q2.3 Interpretive tags — **ANSWERED (D12, 2026-05-29)**: auto-apply factual reference markers (Quran/hadith/term/topic, corpus-verified); interpretive tags (esoteric/reality/sharia) are SUGGEST-ONLY — shown in editor as dismissible suggestions, applied only on Asif's accept, never auto-applied.
- [x] DECISION (derived, build-time): add `verify_and_classify(span, context)` 7th blackbox tool; build the corpus FTS/lookup index (SQLite per D4, replacing the unbuilt mirror.db plan — Docker no longer required); re-point reader popovers (QuranPopover/TermPopover) off quran.com/Gemini to the corpus/blackbox. **Authority rule (D13)**: corpus is the ONLY source for verified content; NO fallback to quran.com/Gemini for authoritative display — unverifiable spans render `verified=false`, never as authoritative.

**T2 STATUS: ✅ CONVERGED 2026-05-29** (D10–D13). Plan entry deferred to holistic T1+T2+T3 write-up. The Wisdom Corpus UI wave (D9) and the editor marker-render work are the UI surfaces this depends on.

### T3 — Intelligence ↔ podcast pipeline integration  ·  STATUS: ✅ CONVERGED 2026-05-29
Doc: `05-intelligence-podcast-integration.md`. Wire extractor→librarian→augmenter into the orchestrator + feed the reader.
- [x] Q3.2 Single pass, two renderers — **YES (D14)**: ONE knowledge phase reads each chapter once → ONE verified-atom set → two cheap/free renderers (episode-framing injection + reader-sidecar markers from T2). LLM read happens once, cached/skipped when chapter unchanged. DRY; no second extraction pass.
- [x] DECISION phase placement — **D14**: knowledge phase runs after enrich (0e), immediately BEFORE the existing source-review gate (06a) — so 06a reviews what the phase wants to inject and surfaces conflicts. REUSE 06a; NO new gate/halt. (Resolves audit G2 phase-numbering: map to real CANONICAL_PHASES, not the doc's invented "0h/11g/13".)
- [x] Q3.1 + Q3.3 Rollout — **D15**: augmenter tradition-filtered (T1/D5 firewall); pilot end-to-end on **ayyuhal-walad** (5 chapters, already in reader); flip on-by-default for all books only AFTER pilot proves clean.
- [x] Anti-over-engineering guardrails (D14) — NO second reader pass, NO new gate, NO auto conflict-resolution (conflicts surface to human at 06a), DEFER audit nice-to-haves (P1 cross-episode similarity, P2 model-version tracking, embeddings).

---

### T4 — Complete podcast-factory Astro site redesign  ·  STATUS: 🔄 DISCUSS (before implementation)
Asif (2026-05-29): overwhelmed reading dense text in the editor; wants the design understandable VISUALLY on the site. Requirements (HARD):
- Update the appropriate existing views to reflect ALL the converged changes (D1–D18 + the 5-wave program) visually.
- Use a VARIETY of diagram styles — simple flowcharts, UML diagrams, high-level/system diagrams — so it doesn't look like the same diagram repeated.
- INFRASTRUCTURE ARCHITECTURE views exist and are meant for technical teams → add the relevant missing content there too.
- **Always flow diagrams VERTICALLY, not horizontally.**
- **No max-height limit on the SVG diagram containers** (let them grow).
- Asif wants a full REDESIGN discussion FIRST (work-with-me: Claude states how it can help + what it will update per view) BEFORE any implementation.
- Plan-first gate still applies: redesign → plan entry → snapshot → approval → build.
- Decisions to log here: T4.1 diagram tech ✓, T4.2 per-view content map, T4.3 audience split (Asif-facing conceptual vs technical-team infra), T4.4 information architecture / navigation.
- **D19 (T4.1 diagram tech)** — HYBRID: Mermaid (build-time → inline SVG, default top-down/vertical, uncapped height) for new flowcharts/UML/sequence diagrams; keep existing bespoke React/SVG components (C4ContextDiagram, PhaseSwimlaneDiagram, DbArchitecture, TrustBoundaryDFD, etc.) for high-level system + trust-boundary. d3 already a dep; Mermaid is the one new dependency. Vertical-flow + no-height-cap baked into shared diagram styling, not per-page.
- **Site inventory (verified 2026-05-29):** 12 top-level views — index, overview, dashboard, architecture, system-map, infrastructure, db-schema, intelligence, quality, security, plan, annotation-ops — plus library/ (reader+editor) and wisdom/ (corpus area already routed: wisdom/index + wisdom/[shelf]/[book]). Existing diagram components: C4ContextDiagram, PhaseSwimlaneDiagram, StackFlow, StepDiagram, SpendChart, DbArchitecture, InfraColumns, LayerStack, NarrativeScroll, TrustBoundaryDFD, CredentialMap, PipelineSpine, PipelineOverviewRail.
- **D20 (T4.4 information architecture)** — Single guided "Overview" front door: a top-to-bottom narrative (reuse `NarrativeScroll`) that explains the whole system in plain language with vertical diagrams; the 12 detailed views become drill-downs, each labeled by audience ("For you" conceptual vs "For technical teams" infra) and linked from the narrative. Fixes the "too much to read" problem: understand in one pass, drill down on demand.
- **D21 (T4 rollout)** — DESIGN ALL VIEWS ON PAPER FIRST, then build everything (Asif overrode the pilot-first rec). → Author a complete per-view diagram spec (every view, every diagram: type/audience/content/flow) BEFORE any build. Spec = doc `07-site-redesign-spec.md`; then plan entry → snapshot → approval → build. No incremental pilot.
- **Per-view update map (T4.2) → full spec authored in `07-site-redesign-spec.md`.**

## Straightforward items (await go-ahead, not blocking topics)

### S1 — Reader/site plan reconciliation  ·  STATUS: ⏳ ready
Doc: `01`. Reader already in `plan-dashboard/`. Mark SPA wave COMPLETE; add "Reader⇄Wisdom" wave; regen snapshots.

### S2 — YNAB removal + key rotation + memory flush + loop-ledger fix  ·  STATUS: 🔄 PARTLY DONE
Doc: `02`.
- [x] **YNAB MCP removed** 2026-05-29 — stripped from root `.mcp.json` (gitignored) AND `.vscode/mcp.json` (tracked, committed `b463cb4`). source-library MCP intact.
- [x] Plaintext token confirmed **never tracked / never pushed** (gitignored file); redacted from doc 02; wiped from disk.
- [ ] **Asif to ROTATE the YNAB token** in the YNAB account (hygiene — it sat in plaintext). Only Asif can do this.
- [ ] Flush stale `project_podcast_reader.md` (reader is in `plan-dashboard/`, not a `podcast-reader/` dir).
- [ ] Truncate duplicated `loop-intelligence.md` log (~100 dup lines).

### S3 — Ayyuhal Walad annotation prompt  ·  STATUS: ⏳ blocked on T1/T2
Doc: `06`. Executable spec ready; runs once corpus + blackbox engine land. (`anwar` book does not exist — confirm typo vs real.)

### WAVE — Wisdom Corpus UI (D9)  ·  STATUS: ⏳ deferred discussion
Rename the "Kashkole" reader link → "Wisdom Corpus". Build a completely redesigned UI view giving Asif keep/delete curation control over corpus records; hosts the D7 dedup review/confirm queue. Own wave; discuss after T1–T3 design topics. Sits inside the plan-dashboard/reader app (same surface as the library).

---

## Pending inputs from Asif (drop in _workspace/inbox/)
- [ ] Apps frozen vs live (T1.1) — verbal OK
- [ ] KASHKOLE/KSESSIONS data-model / ERD / data dictionary (T1.4) — optional, else infer from dumps
- [ ] `anwar` book source PDF/text — if real
- [ ] External "wisdom corpus" vision note — if one exists

## Decisions log
- **2026-05-29 · D1 (T1.1)** — Source-app lifecycle is MIXED. KQUR frozen, KASHKOLE frozen → one-time canonical import, no sync. KSESSIONS active → corpus must support idempotent re-ingest (re-sync from fresh KSESSIONS dumps without duplicating). KSESSIONS is the only live-authoring surface; the corpus is the consolidation target, not the authoring tool for sessions.
- **2026-05-29 · D2 (T1 architecture)** — Option A CONFIRMED & strengthened: build a NEW purpose-built Wisdom corpus, intelligently extract ONLY podcast/intelligence-relevant content, aggressive dedup (40%+ overlap KASHKOLE↔KSESSIONS and intra-book), retire originals. Everything injectable but intelligently filtered — no irrelevant baggage. NOT a lift-and-shift of app schemas.
- **2026-05-29 · D3 (T1 KSESSIONS)** — KSESSIONS KEPT live as session system-of-record; corpus re-syncs from it. KQUR + KASHKOLE deleted post-extraction. Single-home retirement of KSESSIONS deferred.
- **2026-05-29 · D4 (T1 tech)** — corpus = SQLite (server-less, in-repo, machine-agnostic). SQL Server + Docker dropped for the corpus. Useful queries re-expressed in Python.
- **2026-05-29 · D5 (T1 tradition)** — single tradition; auto-stamp by source/content-type: teaching → `fatimid-ismaili`, raw Quran/hadith → `universal`. Per-record `tradition` field on every atom. No hand-labeling.
- **2026-05-29 · D6 (T1 Quran)** — KQUR is canonical Quran; KASHKOLE HQ* duplicate removed with KASHKOLE.
- **2026-05-29 · D7 (T1 dedup)** — TIERED dedup: high-confidence near-identical → auto-merge to ONE canonical record (most complete/recent wins; others linked as references, not copied). Borderline near-duplicates → review queue (reuse the pipeline's manual-review queue) for human confirm. Ambiguous never auto-merged. Detection = exact + semantic/fuzzy. Balances efficiency (bulk auto-removed) with accuracy (no silent wrong-merge of distinct teachings).
- **2026-05-29 · D8 (T1 KASHKOLE no-retranslate — HARD CONSTRAINT)** — KASHKOLE's Urdu has ALREADY been processed + polished into English (expensive; must NOT be redone). Extraction takes the EXISTING polished English **as-is**. The Urdu OCR is **preserved/stored** (kept as a source field on the record) but is **NEVER retranslated**. KASHKOLE content does NOT pass through Azure Translator or any re-translation step. (The Turboscribe-Urdu → Azure-Translator path applies ONLY to NEW Urdu lecture intake e.g. Anwaar — never to KASHKOLE.) Double-checked: nothing in the corpus build may re-run translation on KASHKOLE.
- **2026-05-29 · D9 (T1 Wisdom Corpus UI — new deferred wave)** — The "Kashkole" link is **renamed "Wisdom Corpus"** and gets a **completely redesigned UI view** giving Asif curation control: keep/delete over corpus records (and the natural home for the D7 dedup review queue). This is its own wave — **WAVE: Wisdom Corpus UI** — to be discussed later (not now). Logged below under deferred waves.
- **T1 ✅ CONVERGED 2026-05-29** (D1–D9). Plan entry deferred to holistic T1+T2+T3 write-up.
- **2026-05-29 · D10 (T2 marker storage)** — sidecar `<chapter>.annotations.json`, position-keyed; prose stays clean, survives re-authoring, matches glossary-sidecar pattern. HARD REQ: markers must visually project into the chapter EDITOR (not only the read view) with distinct per-type treatment so Asif can find + comment on them. Editor consumes the sidecar; integrates with existing comment/tag UI.
- **2026-05-29 · D11 (T2 annotation timing)** — annotation runs as an automatic pipeline phase, regenerated on chapter-text change, + a manual "refresh markers" action in the editor for post-edit refresh. Deterministic, always-present, zero per-read cost.
- **2026-05-29 · D12 (T2 interpretive tags)** — auto-apply factual reference markers; interpretive tags (esoteric/reality/sharia) suggest-only (editor-surfaced, accept-to-apply, never auto). Machine handles facts; human owns doctrine.
- **2026-05-29 · D13 (T2 mechanics + authority)** — add `verify_and_classify` 7th blackbox tool; corpus FTS/lookup index in SQLite (no Docker, supersedes unbuilt mirror.db); re-point reader popovers off quran.com/Gemini to corpus/blackbox; corpus is the SOLE authoritative source — no public-source fallback, unverifiable spans = `verified=false`.
- **T2 ✅ CONVERGED 2026-05-29** (D10–D13).
- **2026-05-29 · D14 (T3 lean integration)** — ONE knowledge phase after enrich (0e), before the existing source-review gate (06a). One LLM read per chapter (cached/skipped if unchanged) → one verified-atom set → two free renderers (podcast-framing injection + reader-sidecar markers). Reuse 06a (no new gate); conflicts surface to human there (no auto-resolution). Anti-over-engineering: no second reader pass, defer similarity/model-version/embedding extras. Maps doc's invented phase numbers to real CANONICAL_PHASES (audit G2).
- **2026-05-29 · D15 (T3 rollout)** — tradition-filtered injection (D5 firewall); pilot end-to-end on ayyuhal-walad; default-on for all books only after pilot proves clean.
- **T3 ✅ CONVERGED 2026-05-29** (D14–D15). **ALL THREE DESIGN TOPICS CONVERGED.** Next per plan-first gate: write ONE holistic plan entry (T1+T2+T3 + deferred Wisdom Corpus UI wave) into plan.yaml/plan.md → regen dashboard snapshots → Asif approval → then (and only then) code.

---

## Gap-fill decisions (holistic plan review, 2026-05-29)
- **D16 (REVISES D2/D4 wording)** — The wisdom corpus IS the existing `CONTENT/knowledge-base/knowledge.db`, NOT a new separate file. Verified live: it already has `external_corpora` (quran/hadith/scholarly registry), `corpus_chapters` (with KASHKOLE `binder_id/binder_slug`, `ingestion_status`, `needs_review`, `correction_notes` — review UI anticipated), `atoms` (type quran/hadith/term/citation/doctrine; **tradition field already present** → audit R3/B2.1 already applied), `atoms_sources`, `atoms_variants`, `manual_review_queue`, and a live annotation system (`paragraph_annotations`/`annotation_tags`/`paragraph_notes`). All corpus tables EMPTY (0 rows); annotation tables have data. The 5 default annotation_tags = esoteric/reality/sharia/mark-for-deletion/mark-for-improvement (exactly the screenshot). → Populate/extend, don't rebuild. D7 review queue = `manual_review_queue`. D10/D12 markers: reference markers from `atoms`; interpretive tags already = `annotation_tags`.

- **D17 (KSESSIONS sync)** — dump-based idempotent re-ingest: Asif drops a refreshed KSESSIONS dump (like the existing `KSessions.sql`), corpus re-ingests + dedupes. No live DB connection, no credentials, machine-agnostic, repeatable. (NOT change-feed — over-engineered for the volume.)
- **D18 (plan scope)** — the holistic plan ABSORBS the prior-converged audio-intake/translation/review-gate/Gemini work (the "Wave I" body) as its own wave, alongside corpus + annotation + intelligence-integration. One complete plan; closes audit G1 (Wave I invisible). Reconcile INTO existing `plan.yaml` (sections: `database`, `intelligence_layer`, `spa`, `waves`, `open_questions`), not a parallel plan.
- **Verified facts (2026-05-29, grounding the plan):** (a) editor exists — `plan-dashboard/src/components/reader/ChapterEditor.tsx` + `ParagraphAnnotationBar.tsx` + `api/annotations*.ts`; D10 marker-render EXTENDS these, not greenfield. (b) plan.yaml is rich (`database`/`intelligence_layer`/`spa`/`open_questions` sections; waves A–E + `waves_ghj`). (c) atoms.tradition already present (audit R3 done).
- **Remaining smaller gaps — proceeding on best assumption (Asif may correct):** (1) data-model mapping — KASHKOLE topics → `external_corpora` corpus_type `scholarly` + `corpus_chapters` (binder/chapter); teaching/sessions → `atoms` (doctrine/term/citation); Quran/hadith → corpus_type quran/hadith. (2) Audit live regressions R5/R6 → recorded as plan/debt items, fixed in execution phase (not under current no-code mode). (3) `anwar` book → still unconfirmed; pilot is `ayyuhal-walad` regardless. (4) Build order → T1 corpus → T2 blackbox+annotation → T3 intelligence phase → Wisdom Corpus UI; audio-intake wave parallel. (5) Pilot = ayyuhal-walad end-to-end after corpus populated.

- **D22 (T4 styling DoD — HARD)** — Site overhaul Definition of Done: (1) do NOT modify existing CSS or colour theme; (2) ZERO inline styling on any view (no `style=`, no inline `<style>`/`<script>` bodies); (3) ALL styling + scripts via external file links. Overrides the old visual-build "Tailwind utilities" note. In plan.yaml WC6 + spec 07.
- **D23 (Cortex craft standard adopted as a skill)** — The HTML View Quality Standard v2.0.0 ("Cortex", `docs/standards/html-view-quality.md`, 74 immutable `REQ-NNN` rules tagged MUST/SHOULD/MAY) is adopted as the canonical craft contract for every WC6 view. Adapted into `skills-staging/html-view-quality/SKILL.md`, rewritten for **Astro delivery**: external-file mechanics (no inline — satisfies D22), the page-shell (skip-link → header → sticky nav → main → footer → back-to-top) mapped to a shared Astro layout, Mermaid rendered at build → inline SVG (D19), `REQ-NNN` IDs preserved verbatim so findings stay citable. **Conflict-resolution rule (Asif, 2026-05-29):** blend both standards; **content + SVG lean Cortex**; delivery mechanics follow D22.
- **D24 (conformance enforced by a challenger agent)** — A new `html-view-challenger` agent (canonical `infra/claude-agents/html-view-challenger.md` + discovery stub `.github/agents/html-view-challenger.agent.md`) validates each built view against Cortex §10 self-audit + §11 automated checks, emits `REQ-NNN`-cited MUST/SHOULD findings, converges fix→re-audit (mirrors `podcast-challenger`), and stamps conformance Level 1/2/3. The per-view DoD becomes "passes the challenger at the declared level" — the D22 styling DoD stops being a hope and becomes an enforced gate.
- **D25 (theme-adapter bridge — no theme change)** — Cortex's 18 base tokens map onto the existing `plan-dashboard/src/styles/theme.css` `--c-*` tokens via a thin adapter (Cortex §9 Pattern B); the 4 missing (`--font-display`, `--font-mono`, `--glass-bg`, `--glass-border`) are added as NEW aliases, never replacing existing values — colour theme untouched (honours D22 + the editorial-modern reader aesthetic). **Audit 2026-05-29:** 15/18 Cortex tokens already have equivalents; ~90 inline `style=` instances + 6 inline `<style>` + 2 inline `<script>` blocks quantified for remediation (WC6 acceptance already commits to repo-wide zero inline styling). **Stale-reference correction:** the active Astro app is `plan-dashboard/` — all 12 architecture views live there; the "podcast-reader/" app referenced in the continuation prompt + memory does not exist on disk.
- **Prompts cleanup (2026-05-29):** Deleted (content absorbed): `intelligence-pipepine-discussion.md` (→ WC5 + ledger; Plan Audit + decision tables preserved in doc 00), `architecture-diagram-brief.md` (→ spec 07 styling standard), `podcast-factory-visual-build.md` (→ spec 07 build methodology + continuation prompt). KEPT (live, not absorbed): `gemini-bundle-auditor.md` (canonical Gem prompt, paired with pack_bundle_for_gemini.py), `loop-intelligence.md` (live loop/heartbeat ledger), `luum-onboarding-bootstrap.md` (pending future-subject prompt, unrelated to PF dev — flag if it should move/delete). Created `CONTINUE-site-overhaul.md` (fresh-session continuation prompt).

## Standing preferences (this repo)
- **NO pull requests for podcast-factory.** Asif's personal project; never run `gh pr create` or offer to open a PR for this repo. Commit + push directly to `develop` (production releases to `main` still need Asif's explicit approval). The VS Code "Create PR" bar is NOT configurable to hide (confirmed 2026-05-29 via docs) — it is inert unless clicked; optional `/feedback` request to Anthropic for a `hidePRBar` setting. Mirrored to AI memory.

## Session actions log
- **2026-05-29** — Committed + pushed `b463cb4` to `origin/develop`: improvement docs + ledger, YNAB MCP removal, snapshot refresh, key redaction. No PR (per standing preference). Pre-flight security scan confirmed no secret entered git.
