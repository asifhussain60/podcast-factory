> **[ARCHIVED — pre-2026-05-22 split | last-checked-against-disk: 2026-05-23]**
>
> Companion to `podcast-plan.yaml`, which was authored before the repo split (2026-05-22) and Phase-9.5 hoist. Many path and script references below have been retired (audit finding AU-A1-001, 2026-05-23-204940). Preserved for historical context; authoritative current sources are `skills-staging/podcast/SKILL.md` and the actual `scripts/podcast/` directory.

# Acceptance Criteria — Master Checklist

**Companion to:** [`podcast-plan.yaml`](./podcast-plan.yaml). Version is tracked in [`./VERSION`](./VERSION) — single source of truth. This file is the SHIP/DONE oracle: every row maps to one verifiable acceptance criterion from the canonical YAML.
**Companion to:** [`view/index.html`](./view/index.html), [`research/findings.md`](./research/findings.md), [`numeric-symbolic-disambiguation-plan.md`](./numeric-symbolic-disambiguation-plan.md) (P4 design doc)
**Audited by:** `/repo-surgeon --plan-only` Pass 5 L10 (acceptance ↔ YAML sync)
**Read by:** journal-challenger Category B, podcast-challenger Category S + Loop N (all consult this file)

Use `- [x]` to mark done; `- [ ]` to mark pending. Group anchors (`### Wave N — …`) match `waves[]` in the YAML; row IDs (e.g., `P1.1`) match `phases[].tasks[].id` OR the prefix of `phases[].tasks[].acceptance[]` / `phases[].acceptance[]` strings (e.g., row `**P22.range**` matches an inline string in `P22.acceptance[]` that begins with `"P22.range ✅ ..."`). The latter form was introduced 2026-05-19 with Changes A–F + content-range — when a phase has many fine-grained acceptance items that don't warrant separate `tasks:` blocks, the convention is to prefix each inline string with a row ID so this md file can reference them. Pass 5 L10 verifies alignment.

**Verdict legend:** ✅ verifiable today · 🟡 verifiable after dependency · 🔒 manual gate · 📊 metric-bound

**Wave kickoff cmds** (autonomous scheduled-task units; see `waves[]` in YAML):
- W1 → `python3 scripts/podcast/run_wave.py 1`
- W2 → `python3 scripts/podcast/run_wave.py 2`
- W3 → `python3 scripts/podcast/run_wave.py 3 --book <slug>`
- W4 → `python3 scripts/podcast/run_wave.py 4`
- W5 → manual: `python3 scripts/podcast/run_wave.py 5 --phase P17` (trigger-gated, not time-scheduled)

---

## Wave 1 — Foundation & Guardrails (Phases P1–P6, parallel-safe, no LLM cost)

### P1 — Journal/podcast boundary verification + CI lock-down 

- [x] **P1.1** ✅ `scripts/podcast/_boundary_check.py` exists; runs <2s; exit 0 on clean tree; non-zero with `file:line` on any write/append/`open(...,'w')` targeting `content/babu-memoir/**`, `content/_shared/**`, `scripts/memoir/**`, `scripts/site/**`
- [x] **P1.1** ✅ Boundary contract documented in `skills-staging/podcast/SKILL.md` (grep returns the section)
- [x] **P1.1** ✅ Whitelisted exception honored: `content/_shared/arabic/06-abjad-numerals.md` (P4) does NOT trip the check
- [x] **P1.2** ✅ "Manual library handoff" section in `skills-staging/podcast/SKILL.md` (grep returns it)
- [x] **P1.2** ✅ `docs/podcast/manual-library-handoff.md` exists; documents promotion workflow
- [x] **P1.2** ✅ `scripts/podcast/_proposal_writer.py` exists; emits schema-valid `proposed-library-entries.md` with frontmatter `schema_version`, `book_slug`, `episode_id`, `generated_by`, `generated_at`
- [ ] **P1.3** 🟡 CI wiring deferred to P16; P1.1 invocation present in `.github/workflows/podcast-isolation.yml`
- [x] **P1.4** ✅ `scripts/podcast/run_wave.py` exists; subcommands 1–5; idempotent (second invocation does zero work when wave already done) — verified by `MainArgvTests.test_done_wave_idempotent_exits_zero`
- [x] **P1.4** ✅ `run_wave.py --check N` computes wave N done_signal from `acceptance-criteria.md` without executing — verified by `MainArgvTests.test_check_flag_reports_without_dispatching`
- [x] **P1.4** ✅ W3 invocation refuses if `cost-ledger.jsonl` shows >$50 in current book (hard cap from P6.3) — verified by `MainArgvTests.test_w3_refuses_when_cost_over_cap` + override path
- [x] **P1.4** ✅ Exit codes: 0=already done, 2=executed+DONE, 3=halted at human-review gate, 1=error — verified by `MainArgvTests` exit-code assertions
- [x] **P1.4** ✅ Exit code 4 = "wave DONE but P-9 invariant violated" — fixture_coverage_pct dropped OR `test_challenger.py` red on develop OR last_trainer_outcome=NEVER_RAN without rationale; scheduler treats as halt-for-inspection — verified by `P9InvariantTests.test_returns_false_on_subprocess_non_zero`

### P2 — E2E test harness 

- [x] **P2.1** ✅ `scripts/podcast/tests/e2e/` exists with `__init__.py`, `conftest.py`, `fixtures/tiny-book/` (3-chapter, ~5k word synthetic source with ≥1 Arabic phrase + ≥1 numeric claim for Loop N)
- [x] **P2.1** 📊 Tiny-book fixture cost <$0.50/full pass
- [x] **P2.2** ✅ `scripts/podcast/tests/e2e/test_full_pipeline.py` exists; `pytest scripts/podcast/tests/e2e/ -v` passes
- [x] **P2.2** ✅ Sunny-day asserts: state.json shows each phase completed in order; refined-english + _phonetics >100 words; every `_chunks/05-refine-english/win-*.in.md` has matching non-zero `win-*.out.md`; ≥1 chapter-contract; ≥1 chapter txt; halts at 09-series-plan gate; heartbeat updates ≤30s (post-P7); **NO `NO ARTIFACT` log line**; `numeric-disambiguation-register.md` present
- [x] **P2.2** ✅ Sunny-day fails when P5 bug class returns (regression toggle `--permission-mode`)
- [x] **P2.2** 📊 Tiny-book sunny-day total <15min, cost <$1
- [ ] **P2.3** ✅ `test_failure_modes.py` exists; mock `claude -p` rc=0 with no file write → typed error; resume-after-kill restores `.out.md` checkpoints; `--retry-phase` on failed 06-phonetics works
- [x] **P2.4** ✅ `.github/workflows/podcast-e2e.yml` exists; PRs touching `scripts/podcast/` fail CI when E2E fails; `skills-staging/podcast/SKILL.md` documents the gate
- [ ] **P2.5** ✅ `scripts/podcast/tests/e2e/test_learning_loop.py` exists; `pytest scripts/podcast/tests/e2e/test_learning_loop.py -v` exits 0
- [ ] **P2.5** ✅ Test asserts: tiny-book run → ≥3 ledger rows appended → `learn_aggregate.py` regenerates `patterns.md` → `learn_propose.py` emits ≥1 proposal → `test_challenger.py` exits 0 → `write_health.py` writes health + appends `health-trend.md`
- [ ] **P2.5** ✅ Idempotency: second run produces no duplicate findings (line-count stable); no new proposal emitted for an already-promoted signature
- [ ] **P2.5** ✅ `.github/workflows/podcast-learning-loop.yml` runs `test_challenger.py` on every PR touching `scripts/podcast/`, `.github/agents/podcast-challenger.agent.md`, or `content/podcast/.skill/handbook/`; red harness BLOCKS merge to develop
- [ ] **P2.5** 🔒 P-9 invariant: `test_challenger.py` exits 0 on `develop` at all times (manual gate at every wave kickoff)
- [ ] **P2.6** ✅ `scripts/podcast/tests/e2e/test_refinement_determinism.py` exists; `pytest scripts/podcast/tests/e2e/test_refinement_determinism.py -v` exits 0
- [ ] **P2.6** ✅ Asserts: Levenshtein ratio across two same-input refinement runs ≥ 0.90; structural-key parity 100% (H2 / paragraph / parenthetical counts); word-count delta < 5%
- [ ] **P2.6** ✅ Committed golden `tests/e2e/fixtures/tiny-book/golden/refined-english.md` exists; PR diff to it requires commit message `GOLDEN-REFRESH: <reason>`
- [ ] **P2.6** 📊 Run cost <$1; wall-clock <10min on tiny-book fixture
- [ ] **P2.6** ✅ Test fails loud if a future `_authoring.py` change drifts the refinement style — operationalizes the bit-stable quality contract

### P3 — Doc regressions from 2026-05-19 legacy cleanup

- [x] **P3.1** ✅ `docs/architecture/podcast-overview.html` paragraph rewritten; chatgpt-portable card points at `skills-staging/podcast/SKILL.md`; deletion annotated
- [x] **P3.2** ✅ Every reference to the 4 deleted basenames (`chatgpt-podcast-skill-prompt`, `folder-cleanup-prompt`, `podcast-refactor-executive-summary`, `podcast-orchestrator-large-books`) outside plan/chats paths is annotated `deleted`/`retired`/`RETIRED`/`DELETED`/`closed`

### P4 — Numeric/Symbolic Disambiguation protocol

- [x] **P4.1** ✅ `content/_shared/arabic/06-abjad-numerals.md` exists; both Mashriqi + Maghribi tables; Hisab al-Jummal practice; verified reference calculations (Allah=66, basmala=786, Muhammad=92, Ali=110) AND Ch-02 worked calcs (kun=70, fayakun=166)
- [x] **P4.1** 🔒 Post-create, file treated as READ-ONLY by both skills (manual gate; Pass 5 L5 enforces no further writes)
- [x] **P4.2** ✅ `content/podcast/.skill/handbook/numeric-symbolic-disambiguation.md` exists; 6 sections (triggers, workflow, enumerate-once rule, anachronism handling, invented-content-is-P0, source-preference register)
- [x] **P4.2** ✅ Handbook references `06-abjad-numerals.md` as abjad authority + `numeric-symbolic-disambiguation-plan.md` as worked-example source
- [x] **P4.3** ✅ `skills-staging/podcast/SKILL.md` pre-read list includes reference #21 (handbook) + SHARED_ARABIC entry now lists 7 files (00–06)
- [x] **P4.4** ✅ `content/podcast/.skill/handbook/pre-refined-source-mode.md` has new "Numeric Disambiguation" scaffolding step + new failure-mode entry #6 (invented enumeration = P0 BLOCKED)
- [ ] **P4.4b** ✅ `content/podcast/.skill/_learning/fixtures/loop_n_numeric_invented/{input.txt,expected.json}` exist (P-9 invariant: every new check ships a fixture)
- [ ] **P4.4b** ✅ `test_challenger.py` covers Loop N detector and exits 0 with 8/8 fixtures (7 prior + 1 Loop N)
- [ ] **P4.4b** ✅ If Loop N check IDs evolve in P4.5, `expected.json` updates in the same commit
- [ ] **P4.5** ✅ podcast-challenger spec contains Loop N section: 5 checks (enumeration coverage, one-time enumeration, abjad cipher coverage, anachronism labeling, no invented content) + severity ladder (P0/P1/P2)
- [ ] **P4.5** ✅ Loop N spec mirrored in `.claude/agents/podcast-challenger.md` (byte-identical post-suffix-strip)
- [ ] **P4.5** ✅ Loop N's `reads_guidance` lists `06-abjad-numerals.md` + `numeric-symbolic-disambiguation.md` handbook
- [ ] **P4.6** ✅ `scripts/podcast/_authoring.py` Phase 07-chapter-design prompt instructs LLM to emit `numeric-disambiguation-register.md`
- [ ] **P4.6** ✅ E2E test (P2.2) verifies register file exists when fixture contains numeric claims
- [x] **P4.7** ✅ Master & Disciple Ch-02 scaffolding updates landed: `02-glossary.md` (5 new entries), `03-source-integrity-notes.md` (Numeric/Symbolic enumeration register + Anachronism register), `ch02-scaffolding.md` (Numeric Disambiguation section + appended NotebookLM instructions), `06-human-review-checklist.md` (§J with 9 checkboxes + failure-mode escalation)
- [x] **P4.7** ✅ Decision log captured: 12-jazāʾir = symbolic+historical; sphere-cipher = NEEDS HUMAN REVIEW; fifth intermediary = NEEDS HUMAN REVIEW
- [x] **P4.8** ✅ `intelligence_sources.podcast.consult_before_any_edit` includes handbook + abjad reference
- [x] **P4.8** ✅ `_workspace/plan/numeric-symbolic-disambiguation-plan.md` header points to its P4 canonical home in podcast-plan.yaml

