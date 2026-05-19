# Acceptance Criteria — Master Checklist

**Companion to:** [`podcast-plan.yaml`](./podcast-plan.yaml) **v3.2** (2026-05-19 — v3.2 DoR rebalancing: P5.1 SHIPPED; W5 absorbed into W1/W2 via P5.4+P8.6+P8.7+P8.8; P2.6 refinement determinism; P10.1 cost-eta; P11 demoted; P12.3 mutation pytest harness; P19 expanded to self-learning P19.1/P19.2/P19.3 + R9 cap; P1.4 exit-code 4 for P-9 violation. Prior: v3.1 learning-loop production-readiness; v3 6-wave restructure; SDK migration cancelled; P4 numeric/symbolic disambiguation)
**Companion to:** [`view/index.html`](./view/index.html), [`research/findings.md`](./research/findings.md), [`numeric-symbolic-disambiguation-plan.md`](./numeric-symbolic-disambiguation-plan.md) (P4 design doc)
**Audited by:** `/repo-surgeon --plan-only` Pass 5 L10 (acceptance ↔ YAML sync)
**Read by:** journal-challenger Category B, podcast-challenger Category S + Loop N (all consult this file)

This file is the SHIP / DONE oracle. Every row maps to one verifiable acceptance criterion from the canonical YAML. Use `- [x]` to mark done; `- [ ]` to mark pending. Group anchors (`### Wave N — …`) match `waves[]` in the YAML; row IDs (e.g., `P1.1`) match `phases[].tasks[].id`. Pass 5 L10 verifies alignment.

**Verdict legend:** ✅ verifiable today · 🟡 verifiable after dependency · 🔒 manual gate · 📊 metric-bound

**Wave kickoff cmds** (autonomous scheduled-task units; see `waves[]` in YAML):
- W1 → `python3 scripts/podcast/run_wave.py 1`
- W2 → `python3 scripts/podcast/run_wave.py 2`
- W3 → `python3 scripts/podcast/run_wave.py 3 --book <slug>`
- W4 → `python3 scripts/podcast/run_wave.py 4`
- W5 → `python3 scripts/podcast/run_wave.py 5 --confirm-zero-inflight`
- W6 → manual: `python3 scripts/podcast/run_wave.py 6 --phase P17` (promotion-gated)

---

## Wave 1 — Foundation & Guardrails (Phases P1–P6, parallel-safe, no LLM cost)

### P1 — Journal/podcast boundary verification + CI lock-down  *(was P0a)*

- [ ] **P1.1** ✅ `scripts/podcast/_boundary_check.py` exists; runs <2s; exit 0 on clean tree; non-zero with `file:line` on any write/append/`open(...,'w')` targeting `content/babu-memoir/**`, `content/_shared/**`, `scripts/memoir/**`, `scripts/site/**`
- [ ] **P1.1** ✅ Boundary contract documented in `skills-staging/podcast/SKILL.md` (grep returns the section)
- [ ] **P1.1** ✅ Whitelisted exception honored: `content/_shared/arabic/06-abjad-numerals.md` (P4) does NOT trip the check
- [ ] **P1.2** ✅ "Manual library handoff" section in `skills-staging/podcast/SKILL.md` (grep returns it)
- [ ] **P1.2** ✅ `docs/podcast/manual-library-handoff.md` exists; documents promotion workflow
- [ ] **P1.2** ✅ `scripts/podcast/_proposal_writer.py` exists; emits schema-valid `proposed-library-entries.md` with frontmatter `schema_version`, `book_slug`, `episode_id`, `generated_by`, `generated_at`
- [ ] **P1.3** 🟡 CI wiring deferred to P16; P1.1 invocation present in `.github/workflows/podcast-isolation.yml`
- [ ] **P1.4** ✅ `scripts/podcast/run_wave.py` exists; subcommands 1–6; idempotent (second invocation does zero work when wave already done)
- [ ] **P1.4** ✅ `run_wave.py --check N` computes wave N done_signal from `acceptance-criteria.md` without executing
- [ ] **P1.4** ✅ W3 invocation refuses if `cost-ledger.jsonl` shows >$50 in current book (hard cap from P6.3)
- [ ] **P1.4** ✅ W5 invocation refuses without `--confirm-zero-inflight` AND a passing prereq_gate
- [ ] **P1.4** ✅ Exit codes: 0=already done, 2=executed+DONE, 3=halted at human-review gate, 1=error
- [ ] **P1.4** ✅ **(v3.2 NEW)** Exit code 4 = "wave DONE but P-9 invariant violated" — fixture_coverage_pct dropped OR `test_challenger.py` red on develop OR last_trainer_outcome=NEVER_RAN without rationale; scheduler treats as halt-for-inspection

### P2 — E2E test harness  *(was P0b)*

