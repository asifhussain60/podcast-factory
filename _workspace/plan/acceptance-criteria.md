# Acceptance Criteria — Master Checklist

**Companion to:** [`podcast-plan.yaml`](./podcast-plan.yaml) v2 (gap-closed + execute-readied 2026-05-19)
**Companion to:** [`view/index.html`](./view/index.html), [`research/findings.md`](./research/findings.md)
**Audited by:** `/repo-surgeon --plan-only` Pass 5 L10 (acceptance ↔ YAML sync)
**Read by:** journal-challenger Category B, podcast-challenger Category S (both consult this file)

This file is the SHIP / DONE oracle. Every row maps to one verifiable acceptance criterion from the plan. Use `- [x]` to mark done; `- [ ]` to mark pending. Group anchors (`### P0a — …`) match `phases[].id` in the YAML; row IDs (e.g., `P0a.1`) match `phases[].tasks[].id` so Pass 5 L10 can verify alignment.

**Verdict legend:** ✅ verifiable today · 🟡 verifiable after dependency · 🔒 manual gate · 📊 metric-bound

---

## P0-tier (parallel blockers — all four have `depends_on: []`)

### P0a — Journal/podcast boundary verification + CI lock-down

- [ ] **P0a.1** ✅ `scripts/podcast/_boundary_check.py` exists; runs in <2s over `scripts/podcast/`; exit 0 on a clean tree; exit non-zero with `file:line` on any write/append/`open(...,'w')` targeting `content/babu-memoir/**`, `content/_shared/**`, `scripts/memoir/**`, or `scripts/site/**`
- [ ] **P0a.1** ✅ Boundary contract documented as a section in `skills-staging/podcast/SKILL.md` (grep `boundary contract` returns the section)
- [ ] **P0a.2** ✅ `skills-staging/podcast/SKILL.md` contains a "Manual library handoff" section (grep returns it)
- [ ] **P0a.2** ✅ `docs/podcast/manual-library-handoff.md` exists, links to the proposed-library-entries.md schema, documents promotion workflow
- [ ] **P0a.2** ✅ `scripts/podcast/_proposal_writer.py` exists; given a populated chapter contract it emits a schema-valid `proposed-library-entries.md` with frontmatter `schema_version`, `book_slug`, `episode_id`, `generated_by`, `generated_at`
- [ ] **P0a.3** 🟡 CI gate wired in P6.3 (see P6.3 row); P0a.1 invocation present in `.github/workflows/podcast-isolation.yml`

### P0b — E2E test harness for the podcast pipeline

- [ ] **P0b.1** ✅ `scripts/podcast/tests/e2e/` directory exists with `__init__.py`, `conftest.py`, `fixtures/tiny-book/` (3-chapter, ~5k word synthetic source with ≥1 Arabic phrase)
- [ ] **P0b.1** 📊 Tiny-book fixture run cost <$0.50 per full pass (measured against cost-ledger when P3.4 lands; until then, manual verification with `claude -p` token logs)
- [ ] **P0b.2** ✅ `scripts/podcast/tests/e2e/test_full_pipeline.py` exists; `pytest scripts/podcast/tests/e2e/ -v` passes
- [ ] **P0b.2** ✅ Sunny-day test asserts: state.json shows each phase completed in order; refined-english.md AND _phonetics.md non-empty with >100 words each; every `_chunks/0b/win-*.in.md` has matching non-zero `win-*.out.md`; ≥1 chapter-contract; ≥1 chapter txt; halts at 0f; heartbeat updates within 30s; **NO log line containing `NO ARTIFACT`**
- [ ] **P0b.2** ✅ Sunny-day test fails when the P0 bug class returns (verified by toggling `--permission-mode` in a regression branch)
- [ ] **P0b.2** 📊 Tiny-book sunny-day total wall-clock <15min; cost <$1
- [ ] **P0b.3** ✅ `scripts/podcast/tests/e2e/test_failure_modes.py` exists; injects mock `claude -p` returning rc=0 with no file write; asserts orchestrator raises typed error (no silent advance); tests resume after kill mid-window (verifies `.out.md` checkpoint reuse); tests `--retry-phase` on failed 0c
- [ ] **P0b.4** ✅ `.github/workflows/podcast-e2e.yml` exists; PRs touching `scripts/podcast/` fail CI when E2E test fails; `skills-staging/podcast/SKILL.md` documents the gate