### P5 — `claude -p` permission-mode fix + artifact validation  *(was P0)*

- [x] **P5.1** ✅ **SHIPPED** — `grep 'claude -p' scripts/podcast/` returns 0 results without `--permission-mode acceptEdits`; both call sites pass the flag: `_authoring.py:99` and `_chunking.py:255` now invoke `[CLAUDE_CMD, "-p", "--permission-mode", "acceptEdits", prompt]`
- [x] **P5.2** ✅ Artifact check raises typed error when `out_path` missing OR `file_size == 0`; no silent `NO ARTIFACT`; stdout/stderr captured — verified by `ChunkingArtifactValidationTests.test_rc_zero_no_artifact_raises_fatal` + `AssertArtifactTests` (4 tests); `ChunkingError` extended with `stdout`/`stderr` kwargs; chapter-design (07) + enrichment (08) loops now raise on rc=0-no-artifact instead of `continue`
- [ ] **P5.3** ✅ P5.1 + P5.2 merged to `develop` BEFORE `book/kitab-al-riyad` resume; book branch rebased clean; `_system/orchestrator-state.json` untouched by rebase; all N windows produce non-empty `.out.md`; phase transitions 05-refine-english → 06-phonetics → 07-chapter-design → 08-enrichment cleanly OR halts cleanly at 09-series-plan gate
- [x] **P5.4** ✅ `scripts/podcast/_phases.py` module exists; `Phase` StrEnum with 14 values in PHASE_ORDER (01-preflight..14-done); `LEGACY_ALIAS` covers 0a..0g + named-step set; `resolve()` raises ValueError on unknown name
- [x] **P5.4** ✅ `scripts/podcast/tests/test_phases.py` asserts: Phase is StrEnum, PHASE_ORDER==tuple(Phase), every LEGACY_ALIAS key resolves, unknown raises ValueError
- [x] **P5.4** ✅ Importing `_phases.py` has zero side effects (no FS writes, no network)
- [x] **P5.4** 🟡 Consumed by W2 P8.6 bulk rewrite — W1 deliverable is the module + tests only; other modules not yet importing it

### P6 — Cost ledger + soft/hard caps  *(was P3.4; decoupled from cancelled SDK migration)*

- [x] **P6.1** ✅ `scripts/podcast/_cost_ledger.py` exists; appends `{ts, phase, step, model, input_tokens, output_tokens, cache_read, cache_create, cost_usd}` to `<book>/_system/cost-ledger.jsonl` after every `claude -p`
- [x] **P6.1** ✅ Pricing table constant; unknown model emits structured warning, not silent zero
- [x] **P6.2** ✅ `scripts/podcast/cost_ledger_summary.py` exits 0; prints structured totals; regenerates `cost-validation.json` (diffable in PR review)
- [x] **P6.2** 🔒 Manual cross-check vs Anthropic console for first W3 book: ledger within ±1%
- [ ] **P6.3** ✅ Soft warning at $20 (heartbeat); hard halt before Phase 07-chapter-design at $50; `--cost-cap-soft` / `--cost-cap-hard` CLI flags AND `state.config.cost_cap_*` keys override
- [ ] **P6.4** ✅ `invoke_trainer()` prompt extended with Protocol §3.5 (read cost-ledger.jsonl, propose remediation if budget exceeded by >20%)
- [ ] **P6.4** ✅ `.github/agents/podcast-trainer.agent.md` Protocol §3 references cost-ledger cross-cut
- [ ] **P6.4** ✅ Trainer end-of-run audit line includes `cost-context: $X.XX`
- [ ] **P6.4** ✅ Q3 row in YAML reopened; closes only when P6.4 lands on develop
- [ ] **P6.4** ✅ Cost-budget overrun (>20% over tier budget) surfaces a P1-class commentary tombstone in `_learning/{promoted,archive}/`

#### P6.5 — Fix `datetime.UTC` AttributeError in cost-ledger append path (surfaced by KaR pilot 2026-05-19)

- [ ] **P6.5.fix** ✅ `grep -n 'datetime.UTC' scripts/podcast/_cost_ledger.py` returns 0 results; replaced with `timezone.utc` (`from datetime import timezone`)
- [ ] **P6.5.compat** ✅ Cost-ledger import + append succeeds on Python 3.10 (verify via CI matrix or local pyenv shim)
- [ ] **P6.5.regression** 📊 On a fresh book run, `<book>/_system/cost-ledger.jsonl` contains ≥1 row per LLM-shellout call; no `cost-ledger append failed` lines in stderr (verify via tail of orchestrator stderr)
- [ ] **P6.5.retroactive** 🔒 KaR's missing ledger rows are NOT retroactively reconstructed — accepted as a one-time gap (P9.0 cost tracking will be approximate; future books are clean)

**Context:** Surfaced during KaR pilot run 2026-05-19 Phase 0c+0d. Every claude -p invocation emitted `[_run_claude_p] cost-ledger append failed: AttributeError("module 'datetime' has no attribute 'UTC'")`. Means `_cost_ledger.py` uses Python-3.11+ idiom `datetime.UTC` while operator runs Python <3.11. Net: cost-ledger.jsonl is empty — cost cap enforcement (P6.3) silently no-ops, trainer cost-context (P6.4) reads empty file, P9.8 yield report has no data. Silent data loss — the exception is caught at `_run_claude_p` and logged then suppressed.

---

## Wave 2 — Observability (Phases P7–P8)

### P7 — Heartbeat + status CLI + wait-banner 

- [ ] **P7.1** ✅ `scripts/podcast/_progress.py` daemon thread writes `<book>/_system/heartbeat.json` atomically every 30s with fields `pid, phase, phase_status, elapsed_in_phase_s, last_chunk_written, last_chunk_mtime, last_log_line, subprocess_pid, hostname, cost_so_far_usd`
- [ ] **P7.1** ✅ daemon=True; orchestrator exit terminates cleanly
- [ ] **P7.1** ✅ Zero impact on `claude -p` timing (side-channel only; verified by comparing wall-clock with/without on tiny-book)
- [ ] **P7.2** ✅ Within 30s of any LLM call starting, heartbeat `label` reflects it (e.g., `05-refine-english · win-007 · 3082 words`); E2E assertion
- [ ] **P7.3** ✅ `scripts/podcast/orchestrator_status.py` runs <1s on 260-page book state; falls back to log tail when heartbeat missing
- [ ] **P7.3** ✅ Exit codes: 0=alive, 2=dead, 1=stale (>5min)
- [ ] **P7.3** ✅ Boxed banner preserves row/column structure of `meta.async_safety.wait_banner_format`; structural-match unit test passes
- [ ] **P7.3** ✅ `--ascii` flag emits ASCII-fallback banner
- [ ] **P7.4** ✅ `<book>/_system/events.jsonl` tails cleanly with `tail -F`; schema `{ts, phase, step, total, label, level, msg}` documented
- [ ] **P7.5** ✅ heartbeat.json includes 6 new learning fields: `learning_findings_appended_this_run`, `learning_proposals_open`, `learning_promoted_total`, `learning_fixture_count`, `last_trainer_outcome`, `challenger_version`
- [ ] **P7.5** ✅ Fields update within 30s of any substrate change (new file appears in `promoted/` or `fixtures/`)
- [ ] **P7.5** ✅ Zero impact on `claude -p` timing (tiny-book wall-clock comparison)

### P8 — Read-only Status API + browser dashboard 

- [ ] **P8.1** ✅ `scripts/podcast/requirements.txt` exists; `pip install -r` succeeds in clean venv
- [ ] **P8.2** ✅ `scripts/podcast/service/` has `__init__.py`, `app.py`, `models.py`, `sources.py`
- [ ] **P8.2** ✅ Server runs on `127.0.0.1:8765`
- [ ] **P8.2** ✅ `/docs` renders OpenAPI
- [ ] **P8.2** ✅ pytest: every non-stream endpoint returns content-type `application/json`; `/books/{slug}/stream` returns `text/event-stream`
- [ ] **P8.2** ✅ New endpoint `/books/{slug}/cost` returns ledger summary
- [ ] **P8.2** ✅ New endpoint `/books/{slug}/disambiguation` returns numeric-disambiguation register as JSON
- [ ] **P8.2** ✅ Service uses filesystem ONLY (no DB, no global state)
- [ ] **P8.3** ✅ Dashboard SPA at `http://127.0.0.1:8765/`; book picker + phase timeline + live event stream + cost panel + P4 disambiguation findings panel
- [ ] **P8.3** ✅ Heartbeat age >2min yellow; >10min red
- [ ] **P8.3** ✅ Disambiguation panel surfaces P0/P1 findings prominently
- [ ] **P8.4** ✅ `infra/launchd/com.journal.podcast-service.plist` passes `plutil -lint`
- [ ] **P8.4** ✅ `docs/podcast/service-startup.md` documents install/verify/behavior-when-down/manual-start
- [ ] **P8.4** ✅ Dashboard shows "service not running — see docs" card on connection failure
- [ ] **P8.5** ✅ `GET /learning` returns repo-wide summary (findings_total, distinct_signatures, proposals_open, promoted_total, archived_total, fixtures_count, challenger_version, last_trainer_run_ts, fixture_coverage_pct)
- [ ] **P8.5** ✅ `GET /books/{slug}/learning` returns per-book substrate state (health_score, health_history, findings by severity, last_trainer_outcome, promoted_during_this_book)
- [ ] **P8.5** ✅ `GET /books/{slug}/health-trend` returns the tail of `health-trend.md`
- [ ] **P8.5** ✅ Dashboard "Learning" tab renders: fixture-coverage % + ↑/↓ vs last week; per-book health row; promotions feed (latest 10 from `_learning/promoted/`)
- [ ] **P8.5** ✅ Red-harness banner appears when `test_challenger.py` exit != 0 (verified by injecting a failing fixture in CI)
- [ ] **P8.5** ✅ 14-day flat-line on `promoted_total` AND zero `archived/` activity → "system isn't learning" warning band

### P8.6 — Bulk phase rename + HTML doc rewrite

- [ ] **P8.6** 🔒 Prereq verified: `orchestrator_status.py --all --json | jq '[.books[] | select(.phase_status=="running" or .phase_status=="failed")] | length'` returns 0 (naturally true in W2 closing window, before W3)
- [ ] **P8.6** ✅ All consumer modules (`orchestrate_book.py`, `_authoring.py`, `_chunking.py`, `_progress.py`, `_convergence.py`, `extract_chapter.py`, `build_episode_txt.py`) import `Phase` enum from `scripts/podcast/_phases.py` instead of literal phase strings
- [ ] **P8.6** ✅ `read_state()` detects `schema_version=1` and rewrites legacy keys via `_phases.LEGACY_ALIAS`; `write_state()` emits `schema_version=2` with new keys only
- [ ] **P8.6** ✅ `--retry-phase` accepts ONLY canonical phase names (e.g., `05-refine-english`); no legacy aliases — `Phase("0b")` raises ValueError
- [ ] **P8.6** ✅ `grep -rE '\b0[a-g]\b' scripts/podcast/ --include='*.py'` returns 0 literal phase-ID matches outside `_phases.LEGACY_ALIAS`
- [ ] **P8.6** ✅ `grep -n '"trainer"' scripts/podcast/ --include='*.py'` returns 0 raw matches outside `_phases.LEGACY_ALIAS`
- [ ] **P8.6** ✅ `tests/e2e/test_phase_rename.py` asserts state.json shows `12-trainer` after the trainer step on a `schema_version=2` fixture; `schema_version=1` fixture migrates; `--retry-phase trainer` resolves to `Phase.TRAINER`
- [ ] **P8.6** ✅ All 5 `docs/architecture/podcast-*.html` files updated in lockstep with code; grep on each for literal `0a..0g` returns 0 results
- [ ] **P8.6** ✅ All 4 `_workspace/plan/view/*.html` files updated (phase-pill grid labels reflect new step names)
- [ ] **P8.6** ✅ `.github/agents/podcast-trainer.agent.md` updated to reference `12-trainer` in any phase-name strings (was P15.4, now folded here)