- [ ] **P2.1** ✅ `scripts/podcast/tests/e2e/` exists with `__init__.py`, `conftest.py`, `fixtures/tiny-book/` (3-chapter, ~5k word synthetic source with ≥1 Arabic phrase + ≥1 numeric claim for Loop N)
- [ ] **P2.1** 📊 Tiny-book fixture cost <$0.50/full pass
- [ ] **P2.2** ✅ `scripts/podcast/tests/e2e/test_full_pipeline.py` exists; `pytest scripts/podcast/tests/e2e/ -v` passes
- [ ] **P2.2** ✅ Sunny-day asserts: state.json shows each phase completed in order; refined-english + _phonetics >100 words; every `_chunks/0b/win-*.in.md` has matching non-zero `win-*.out.md`; ≥1 chapter-contract; ≥1 chapter txt; halts at 0f; heartbeat updates ≤30s (post-P7); **NO `NO ARTIFACT` log line**; `numeric-disambiguation-register.md` present
- [ ] **P2.2** ✅ Sunny-day fails when P5 bug class returns (regression toggle `--permission-mode`)
- [ ] **P2.2** 📊 Tiny-book sunny-day total <15min, cost <$1
- [ ] **P2.3** ✅ `test_failure_modes.py` exists; mock `claude -p` rc=0 with no file write → typed error; resume-after-kill restores `.out.md` checkpoints; `--retry-phase` on failed 0c works
- [ ] **P2.4** ✅ `.github/workflows/podcast-e2e.yml` exists; PRs touching `scripts/podcast/` fail CI when E2E fails; `skills-staging/podcast/SKILL.md` documents the gate
- [ ] **P2.5** ✅ `scripts/podcast/tests/e2e/test_learning_loop.py` exists; `pytest scripts/podcast/tests/e2e/test_learning_loop.py -v` exits 0
- [ ] **P2.5** ✅ Test asserts: tiny-book run → ≥3 ledger rows appended → `learn_aggregate.py` regenerates `patterns.md` → `learn_propose.py` emits ≥1 proposal → `test_challenger.py` exits 0 → `write_health.py` writes health + appends `health-trend.md`
- [ ] **P2.5** ✅ Idempotency: second run produces no duplicate findings (line-count stable); no new proposal emitted for an already-promoted signature
- [ ] **P2.5** ✅ `.github/workflows/podcast-learning-loop.yml` runs `test_challenger.py` on every PR touching `scripts/podcast/`, `.github/agents/podcast-challenger.agent.md`, or `content/podcast/.skill/handbook/`; red harness BLOCKS merge to develop
- [ ] **P2.5** 🔒 P-9 invariant: `test_challenger.py` exits 0 on `develop` at all times (manual gate at every wave kickoff)
- [ ] **P2.6** ✅ **(v3.2 NEW)** `scripts/podcast/tests/e2e/test_refinement_determinism.py` exists; `pytest scripts/podcast/tests/e2e/test_refinement_determinism.py -v` exits 0
- [ ] **P2.6** ✅ **(v3.2 NEW)** Asserts: Levenshtein ratio across two same-input refinement runs ≥ 0.90; structural-key parity 100% (H2 / paragraph / parenthetical counts); word-count delta < 5%
- [ ] **P2.6** ✅ **(v3.2 NEW)** Committed golden `tests/e2e/fixtures/tiny-book/golden/refined-english.md` exists; PR diff to it requires commit message `GOLDEN-REFRESH: <reason>`
- [ ] **P2.6** 📊 **(v3.2 NEW)** Run cost <$1; wall-clock <10min on tiny-book fixture
- [ ] **P2.6** ✅ **(v3.2 NEW)** Test fails loud if a future `_authoring.py` change drifts the refinement style — operationalizes the v3.2 bit-stable quality contract

### P3 — Doc regressions from 2026-05-19 legacy cleanup  *(was P0c — partially done)*

- [x] **P3.1** ✅ `docs/architecture/podcast-overview.html` paragraph rewritten; chatgpt-portable card points at `skills-staging/podcast/SKILL.md`; deletion annotated  *(was P0c.1)*
- [x] **P3.2** ✅ Every reference to the 4 deleted basenames (`chatgpt-podcast-skill-prompt`, `folder-cleanup-prompt`, `podcast-refactor-executive-summary`, `podcast-orchestrator-large-books`) outside plan/chats paths is annotated `deleted`/`retired`/`RETIRED`/`DELETED`/`closed`  *(was P0c.2; verified by Pass 5 L8)*

### P4 — Numeric/Symbolic Disambiguation protocol *(NEW — folded from numeric-symbolic-disambiguation-plan.md)*