### P0c — Doc regressions introduced by legacy-file cleanup (2026-05-19)

- [x] **P0c.1** ✅ `docs/architecture/podcast-overview.html` paragraph rewritten; ChatGPT-portable card now points at `skills-staging/podcast/SKILL.md` and annotates the deletion (no broken link)
- [x] **P0c.2** ✅ Every reference to the four deleted basenames (`chatgpt-podcast-skill-prompt`, `folder-cleanup-prompt`, `podcast-refactor-executive-summary`, `podcast-orchestrator-large-books`) outside `_workspace/plan/` and `_workspace/.chats/` is annotated with one of: `deleted`, `retired`, `RETIRED`, `DELETED`, `closed` (verified by Pass 5 L8)

### P0 — Critical bug fix: `claude -p` permission mode

- [ ] **P0.1** ✅ `grep 'claude -p' scripts/podcast/` returns 0 results without `--permission-mode acceptEdits`; both call sites (`_chunking.py:_run_one_window`, `_authoring.py:_run_claude`) pass the flag
- [ ] **P0.2** ✅ Artifact check raises typed error when `out_path` missing OR `file_size == 0`; no silent `NO ARTIFACT` continuation; stdout/stderr captured in the exception
- [ ] **P0.3** ✅ P0.1 + P0.2 merged to `develop` BEFORE `book/kitab-al-riyad` resume; `book/kitab-al-riyad` rebased clean onto develop with `_system/orchestrator-state.json` untouched by the rebase; all N windows produce non-empty `.out.md` files; phase transitions `0b → 0c → 0d → 0e` cleanly OR halts cleanly at 0f human gate

---

## P1 — Observability foundation: heartbeat + status CLI + wait-banner

- [ ] **P1.1** ✅ `scripts/podcast/_progress.py` exposes daemon thread writing `<book>/_system/heartbeat.json` atomically (tmp + rename) every 30s with fields: `pid`, `phase`, `phase_status`, `elapsed_in_phase_s`, `last_chunk_written`, `last_chunk_mtime`, `last_log_line`, `subprocess_pid`; daemon=True so orchestrator exit terminates it cleanly
- [ ] **P1.1** ✅ Heartbeat impact on `claude -p` timing is zero (side-channel only; measured by comparing wall-clock with/without heartbeat on tiny-book fixture)
- [ ] **P1.2** ✅ Within 30s of any LLM call starting, `heartbeat.json` `label` reflects it (e.g., `0b · win-007 · 3082 words`); verified by E2E assertion
- [ ] **P1.3** ✅ `scripts/podcast/orchestrator_status.py` exists; runs in <1s on a 260-page book's state; falls back gracefully if `heartbeat.json` missing (uses log tail)
- [ ] **P1.3** ✅ Exit codes: 0 if process alive; 2 if dead; 1 if state stale (>5min)
- [ ] **P1.3** ✅ Boxed banner preserves row/column structure of `meta.async_safety.wait_banner_format` (template) with field substitution; structural-match unit test passes
- [ ] **P1.3** ✅ `--ascii` flag emits the same banner using `meta.async_safety.wait_banner_format_ascii` (ASCII fallback `+ - |` chars) for terminals without UTF-8 box support
- [ ] **P1.4** ✅ `<book>/_system/events.jsonl` tails cleanly with `tail -F`; line schema `{ts, phase, step, total, label, level, msg}` documented in `_progress.py` docstring

