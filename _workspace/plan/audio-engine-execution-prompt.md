# Execution brief — Audio Engine v2 (ElevenLabs autonomous path + NotebookLM preserved)

Paste everything below this line into a fresh Claude Code session in
~/PROJECTS/podcast-factory to begin execution. Approved by Asif on 2026-06-12.

---

Execute the approved Audio Engine v2 plan. The plan was designed and approved in a
prior session on 2026-06-12; this brief is the complete, self-contained spec. Do not
re-litigate the design. Work autonomously, halting only at the halt points listed at
the end.

## Mission

Add a fully autonomous audio path to the podcast pipeline using the ElevenLabs v3
text-to-dialogue API, behind a pluggable per-book audio-engine setting, while
preserving the existing Google NotebookLM path byte-identically as the default
engine. The dual-engine pipeline becomes the canonical pipeline (archive-and-replace
via backup branch + merge). Quality of CONTENT outranks cost everywhere; cost
discipline is achieved by construction (render-once, caching, pre-synthesis gating),
never by cutting content.

## Branch + git rules

- Create branch `infra/audio-engine-v2` off up-to-date `develop`. All work happens there.
- Before the final merge to develop, create backup branch
  `backup/pre-audio-engine-v2-<YYYY-MM-DD>` pointing at develop HEAD and push it
  (restore point, same pattern as backup/pre-restructure-2026-05-23-1849).
- Commit in small reviewable units; no PRs (direct merge per repo policy); merging
  `infra/audio-engine-v2` -> develop happens only after the post-merge audit step and
  is announced to Asif first.
- Do NOT touch in-flight book branches (Islamic/the-master-and-the-disciple continues
  on the NotebookLM path untouched).
- ASCII-only in all output files.

## Context to read first (in this order)

1. CLAUDE.md (auto-loaded) — tiers, standing rules, branch policy.
2. `_workspace/experiments/elevenlabs-audition/render_audition.py` and
   `_workspace/experiments/stephanie-interview-prep/generate_audio_v3.py` — proven
   renderer patterns (key resolution, dialogue API, chunking, retries, credit metering).
   API key already in macOS keychain as `elevenlabs_api_key`.
3. `scripts/podcast/_engine.py` — existing engine policy table (TASK_* -> ENGINE_*).
4. `scripts/podcast/_extract_helpers.py` (render_framing) + `build_episode_txt.py` +
   `extract_chapter.py` — per-chapter artifact flow and framing structure.
5. `scripts/podcast/_validators.py`, `_validators_framing.py`, `_rules.py` — the
   deterministic rule system (R-* constants) to extend to dialogue scripts.
6. `scripts/podcast/orchestrate_book.py` + `scripts/podcast/phases/` — phase registry
   (`_progress.PHASES` is the single source of truth) and the per-chapter convergence
   loop (`_authoring/_convergence.py`).
7. `scripts/podcast/normalize_m4a.py` + `transcribe_notebooklm.py` — canonical m4a +
   transcript layout the new renderer must write into directly.
8. A real book's `_system/series-config.yaml` + `_system/glossary.yml`
   (content/Islamic/the-master-and-the-disciple/) — config schema and the
   phonetic<->Arabic glossary asset the pronunciation compiler consumes.

## ElevenLabs facts (verified against docs 2026-06-12)

- Model for all FINAL renders: `eleven_v3` via POST /v1/text-to-dialogue
  (inputs = [{text, voice_id}], ~1 credit/char, API discounted). Flash v2.5
  (0.5 credit/char) may be used ONLY for voice-casting auditions, never finals.