- [ ] **P4.1** ✅ `content/_shared/arabic/06-abjad-numerals.md` exists; both Mashriqi + Maghribi tables; Hisab al-Jummal practice; verified reference calculations (Allah=66, basmala=786, Muhammad=92, Ali=110) AND Ch-02 worked calcs (kun=70, fayakun=166)
- [ ] **P4.1** 🔒 Post-create, file treated as READ-ONLY by both skills (manual gate; Pass 5 L5 enforces no further writes)
- [ ] **P4.2** ✅ `content/podcast/.skill/handbook/numeric-symbolic-disambiguation.md` exists; 6 sections (triggers, workflow, enumerate-once rule, anachronism handling, invented-content-is-P0, source-preference register)
- [ ] **P4.2** ✅ Handbook references `06-abjad-numerals.md` as abjad authority + `numeric-symbolic-disambiguation-plan.md` as worked-example source
- [ ] **P4.3** ✅ `skills-staging/podcast/SKILL.md` pre-read list includes reference #21 (handbook) + SHARED_ARABIC entry now lists 7 files (00–06)
- [ ] **P4.4** ✅ `content/podcast/.skill/handbook/pre-refined-source-mode.md` has new "Numeric Disambiguation" scaffolding step + new failure-mode entry #6 (invented enumeration = P0 BLOCKED)
- [ ] **P4.4b** ✅ `content/podcast/.skill/_learning/fixtures/loop_n_numeric_invented/{input.txt,expected.json}` exist (P-9 invariant: every new check ships a fixture)
- [ ] **P4.4b** ✅ `test_challenger.py` covers Loop N detector and exits 0 with 8/8 fixtures (7 prior + 1 Loop N)
- [ ] **P4.4b** ✅ If Loop N check IDs evolve in P4.5, `expected.json` updates in the same commit
- [ ] **P4.5** ✅ podcast-challenger spec contains Loop N section: 5 checks (enumeration coverage, one-time enumeration, abjad cipher coverage, anachronism labeling, no invented content) + severity ladder (P0/P1/P2)
- [ ] **P4.5** ✅ Loop N spec mirrored in `.claude/agents/podcast-challenger.md` (byte-identical post-suffix-strip)
- [ ] **P4.5** ✅ Loop N's `reads_guidance` lists `06-abjad-numerals.md` + `numeric-symbolic-disambiguation.md` handbook
- [ ] **P4.6** ✅ `scripts/podcast/_authoring.py` Phase 0d prompt instructs LLM to emit `numeric-disambiguation-register.md`
- [ ] **P4.6** ✅ E2E test (P2.2) verifies register file exists when fixture contains numeric claims
- [ ] **P4.7** ✅ Master & Disciple Ch-02 scaffolding updates landed: `02-glossary.md` (5 new entries), `03-source-integrity-notes.md` (Numeric/Symbolic enumeration register + Anachronism register), `ch02-scaffolding.md` (Numeric Disambiguation section + appended NotebookLM instructions), `06-human-review-checklist.md` (§J with 9 checkboxes + failure-mode escalation)
- [ ] **P4.7** ✅ Decision log captured: 12-jazāʾir = symbolic+historical; sphere-cipher = NEEDS HUMAN REVIEW; fifth intermediary = NEEDS HUMAN REVIEW
- [ ] **P4.8** ✅ `intelligence_sources.podcast.consult_before_any_edit` includes handbook + abjad reference
- [ ] **P4.8** ✅ `_workspace/plan/numeric-symbolic-disambiguation-plan.md` header points to its P4 canonical home in podcast-plan.yaml

### P5 — `claude -p` permission-mode fix + artifact validation  *(was P0)*

- [x] **P5.1** ✅ **SHIPPED** (v3.2 2026-05-19) — `grep 'claude -p' scripts/podcast/` returns 0 results without `--permission-mode acceptEdits`; both call sites pass the flag: `_authoring.py:99` and `_chunking.py:255` now invoke `[CLAUDE_CMD, "-p", "--permission-mode", "acceptEdits", prompt]`
- [ ] **P5.2** ✅ Artifact check raises typed error when `out_path` missing OR `file_size == 0`; no silent `NO ARTIFACT`; stdout/stderr captured
- [ ] **P5.3** ✅ P5.1 + P5.2 merged to `develop` BEFORE `book/kitab-al-riyad` resume; book branch rebased clean; `_system/orchestrator-state.json` untouched by rebase; all N windows produce non-empty `.out.md`; phase transitions 0b → 0c → 0d → 0e cleanly OR halts cleanly at 0f
- [ ] **P5.4** ✅ **(v3.2 NEW)** `scripts/podcast/_phases.py` module exists; `Phase` StrEnum with 14 values in PHASE_ORDER (01-preflight..14-done); `LEGACY_ALIAS` covers 0a..0g + named-step set; `resolve()` raises ValueError on unknown name
- [ ] **P5.4** ✅ **(v3.2 NEW)** `scripts/podcast/tests/test_phases.py` asserts: Phase is StrEnum, PHASE_ORDER==tuple(Phase), every LEGACY_ALIAS key resolves, unknown raises ValueError
- [ ] **P5.4** ✅ **(v3.2 NEW)** Importing `_phases.py` has zero side effects (no FS writes, no network)
- [ ] **P5.4** 🟡 **(v3.2 NEW)** Consumed by W2 P8.6 bulk rewrite — W1 deliverable is the module + tests only; other modules not yet importing it