---

## P2 — Read-only Status API + browser dashboard

- [ ] **P2.0** ✅ `scripts/podcast/requirements.txt` exists; `pip install -r scripts/podcast/requirements.txt` succeeds in a clean venv
- [ ] **P2.1** ✅ `scripts/podcast/service/` exists with `__init__.py`, `app.py`, `models.py`, `sources.py`
- [ ] **P2.1** ✅ Server runs on `127.0.0.1:8765` (localhost only by default)
- [ ] **P2.1** ✅ `/docs` renders the OpenAPI spec
- [ ] **P2.1** ✅ pytest asserts every non-stream endpoint returns content-type `application/json` AND parses to valid JSON
- [ ] **P2.1** ✅ pytest asserts `/books/{slug}/stream` returns content-type `text/event-stream` AND emits at least one event
- [ ] **P2.1** ✅ Service uses filesystem ONLY (no DB, no global state)
- [ ] **P2.2** ✅ Dashboard SPA loads at `http://127.0.0.1:8765/`; book picker + phase timeline + live event stream rendered
- [ ] **P2.2** ✅ Phase-stuck detection: heartbeat age >2min flashes yellow; >10min flashes red
- [ ] **P2.3** ✅ `infra/launchd/com.journal.podcast-service.plist` passes `plutil -lint`
- [ ] **P2.3** ✅ `docs/podcast/service-startup.md` documents: install / verify-loaded / behavior-when-down / manual-start
- [ ] **P2.3** ✅ Dashboard JS shows friendly "service not running — see docs" card on connection failure

---

## P3 — Anthropic SDK migration: replace `claude -p` shell-out

- [ ] **P3.1** ✅ `anthropic` added to `scripts/podcast/requirements.txt` (one-line append, NOT a new file)
- [ ] **P3.1** ✅ `scripts/podcast/_claude_client.py` exposes `call_claude(prompt, *, max_tokens, model, on_token=None, on_error=None) -> str`; bubbles typed errors (RateLimit, Overloaded, Auth, ContentPolicy)
- [ ] **P3.1** ✅ Reads `ANTHROPIC_API_KEY` from env (keychain-stored per `store-keychain-keys.sh`)
- [ ] **P3.1** ✅ Implements Claude 4.6+ continuation pattern for interrupted streams
- [ ] **P3.2** ✅ `grep 'subprocess\.\(run\|Popen\)' scripts/podcast/_chunking.py` returns 0; `out_path` written by Python after `call_claude` returns; per-token heartbeat bumps via `on_token`
- [ ] **P3.3** ✅ Same as P3.2 for `_authoring.py` (0d/0e and per-chapter authoring)
- [ ] **P3.4** ✅ `<book>/_system/cost-ledger.jsonl` populated; line schema `{ts, phase, step, model, input_tokens, output_tokens, cache_read, cache_create, cost_usd}`
- [ ] **P3.4** ✅ `scripts/podcast/cost_ledger_summary.py` exists; exit 0; prints structured totals
- [ ] **P3.4** ✅ `cost-validation.json` regenerated each run; diffable in PR review
- [ ] **P3.4** 🔒 Manual cross-check vs Anthropic console for first SDK book: ledger total within ±1%
- [ ] **P3.4** ✅ Cost ceiling implemented per `open_questions.Q2.default_until_overridden`: soft warning at $20 (heartbeat); hard halt before Phase 0d at $50; CLI overrides `--cost-cap-soft` / `--cost-cap-hard`
- [ ] **P3.5** ✅ Full re-run on tiny-book OR kitab-al-riyad with SDK path: all phases complete; zero subprocess errors; dashboard shows live token counts during 0d/0e; cost-ledger populated
- [ ] **P3.5** ✅ P0b E2E suite passes on SDK code path
- [ ] **P3.6** ✅ `PODCAST_LLM_BACKEND=cli` replicates old behavior end-to-end on tiny-book fixture
- [ ] **P3.6** ✅ Default behavior unchanged when env var unset (SDK path)
- [ ] **P3.6** 🟡 Removal scheduled in P6.5 (after first xlarge book ships clean on SDK)