### P8.7 — D3.js view upgrade (6 diagrams across 4 views, offline-bundled) 

- [ ] **P8.7** ✅ `_workspace/plan/view/assets/js/d3.v7.min.js` exists (~280KB bundled vendor copy; no CDN)
- [ ] **P8.7** ✅ `_workspace/plan/view/assets/js/diagrams.js` exists; registers 6 diagram builders
- [ ] **P8.7** ✅ `_workspace/plan/view/assets/css/diagrams.css` exists; uses only existing `theme.css` CSS variables — no new color literals
- [ ] **P8.7** ✅ D1 wave dependency DAG renders in `index.html` above the wave-row stack; hover shows `done_signal`; click jumps to acceptance anchor
- [ ] **P8.7** ✅ D2 phase Gantt renders in `phased-plan.html`; every phase P1-P20 has a bar; OBSOLETED phases (P15, P16) greyed-out with redirect tooltip
- [ ] **P8.7** ✅ D3 P4 numeric disambiguation decision tree renders in `phased-plan.html`; click to expand/collapse; leaves show P0/P1/P2 verdict
- [ ] **P8.7** ✅ D4 pipeline flowchart renders in `podcast-capabilities.html`; hover shows `_authoring.py` function name
- [ ] **P8.7** ✅ D5 agent topology graph renders in `podcast-capabilities.html`; exactly 4 agent nodes; only trainer has dashed outbound (spec-edit) edges
- [ ] **P8.7** ✅ D6 acceptance heatmap renders in `acceptance-criteria.html`; cell totals sum to current row inventory (~200)
- [ ] **P8.7** ✅ All 6 diagrams render with NO network access (verified by offline test); no `fetch()` of off-domain URLs; no `<script src="http...">` references
- [ ] **P8.7** ✅ Phase IDs cited inside each diagram match `phases[].id` in `podcast-plan.yaml` (Pass 5 L7 conformance)
- [ ] **P8.7** ✅ Accessibility: every diagram has aria-labels + keyboard nav (tabindex) + fallback summary table beneath

### P8.8 — Agent dedup + isolation CI (single-commit collapse of former W5 P16) 

- [ ] **P8.8** ✅ `.github/agents/podcast-challenger.agent.md` exists (materialized with staged Loop N edits from P4.5); byte-identical to former `.claude/agents/podcast-challenger.md` post-suffix-strip
- [ ] **P8.8** ✅ `.github/agents/podcast-extract.agent.md` exists (materialized)
- [ ] **P8.8** ✅ `.github/agents/ui-reviewer.agent.md` exists (materialized)
- [ ] **P8.8** ✅ `infra/claude-agents/` directory removed (`git rm -r`; history preserved)
- [ ] **P8.8** ✅ `scripts/install-claude-skills.sh` rewritten: reads `.github/agents/*.agent.md` and materializes `.claude/agents/<basename without .agent>.md`; second run produces zero diffs (idempotent)
- [ ] **P8.8** ✅ `scripts/check_agent_dedup.py` exists; exits 0 only when name sets across `.github/+.claude/` match after suffix-strip; runs in CI
- [ ] **P8.8** ✅ `scripts/podcast/_isolation_check.py` exists; AST scan fails build on `import scripts.site.*` or `import scripts.memoir.*`; honors P1.1 boundary whitelist
- [ ] **P8.8** ✅ `.github/workflows/podcast-isolation.yml` exists; runs boundary_check + isolation_check + dedup_check + test_challenger.py; all green on clean tree
- [ ] **P8.8** ✅ VS Code / Claude Code agent picker shows each agent exactly once (visual verification in PR description)

### P22 — Operator-review gate after Phase 0a/0b (English-transcript halt)