### P6 — Cost ledger + soft/hard caps  *(was P3.4; decoupled from cancelled SDK migration)*

- [ ] **P6.1** ✅ `scripts/podcast/_cost_ledger.py` exists; appends `{ts, phase, step, model, input_tokens, output_tokens, cache_read, cache_create, cost_usd}` to `<book>/_system/cost-ledger.jsonl` after every `claude -p`
- [ ] **P6.1** ✅ Pricing table constant; unknown model emits structured warning, not silent zero
- [ ] **P6.2** ✅ `scripts/podcast/cost_ledger_summary.py` exits 0; prints structured totals; regenerates `cost-validation.json` (diffable in PR review)
- [ ] **P6.2** 🔒 Manual cross-check vs Anthropic console for first W3 book: ledger within ±1%
- [ ] **P6.3** ✅ Soft warning at $20 (heartbeat); hard halt before Phase 0d at $50; `--cost-cap-soft` / `--cost-cap-hard` CLI flags AND `state.config.cost_cap_*` keys override
- [ ] **P6.4** ✅ `invoke_trainer()` prompt extended with Protocol §3.5 (read cost-ledger.jsonl, propose remediation if budget exceeded by >20%)
- [ ] **P6.4** ✅ `.github/agents/podcast-trainer.agent.md` Protocol §3 references cost-ledger cross-cut
- [ ] **P6.4** ✅ Trainer end-of-run audit line includes `cost-context: $X.XX`
- [ ] **P6.4** ✅ Q3 row in YAML reopened; closes only when P6.4 lands on develop
- [ ] **P6.4** ✅ Cost-budget overrun (>20% over tier budget) surfaces a P1-class commentary tombstone in `_learning/{promoted,archive}/`

---

## Wave 2 — Observability (Phases P7–P8)

### P7 — Heartbeat + status CLI + wait-banner  *(was v2 P1)*

- [ ] **P7.1** ✅ `scripts/podcast/_progress.py` daemon thread writes `<book>/_system/heartbeat.json` atomically every 30s with fields `pid, phase, phase_status, elapsed_in_phase_s, last_chunk_written, last_chunk_mtime, last_log_line, subprocess_pid, hostname, cost_so_far_usd`
- [ ] **P7.1** ✅ daemon=True; orchestrator exit terminates cleanly
- [ ] **P7.1** ✅ Zero impact on `claude -p` timing (side-channel only; verified by comparing wall-clock with/without on tiny-book)
- [ ] **P7.2** ✅ Within 30s of any LLM call starting, heartbeat `label` reflects it (e.g., `0b · win-007 · 3082 words`); E2E assertion
- [ ] **P7.3** ✅ `scripts/podcast/orchestrator_status.py` runs <1s on 260-page book state; falls back to log tail when heartbeat missing
- [ ] **P7.3** ✅ Exit codes: 0=alive, 2=dead, 1=stale (>5min)
- [ ] **P7.3** ✅ Boxed banner preserves row/column structure of `meta.async_safety.wait_banner_format`; structural-match unit test passes
- [ ] **P7.3** ✅ `--ascii` flag emits ASCII-fallback banner
- [ ] **P7.4** ✅ `<book>/_system/events.jsonl` tails cleanly with `tail -F`; schema `{ts, phase, step, total, label, level, msg}` documented
- [ ] **P7.5** ✅ heartbeat.json includes 6 new learning fields: `learning_findings_appended_this_run`, `learning_proposals_open`, `learning_promoted_total`, `learning_fixture_count`, `last_trainer_outcome`, `challenger_version`
- [ ] **P7.5** ✅ Fields update within 30s of any substrate change (new file appears in `promoted/` or `fixtures/`)
- [ ] **P7.5** ✅ Zero impact on `claude -p` timing (tiny-book wall-clock comparison)

### P8 — Read-only Status API + browser dashboard  *(was v2 P2)*

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

### P8.6 — Bulk phase rename + HTML doc rewrite  *(v3.2 NEW; absorbed from former W5 P15)*