---

## P4 — Sample corpus validation (graduated 30p → 865p)

- [ ] **P4.1** 📊 Ayyuhal Walad (30p): full pipeline to merge in <2h wall-clock; cost <$5
- [ ] **P4.2** 📊 Masaail searchable (81p): full pipeline; metrics recorded (token/cost/wall-clock)
- [ ] **P4.3** 📊 Majalis Moyyada (139p): full pipeline; metrics recorded
- [ ] **P4.4** 📊 Kitab Maqbas (392p): full pipeline; chapter contracts hold
- [ ] **P4.5** 📊 Asaas Al-Taveel (416p): full pipeline; metrics recorded
- [ ] **P4.6** 📊 Raahat al-Aqal (591p): full pipeline OR Doc Intelligence 600s poll budget remediation documented
- [ ] **P4.7** 📊 Rasail Ikhwan AsSafa (865p): full pipeline OR failure mode + remediation issue
- [ ] **P4.8** ✅ `scripts/podcast/orchestrator_status.py --eta` predicts wall-clock within ±30% on a held-out book (linear regression over P4.1–P4.7 runs)

---

## P5 — Control plane: mutation API + worker pool + SQLite cache

- [ ] **P5.0** ✅ `docs/podcast/multi-mac-decision.md` exists; documents the choice (default lean: primary-only service; secondary Macs are SSH-tunneled read-only viewers)
- [ ] **P5.0** ✅ `open_questions.Q1` marked resolved in YAML with a one-line decision ref
- [ ] **P5.1** ✅ All five mutation endpoints exist and return audit rows in `_workspace/podcast-audit.jsonl`
- [ ] **P5.1** ✅ Pause/resume verified on a live run (SIGSTOP/SIGCONT confirmed by ps state)
- [ ] **P5.1** ✅ Bearer-token auth from keychain; localhost-only default
- [ ] **P5.2** ✅ 2 books run truly in parallel without state corruption
- [ ] **P5.2** ✅ Server restart picks up orphaned runs via state.json scan (read-only resume detect)
- [ ] **P5.3** ✅ `_workspace/podcast.db` gitignored
- [ ] **P5.3** ✅ Fresh empty DB rebuild reproduces identical state from filesystem
- [ ] **P5.4** ✅ Destructive UI ops require typed slug to confirm

---

## P6 — Polish: phase rename + agent dedup + isolation CI + fallback retirement