- [x] **P22.spec** ✅ Phase scoped in `podcast-plan.yaml` with halt-point heuristic (Arabic scan → after 0b; English text-layer → after 0a; markdown → after 0a) — promoted 2026-05-19 per operator opt-in
- [ ] **P22.impl** ✅ `scripts/podcast/_transcript_writer.py` exists; paginator converts `refined-english.md` (or `normalized.md`) → `english-transcript.md` with page breadcrumbs and review margins
- [ ] **P22.impl** ✅ `scripts/podcast/orchestrate_book.py` halts at the detected gate point with phase_status=`halted-for-transcript-review` and exit code 3
- [ ] **P22.impl** ✅ `<book>/english-transcript.md` and `<book>/operator-review.md` written at halt point (top-level, not buried under `_system/`)
- [ ] **P22.impl** ✅ `--approve-transcript` flag resumes from halt; refuses when `operator-review.md` has comments but no `I approve` checkbox
- [ ] **P22.impl** ✅ Downstream phases from the halt point onwards include `<operator-review>` XML block when comments present (Phase 0b+ for English-text-layer/markdown halt-after-0a; Phase 0c+ for Arabic-scan halt-after-0b)
- [ ] **P22.impl** ✅ `--skip-transcript-gate` flag bypasses the halt (backward compat for legacy run modes)
- [ ] **P22.test** ✅ E2E test `test_operator_review_gate.py` asserts: halt at correct phase per source type; comments influence refined.md downstream (Levenshtein delta); operator-review.md never overwritten on resume
- [ ] **P22.docs** ✅ `docs/podcast/operator-review-gate.md` documents operator workflow + when to use `--skip-transcript-gate`
- [ ] **P22.preflight-invariant** 🔒 Hand-authored preflight artifacts NEVER overwritten by orchestrator on resume: if `<book>/_system/source/text/chapters-rationale.md`, `<book>/_system/concept-glossary.md`, or `<book>/_system/registry.md` exists at halt time, `--approve-transcript` must skip the auto-regeneration step for that file. Asaas case validates this. (Without this guardrail, the operator's pre-Phase-0a intelligence is silently destroyed.)
- [ ] **P22.git-policy** ✅ `english-transcript.md` and `operator-review.md` are git-tracked (NOT under .gitignore); operator-review commits follow convention `podcast(<book-slug>): operator transcript review — <one-line summary>` for searchable audit trail

### P22.markers — Phase 0b refinement preserves all page markers (asaas-discovered defect 2026-05-20)

**Context:** Discovered during asaas-al-taveel Phase 0b post-mortem 2026-05-20. Of 49 chunked refinement windows, 7 (003, 007, 016, 019, 029, 038, 039) emitted 0 page markers from inputs containing 7–10 each; net 58/416 page anchors missing from `refined-english.md`. Body content preserved; metadata loss only. Root cause: refinement prompt template does not enforce verbatim preservation of `<!-- page N -->` HTML comments. This breaks P22 operator navigation, P4.10 content-range precision, P21 citation accuracy, and Loop N anchoring. Fix is one-line prompt edit + regression fixture + re-run.

- [ ] **P22.markers.fixture** ✅ `scripts/podcast/tests/test_phase_0b_preserves_page_markers.py` exists; 2-page mock input with `<!-- page 1 -->` + `<!-- page 2 -->`; asserts both markers appear verbatim at correct relative positions in refined output; runs <5s; zero LLM call (uses recorded fixture, not live `claude -p`)
- [ ] **P22.markers.fixture-fails-pre-fix** ✅ Fixture fails against the unfixed prompt template (proves the bug is real, not a phantom)
- [ ] **P22.markers.prompt-fix** ✅ Phase 0b refinement prompt in `scripts/podcast/_authoring.py` (or wherever the refinement system prompt lives) instructs explicitly: "Preserve every `<!-- page N -->` HTML comment verbatim, at the same relative position in the output as in the input. Do NOT collapse adjacent markers, do NOT renumber them, do NOT omit any, do NOT invent new ones." The instruction is in the system prompt section, not the user-turn payload (so it can't be diluted by long inputs).
- [ ] **P22.markers.fixture-passes-post-fix** ✅ Same fixture passes against the fixed prompt template (proves the fix works without a live re-run)
- [ ] **P22.markers.audit-tool** ✅ `scripts/podcast/audit_page_markers.py --book <slug>` exists; compares page-marker set in `_system/source/text/raw-extract.md` vs `refined-english.md`; exits 0 when 1:1 match; exits non-zero with per-chunk breakdown table on mismatch
- [ ] **P22.markers.asaas-staircase** 🔒 Phase 0b re-run executes as smoke (1 chunk — start with win-003, the most-broken) → first-broken-cohort (the 7 originally-broken windows) → full re-run (all 49). Operator halt for sample review between each rung. No silent advance.
- [ ] **P22.markers.asaas-coverage** 📊 After asaas re-run: `refined-english.md` contains 416/416 page markers (vs 358/416 pre-fix); audit tool exits 0
- [ ] **P22.markers.asaas-no-hallucinated** 📊 Zero chunks emit a marker absent from input (vs 1 hallucinated in win-010 pre-fix)
- [ ] **P22.markers.line-ratio** 📊 Per-chunk line-ratio variance (out-lines / in-lines) stays within 50%–130% across all 49 windows post-fix (vs observed 35%–150% pre-fix; signals refinement consistency)
- [ ] **P22.markers.kar-backcompat** 🟡 KaR re-run with fixed prompt produces `refined-english.md` within Levenshtein 0.95 of pre-fix shipped version (proves the prompt fix doesn't regress refinement quality on already-shipped books). Run after asaas validates the fix.
- [ ] **P22.markers.ci** ✅ `tests/test_phase_0b_preserves_page_markers.py` runs on every PR touching `scripts/podcast/_authoring.py` OR `_chunking.py`; red harness BLOCKS merge

### P23 — Phase 0a.5 Named-Entity Recognition pre-seeding via Azure Text Analytics (operator-review automation)

**Context:** P22's operator-review.md §3 (glossary candidates) and §4 (pronunciation table) are currently hand-authored by Claude from `chapters-rationale.md` context — coverage is low (12 terms on asaas) and inconsistent across books. P23 inserts a new Phase 0a.5 between 0b and the operator-review scaffold: run Azure Text Analytics S0 (Language service, prebuilt NER) over `refined-english.md`, emit `_system/candidate_named_entities.json`, then the scaffolder pre-fills §3 and §4 from that file ranked by occurrence frequency. Zero Azure cost on Free F0 tier (5,000 records/month; one asaas-size book is ~150 records). Per-book quality improvement: catches the dozens of intermediate-prophet names (Yūshaʿ bin Nūn, Ṭālūt, Dāwūd, Baḥīrā, etc.) that hand-authored lists miss.

- [ ] **P23.azure-setup** 🔒 Operator creates Text Analytics F0 resource in Azure portal (region `eastus`, same resource group as `journal-docintel`); copies KEY 1 + endpoint to environment variables `AZURE_LANGUAGE_KEY` and `AZURE_LANGUAGE_ENDPOINT`. Verify via `echo $AZURE_LANGUAGE_ENDPOINT` returning the URL.
- [ ] **P23.azure-tier-doc-intel** 🔒 Operator confirms Document Intelligence resource (`journal-docintel`) is on Standard S0 tier with first-year free 500 transactions/month credit (Azure Portal → resource → Pricing tier). Switch to S0 if currently on a higher paid tier.
- [ ] **P23.azure-tier-translator** 🔒 Operator confirms Translator resource is on Standard S1 with first-year free 2M characters/month credit. Switch to S1 if currently elsewhere.
- [ ] **P23.client** ✅ `scripts/podcast/_text_analytics.py` exposes `extract_entities(text: str, language: str = "en") -> list[Entity]` where `Entity` is a dataclass with fields `{text, category, subcategory, confidence, offset, length}`; chunks long inputs to fit per-document char cap (5120 chars); reads credentials from env vars only (no hardcoded keys; passes P17.1 boundary check)
- [ ] **P23.integration** ✅ `scripts/podcast/orchestrate_book.py` Phase 0a.5 runs after Phase 0b completes; invokes `extract_entities()` over `refined-english.md`; emits `_system/candidate_named_entities.json`; phase tracked in `state.json.phases["0a.5"]`
- [ ] **P23.schema** ✅ `_system/candidate_named_entities.json` schema: `{schema_version: 1, generated_at, source_file, source_chars, total_records_used, entities: [{text, category, subcategory, occurrences, sample_offsets, confidence_avg}]}`; sorted by `occurrences` descending; schema documented in `book-dir-layout.md`
- [ ] **P23.operator-review-prefill** ✅ When orchestrator (or Claude in manual P22 mode) scaffolds `operator-review.md`, §3 (glossary) and §4 (pronunciation) sections are pre-filled from `candidate_named_entities.json`: categories `Person`, `Location`, `Organization`, `Event` → §4 pronunciation table (pronunciation hint left blank for operator); other entity categories + recurring abstract terms (caught via Key Phrase Extraction, secondary API call) → §3 glossary candidates
- [ ] **P23.tests** ✅ `scripts/podcast/tests/test_text_analytics.py` exists; uses recorded fixture (no live API call); asserts client returns expected `Entity` structure; tests chunking, edge cases (empty input, non-UTF8), failure modes; runs <5s
- [ ] **P23.fallback** ✅ Phase 0a.5 fails gracefully: if Azure Language API returns non-2xx, network fails, or env vars missing, orchestrator logs warning, emits empty `candidate_named_entities.json`, continues. Operator-review.md scaffolder treats empty entities file as "fall back to hand-authored §3/§4" — current behavior preserved.
- [ ] **P23.cost-ledger** ✅ Each Text Analytics call appends a `cost-ledger.jsonl` row with `service='azure-language'`, `model='ta-S0-prebuilt-ner'`, `records_used=<N>`, `cost_usd=0.0` (free tier); ledger tracks cumulative records used vs 5,000/month F0 cap
- [ ] **P23.cap-warning** ✅ When cumulative `records_used` this calendar-month exceeds 4,500 (90% of F0 cap), orchestrator emits a heartbeat warning + console message; at 5,000 the next call raises `AzureFreeTierExhaustedError` (rather than silently incurring paid-tier charges)
- [x] **P23.docs** ✅ DONE 2026-05-21 — `_workspace/plan/operators/setup/azure-stack.md` exists (relocated from the originally planned `docs/podcast/azure-setup.md`); documents creation flow for all four Azure resources (Document Intelligence, Translator, Language, Speech as optional) including free-tier limits, keychain population via `infra/azure/store-keychain-keys.sh`, key rotation, regional placement, recreate-from-scratch procedure, live verification probe; linked from `mac-studio-primary.md` §13 (Azure resources) and from `_workspace/plan/operators/setup/README.md`. The operators/setup/ folder co-locates this with `machines.md` + `recreate-from-scratch.md` + `runtime-compatibility.md` for a single setup reference surface.
- [ ] **P23.regression** 📊 Compared to hand-authored operator-review.md §3+§4 on a 5-book sample: NER pre-seeded version surfaces ≥2× more named entities; operator approval rate (terms kept vs deleted) stays >70% (proves the candidates are useful, not noise)
- [ ] **P23.computer-vision-fallback** 🟡 `scripts/podcast/adapters/_azure_client.py` includes Computer Vision OCR (Free S1, 5,000 transactions/month) as fallback adapter for books exceeding Document Intelligence's 500 pages/month cap. Forward-looking; not exercised by asaas (416 pages). Promote when first 500+ page book lands and DI cap is hit.
### P24 — podcast-blueprint (content-aware episode-structure planner, slot 05.5-blueprint)

P24 inserts a content-aware classifier + episode planner between the P22 transcript-review resume and the existing `06-phonetics` stage. Three layers — Layer 1 scan/classify (Haiku default, recommends model for Layers 2/3), Layer 2 episode planner, Layer 3 first-run-only arc-conventions.md emitter. Tradition-agnostic; seeds P23's `series-config.yaml` `audience_profile` + `source_tradition`. The four LOCKED decisions (operator-set 2026-05-20 from Air session 7768a31c): (1) name = `podcast-blueprint`; (2) slot = phase `0b.5` / orchestrator slug `05.5-blueprint`; (3) Layer 1 auto-upgrades model for Layers 2-3, `--force-model` overrides; (4) `arc-conventions.md` OPTIONAL on input, agent-seeded DRAFT first run, operator-editable thereafter, Layer 3 NEVER overwrites. Status (2026-05-20): P24.1 surface SHIPPED; P24.2/P24.3 BLOCKED on truncated Air handoff.

- [x] **P24.1.agent-spec** ✅ `infra/claude-agents/podcast-blueprint.md` exists with `name`, `description`, `tools`, `model` frontmatter; mirrors `podcast-extract.md` conventions (shipped 2026-05-20)
- [x] **P24.1.dual-home** ✅ `.github/agents/podcast-blueprint.agent.md` mirrors `infra/` spec; P8.8 deprecation path applies (shipped 2026-05-20)
- [x] **P24.1.skill-scaffold** ✅ `skills-staging/podcast-blueprint/SKILL.md` exists with three-layer protocol stub + locked-decisions block (shipped 2026-05-20)
- [x] **P24.1.schema** ✅ `content/podcast/.skill/handbook/_schemas/classification.schema.json` validates the eleven locked classification fields (`genre_primary`, `density_score`, `narrative_mode`, `structural_units`, `cross_reference_load`, `vocabulary_contestedness`, `recommended_model_for_layer_2`, `recommended_audience_profile`, `recommended_source_tradition`, `recommended_episode_planning_mode`, `rationale`) plus four meta fields (shipped 2026-05-20)
- [x] **P24.1.template** ✅ `content/podcast/.skill/handbook/_templates/arc-conventions.template.md` exists with placeholders for every Layer 1 classification field + commented examples per `planning_mode` (shipped 2026-05-20)
- [x] **P24.1.handbook** ✅ `content/podcast/.skill/handbook/blueprint-protocol.md` documents: when to override classification, what each `planning_mode` means, how to edit `arc-conventions.md`, how the P23 synergy works (shipped 2026-05-20)
- [x] **P24.1.pydantic** ✅ `scripts/podcast/_blueprint_schema.py` defines `Classification` + `EpisodePlanFrontmatter` + `ArcConventionsFrontmatter` `@dataclass(frozen=True)` models; JSON round-trip without loss (shipped 2026-05-20; repo style — no pydantic dep)
- [x] **P24.1.tests** ✅ `scripts/podcast/tests/test_blueprint_schema.py` covers (a) valid round-trip, (b) missing required field fails loud, (c) invalid `genre_primary` enum fails loud, (d) `recommended_model_for_layer_2` enum gates `{haiku, sonnet, opus}`, (e) audience_profile enum, (f) source_tradition null-OR-slug, (g) rationale 50-500 char bounds, (h) projection preserves locked fields — 28 tests green (shipped 2026-05-20)
- [x] **P24.1.runner** ✅ `scripts/podcast/phases/p24_1.py` halt-with-DoR runner prints the four LOCKED decisions + the gate on Air's truncated handoff every launchd tick; auto-marks `P24.1` on first tick after surface ships (shipped 2026-05-20)
- [ ] **P24.1.boundary** 🔒 Boundary check passes: no files outside `content/podcast/`, `scripts/podcast/`, `infra/claude-agents/`, `.github/agents/`, `skills-staging/podcast-blueprint/`, `_workspace/plan/`
- [ ] **P24.2.cli** 🟠 `scripts/podcast/blueprint_book.py <book-slug> --layer 1` emits `<book>/_system/blueprint/classification.json` (BLOCKED on Air handoff)
- [ ] **P24.2.haiku-default** 🟠 Default model is Haiku; cost-ledger records `model_used=claude-haiku-4-5` (BLOCKED on Air handoff)
- [ ] **P24.2.schema-conformant** 🟠 Emitted `classification.json` validates against `classification.schema.json` (BLOCKED on Air handoff)
- [ ] **P24.2.fixtures** 🟠 Five per-genre fixtures (one per `planning_mode`) round-trip cleanly; classifier output matches `expected.json` modulo `source_signature` (BLOCKED on Air handoff)
- [ ] **P24.2.stability** 🟠 Run Layer 1 twice on the same input → byte-identical `classification.json` except `source_signature` timestamp (BLOCKED on Air handoff)
- [ ] **P24.2.golden** 🟠 Ayyuhal Walad `refined-english.md` `classification.json` committed with `GOLDEN-ESTABLISHED` marker; tiny-book `classification.json` same (BLOCKED on Air handoff)
- [ ] **P24.3.cli** 🟠 `blueprint_book.py <book-slug> --layer 2` emits `episode-plan.md`; `--layer 3` emits `arc-conventions.md` first run only (BLOCKED on Air handoff)
- [ ] **P24.3.model-honored** 🟠 Layer 2 uses Layer 1's recommended model unless `--force-model` overrides; cost-ledger records both `model_used` + `model_recommended` (BLOCKED on Air handoff)
- [ ] **P24.3.layer3-no-overwrite** 🔒 If `<book>/arc-conventions.md` exists, Layer 3 is NO-OP — does not read, does not write, does not error; cost-ledger records `skip_reason=arc-conventions-already-present`
- [ ] **P24.3.synergy-patch** 🟠 `<book>/_system/blueprint/proposed-config.yaml` emitted alongside `arc-conventions.md`; `--approve-blueprint` resume merges patch into `<book>/series-config.yaml` (BLOCKED on Air handoff)
- [ ] **P24.3.tests** 🟠 `test_blueprint_planner.py` covers Layer 2 + Layer 3 happy paths, Layer 3 no-overwrite invariant, model-override flag (BLOCKED on Air handoff)
- [ ] **P24.4.slot-registered** 🟠 `scripts/podcast/_phases.py` exports `PHASE_05_5_BLUEPRINT` constant; `05.5-blueprint` appears in `PHASE_ORDER` between `05-refine-english` and `06-phonetics`
- [ ] **P24.4.flags** 🟠 `orchestrate_book.py` accepts `--force-model`, `--auto-approve-blueprint`, `--approve-blueprint`, `--skip-blueprint-gate` with `--help` text
- [ ] **P24.4.shell-halt** 🔶 When `_blueprint.py` is not yet implemented, the slot halts cleanly with rc=3 and prints the DoR block for P24.2/P24.3 — this is the LAND-NOW behavior
- [ ] **P24.4.cost-ledger** 🟠 Cost-ledger row schema extended with `agent_id`, `layer`, `model_used`, `model_recommended`, `model_overridden_by_operator` fields
- [ ] **P24.4.skip-flag** 🟠 `--skip-blueprint-gate` bypasses the slot entirely (zero-regression for legacy run modes; existing in-flight books are NOT replanned)
- [ ] **P24.4.backward-compat** 🔒 Books past `05.5-blueprint` at slot-introduction time (asaas-al-taveel mid-0b, kitab-al-riyad at 0d→0e) are NOT replanned; orchestrator detects past-slot state from `state.json` and skips with audit log entry
- [ ] **P24.5.e2e** 🟠 `test_blueprint_e2e.py` runs blueprint on tiny-book end-to-end; asserts all three layer outputs match goldens (BLOCKED on P24.2 + P24.3 + P24.4)
- [ ] **P24.5.stability** 🟠 Re-running blueprint on the same input produces byte-identical `classification.json` except `source_signature` and Levenshtein ≥0.90 on `episode-plan.md` prose (BLOCKED on P24.2 + P24.3 + P24.4)
- [ ] **P24.5.ci** 🟠 CI workflow runs blueprint E2E on every PR touching `scripts/podcast/_blueprint.py` or `skills-staging/podcast-blueprint/**` (BLOCKED on P24.2 + P24.3 + P24.4)
- [ ] **P24.5.cost-bound** 🟠 Full P24.5 E2E suite costs <$0.50 per run (Haiku Layer 1 + Sonnet Layer 2/3 on tiny-book)
- [x] **P24.6.dor** ✅ `podcast-plan-DoR-appendix.md` has P24 section listing each task with status + blockers + assumptions + ambiguities + operator action (shipped 2026-05-20)
- [x] **P24.6.criteria** ✅ `acceptance-criteria.md` has rows for every P24.x acceptance string (shipped 2026-05-20)
- [x] **P24.6.synergy-doc** ✅ `episode-format-contract.md` has one-line forward reference to `blueprint-protocol.md` explaining the P24 → P23 synergy (shipped 2026-05-20)

---

## Wave 3 — Corpus Validation (Phases P9–P10)

### P9.0 — Kitab al-Riyad (pilot — dogfooding, not formal W3 corpus member)

KaR is the **pilot / dogfooding** run that exercises the pipeline ahead of the formal W3 corpus (P9.1–P9.7). Tracking it here for two reasons: (1) it surfaces real bugs (the stale-running-status bug — see project-orchestrator-resume-bug memory) and proof-points (Pattern 5 series_pattern in registry.md; content-range.md authoring at P22 gate) that the W3 corpus is supposed to validate, so its acceptance evidence is reusable; (2) the operator deserves visibility on what's in flight without having to grep state files. Severity markers reflect **per-book ship-gate** semantics, not pipeline-tooling acceptance.

- [x] **P9.0.scaffold** ✅ `content/podcast/library/books/kitab-al-riyad/` tree exists per book-dir-layout; `_README.md`, `_system/registry.md`, `_system/pronunciation.md`, `_system/mangle-map.md`, `_system/meta-prose-tells.md`, `_system/enrichment-whitelist.md`, `_system/enrichment-log.md` all present (shipped 2026-05-18)
- [x] **P9.0.phase-0a** ✅ Phase 0a (Azure OCR + translate) complete; `_system/source/text/raw-extract.md` written (~462 KB) with `<!-- page N -->` breadcrumbs across 254 PDF pages (completed 2026-05-19 05:25 UTC)
- [x] **P9.0.phase-0b** ✅ Phase 0b (English refinement, chunked across 5 windows) complete; `_system/source/text/refined-english.md` written (3,709 lines / 485 KB); top-level mirror `english-transcript.md` written via paginator passthrough (completed 2026-05-19 19:06 UTC)
- [x] **P9.0.review-gate** ✅ P22-style operator transcript review completed manually 2026-05-19: §6 Bāb N · §M naming chosen; §7 content range 52–232 confirmed (preface in, TOC out); §8 approved. `operator-review.md` checked + git-tracked at book top level. First exercise of the P22 workflow.
- [x] **P9.0.content-range** ✅ `content/podcast/library/books/kitab-al-riyad/_system/source/text/content-range.md` shipped 2026-05-19 declaring `body_starts_at_page: 52`, `body_ends_at_page: 232`. Forward-looking artifact — honored by P4.10 code when shipped; current run processes whole transcript (~$3-5 extra LLM cost; Loop N may spuriously flag editor's 25-work bibliography).
- [x] **P9.0.phase-0c** ✅ Phase 0c (Arabic phonetic pass, chunked across 13 windows) complete 2026-05-19; `_system/source/text/_phonetics.md` populated; no claude -p refusals (committed on `book/kitab-al-riyad` @ `29e7f85`)
- [ ] **P9.0.phase-0d** 🟡 Phase 0d (chapter segmentation) — step 1/3 (TOC + segmentation) ✅; step 2/3 reached sc 004/10 before sc 005/10 timeout (1200s LLM call hung). 6 chapter files + 5 contracts emitted; `chapters/chNN-bab-N-*.txt` slugs honor operator's Bāb/§ preference organically. Partial commit on `book/kitab-al-riyad` @ `b59b4d8`. Resume attempt in flight (task `becvcttj8`).
- [ ] **P9.0.phase-0e** 📊 Phase 0e (enrichment) complete; enrichment-log.md populated per chapter; bāb + fasl added as concept-glossary entries
- [ ] **P9.0.phase-0f-gate** 🔒 Phase 0f operator gate cleared with persona override (likely Mentor+Student per book audience), tier (long-form 10-14 beats), `series_pattern` declared in registry.md if applicable, episode count + boundaries reviewed
- [ ] **P9.0.phase-0g** 📊 Phase 0g per-chapter authoring loop complete for all episodes; `_system/episode-drafts/EP##-<slug>/` populated with framing/key-passages/context-pack/discussion-spine
- [ ] **P9.0.assembly** 📊 `build_episode_txt.py` produced `episodes/EP##-*.txt` files passing META_PROSE_TELLS / R-PHONETICS-OUT / R-HONORIFIC-ONCE / framing DENY checks
- [ ] **P9.0.challenger** 📊 `podcast-challenger` Category P green; concept-glossary referenced by ≥1 framing per episode (per P4.9.challenger rule)
- [ ] **P9.0.loop-n** 🔒 Loop N converges clean; if editor's 25-work bibliography (page 31) triggers an "invented enumeration" finding, operator manually marks it as false-positive at convergence
- [ ] **P9.0.cost-cap** 📊 Total cost within `cost_cap_hard` (default $50); cost-ledger.jsonl rows emitted per phase
- [ ] **P9.0.ship** ✅ Episodes uploaded to NotebookLM; transcripts dropped in `transcripts/`; `_system/challenger-report.md` verdict = SHIP-READY

### P9 — Sample corpus validation (graduated 30p → 865p, 7 books) 

- [ ] **P9.1** 📊 Ayyuhal Walad (30p): full pipeline <2h, cost <$5
- [ ] **P9.2** 📊 Masaail searchable (81p): full pipeline; token/cost/wall-clock recorded
- [ ] **P9.3** 📊 Majalis Moyyada (139p): full pipeline; metrics recorded; **P4 numeric-disambiguation-register.md populated for ≥3 chapters; Loop N raises no P0 findings post-convergence**
- [ ] **P9.4** 📊 Kitab Maqbas (392p): full pipeline; chapter contracts hold; Loop N clean
- [x] **P9.5.pre1** ✅ `content/podcast/library/books/asaas-al-taveel/_system/source/text/chapters-rationale.md` exists with the 6-chapter natiq map (Adam/Nuh/Ibrahim/Musa/Isa/Muhammad + the unwritten Qa'im) — shipped 2026-05-19
- [x] **P9.5.pre2** ✅ `content/podcast/library/books/asaas-al-taveel/_system/concept-glossary.md` exists with ≥20 entries across cosmology, hermeneutics, neoplatonic emanation, Fatimid doctrinal terms — shipped 2026-05-19
- [x] **P9.5.pre3** ✅ `content/podcast/library/books/asaas-al-taveel/_system/registry.md` exists with `series_pattern: recursive_scaffold` declared at series level + 6-episode skeleton — shipped 2026-05-19 (closes audit Gap 5: Pattern 5 gating would otherwise silently no-op when P9.5 runs)
- [ ] **P9.5.pre4** 🔒 Operator-recommended 6-episode preset reviewed at Phase 0f gate (Mentor+Student persona; `series_pattern=recursive_scaffold`; long-form tier)
- [ ] **P9.5** 📊 Asaas Al-Taveel (416p): full pipeline; metrics recorded; Loop N clean
- [ ] **P9.5** ✅ Episode 6 (The Seventh Silence) honors the unwritten Qa'im chapter as content — not silently skipped
- [ ] **P9.5** ✅ Concept-glossary referenced by ≥1 framing per episode OR zero-new-vocab declaration logged
- [ ] **P9.5** ✅ P4 numeric-disambiguation register populated; 7-natiq and 12-hujja enumerations carry citations

#### P9.5 — SHIP-READY criteria (raised quality bar, added 2026-05-20)

**Context:** Operator committed to "complete Phase 0 perfectly on the hardest book; cost is not the constraint, output quality is." Budget envelope raised from default `cost_cap_hard: $50` to ~$130 for asaas. Per-chapter `podcast-challenger` verdict must be SHIP-READY (not SHIP-WITH-CAUTION). Staircase pattern (smoke → cohort → full) governs each LLM-spending phase. EP01 is the firmest halt point.

- [ ] **P9.5.framework-deps** 🔒 All framework dependencies green BEFORE asaas Phase 0c resume — no phase advance with yellow/red dep: P5.5 (this work), P6.5 (cost-ledger), P22.impl (all rows), P22.markers (all rows), P4.10 (parser, validator, phase0d, phase0e_phase11, loopN, backcompat), P23 (client, integration, schema, operator-review-prefill, tests, fallback, cost-ledger, docs)
- [ ] **P9.5.staircase-0b** 🔒 Phase 0b re-run executes as staircase: smoke (1 chunk — win-003, most-broken cohort) → first-broken (7 originally-zero-marker windows) → full (49 chunks). Operator halt for sample review between rungs. Each rung's audit logged to `_workspace/plan/checkpoints/asaas-0b.md` (see STAIRCASE.checkpoint-log).
- [ ] **P9.5.staircase-0c** 🔒 Phase 0c (Arabic phonetic pass) staircase: smoke (1 chapter — Ādam, smallest body chapter) → full (6 chapters). Operator halt for phonetic sample diff vs operator-review.md §4 between rungs. Abort signal: phonetic for any named entity contradicts §4.
- [ ] **P9.5.staircase-0e** 🔒 Phase 0e enrichment staircase: smoke (Ādam glossary buildout — heaviest foundational-term load per chapters-rationale.md §3) → full (5 remaining chapters). Operator halt for glossary review between rungs. Abort signal: EP01 enrichment misses ≥2 of the 8–10 foundational terms OR pulls footnotes into body.
- [ ] **P9.5.ep01-firm-halt** 🔒 Phase 0g EP01 (Ādam — The Hidden Code) authored alone to `podcast-challenger` verdict SHIP-READY; orchestrator HALTS for operator full-episode review before EP02 begins. This is the single firmest checkpoint for asaas — EP01 establishes the recursive-scaffold template that EP02–06 inherit, so a defective EP01 propagates to all six episodes if not caught here.
- [ ] **P9.5.ep01-foundational-glossary** 📊 EP01 framing introduces all 8–10 foundational glossary terms at first occurrence (nāṭiq, asās, ḥujja, taʾwīl, ẓāhir, bāṭin, mubdaʿ, ʿaql awwal, nafs kulliyya) with audible operator-confirmed pronunciation; cross-references resolve to `_system/concept-glossary.md` slugs
- [ ] **P9.5.ep01-pattern5** 📊 EP01 establishes the recursive_scaffold template per `episode-architecture.md` Pattern 5; EP02–06 each open with 30-sec recap referencing EP01's template (passes Category P sub-check P4.9.challenger)
- [ ] **P9.5.ep02-06-challenger** 📊 Each of EP02, EP03, EP04, EP05, EP06 reaches `podcast-challenger` verdict SHIP-READY (NOT SHIP-WITH-CAUTION); convergence allowed up to 3 outer × 5 inner iterations per orchestrator design; chapter halting at iteration cap for human input
- [ ] **P9.5.ep06-unwritten** ✅ EP06 (The Seventh Silence) treats the unwritten Qāʾim chapter as content; recursive-scaffold recap honors the deliberate absence; Mentor+Student persona handles the structural weirdness explicitly (not as an editorial note tacked on)
- [ ] **P9.5.cross-episode-pass** 📊 Series-level `podcast-challenger` pass across all 6 episodes after per-chapter convergence completes; verdict SHIP-READY for the series; catches cross-episode glossary drift, recursive_scaffold breakdown, pacing inconsistency, persona drift
- [ ] **P9.5.loop-n-asaas** 🔒 Loop N converges clean on asaas's heavy numeric/symbolic surface: 7 nāṭiqs (enumeration coverage + one-time enumeration), 12 ḥujjas (enumeration coverage), abjad ciphers (cipher coverage per `06-abjad-numerals.md`), Fatimid-doctrine-into-Qurʾānic-narrative anachronism (labeling per handbook §4); no P0 findings; `<allowed_symbolic_readings>` pre-seeded from operator-review.md §5 honored at finding time
- [ ] **P9.5.budget** 📊 Total asaas Phase 0 through per-chapter cost target $80–$110; hard cap $130 (raised from default `cost_cap_hard: $50` for this run; documented in `state.json.config.cost_cap_hard=130`); cost-ledger rows present for every LLM call AND every Azure call (P6.5 + P23.cost-ledger both shipped by this point)
- [ ] **P9.5.azure-budget** 📊 Asaas Azure spend stays $0 (Document Intelligence S0 free tier: 416 / 500 transactions used; Translator S1 free tier: ~720K / 2M chars used; Language F0: ~150 / 5000 records used). Verified via Azure Portal cost analysis post-shipment.
- [ ] **P9.5.checkpoint-trail** ✅ `_workspace/plan/checkpoints/asaas-*.md` files present for every operator halt-and-review (one per phase rung); each cites the sample artifacts reviewed and the explicit operator decision; searchable audit trail
- [ ] **P9.5.ship-or-bust** 🔒 If any P9.5.* row above can't be cleared, orchestrator HALTS rather than degrading to SHIP-WITH-CAUTION. Quality is the binding constraint; budget is not.
- [ ] **P9.6** 📊 Raahat al-Aqal (591p): full pipeline OR Doc Intelligence 600s poll budget remediation issue filed
- [ ] **P9.7** 📊 Rasail Ikhwan AsSafa (865p): full pipeline OR failure-mode + remediation issue filed; P4 register exercised on classical-philosophical numeric structures

### P9 — Per-book ship gate (P-9 invariant; applies to EVERY P9.* row above)

- [ ] **P9.gate** ✅ For each shipped book: cost-ledger row appended for every claude -p call
- [ ] **P9.gate** ✅ For each shipped book: ≥1 finding row in `findings.jsonl` OR documented zero-findings rationale in `challenger-report.md`
- [ ] **P9.gate** ✅ For each shipped book: `health/<slug>.json` written; `health-trend.md` row appended
- [ ] **P9.gate** ✅ For each shipped book: trainer ran; outcome ∈ {PROMOTED, ARCHIVED} (never NEVER_RAN unless explicitly documented)
- [ ] **P9.gate** ✅ For each shipped book: `test_challenger.py` exits 0 AFTER any trainer commit
- [ ] **P9.gate** ✅ If trainer promoted a rule on this book: `CHALLENGER_VERSION` bumped by 0.1 in `_rules.py` in the same commit

### P9.8 — Cross-book learning yield report  *(W3 terminal artifact; P-9 measurable improvement)*

- [ ] **P9.8** ✅ `_workspace/plan/research/learning-yield-report.md` exists; cites every P9.* book that completed (or documents why one didn't)
- [ ] **P9.8** ✅ Per-book columns: health-score trajectory, findings count by severity, fixture additions, promotions, archived proposals
- [ ] **P9.8** 📊 `fixture_coverage_pct` at W3 end > `fixture_coverage_pct` at W3 start (P-9 invariant)
- [ ] **P9.8** 📊 `promoted/` cardinality at W3 end ≥ start + 1 OR documented rationale (e.g., "regression harness protecting against premature promotion")
- [ ] **P9.8** ✅ `CHALLENGER_VERSION` trajectory recorded; any cost-budget breaches from P6.4 surfaced
- [ ] **P9.8** ✅ Report linked from `done_when` block + this Wave 3 group

### P10 — ETA model 

- [ ] **P10.1** ✅ `scripts/podcast/orchestrator_status.py --eta` predicts wall-clock within ±30% on held-out book (linear regression over P9.1–P9.7 runs)
- [ ] **P10.1** ✅ Parallel regression target: cost-per-phase (USD). `--cost-eta <book-slug>` predicts total cost within ±25%
- [ ] **P10.1** ✅ `run_wave.py 3 --book <slug>` invokes `--cost-eta` as pre-flight; exits non-zero if predicted cost > `cost_cap_hard`; prints predicted/cap/explanation
- [ ] **P10.1** ✅ CLI flag `--retrain-eta` re-fits both regressions after a new book lands

---

## Wave 4 — Control Plane (Phases P11–P14)

### P11 — Multi-Mac decision (doc-only)

- [x] **P11.1** ✅ `docs/podcast/multi-mac-decision.md` exists — single page (~1 screen): primary-only service; secondary Macs are SSH-tunneled read-only viewers; localhost-bound bearer-token auth from keychain; heartbeat hostname enforcement for R3
- [x] **P11.1** ✅ Q1 marked RESOLVED in YAML with closed_at=2026-05-19 + decision ref
- [x] **P11.1** ✅ P12 acceptance no longer references P11 as a prerequisite (P12.depends_on changed from [P11] to [P10])

### P12 — Mutation API + worker pool 

- [ ] **P12.1** ✅ All five mutation endpoints exist + audit rows in `_workspace/podcast-audit.jsonl`
- [ ] **P12.1** ✅ Pause/resume verified on live run (SIGSTOP/SIGCONT confirmed by ps state)
- [ ] **P12.1** ✅ Bearer-token auth from keychain; localhost-only default
- [ ] **P12.2** ✅ 2 books run truly parallel without state corruption
- [ ] **P12.2** ✅ Server restart picks up orphaned runs via state.json scan

### P12.3 — Mutation API pytest harness 

- [ ] **P12.3** ✅ `scripts/podcast/tests/api/test_mutations.py` + `test_auth.py` exist; `pytest scripts/podcast/tests/api/ -v` exits 0
- [ ] **P12.3** ✅ Every mutation flow has ≥2 test cases (start, pause, resume, retry-phase, delete)
- [ ] **P12.3** ✅ Auth tests assert 401 for missing/invalid bearer; 200 with valid
- [ ] **P12.3** ✅ Audit row asserted for every mutation flow (TestClient + Popen mock)
- [ ] **P12.3** ✅ Idempotency asserted: pause+pause is no-op; resume+resume is no-op
- [ ] **P12.3** ✅ `DELETE /books/{slug}` without `?rollback_branch=true` keeps git branch (mock not called); with the flag, branch deletion is invoked
- [ ] **P12.3** ✅ Cross-book parallel mutation test passes without state corruption (P13.1 SQLite read consistency)
- [ ] **P12.3** 📊 Tests use TestClient + subprocess mock — no live subprocess, no API spend; <30s wall-clock

### P13 — SQLite cross-book index (READ-ONLY cache) 

- [ ] **P13.1** ✅ `_workspace/podcast.db` gitignored
- [ ] **P13.1** ✅ Fresh empty DB rebuild reproduces identical state from filesystem
- [ ] **P13.1** ✅ Per-book row includes `disambiguation_pending_count` (P4 link)

### P14 — Dashboard mutation UI 

- [ ] **P14.1** ✅ Destructive UI ops require typed slug to confirm
- [ ] **P14.1** ✅ All button actions audit-logged via P12.1

---


## Wave 5 — Deferred + Self-Learning (trigger-gated, no acceptance until promoted)

- [ ] **P17** 🟡 PDF pre-splitting — promote when book exceeds 500MB OR 2000 pages OR DI 600s poll budget 

#### P17.1 — Source-adapter registry (pluggable input formats) 

- [ ] **P17.1** 🟡 Promote when first non-Arabic-PDF source arrives (Urdu PDF, scanned image, video transcript) OR user explicitly opts in
- [ ] **P17.1** ✅ `scripts/podcast/adapters/` Python package exists; `_base.py` defines `SourceAdapter` Protocol + `RawText` dataclass
- [ ] **P17.1** ✅ `adapters/__init__.py` exports `REGISTRY` dict + `dispatch(source_path)` function; raises `UnsupportedSourceError` on unknown type
- [ ] **P17.1** ✅ `adapters/arabic_pdf.py` implements `SourceAdapter` for `.pdf` files with `source_lang='ar'`; passes `isinstance(..., SourceAdapter)` runtime check
- [ ] **P17.1** ✅ `adapters/_azure_client.py` is the SOLE site reading Azure credentials from Keychain; `grep -rE 'KEYCHAIN|az_key|api_key' scripts/podcast/adapters/` outside `_azure_client.py` returns 0 results
- [ ] **P17.1** ✅ `orchestrate_book.py` Phase 04 calls `adapters.dispatch(source_path).extract(...).normalize().emit(book_dir)` — no direct `_azure.py` imports
- [ ] **P17.1** ✅ `tests/adapters/test_registry.py` asserts Protocol conformance + dispatch resolution + UnsupportedSourceError handling
- [ ] **P17.1** ✅ `tests/adapters/test_arabic_pdf.py` asserts golden-fixture parity: tiny-book pre- vs. post-migration `raw-extract.md` (byte-identical OR Levenshtein ≥0.95 if Azure OCR non-determinism, documented)
- [ ] **P17.1** ✅ `docs/podcast/source-adapter-registry.md` exists; extension guide with worked example
- [ ] **P17.1** 🔒 Walk-through test: adding hypothetical `urdu_pdf.py` touches exactly 3 files (adapters/urdu_pdf.py + adapters/__init__.py one-line + tests/adapters/test_urdu_pdf.py); ZERO edits to orchestrate_book.py, _authoring.py, _chunking.py, SKILL.md, or any agent file
- [ ] **P17.1** ✅ Boundary check (P1.1): `adapters/` participates in podcast isolation — no imports from `scripts/site/` or `scripts/memoir/`
- [ ] **P17.1** ✅ Cost-ledger integration: each adapter call appends a `cost-ledger.jsonl` row via shared `_cost_ledger.py`; Azure spend itemized by adapter

#### P17.1 ext — Change D — Manifest-driven multi-source ingestion (promoted 2026-05-19)

- [ ] **P17.1.ext.1** ✅ Manifest schema (`schema_version`, `bundle_kind`, `voice_mode`, `documents[]`) documented in `book-dir-layout.md`; YAML validator at `scripts/podcast/adapters/_manifest.py`
- [ ] **P17.1.ext.2** ✅ Four new adapters land: `english_pdf.py`, `markdown.py`, `transcript.py`, `auto.py` — each implements `SourceAdapter` Protocol; parity tests under `tests/adapters/`
- [ ] **P17.1.ext.3** ✅ `scaffold_book.py` auto-generates 1-doc manifest stub for new single-source books (backward-compat shim); `scaffold_bundle.py` walks a folder + emits N-doc manifest stub
- [ ] **P17.1.ext.4** ✅ `orchestrate_book.py` Phase 0a honors manifest ordering + adapter dispatch; concatenated `normalized.md` preserves doc-boundary comment markers (`<!-- DOC: file.pdf | role: chapter -->`)
- [ ] **P17.1.ext.5** ✅ Phase 0d respects manifest `chapter_slug` declarations; falls back to auto-segmentation only when manifest is silent
- [ ] **P17.1.ext.6** ✅ `voice_mode` field (`single_author | curated_anthology | editor_voice`) consumed by `_authoring.py` Phase 11; default = `single_author` preserves existing behavior
- [ ] **P17.1.ext.7** 📊 Folder-bundle fixture `_learning/fixtures/folder_bundle/three-articles/` runs clean through Phase 0a → Phase 11; produces episode txt with cross-doc references intact
- [ ] **P17.1.ext.8** ✅ Single-PDF parity: existing W3 corpus books produce byte-identical `refined-english.md` + chapter txt with auto-scaffolded 1-doc manifest (golden frozen at tiny-book + Ayyuhal Walad)
- [ ] **P17.1.ext.9** 🔒 Sequencing-enforcement: `run_wave.py 5 --phase P17` refuses dispatch until `orchestrator_status.py --book asaas-al-taveel` reports `phase_status=complete`; override requires both `--force-pre-asaas` flag AND `ASAAS_OVERRIDE=1` env var (documented in `docs/podcast/source-adapter-registry.md`). Closes the audit's single biggest sequencing risk.

#### Handbook deltas (shipped 2026-05-19 alongside P17.1 promotion)

- [x] **P4.9** ✅ `content/podcast/.skill/handbook/book-dir-layout.md` documents per-book `concept-glossary.md` schema + body shape (Change A)
- [x] **P4.9** ✅ `content/podcast/.skill/handbook/episode-architecture.md` Pattern 5 — Recursive Scaffold added (Change B); registry.md `series_pattern: recursive_scaffold` documented
- [x] **P4.9** ✅ `content/podcast/.skill/handbook/two-host-framing.md` `Voice mode override` section added (Change D prep)
- [ ] **P4.9.fixtures** 📊 Pattern 5 fixtures landed under `_learning/fixtures/phase_prompts/07-chapter-design/recursive-scaffold/`: three sub-fixtures (`golden`, `missing-recap`, `wrong-pattern-declared`) — `golden` passes; `missing-recap` and `wrong-pattern-declared` fail loud with a Category P finding. Until these ship, Pattern 5 is documentation-only (no behavioral enforcement on Ep2+ recap).
- [ ] **P4.9.challenger** 📊 Challenger Category P sub-check: when `concept-glossary.md` exists in a book, every framing must reference ≥1 glossary slug OR contain the literal "no new technical vocabulary in this episode". Implemented in `infra/claude-agents/podcast-challenger/_rules.py` (or wherever Category P is housed); fixture-gated; emits P1-severity finding on violation.

#### P4.10 — Per-book content-range convention (skip editor's apparatus + back-matter indexes)

- [x] **P4.10.docs** ✅ `content-range.md` schema documented in `book-dir-layout.md` with worked Kitab al-Riyad example — shipped 2026-05-19
- [ ] **P4.10.parser** ✅ `scripts/podcast/_content_range.py` exposes `parse(book_dir) -> ContentRange | None`; `ContentRange` dataclass with `body_starts_at_page`, `body_ends_at_page`, `include_author_preface`, `include_author_toc` fields
- [ ] **P4.10.validator** ✅ Validator rejects `content-range.md` with `body_ends_at_page <= body_starts_at_page`, page numbers outside refined-english.md range, or missing/wrong `schema_version`
- [ ] **P4.10.phase0d** ✅ Phase 0d (chapter segmentation) reads `content-range.md` when present; sections whose page falls outside `[body_starts_at_page, body_ends_at_page]` are dropped from `chapters-rationale.md` and `chapters/chNN-*.txt`
- [ ] **P4.10.phase0e_phase11** ✅ Phase 0e (enrichment) + Phase 11 (per-chapter framing) only load body content; cost-ledger row labels skipped page range with `method='content-range-skip'` (no LLM call for skipped pages)
- [ ] **P4.10.loopN** 🔒 Loop N skips numeric claims whose source page falls outside body range — editor's bibliographic lists (e.g., al-Kirmani's 25 works on KaR page 31) do NOT trigger "invented enumeration" findings
- [ ] **P4.10.backcompat** ✅ When `content-range.md` is absent, behavior is byte-identical to pre-2026-05-19 (golden frozen at tiny-book + Ayyuhal Walad)
- [ ] **P4.10.metric** 📊 W3 corpus: token spend on Phases 0c/0e/11 drops by ≥10% on books that adopt content-range vs same book without (measured via cost-ledger before/after)
- [ ] **P22.range** ✅ `operator-review.md` template includes §7 Content range with heuristic-suggested defaults; on `--approve-transcript` resume the orchestrator emits `_system/source/text/content-range.md` from §7 (per P4.10). Blank §7 → no content-range.md emitted → Phase 0d ingests whole transcript as today (backward-compat default).

- [ ] **P18** 🟡 Parallel per-chapter LLM calls — promote when P6 cost-tracking stable AND user opts in 
- [ ] **P19** 🟡 Trainer self-learning — phase-prompt addenda + regression fixtures + health recursion; promote when P13 SQLite proven stable AND P2.6 refinement determinism green AND P9.8 yield report shows fixture_coverage_pct UP

#### P19.1 — Phase-prompt addendum substrate 

- [ ] **P19.1** ✅ `content/podcast/.skill/handbook/_learned-addenda/` directory exists with `README.md` documenting schema + R9 cap
- [ ] **P19.1** ✅ `_authoring.py` prompt assembly reads addenda matching current phase and concatenates them in `<learned-addenda>` XML block at end of system prompt
- [ ] **P19.1** ✅ R9 cap enforced: 6th addendum to same phase triggers FIFO eviction (oldest → `_archive/`)
- [ ] **P19.1** ✅ `podcast-trainer.agent.md` Protocol §3 documents the addendum-writing flow with ≤5 cap
- [ ] **P19.1** ✅ Every addendum file's frontmatter validates against schema (schema_version, phase, signature, authored_by, authored_at, authored_from_books)

#### P19.2 — Phase-prompt regression fixtures + Goodhart guard 

- [ ] **P19.2** ✅ ≥3 fixtures per phase under `_learning/fixtures/phase_prompts/<phase>/` (05-refine-english, 06-phonetics, 07-chapter-design, 08-enrichment, 11-per-chapter)
- [ ] **P19.2** ✅ `scripts/podcast/test_phase_prompts.py` exits 0 against current fixtures (post-P19.1 substrate; no addenda yet)
- [ ] **P19.2** ✅ Trainer addendum proposals MUST pass `test_phase_prompts.py` before write; failing proposals archived with tombstone
- [ ] **P19.2** ✅ `podcast-trainer.agent.md` INVARIANTS reaffirms: trainer never authors or modifies phase_prompts fixtures (only humans)
- [ ] **P19.2** ✅ CI: `test_phase_prompts.py` runs on every PR touching `scripts/podcast/_authoring.py` OR `content/podcast/.skill/handbook/_learned-addenda/`

#### P19.3 — Health-score recursion (next-book post-addendum verification) 

- [ ] **P19.3** ✅ `invoke_trainer` records `addenda_in_effect` list in end-of-book audit
- [ ] **P19.3** ✅ Next-book trainer pass computes per-signature health-score delta vs. last-book-with-this-signature; reverts regressed addenda automatically
- [ ] **P19.3** ✅ Revert-tombstone in `_learned-addenda/_archive/` cites the regression measurements
- [ ] **P19.3** ✅ If addendum reverts 2+ times for the same signature, signature escalates to human-review queue (P14 dashboard surface)
#### P21 — Cross-book learning store (promoted-when ≥3 W3 books shipped)

- [ ] **P21.api** ✅ `scripts/podcast/_learning_store.py` exposes `lookup_term(term, lang)`, `promote_term(...)`, `lookup_pattern(...)`, `promote_pattern(...)`; lookups <5ms p99
- [ ] **P21.store** ✅ `content/podcast/_learning/vocabulary.sqlite` (gitignored) + `vocabulary.jsonl` (git-tracked audit log); rebuild from .jsonl reproduces .sqlite byte-identical
- [ ] **P21.store** ✅ `content/podcast/_learning/patterns.sqlite` + `patterns.jsonl`; `author-profiles/` directory; `operator-prefs.yml` with voice_mode + tier defaults
- [ ] **P21.telemetry** ✅ Per-run `cache-stats.jsonl` row per phase: `{phase, lookups, hits, misses, hit_rate, elapsed_ms_saved}`
- [ ] **P21.integration** ✅ Phase 0c (`_chunking.py`) looks up known terms before claude -p call; cache hits skip LLM with `method=cache-hit` ledger row
- [ ] **P21.integration** ✅ Phase 0b/0e (`_authoring.py`) consults author-profile + pattern store; misses promote LLM output to store after success
- [ ] **P21.review** ✅ Dashboard (P8) `/learning/vocabulary` endpoint lists recent additions; operator can mark terms `operator_locked=true` to freeze the canonical value
- [ ] **P21.goodhart** ✅ `operator_locked` terms never re-derived; locked terms surface in challenger findings if downstream LLM output contradicts them
- [ ] **P21.boundary** ✅ `_learning_store.py` reads but does not write outside `content/podcast/_learning/` (P1.1 boundary check)
- [ ] **P21.audit** ✅ Every store write also appends to `.jsonl`; `rebuild_from_jsonl` reproduces `.sqlite` byte-identical OR within documented tolerance
- [ ] **P21.cost-ledger** ✅ Cost-ledger rows include hit/miss field; LLM-skipped calls show $0 cost with `method='cache-hit'`
- [ ] **P21.seed-glossary** ✅ Per-book `concept-glossary.md` is the primary seed source for `vocabulary.sqlite` (see `seed_corpus_policy` in YAML): confidence 0.95 hand-authored, 0.7 claude-p-generated; `operator_locked=false` on initial promotion
- [ ] **P21** 📊 Cache-hit rate on book #5 of W3 corpus: Phase 0c ≥50%; Phase 0e ≥30%

- [ ] **P20** 🟡 Web upload for PDFs in dashboard — promote when P12 mutation API stable 

---


## Cross-cutting acceptance gates

### Boundary integrity (enforced by journal-challenger Category B + podcast-challenger Category S + repo-surgeon Pass 5 L4/L5)

- [ ] **B1/S2** ✅ No file under `scripts/podcast/` writes to `content/babu-memoir/**`, `content/_shared/**` (except whitelisted `content/_shared/arabic/06-abjad-numerals.md`), `scripts/memoir/**`, `scripts/site/**` (verified by `_boundary_check.py` AND Pass 5 L5)
- [ ] **B2** ✅ Memoir chapters contain no content sourced from `content/podcast/library/books/*/chapters/` without explicit `// source:` comment AND human review
- [ ] **B3/S3** ✅ Every `proposed-library-entries.md` carries schema_version=1 frontmatter; every promoted entry has a ledger row
- [ ] **B4/S5** ✅ Journal authoring sessions never edit files under `content/podcast/**` or `scripts/podcast/**`

### Async safety (podcast-challenger Category S + repo-surgeon Pass 5 L6)

- [ ] **S1/L6** ✅ When orchestrator runs on a book, no agent or operator edits files under that book's `_system/`, `_chunks/`, `chapters/`, `chapter-contracts/`, `episodes/`, `transcripts/`, `_learning/`
- [ ] **S1/L6** ✅ Wait-banner emitted before any HALT; banner field substitution succeeds on populated `heartbeat.json`

### Staircase + early-course-correct discipline (governance, added 2026-05-20)

Applies to every LLM-spending phase to cap blast radius from defects we haven't yet seen. Operationalizes the "fix bugs at the smallest possible spend, not at the end" principle. Lessons learned via asaas Phase 0b post-mortem (58 page markers dropped, discovered only after audit; would have been caught at chunk 003 if smoke pattern was in place).

- [ ] **STAIRCASE.fixture-first** 🔒 Before any LLM-spending phase fix, a regression fixture exists that fails against pre-fix template and passes against post-fix template. Fixture-development cost: zero LLM, ~5 min. Examples: P22.markers.fixture (Phase 0b), P23.tests (Phase 0a.5).
- [ ] **STAIRCASE.smoke-first** 🔒 Before scaling a phase to all units, a smoke run executes against the smallest meaningful unit: 1 chunk for Phase 0b/0c; 1 chapter for Phase 0d/0e/0g. Sample artifact surfaced to operator. Halt for explicit "looks good" or course-correction before staircase rung 2.
- [ ] **STAIRCASE.rung-pattern** ✅ Each phase advances in rungs (typically 1 → cohort → all). Each rung's artifacts audited against per-phase quality criteria before next rung commits. ~12% cost overhead vs single-shot, in exchange for capping blast radius if an early-rung defect is found.
- [ ] **STAIRCASE.abort-signal** 🔒 Each phase has a pre-defined abort signal documented in the per-phase plan; firing the signal halts the phase immediately, surfaces sample + stderr to operator, sets `phase_status=halted-abort-signal-<name>` in state.json.
- [ ] **STAIRCASE.checkpoint-log** ✅ Each operator halt-and-review recorded in `_workspace/plan/checkpoints/<book>-<phase>.md` with timestamp, sample artifacts reviewed, operator decision, and rationale if course-correcting. Searchable audit trail across multi-day runs; survives orchestrator restarts.
- [ ] **STAIRCASE.cap-cost-by-rung** 🔒 Per-phase wall-clock cost caps enforce rung discipline: a single rung cannot exceed (phase_total_estimated × 1.2) before automatic halt. Caps documented in YAML per phase.
- [ ] **STAIRCASE.applies-to-all** ✅ All future books (W3 corpus P9.1–P9.7, future ad-hoc) inherit this discipline by default; opting out requires explicit `--no-staircase` flag and a documented rationale in the run's commit message

### Plan conformance (repo-surgeon Pass 5)

- [ ] **L1** ✅ `_workspace/plan/podcast-plan.yaml` parses cleanly
- [ ] **L2** ✅ Every `done_when` references a phase id that exists; every `depends_on` resolves
- [ ] **L3** ✅ Every `intelligence_sources` path exists (no `<book>` template, no glob); P4 deliverable paths tracked as 🟡 until Wave 1 ships
- [ ] **L4** ✅ No cross-imports between `scripts/podcast/`, `scripts/memoir/`, `scripts/site/`
- [ ] **L7** ✅ `_workspace/plan/view/index.html` references every phase id (P1–P20) AND every wave id (W1–W6) from the YAML
- [ ] **L8** ✅ Every reference to a `meta.legacy_cleanup_basenames` entry outside plan/chats paths is annotated as deleted/retired/closed
- [ ] **L9** ✅ Every CANCELLED phase row above (v2 P3.x) has zero non-strikethrough references in plan files. Note: P6.4 was resurrected for the trainer cost-ledger hook (Q3 resolution); P6.5 was resurrected 2026-05-19 for the datetime.UTC fix surfaced by the KaR pilot.
- [ ] **L10** ✅ Every checkbox here references an id that exists in YAML (or a known marker — B*, S*, L*, Q*, R*, W*)
- [ ] **L11** ✅ Every `legacy_id` mapping in YAML `meta.legacy_id_map` is consistent with the row's `wave` + `id` in `phases[]`

### Wave kickoff conformance (NEW v3)

- [ ] **W1.k** ✅ `scripts/podcast/run_wave.py` exists with subcommands 1–6
- [ ] **W1.k** ✅ Each wave's `done_signal` is computable from acceptance-criteria.md row-state by `run_wave.py --check`
- [ ] **W5.k** ✅ Wave 5 `--confirm-zero-inflight` flag enforces the prereq_gate; refuses to proceed without it

### Intelligence-source wiring

- [ ] **IS1** ✅ Podcast agents read all entries in `intelligence_sources.podcast.consult_before_any_edit` at session start; verified by SKILL.md preflight matching the YAML
- [ ] **IS2** ✅ Journal agents read all entries in `intelligence_sources.journal.consult_before_any_edit`
- [ ] **IS3** ✅ Conflict resolution honored per `intelligence_sources.conflict_resolution`
- [ ] **IS4** ✅ Plan staleness detection: agents run `/repo-surgeon --plan-only` when `meta.restructured` >7 days old AND active wave changed
- [ ] **IS5** ✅ P4 deliverables added to `consult_before_any_edit` list (handbook + abjad reference)

### Challenger acceptance

- [ ] **CH1** ✅ journal-challenger Category B (B1–B4) implemented; revision-log entry dated 2026-05-19 present
- [ ] **CH2** ✅ podcast-challenger Category S (S1–S6) implemented; v1.8 entry dated 2026-05-19 present
- [ ] **CH3** ✅ podcast-challenger Loop N (P4.5) implemented; v1.9 entry dated 2026-05-19
- [ ] **CH4** ✅ Both challengers include `podcast-plan.yaml` + `acceptance-criteria.md` in `reads_guidance`
- [ ] **CH5** ✅ Loop N includes `numeric-symbolic-disambiguation.md` handbook + `06-abjad-numerals.md` in `reads_normative`
- [ ] **CH6** ✅ podcast-challenger S1/S3/S5 halt-block before any other category runs when fired P0
- [ ] **CH7** ✅ Loop N P0 findings (invented enumeration; unsourced cipher decoding) BLOCK ship
- [ ] **CH8** ✅ Both challengers emit sidecar report referencing this file's row IDs when verdict is BLOCKED

### Learning-loop conformance  *(codifies P-9 invariant)*

- [ ] **LL1** ✅ `_learning/` substrate intact: `findings.jsonl`, `patterns.md`, `proposals/`, `promoted/`, `archive/`, `fixtures/`, `health/`, `README.md` all present
- [ ] **LL2** ✅ `findings.jsonl` schema matches `emit_finding()` kwargs in `scripts/podcast/_rules.py` (verified by P2.5 E2E)
- [ ] **LL3** ✅ `scripts/podcast/test_challenger.py` exits 0 on `develop` at all times (gated by P2.5 CI)
- [ ] **LL4** ✅ `scripts/podcast/learn_aggregate.py` regeneration of `patterns.md` is byte-deterministic given the same ledger (unit test)
- [ ] **LL5** ✅ `scripts/podcast/learn_propose.py` is idempotent (re-running with no new findings produces zero new proposals)
- [ ] **LL6** ✅ `_learning/promoted/` is append-only in PR review (deleting a tombstone requires explicit rationale)
- [ ] **LL7** ✅ `CHALLENGER_VERSION` in `_rules.py` is the SOLE version source; stamped in every challenger report + ledger record
- [ ] **LL8** ✅ Trainer audit one-liner emitted at end of every `invoke_trainer` pass: `podcast-trainer: K proposals processed; A accepted; R archived; CHALLENGER_VERSION X→Y; cost-context: $Z`
- [ ] **LL9** ✅ For every new challenger check (Loop N, future), at least one fixture lands in `_learning/fixtures/` in the same commit (per P-9; enforced by reviewer + P4.4b precedent)
- [ ] **LL10** ✅ Dashboard learning panel (P8.5) shows fixture-coverage % trending UP across the W3 corpus (visual P-9 verification)
- [ ] **LL11** ✅ `_workspace/plan/research/learning-yield-report.md` (P9.8) exists at end of W3
- [ ] **LL12** ✅ Post-publication SLA (`post_publish.py` + `audit_transcript.py` + Loop M) wired into the substrate — every audit-run appends to `findings.jsonl` (verified by re-running `post_publish.py` on a known transcript)
- [ ] **LL13** ✅ Heartbeat (P7.5) exposes substrate state to operator without dashboard
- [ ] **LL14** ✅ Trainer reads cost-ledger.jsonl (P6.4) and emits cost-context field in audit one-liner
- [ ] **LL15** ✅ Quarterly `findings.jsonl` rotation works: file `_learning/archive/findings-YYYYQN.jsonl` exists after first calendar-quarter rollover; ledger never grows unbounded

---

## Refinement-prompt deliverables (refinement prompt §"Output Format")

- [x] **OP-1** ✅ Understanding — two-skill boundary confirmed (README.md "Bounded scope")
- [x] **OP-2** ✅ Current-State Findings — `research/findings.md` §7 + §8
- [x] **OP-3** ✅ Consolidated Todo List — this file
- [x] **OP-4** ✅ Safety Assessment — YAML `async_safety` + per-phase `depends_on` + wave `parallelism`
- [x] **OP-5** ✅ Execution Plan — README phase summary + wave structure here
- [x] **OP-6** ✅ Acceptance Criteria — this file
- [ ] **OP-7** 🔒 Final Recommendation — per session (current v3: kick off Wave 1 once user signals go; Wave 1 produces P5 fix that unblocks `book/kitab-al-riyad` resume)

---

## How to update this file

1. Mark a row `- [x]` ONLY when its acceptance command/check has been run and passes (or is observably true).
2. NEVER mark a row done without verification.
3. If a row no longer maps to a YAML id (drift), Pass 5 L10 will flag it.
4. When a new phase task is added to `podcast-plan.yaml`, add a row here in the same session.
5. Date completed batches in the commit message; the file itself stays terse.

## Inventory

- Total checkboxes: ~275 (count regenerated by Pass 5 L10; +45 added 2026-05-20: P22.markers ×11, P23 ×13, P9.5 SHIP-READY ×14, STAIRCASE governance ×7)
- Currently checked: 9 (P3.1, P3.2, P5.1 SHIPPED, OP-1..OP-6)
- Currently pending: ~266
- Verification mix: ✅ auto-verifiable (majority) · 🟡 dep-blocked · 🔒 manual gate · 📊 metric-bound

**2026-05-20 additions (this commit):**
- **P22.markers** — Phase 0b page-marker preservation (asaas-discovered defect; regression fixture + prompt fix + audit tool + staircase re-run)
- **P23** — Phase 0a.5 NER pre-seeding via Azure Text Analytics F0 (replaces hand-authored operator-review.md §3+§4; zero Azure cost on free tier)
- **P9.5 SHIP-READY criteria** — asaas as the hardest test case; SHIP-READY per-chapter (not SHIP-WITH-CAUTION); $130 hard cap (raised from $50); EP01 firm halt; Loop N convergence required
- **STAIRCASE.\*** — cross-cutting governance pattern (fixture-first → smoke → cohort → full, with operator halt and abort signals at each rung)

**YAML cross-ref status:** New rows P22.markers.\*, P23.\*, P9.5.\* (SHIP-READY), STAIRCASE.\* are not yet mirrored in `podcast-plan.yaml` `phases[].acceptance[]`. Pass 5 L10 will flag the drift until reconciled. Reconciliation deferred to the YAML-edit session at the start of the framework code work (next session).

## Wave summary (autonomous scheduling targets)

| Wave | Phases | Effort | DONE-when (high-level) | Schedule intent |
|---|---|---|---|---|
| W1 Foundation | P1–P6 | 2–4 days (parallel) | All W1 rows checked incl. P2.6 determinism + P5.4 phase constants; kitab-al-riyad resume passes | Overnight idempotent run; zero LLM cost (P2.5+P2.6 tiny-book ~<$2) |
| W2 Observability + Polish | P7–P8 (incl. P8.6/P8.7/P8.8) | ~1.5 wk | Dashboard reachable; phase rename schema_version=2; D3 views render 6 diagrams; agent dedup + isolation CI green | Daytime+overnight; trivial LLM cost; W2 closes BEFORE W3 starts (zero-in-flight naturally true) |
| W3 Corpus | P9–P10 | ~1 wk wall-clock | 7 books shipped clean OR failure-modes documented; ETA ±30% (clock) AND ±25% (cost) | One book per scheduled invocation; cost-capped (pre-flight cost-eta check) |
| W4 Control Plane | P11(doc)–P14 | ~1 wk | 2 books parallel; mutations audit-logged + pytest-harnessed (P12.3); typed-slug destructive confirmation | Single window; mutation surface live |
| W5 Deferred + Self-Learning | P17, P17.1, P18, P19, P20 | N/A | Per-phase `promote_when` triggers fire | Not time-scheduled | Per-phase `promote_when` triggers fire; P19 self-learning gated by P13 + P2.6 + P9.8 | Not time-scheduled |