- [ ] **P8.6** 🔒 **(v3.2)** Prereq verified: `orchestrator_status.py --all --json | jq '[.books[] | select(.phase_status=="running" or .phase_status=="failed")] | length'` returns 0 (naturally true in W2 closing window, before W3)
- [ ] **P8.6** ✅ **(v3.2)** All consumer modules (`orchestrate_book.py`, `_authoring.py`, `_chunking.py`, `_progress.py`, `_convergence.py`, `extract_chapter.py`, `build_episode_txt.py`) import `Phase` enum from `scripts/podcast/_phases.py` instead of literal phase strings
- [ ] **P8.6** ✅ **(v3.2)** `read_state()` detects `schema_version=1` and rewrites legacy keys via `_phases.LEGACY_ALIAS`; `write_state()` emits `schema_version=2` with new keys only
- [ ] **P8.6** ✅ **(v3.2)** `--retry-phase 0b` AND `--retry-phase 05-refine-english` both resolve to `Phase.REFINE_ENG`
- [ ] **P8.6** ✅ **(v3.2)** `grep -rE '\b0[a-g]\b' scripts/podcast/ --include='*.py'` returns 0 literal phase-ID matches outside `_phases.LEGACY_ALIAS`
- [ ] **P8.6** ✅ **(v3.2)** `grep -n '"trainer"' scripts/podcast/ --include='*.py'` returns 0 raw matches outside `_phases.LEGACY_ALIAS`
- [ ] **P8.6** ✅ **(v3.2)** `tests/e2e/test_phase_rename.py` asserts state.json shows `12-trainer` after the trainer step on a `schema_version=2` fixture; `schema_version=1` fixture migrates; `--retry-phase trainer` resolves to `Phase.TRAINER`
- [ ] **P8.6** ✅ **(v3.2)** All 5 `docs/architecture/podcast-*.html` files updated in lockstep with code; grep on each for literal `0a..0g` returns 0 results
- [ ] **P8.6** ✅ **(v3.2)** All 4 `_workspace/plan/view/*.html` files updated (phase-pill grid labels reflect new step names)
- [ ] **P8.6** ✅ **(v3.2)** `.github/agents/podcast-trainer.agent.md` updated to reference `12-trainer` in any phase-name strings (was P15.4, now folded here)

### P8.7 — D3.js view upgrade (6 diagrams across 4 views, offline-bundled)  *(v3.2 NEW)*

- [ ] **P8.7** ✅ **(v3.2)** `_workspace/plan/view/assets/js/d3.v7.min.js` exists (~280KB bundled vendor copy; no CDN)
- [ ] **P8.7** ✅ **(v3.2)** `_workspace/plan/view/assets/js/diagrams.js` exists; registers 6 diagram builders
- [ ] **P8.7** ✅ **(v3.2)** `_workspace/plan/view/assets/css/diagrams.css` exists; uses only existing `theme.css` CSS variables — no new color literals
- [ ] **P8.7** ✅ **(v3.2)** D1 wave dependency DAG renders in `index.html` above the wave-row stack; hover shows `done_signal`; click jumps to acceptance anchor
- [ ] **P8.7** ✅ **(v3.2)** D2 phase Gantt renders in `phased-plan.html`; every phase P1-P20 has a bar; OBSOLETED phases (P15, P16) greyed-out with redirect tooltip
- [ ] **P8.7** ✅ **(v3.2)** D3 P4 numeric disambiguation decision tree renders in `phased-plan.html`; click to expand/collapse; leaves show P0/P1/P2 verdict
- [ ] **P8.7** ✅ **(v3.2)** D4 pipeline flowchart renders in `podcast-capabilities.html`; hover shows `_authoring.py` function name
- [ ] **P8.7** ✅ **(v3.2)** D5 agent topology graph renders in `podcast-capabilities.html`; exactly 4 agent nodes; only trainer has dashed outbound (spec-edit) edges
- [ ] **P8.7** ✅ **(v3.2)** D6 acceptance heatmap renders in `acceptance-criteria.html`; cell totals sum to current row inventory (~200)
- [ ] **P8.7** ✅ **(v3.2)** All 6 diagrams render with NO network access (verified by offline test); no `fetch()` of off-domain URLs; no `<script src="http...">` references
- [ ] **P8.7** ✅ **(v3.2)** Phase IDs cited inside each diagram match `phases[].id` in `podcast-plan.yaml` (Pass 5 L7 conformance)
- [ ] **P8.7** ✅ **(v3.2)** Accessibility: every diagram has aria-labels + keyboard nav (tabindex) + fallback summary table beneath

### P8.8 — Agent dedup + isolation CI (single-commit collapse of former W5 P16)  *(v3.2 NEW)*

- [ ] **P8.8** ✅ **(v3.2)** `.github/agents/podcast-challenger.agent.md` exists (materialized with staged Loop N edits from P4.5); byte-identical to former `.claude/agents/podcast-challenger.md` post-suffix-strip
- [ ] **P8.8** ✅ **(v3.2)** `.github/agents/podcast-extract.agent.md` exists (materialized)
- [ ] **P8.8** ✅ **(v3.2)** `.github/agents/ui-reviewer.agent.md` exists (materialized)
- [ ] **P8.8** ✅ **(v3.2)** `infra/claude-agents/` directory removed (`git rm -r`; history preserved)
- [ ] **P8.8** ✅ **(v3.2)** `scripts/install-claude-skills.sh` rewritten: reads `.github/agents/*.agent.md` and materializes `.claude/agents/<basename without .agent>.md`; second run produces zero diffs (idempotent)
- [ ] **P8.8** ✅ **(v3.2)** `scripts/check_agent_dedup.py` exists; exits 0 only when name sets across `.github/+.claude/` match after suffix-strip; runs in CI
- [ ] **P8.8** ✅ **(v3.2)** `scripts/podcast/_isolation_check.py` exists; AST scan fails build on `import scripts.site.*` or `import scripts.memoir.*`; honors P1.1 boundary whitelist
- [ ] **P8.8** ✅ **(v3.2)** `.github/workflows/podcast-isolation.yml` exists; runs boundary_check + isolation_check + dedup_check + test_challenger.py; all green on clean tree
- [ ] **P8.8** ✅ **(v3.2)** VS Code / Claude Code agent picker shows each agent exactly once (visual verification in PR description)