- [ ] **P6.1** 🟡 Prereq verified: `orchestrator_status.py --all --json | jq '[.books[] | select(.phase_status=="running" or .phase_status=="failed")] | length'` returns 0
- [ ] **P6.1** ✅ Existing `kitab-al-riyad/_system/orchestrator-state.json` migrates seamlessly on first read (schema_version=1 → 2)
- [ ] **P6.1** ✅ `--retry-phase 0b` and `--retry-phase 05-refine-english` both resolve to the same phase (back-compat alias for one release)
- [ ] **P6.1** ✅ Docs (`docs/architecture/podcast-pipeline.html`, `podcast-orchestrator.html`, `podcast-quality-system.html`, `podcast-overview.html`, `index.html`) updated atomically with the code rename
- [ ] **P6.1** ✅ `grep -rE '\b0[a-g]\b' scripts/podcast/` returns 0 literal phase-ID strings (post-migration)
- [ ] **P6.2** ✅ Every agent in any of `.github/agents/`, `infra/claude-agents/`, `.claude/agents/` exists in `.github/agents/`
- [ ] **P6.2** ✅ `scripts/check_agent_dedup.py` exists; compares names across the three dirs; exits 0 only when set differences are empty; runs in CI
- [ ] **P6.2** ✅ VS Code/Claude Code agent picker shows each agent exactly once (PR description records visual verification step)
- [ ] **P6.2** ✅ `infra/claude-agents/` removed; git log preserves history (tracked deletion, not force-removal)
- [ ] **P6.2** ✅ `install-claude-skills.sh` idempotent: second run produces zero diffs
- [ ] **P6.3** ✅ `scripts/podcast/_isolation_check.py` exists; AST scan fails build on forbidden import
- [ ] **P6.3** ✅ `.github/workflows/podcast-isolation.yml` exists; isolation_check CI job is green on a clean tree
- [ ] **P6.4** ✅ Side-by-side compare on tiny-book fixture: heartbeat final `output_tokens` equals `stream.get_final_message().usage.output_tokens`
- [ ] **P6.4** ✅ `scripts/podcast/tests/e2e/test_token_count_parity.py` exists; passes
- [ ] **P6.5** ✅ `grep -r 'PODCAST_LLM_BACKEND' scripts/podcast/` returns 0 results
- [ ] **P6.5** ✅ `grep -rE 'subprocess\.(run|Popen).*claude' scripts/podcast/` returns 0 results

---

## P7 — Deferred / speculative (no acceptance gates until promoted from `defer_until`)

- [ ] **P7.1** 🟡 PDF pre-splitting (Option B) — promote when a book exceeds 500MB OR 2000 pages OR Doc Intelligence 600s poll budget
- [ ] **P7.2** 🟡 Parallel per-chapter LLM calls in 0e and convergence — promote when cost-tracking proven stable AND user explicitly opts in
- [ ] **P7.3** 🟡 Trainer ingestion of SQLite event log — promote when P5 SQLite index proven stable
- [ ] **P7.4** 🟡 Web upload for PDFs in dashboard — promote when P5 mutation API stable

---

## Cross-cutting acceptance gates

### Boundary integrity (enforced by journal-challenger Category B + podcast-challenger Category S + repo-surgeon Pass 5 L4/L5)

- [ ] **B1/S2** ✅ No file under `scripts/podcast/` writes to `content/babu-memoir/**`, `content/_shared/**`, `scripts/memoir/**`, or `scripts/site/**` (verified by `scripts/podcast/_boundary_check.py` AND repo-surgeon Pass 5 L5)
- [ ] **B2** ✅ Memoir chapters contain no content sourced from `content/podcast/library/books/*/chapters/` without an explicit `// source:` comment AND human review
- [ ] **B3/S3** ✅ Every `proposed-library-entries.md` carries the schema_version=1 frontmatter; every promoted entry has a ledger row
- [ ] **B4/S5** ✅ Journal authoring sessions never edit files under `content/podcast/**` or `scripts/podcast/**` (verified by git-diff against scope_out)

### Async safety (enforced by podcast-challenger Category S + repo-surgeon Pass 5 L6)

- [ ] **S1/L6** ✅ When orchestrator is running on a book, no agent or operator edits files under that book's `_system/`, `_chunks/`, `chapters/`, `chapter-contracts/`, `episodes/`, `transcripts/`, or `_learning/`
- [ ] **S1/L6** ✅ Wait-banner emitted before any HALT; banner field substitution succeeds on populated `heartbeat.json`

### Plan conformance (enforced by repo-surgeon Pass 5)

- [ ] **L1** ✅ `_workspace/plan/podcast-plan.yaml` parses cleanly
- [ ] **L2** ✅ Every `done_when` entry references a phase id that exists in `phases[]`; every `depends_on` resolves
- [ ] **L3** ✅ Every `intelligence_sources` path exists (no `<book>` template, no glob) — current known gap: `scripts/podcast/orchestrator_status.py` (created in P1.3); track as 🟡
- [ ] **L4** ✅ No cross-imports between `scripts/podcast/`, `scripts/memoir/`, `scripts/site/`
- [ ] **L7** ✅ `_workspace/plan/view/index.html` references every phase id from the YAML
- [ ] **L8** ✅ Every reference to a `meta.legacy_cleanup_basenames` entry outside plan/chats paths is annotated as deleted/retired/closed
- [ ] **L10** ✅ Every checkbox in this file references an id that exists in the YAML (or a known marker — B*, S*, L*, Q*, R*)