- Keep total characters per dialogue request <= 2,000 (documented reliability limit;
  the experiment's 2,500 must be lowered).
- `seed` (0-4294967295) gives best-effort determinism only; vendor states determinism
  is not guaranteed.
- `pronunciation_dictionary_locators`: up to 3 per request, each pinned by
  dictionary id + version id. Alias rules work on ALL models/languages (PLS lexicon
  format). Phoneme rules (IPA/CMU) are English-only on legacy models — do NOT use.
- v3 supports 70+ languages incl. Arabic and handles mixed-language text; audio tags
  like [warm] are billed as characters — keep sparse.

## The plan — 10 steps, in order

### Step 1 — Engine registry with capability flags
Add `audio_engine` to series-config.yaml schema: `notebooklm` (default) | `elevenlabs`.
Build a pluggable engine registry (one module; adding an engine = one file, per the
extensibility-first rule) where each engine declares: supports_arabic_script,
supports_audio_tags, max_chunk_chars, credit_rate, render_mode (manual|api).
Validators, cost estimator, and orchestrator read the registry — no hardcoded engine
conditionals anywhere. Books with no `audio_engine` field behave byte-identically to
today (golden-fixture test proves it).

### Step 2 — Script authorship step (Claude Max, no API spend)
New per-chapter artifact: a full two-host dialogue script (speaker turns + sparse
performance tags) authored from chapter text + chapter contract + the same steering
constraints the framing encodes (tensions, host roles A=scholar/B=seeker per
R-HOST-ROLE-PARITY, pronunciation terms, MODERNIZE_DENY/SURPRISE_DENY). Length tier
sets a SOFT character band (pacing target, mirrors existing word-count soft bands).
CONTENT COMPLETENESS OUTRANKS THE BAND: never cut a teaching, tension, or contracted
concept to fit characters; if the chapter needs more, exceed the band and flag P2.
Reuse framing-rendering logic as the script spec — do not duplicate rule text.

### Step 3 — Pre-synthesis content gate (the quality core)
Extend the deterministic validators to dialogue scripts: deny lists, honorifics-once,
citation format, doctrinal checks (content/_shared/islam), host-role parity,
no-doubled-phrases, meta-prose. Add a deterministic COVERAGE check: every tension and
concept declared in the chapter contract must be surfaced in the script (no-teaching-
lost analog). Run the podcast-challenger convergence loop on the script with the same
SHIP-READY / SHIP-WITH-CAUTION verdict gate as today; findings go to
_learning/findings.jsonl so the trainer learning loop compounds on this path too.
The gate report includes the exact credit estimate (chars x registry rate).
NOTHING renders before a passing verdict. Validators are engine-aware via the
registry (e.g. the no-Arabic-Unicode rule applies to shared chapter files always,
but to engine-specific script artifacts only when the engine lacks arabic support).

### Step 4 — Pronunciation compiler (glossary -> versioned dictionary)
Deterministic compile of each book's `_system/glossary.yml` into an ElevenLabs
alias-rule pronunciation dictionary (PLS). Upload once per book, record dictionary id
+ version id in book state, pin the version in every render call. Recompile on
glossary change -> new version recorded in the ledger. Scaffold (off by default,
per-book flag) native Arabic-script rendering of Quranic quotes at the script-compile
layer ONLY — shared chapter artifacts stay engine-neutral and phonetic-only. The flag
flips only after Asif approves an audible sample (halt point H2).

### Step 5 — Production renderer (render once, cache forever)
Productionize the experiment renderer into a pipeline step:
- Deterministic chunker at turn boundaries, <= 2,000 chars/request.
- Per-chunk seed derived from the chunk content hash; model id, voice ids, settings,
  dictionary version all pinned.
- Render ledger: input-hash -> output-hash per chunk; chunk cache so revisions
  re-render only changed chunks; never re-render an unchanged chunk.
- Exact credit metering from the subscription meter (the experiment's pattern).
- Free post-render sanity: chars-per-second band per chunk (catches truncation /
  runaway); optional --deep-verify flag routes through existing Azure transcription.
- Output written DIRECTLY to canonical layout: m4a/ch<NN>-<slug>.m4a +
  m4a/transcripts/ch<NN>-<slug>.transcript.txt + transcripts/EP<NN>-<slug>.transcript.txt
  (transcript = the script text, speaker-labeled). No fingerprint matching, no Azure
  STT spend on this path. Voice casting lives in series-config.yaml.

### Step 6 — Orchestrator wiring (autonomy)
At the point where the NotebookLM path halts for manual upload/download, elevenlabs
books flow straight through: author script -> gate -> render -> video -> finalize.
Add ONE halt per book: before the first paid render, surface the deterministic credit
estimate and await approval (halt point H1; mirrors the Tier-2 first-launch spend
gate). Use the existing phase registry (`_progress.PHASES`) — extend it properly, no
parallel phase list. Heartbeat/watchdog rules apply unchanged.

### Step 7 — Astro site: zero-regression + minimal surfacing
The site reads the same canonical m4a/transcript layout — verify reader, studio,
library, intake all behave identically for both engines (no schema breaks; keep
content-paths.ts <-> _paths.py mirrors in sync if touched). Minimal additive
surfacing per the UI-max rule: show each book's audio engine + rendered-credit spend
(from the cost ledger) in the studio book view. ALL site work follows the Cortex HTML
View Quality Standard (skills-staging/html-view-quality/SKILL.md): external CSS/JS
only, zero inline styling, existing --c-* theme unchanged, gate through
html-view-challenger, lint:views + astro check clean.

### Step 8 — End-to-end test harness (both engines)
- Fixture mini-book + mocked ElevenLabs client (no network in tests).
- Full dry-run e2e of BOTH engine paths in the suite.
- Unit coverage: registry routing, script parsing, chunker determinism, seed
  derivation, cache hits, dictionary version pinning, ledger determinism, coverage
  validator, soft-band-never-cuts-content behavior, golden-fixture byte-identity for
  the NotebookLM path.
- Entire existing suite (650+ tests) stays green after every step — run it per step,
  not just at the end.
- Acceptance: live smoke test on ONE real chapter (halt point H1 approves the spend),
  exact credits reported.

### Step 9 — Docs, ledgers, snapshots
Update framework.md, the podcast SKILL.md, challenger agent spec category catalog
(docs-sweep sub-rule applies — _rules.py changes ship with doc updates in the same
merge), plan.yaml + plan.md entries for what shipped, then regenerate dashboard
snapshots (python3 plan-dashboard/scripts/regenerate-snapshots.py) in the same
response as any plan-file edit. Append a session log entry to
_workspace/plan/copilot-handoff.md.

### Step 10 — Archive and replace
Push the backup branch, run the post-merge audit discipline (repo-surgeon --scope
podcast sweep), announce readiness to Asif, then on his go merge
infra/audio-engine-v2 -> develop with --no-ff. Promote the two experiment folders'
learnings: the experiment scripts under _workspace/experiments/elevenlabs-audition/
are superseded by the pipeline renderer — leave the folder in place (audio artifacts
are Asif's), note supersession in the session log.

## Non-negotiable constraints

- CONTENT QUALITY FIRST: no validator, band, or cost mechanism may ever remove or
  truncate substantive content. Cost control = render-once + caching + gating, never
  content cuts. Audio finals are always eleven_v3 (no Flash downgrade).
- ZERO REGRESSION: NotebookLM path byte-identical (golden test); all existing
  functionality retained — phases 0a-0f, phonetics + glossary bake, chapter design
  contracts, enrichment, challenger/fixer convergence, trainer, blueprint, session
  grouping, slide decks (mandatory), video layer (teaching_hybrid + scenic), reading
  edition (book/* + PDF + Drive delivery), publish gates G1-G7, postprod-review,
  vacuum, normalize_m4a + Azure transcription (NotebookLM path), cross-book
  dashboard, full Astro site. The full test suite green is the floor, not the goal.
- DETERMINISM CONTRACT: frozen hashed script artifact; pure-function chunker;
  hash-derived seeds; pinned model/settings/voices/dictionary-version; render ledger
  input-hash -> output-hash; cache prevents re-spend and silent audio changes. Be
  honest in docs that neural TTS is best-effort reproducible; the pipeline's
  determinism is input-determinism + ledger.
- Spend: ElevenLabs credits only at step-5 renders and only after gates; Azure +
  Gemini standing authorization unchanged; Claude work on Max subscription.

## Halt points (the ONLY stops)

- H1: before the first paid ElevenLabs render of any book (incl. the smoke-test
  chapter) — show exact credit estimate, await go.
- H2: Arabic-script recitation flag default — render the two-variant sample
  (romanized+dictionary vs native script, ~1 minute, after H1 covers it), let Asif's
  ear decide; flag stays off until then.
- H3: the final merge to develop (step 10) — announce, await go.
- Genuine blockers or Tier-2 destructive actions per CLAUDE.md.

## Definition of done

A PDF dropped into intake with audio_engine: elevenlabs produces a published series
(audio + transcripts + video + slides + reading edition + site visibility) with zero
manual audio steps beyond H1 approval; every existing book and the NotebookLM path
behave exactly as before; full suite green; lint:views + astro check clean;
html-view-challenger PASS on touched views; post-merge audit clean; develop carries
the merged pipeline and a pushed backup branch preserves the pre-merge state.