---

## Wave 3 — Corpus Validation (Phases P9–P10)

### P9 — Sample corpus validation (graduated 30p → 865p, 7 books)  *(was v2 P4.1–P4.7)*

- [ ] **P9.1** 📊 Ayyuhal Walad (30p): full pipeline <2h, cost <$5
- [ ] **P9.2** 📊 Masaail searchable (81p): full pipeline; token/cost/wall-clock recorded
- [ ] **P9.3** 📊 Majalis Moyyada (139p): full pipeline; metrics recorded; **P4 numeric-disambiguation-register.md populated for ≥3 chapters; Loop N raises no P0 findings post-convergence**
- [ ] **P9.4** 📊 Kitab Maqbas (392p): full pipeline; chapter contracts hold; Loop N clean
- [ ] **P9.5** 📊 Asaas Al-Taveel (416p): full pipeline; metrics recorded; Loop N clean
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

### P10 — ETA model  *(was v2 P4.8)*

- [ ] **P10.1** ✅ `scripts/podcast/orchestrator_status.py --eta` predicts wall-clock within ±30% on held-out book (linear regression over P9.1–P9.7 runs)
- [ ] **P10.1** ✅ **(v3.2 NEW)** Parallel regression target: cost-per-phase (USD). `--cost-eta <book-slug>` predicts total cost within ±25%
- [ ] **P10.1** ✅ **(v3.2 NEW)** `run_wave.py 3 --book <slug>` invokes `--cost-eta` as pre-flight; exits non-zero if predicted cost > `cost_cap_hard`; prints predicted/cap/explanation
- [ ] **P10.1** ✅ **(v3.2 NEW)** CLI flag `--retrain-eta` re-fits both regressions after a new book lands

---

## Wave 4 — Control Plane (Phases P11–P14)

### P11 — Multi-Mac decision (DEMOTED to doc-only in v3.2)  *(was v2 P5.0)*

- [ ] **P11.1** ✅ **(v3.2 DEMOTED)** `docs/podcast/multi-mac-decision.md` exists — single page (~1 screen): primary-only service; secondary Macs are SSH-tunneled read-only viewers; localhost-bound bearer-token auth from keychain; heartbeat hostname enforcement for R3
- [ ] **P11.1** ✅ **(v3.2)** Q1 marked RESOLVED in YAML with closed_at=2026-05-19 + decision ref
- [ ] **P11.1** ✅ **(v3.2)** P12 acceptance no longer references P11 as a prerequisite (P12.depends_on changed from [P11] to [P10])

### P12 — Mutation API + worker pool  *(was v2 P5.1+P5.2)*

- [ ] **P12.1** ✅ All five mutation endpoints exist + audit rows in `_workspace/podcast-audit.jsonl`
- [ ] **P12.1** ✅ Pause/resume verified on live run (SIGSTOP/SIGCONT confirmed by ps state)
- [ ] **P12.1** ✅ Bearer-token auth from keychain; localhost-only default
- [ ] **P12.2** ✅ 2 books run truly parallel without state corruption
- [ ] **P12.2** ✅ Server restart picks up orphaned runs via state.json scan

### P12.3 — Mutation API pytest harness  *(v3.2 NEW)*

- [ ] **P12.3** ✅ **(v3.2 NEW)** `scripts/podcast/tests/api/test_mutations.py` + `test_auth.py` exist; `pytest scripts/podcast/tests/api/ -v` exits 0
- [ ] **P12.3** ✅ **(v3.2 NEW)** Every mutation flow has ≥2 test cases (start, pause, resume, retry-phase, delete)
- [ ] **P12.3** ✅ **(v3.2 NEW)** Auth tests assert 401 for missing/invalid bearer; 200 with valid
- [ ] **P12.3** ✅ **(v3.2 NEW)** Audit row asserted for every mutation flow (TestClient + Popen mock)
- [ ] **P12.3** ✅ **(v3.2 NEW)** Idempotency asserted: pause+pause is no-op; resume+resume is no-op
- [ ] **P12.3** ✅ **(v3.2 NEW)** `DELETE /books/{slug}` without `?rollback_branch=true` keeps git branch (mock not called); with the flag, branch deletion is invoked
- [ ] **P12.3** ✅ **(v3.2 NEW)** Cross-book parallel mutation test passes without state corruption (P13.1 SQLite read consistency)
- [ ] **P12.3** 📊 **(v3.2 NEW)** Tests use TestClient + subprocess mock — no live subprocess, no API spend; <30s wall-clock