### Intelligence-source wiring (refinement prompt §"P2 — Journal and Podcast Intelligence Sources")

- [ ] **IS1** ✅ Podcast agents read all entries in `intelligence_sources.podcast.consult_before_any_edit` at session start for multi-step tasks; verified by SKILL.md's preflight read list matching the YAML
- [ ] **IS2** ✅ Journal agents read all entries in `intelligence_sources.journal.consult_before_any_edit`; verified by journal SKILL.md's reads list
- [ ] **IS3** ✅ Conflict resolution honored: when sources disagree, agents pick the highest-authority source per `intelligence_sources.conflict_resolution`
- [ ] **IS4** ✅ Plan staleness detection: agents run `/repo-surgeon --plan-only` when `meta.gap_closed` (or `meta.execute_readied`) is >7 days old AND active phase changed

### Challenger acceptance (refinement prompt §"Output Format")

- [ ] **CH1** ✅ journal-challenger Category B (B1–B4) implemented; revision-log entry dated 2026-05-19 present
- [ ] **CH2** ✅ podcast-challenger Category S (S1–S6) implemented; v1.8 entry dated 2026-05-19 present
- [ ] **CH3** ✅ Both challengers include `_workspace/plan/podcast-plan.yaml` and `_workspace/plan/acceptance-criteria.md` in `reads_guidance`
- [ ] **CH4** ✅ podcast-challenger S1/S3/S5 halt-block before any other category runs when fired P0
- [ ] **CH5** ✅ Both challengers emit a sidecar report referencing this file's row IDs when verdict is BLOCKED

---

## Refinement-prompt deliverables (refinement prompt §"Output Format")

The original VS Code Claude Code refinement prompt asked for seven deliverables. Sync against this file:

- [x] **OP-1** ✅ Understanding — two-agent boundary confirmed (`_workspace/plan/README.md` "Bounded scope")
- [x] **OP-2** ✅ Current-State Findings — `_workspace/plan/research/findings.md` §7 + §8
- [x] **OP-3** ✅ Consolidated Todo List — this file
- [x] **OP-4** ✅ Safety Assessment — `_workspace/plan/podcast-plan.yaml` `async_safety` + per-phase `depends_on`
- [x] **OP-5** ✅ Execution Plan — `_workspace/plan/README.md` Phase summary + this file's grouping
- [x] **OP-6** ✅ Acceptance Criteria — this file
- [ ] **OP-7** 🔒 Final Recommendation — issued per session (current: execute P0c.1/P0c.2 cleanup first, then P0 patch, then resume kitab-al-riyad)

---

## How to update this file

1. Mark a row `- [x]` ONLY when its acceptance command/check has been run and passes (or is observably true).
2. NEVER mark a row done without verification; trust but verify.
3. If a row no longer maps to a YAML id (drift), Pass 5 L10 will flag it on the next run — either delete the row or restore the id in the YAML.
4. When a new phase task is added to `podcast-plan.yaml`, add a row here in the same session. Pass 5 catches missing rows.
5. Date completed batches in the commit message; the file itself stays terse.

## Inventory

- Total checkboxes: ~120 (count is illustrative; Pass 5 L10 counts actual rows)
- Currently checked: 8 (P0c repairs + OP-1..OP-6)
- Currently pending: ~112
- Verification mix: ✅ auto-verifiable (majority) · 🟡 dep-blocked · 🔒 manual gate · 📊 metric-bound