### P13 — SQLite cross-book index (READ-ONLY cache)  *(was v2 P5.3)*

- [ ] **P13.1** ✅ `_workspace/podcast.db` gitignored
- [ ] **P13.1** ✅ Fresh empty DB rebuild reproduces identical state from filesystem
- [ ] **P13.1** ✅ Per-book row includes `disambiguation_pending_count` (P4 link)

### P14 — Dashboard mutation UI  *(was v2 P5.4)*

- [ ] **P14.1** ✅ Destructive UI ops require typed slug to confirm
- [ ] **P14.1** ✅ All button actions audit-logged via P12.1

---

## Wave 5 — OBSOLETED by v3.2 — absorbed into W1+W2

All P15 / P16 acceptance rows have been redirected. Track progress under:
- **P5.4** (W1) — phase-id constants module
- **P8.6** (W2) — bulk phase rename + HTML doc rewrite (absorbs P15 + P15.4 acceptance)
- **P8.8** (W2) — agent dedup + isolation CI (absorbs P16.1–P16.4 acceptance)

W5 row remains in the YAML waves[] only so `run_wave.py 5` has a no-op handler.

- [x] **W5.obs** ✅ **(v3.2)** P15 + P15.4 redirected to P5.4 + P8.6 acceptance
- [x] **W5.obs** ✅ **(v3.2)** P16.1-P16.4 redirected to P8.8 acceptance
- [x] **W5.obs** ✅ **(v3.2)** Legacy_id_map updated: `P15`, `P16`, `P15.4`, `"v2 P6.1"`, `"v2 P6.2+P6.3"` all map to OBSOLETED_BY_* values

---

## Wave 6 — Deferred (trigger-gated, no acceptance until promoted)

- [ ] **P17** 🟡 PDF pre-splitting — promote when book exceeds 500MB OR 2000 pages OR DI 600s poll budget  *(was v2 P7.1)*
- [ ] **P18** 🟡 Parallel per-chapter LLM calls — promote when P6 cost-tracking stable AND user opts in  *(was v2 P7.2)*
- [ ] **P19** 🟡 **(v3.2 EXPANDED)** Trainer self-learning — phase-prompt addenda + regression fixtures + health recursion; promote when P13 SQLite proven stable AND P2.6 refinement determinism green AND P9.8 yield report shows fixture_coverage_pct UP

#### P19.1 — Phase-prompt addendum substrate  *(v3.2 NEW)*

- [ ] **P19.1** ✅ **(v3.2)** `content/podcast/.skill/handbook/_learned-addenda/` directory exists with `README.md` documenting schema + R9 cap
- [ ] **P19.1** ✅ **(v3.2)** `_authoring.py` prompt assembly reads addenda matching current phase and concatenates them in `<learned-addenda>` XML block at end of system prompt
- [ ] **P19.1** ✅ **(v3.2)** R9 cap enforced: 6th addendum to same phase triggers FIFO eviction (oldest → `_archive/`)
- [ ] **P19.1** ✅ **(v3.2)** `podcast-trainer.agent.md` Protocol §3 documents the addendum-writing flow with ≤5 cap
- [ ] **P19.1** ✅ **(v3.2)** Every addendum file's frontmatter validates against schema (schema_version, phase, signature, authored_by, authored_at, authored_from_books)

#### P19.2 — Phase-prompt regression fixtures + Goodhart guard  *(v3.2 NEW)*

- [ ] **P19.2** ✅ **(v3.2)** ≥3 fixtures per phase under `_learning/fixtures/phase_prompts/<phase>/` (05-refine-english, 06-phonetics, 07-chapter-design, 08-enrichment, 11-per-chapter)
- [ ] **P19.2** ✅ **(v3.2)** `scripts/podcast/test_phase_prompts.py` exits 0 against current fixtures (post-P19.1 substrate; no addenda yet)
- [ ] **P19.2** ✅ **(v3.2)** Trainer addendum proposals MUST pass `test_phase_prompts.py` before write; failing proposals archived with tombstone
- [ ] **P19.2** ✅ **(v3.2)** `podcast-trainer.agent.md` INVARIANTS reaffirms: trainer never authors or modifies phase_prompts fixtures (only humans)
- [ ] **P19.2** ✅ **(v3.2)** CI: `test_phase_prompts.py` runs on every PR touching `scripts/podcast/_authoring.py` OR `content/podcast/.skill/handbook/_learned-addenda/`

#### P19.3 — Health-score recursion (next-book post-addendum verification)  *(v3.2 NEW)*

- [ ] **P19.3** ✅ **(v3.2)** `invoke_trainer` records `addenda_in_effect` list in end-of-book audit
- [ ] **P19.3** ✅ **(v3.2)** Next-book trainer pass computes per-signature health-score delta vs. last-book-with-this-signature; reverts regressed addenda automatically
- [ ] **P19.3** ✅ **(v3.2)** Revert-tombstone in `_learned-addenda/_archive/` cites the regression measurements
- [ ] **P19.3** ✅ **(v3.2)** If addendum reverts 2+ times for the same signature, signature escalates to human-review queue (P14 dashboard surface)
- [ ] **P20** 🟡 Web upload for PDFs in dashboard — promote when P12 mutation API stable  *(was v2 P7.4)*

---

## Cancelled phases (from v2 SDK migration)

The following v2 phases are **CANCELLED** by the v3 directive "Claude Code is the primary execution mechanism." No acceptance rows; recorded here for traceability:

- ~~v2 P3.1~~ — wholesale `_claude_client.py` SDK wrapper. Replaced by narrow side-channel use only (P6 cost ledger helper, P8 status helper).
- ~~v2 P3.2~~ — swap `_chunking.py` to SDK. CANCELLED — `claude -p` stays primary.
- ~~v2 P3.3~~ — swap `_authoring.py` to SDK. CANCELLED.
- ~~v2 P3.5~~ — end-to-end SDK validation run. CANCELLED.
- ~~v2 P3.6~~ — SDK fallback shim (`PODCAST_LLM_BACKEND=cli`). CANCELLED — no SDK to fall back from.
- ~~v2 P6.4~~ — SDK token-count parity test. CANCELLED — no SDK to compare against.
- ~~v2 P6.5~~ — retire SDK fallback shim. CANCELLED.

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

### Plan conformance (repo-surgeon Pass 5)

- [ ] **L1** ✅ `_workspace/plan/podcast-plan.yaml` parses cleanly
- [ ] **L2** ✅ Every `done_when` references a phase id that exists; every `depends_on` resolves
- [ ] **L3** ✅ Every `intelligence_sources` path exists (no `<book>` template, no glob); P4 deliverable paths tracked as 🟡 until Wave 1 ships
- [ ] **L4** ✅ No cross-imports between `scripts/podcast/`, `scripts/memoir/`, `scripts/site/`
- [ ] **L7** ✅ `_workspace/plan/view/index.html` references every phase id (P1–P20) AND every wave id (W1–W6) from the YAML
- [ ] **L8** ✅ Every reference to a `meta.legacy_cleanup_basenames` entry outside plan/chats paths is annotated as deleted/retired/closed
- [ ] **L9** ✅ Every CANCELLED phase row above (v2 P3.x, P6.4, P6.5) has zero non-strikethrough references in plan files
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

### Learning-loop conformance  *(NEW v3.1 — codifies P-9 invariant)*

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

- Total checkboxes: ~230 (Pass 5 L10 counts actual rows; v3.2 net delta vs v3.1 ≈ +45: +5 P2.6 +4 P5.4 +1 P1.4-ec4 +10 P8.6 +12 P8.7 +9 P8.8 +3 P10.1-cost +3 P11-demote +8 P12.3 +5 P19.1 +5 P19.2 +4 P19.3 −9 P15 −8 P16 +3 W5.obs; v3.2 P5.1 SHIPPED checkbox banks +1 checked row)
- Currently checked: 12 (P3.1, P3.2, P5.1 SHIPPED, W5.obs ×3, OP-1..OP-6)
- Currently pending: ~218
- Verification mix: ✅ auto-verifiable (majority) · 🟡 dep-blocked · 🔒 manual gate · 📊 metric-bound

## Wave summary (autonomous scheduling targets)

| Wave | Phases | Effort | DONE-when (high-level) | Schedule intent |
|---|---|---|---|---|
| W1 Foundation | P1–P6 | 2–4 days (parallel) | All W1 rows checked incl. P2.6 determinism + P5.4 phase constants; kitab-al-riyad resume passes | Overnight idempotent run; zero LLM cost (P2.5+P2.6 tiny-book ~<$2) |
| W2 Observability + Polish | P7–P8 (incl. P8.6/P8.7/P8.8) | ~1.5 wk | Dashboard reachable; phase rename schema_version=2; D3 views render 6 diagrams; agent dedup + isolation CI green | Daytime+overnight; trivial LLM cost; W2 closes BEFORE W3 starts (zero-in-flight naturally true) |
| W3 Corpus | P9–P10 | ~1 wk wall-clock | 7 books shipped clean OR failure-modes documented; ETA ±30% (clock) AND ±25% (cost) | One book per scheduled invocation; cost-capped (pre-flight cost-eta check) |
| W4 Control Plane | P11(doc)–P14 | ~1 wk | 2 books parallel; mutations audit-logged + pytest-harnessed (P12.3); typed-slug destructive confirmation | Single window; mutation surface live |
| W5 OBSOLETED | — | N/A | Auto-DONE when P5.4 + P8.6 + P8.7 + P8.8 all check | N/A (absorbed into W1+W2 by v3.2) |
| W6 Deferred + Self-Learning | P17–P20 incl. P19.1/2/3 | N/A | Per-phase `promote_when` triggers fire; P19 self-learning gated by P13 + P2.6 + P9.8 | Not time-scheduled |
