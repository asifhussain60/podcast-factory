# Podcast Plan — Per-Phase DoR Appendix

**Companion to:** [`podcast-plan-DoR.md`](./podcast-plan-DoR.md) (the 12-check DoR-audit summary). Where that document declares the plan-level DoR GREEN, this appendix breaks each remaining phase into its **blockers / assumptions / ambiguities / operator action**, so the autonomous loop can safely execute or safely halt.

**Source of truth:** mirrored by the halt-with-DoR runners under [`scripts/podcast/phases/`](../../scripts/podcast/phases/). When this doc disagrees with the runner code, the runner code wins (it's machine-enforced).

**Read order:** the launchd-driven autonomous loop reads this implicitly — every tick, the runners print their DoR section to `~/Library/Logs/podcast-w1.log` until the deliverable lands. The operator's first stop is the log; this file is the bird's-eye view.

---

## Phase status legend

| Status | Meaning |
|---|---|
| ✅ shipped | Deliverable exists; runner auto-marks acceptance every tick |
| 🟢 verify-only | Deliverable shipped; runner is a pure-verify check |
| 🟡 halt-with-DoR (operator-content) | Operator must hand-author content; runner halts cleanly with action prompt |
| 🟠 halt-with-DoR (needs-mocks) | Code phase but requires Azure / claude -p mocking — not safe to auto-execute |
| 🔴 halt-with-DoR (needs-azure-spend) | Requires explicit operator authorization for real Azure spend |
| 🔵 halt-with-DoR (agent-spec-edit) | Edits `.github/agents/*.agent.md` or similar — careful diff required |
| ⚪ deferred | Blocked on another phase in a later wave |

---

## Wave 1 — Foundation & Guardrails

### P1.1 — Boundary check  ✅
- Deliverable: [`scripts/podcast/_boundary_check.py`](../../scripts/podcast/_boundary_check.py)
- Runner: [`phases/p1_1.py`](../../scripts/podcast/phases/p1_1.py)
- Status: shipped + tested; runs <2s on the current tree; exit 0 baseline.

### P1.2 — Manual library handoff  ✅
- Deliverables:
  - [`scripts/podcast/_proposal_writer.py`](../../scripts/podcast/_proposal_writer.py) — `ProposalBundle` + `write_proposal()`
  - [`docs/podcast/manual-library-handoff.md`](../../docs/podcast/manual-library-handoff.md) — operator guide
  - SKILL.md `### The one permitted outward connection — Manual library handoff` section
- Runner: [`phases/p1_2.py`](../../scripts/podcast/phases/p1_2.py)
- Status: shipped + 16 tests.

### P1.3 — CI gate cross-reference  ⚪ (blocked on P8.8)
- Resolves when [`P8.8`](../../scripts/podcast/phases/) lands `.github/workflows/podcast-isolation.yml` in W2.
- No runner needed in W1; the acceptance row references the future workflow.

### P1.4 — Wave kickoff harness  ✅
- Deliverable: [`scripts/podcast/run_wave.py`](../../scripts/podcast/run_wave.py)
- 33 unit tests including idempotency, exit-codes, --check flag, W3 cost-cap guard, W5 phase-gate.

### P2.1 — Tiny-book fixture  🟡 (operator-content)
- **Blockers:** content must be hand-authored.
- **Assumptions:**
  - Synthetic text-only (no PDF, no Azure).
  - <$0.50 per full pass.
  - ≥1 Arabic phrase + ≥1 numeric claim for Loop N.
- **Ambiguities:**
  - Match Ayyuhal Walad register vs. generic? (Recommend matching for prompt reuse.)
  - Include intentional `[VERIFY CITATION]` markers? (Recommend yes — exercises Loop A.)
- **Operator action:** create `scripts/podcast/tests/e2e/{__init__.py,conftest.py,fixtures/tiny-book/source.md}` with 3 H2-separated chapter sections, ~5k words.

### P2.2 — Sunny-day E2E  🟠 (needs-mocks)
- **Blockers:** P2.1 first; mock strategy for Azure + `claude -p`.
- **Assumptions:** <15min wall-clock, <$1 cost (zero LLM cost when fully mocked).
- **Ambiguities:** which mock layer (subprocess intercept vs. module replacement vs. HTTP)? Recommend subprocess intercept — closest to live behavior.
- **Operator action:** scaffold `tests/e2e/test_full_pipeline.py` with subprocess.run patched, asserting full PHASE_ORDER + artifact existence.

### P2.3 — Rainy-day E2E  🟠 (needs-mocks)
- **Blockers:** P2.1 + P2.2 first.
- **Assumptions:** mock can inject rc=0-no-write deterministically.
- **Operator action:** assert ChunkingError / AuthoringError raises (P5.2 path); resume-after-kill; --retry-phase on 06-phonetics.

### P2.4 — Podcast-e2e CI workflow  🟡 (operator-content)
- **Blockers:** P2.2 + P2.3 green first.
- **Assumptions:** GitHub Actions has Python 3.14 (or close); use setup-python.
- **Ambiguities:** push-on-PR-only vs. all-pushes? Recommend PR-only.
- **Operator action:** `.github/workflows/podcast-e2e.yml` with path-filter on `scripts/podcast/**`.

### P2.5 — Learning-loop E2E + CI gate  🟠 (needs-mocks)
- **Blockers:** mock challenger that emits canned findings.
- **Assumptions:** `test_challenger.py` exists today (verified) and stays green.
- **Operator action:** `tests/e2e/test_learning_loop.py` + `.github/workflows/podcast-learning-loop.yml`.

### P2.6 — Golden-fixture refinement determinism  🟡 + one-time live  ⚠
- **Blockers:** P2.1 tiny-book fixture first. THEN one-time live `claude -p` to author the golden (~$0.50).
- **Assumptions:** Levenshtein-ratio ≥ 0.90 + structural-key parity is the bit-stability contract.
- **Ambiguities:** Levenshtein library — recommend rapidfuzz (pure-Python fallback available).
- **Operator action:**
  1. Run author_phase_0b ONCE on tiny-book → produce golden refined-english.md
  2. Commit golden with `GOLDEN-ESTABLISHED: tiny-book v1`
  3. Author test_refinement_determinism.py asserting subsequent runs match.

### P3.1 + P3.2 — Doc cleanup  ✅ (already shipped on develop)

### P4.1 — Abjad-numerals shared file  ✅
- Deliverable: [`content/_shared/arabic/06-abjad-numerals.md`](../../content/_shared/arabic/06-abjad-numerals.md)
- Status: shipped. Mashriqi + Maghribi tables, Hisab al-Jummal practice, reference calcs (Allah=66, basmala=786, Muhammad=92, Ali=110), Ch-02 worked examples (kun=70, fayakun=166, kun fayakun=236, irāda+amr+qawl=681).
- Post-create: READ-ONLY for both skills.

### P4.2 — Numeric/symbolic disambiguation handbook  ✅
- Deliverable: [`content/podcast/.skill/handbook/numeric-symbolic-disambiguation.md`](../../content/podcast/.skill/handbook/numeric-symbolic-disambiguation.md)
- Status: shipped. 7 sections (triggers, workflow, one-time enum rule, anachronism, invented-content-is-P0, source-preference register, worked-example pointer). Cross-refs 06-abjad-numerals.md + numeric-symbolic-disambiguation-plan.md.

### P4.3 — SKILL.md pre-read extension  ✅
- Reference #21 + SHARED_ARABIC #6a added; "seven SHARED_ARABIC files" count updated.

### P4.4 — Pre-refined-source-mode handbook extension  ✅
- §"Numeric Disambiguation scaffolding (P4 protocol)" + failure-mode #6 added.

### P4.4b — Loop N regression fixture  ⚪ (waits on P4.5)
- **Blockers:** P4.5 must define Loop N check IDs first; expected.json cites them.
- **Operator action:** after P4.5 lands, create `_learning/fixtures/loop_n_numeric_invented/{input.txt,expected.json}`; extend test_challenger.py.

### P4.5 — Challenger Loop N spec  🔵 (agent-spec-edit)
- **Blockers:** agent currently in `infra/claude-agents/` + `.claude/agents/`; not yet in `.github/agents/` (P8.8 migrates).
- **Assumptions:** 5 checks + P0/P1/P2 severity ladder defined in podcast-plan.yaml P4.5 spec.
- **Ambiguities:** Check IDs naming (N1..N5 vs. N-INVENTED-ENUMERATION etc.). Pick one and document.
- **Operator action:** author the Loop N section in both current locations (infra/+.claude/); stage for P8.8 to carry into .github/agents/. Bump CHALLENGER_VERSION to 2.1 in `_rules.py`.

### P4.6 — Phase 07-chapter-design numeric scan  🟠 (invasive _authoring.py)
- **Blockers:** edits the chapter-design prompt; must be guarded by P2.2 sunny-day staying green.
- **Operator action:** edit `author_phase_0d` (now 07-chapter-design) to scan for numeric claims; emit numeric-disambiguation-register.md.

### P4.7 — Master & Disciple Ch-02 scaffolding  🟡 (operator-content)
- **Source material:** `_workspace/plan/numeric-symbolic-disambiguation-plan.md` §3 has the exact content.
- **Files to update:** `_notebooklm/{02-glossary.md, 03-source-integrity-notes.md, ch02-scaffolding.md, 06-human-review-checklist.md}`.
- **Operator action:** apply the 4 file updates per plan doc §3. Decision log: 12-jazāʾir=both (symbolic+historical); sphere-cipher=NEEDS HUMAN REVIEW; fifth intermediary=NEEDS HUMAN REVIEW.

### P4.8 — intelligence_sources + disambig-plan header  ✅
- Both YAML `intelligence_sources.podcast.consult_before_any_edit` references AND disambig-plan header pointer were already in place pre-this-session; runner verifies + marks.

### P5.1 — Permission-mode flag  ✅ (shipped on develop)

### P5.2 — Artifact validation hardening  ✅ (shipped on this branch)

### P5.3 — kitab-al-riyad resume  🔴 (needs-azure-spend)
- **Blockers:** ~$15-25 Azure + claude -p spend; operator authorization required.
- **Assumptions:** state.json resumes cleanly; Azure quotas have headroom for 260p.
- **Ambiguities:**
  - Run on feature branch or directly on book/kitab-al-riyad? (Recommend cherry-pick P5.2 onto book branch.)
  - Land P6.1 integration with _chunking.py + _authoring.py first? (STRONG yes — otherwise ledger captures only run-total, not per-call.)
- **Operator action:** see P5.3 detect message in the runner. Do NOT auto-execute under launchd.

### P5.4 — Phase-id constants module  ✅

### P6.1 — Cost-ledger writer  ✅
- Deliverable: [`scripts/podcast/_cost_ledger.py`](../../scripts/podcast/_cost_ledger.py)
- 16 unit tests, full pricing table, tolerant stdout-usage parser.
- **Follow-up (not in this acceptance):** wire `append_from_claude_p_stdout()` into the actual `_chunking.py` + `_authoring.py` call sites. Currently the writer EXISTS; integration into those code paths is a separate non-W1 task (could be a sub-task of P6.1 or P6.3).

### P6.2 — Cost-ledger summary CLI  ✅

### P6.3 — Soft/hard cost caps  🟠 (waits on P7 heartbeat for soft path)
- **Blockers:**
  - Soft-warning path: P7 heartbeat (W2) for visible warning surface.
  - Hard-halt path: orchestrate_book.py integration.
- **Operator action:** see P6.3 detect message in the runner.

### P6.4 — Trainer cost-ledger hook  🔵 (agent-spec-edit)
- **Blockers:** edits `.github/agents/podcast-trainer.agent.md` + `invoke_trainer()` prompt.
- **Operator action:** see P6.4 detect message; bump Q3 `closed_at` to today's date when complete.

---

## Wave 2 — Observability + Polish

All phases pending; runners not yet wired. W2 work starts AFTER W1 acceptance is fully green AND the W1 PR merges to develop.

### P7 — Heartbeat + status CLI + wait-banner
### P8 — Read-only Status API + browser dashboard (incl. P8.6 phase rename, P8.7 D3 view upgrade, P8.8 agent dedup)
### P22 — Operator transcript-review gate (English-transcript halt-with-DoR)
### P23 — Episode Format Contract (tradition-agnostic, audience_profile-gated)

### P24 — podcast-blueprint (content-aware episode-structure planner) — slot 05.5-blueprint  🟢 SURFACE SHIPPED

Inserted between the P22 transcript-review resume and the existing `06-phonetics` stage. Three layers — Layer 1 scan/classify (Haiku default; recommends model for Layers 2/3), Layer 2 episode planner, Layer 3 first-run-only `arc-conventions.md` emitter. Tradition-agnostic; seeds P23's `series-config.yaml` `audience_profile` + `source_tradition` via `proposed-config.yaml` patch on `--approve-blueprint`.

Four LOCKED decisions (operator-set 2026-05-20 from Air session 7768a31c, not re-debated):
1. Name = `podcast-blueprint` (NOT `podcast-arc`).
2. Slot = phase `0b.5` (orchestrator slug `05.5-blueprint`).
3. Layer 1 auto-upgrades the model for Layers 2–3 via `classification.recommended_model_for_layer_2`; `--force-model` overrides; cost-ledger audits both.
4. `arc-conventions.md` is OPTIONAL on input, agent-seeded DRAFT on first run, operator-editable thereafter; Layer 3 NEVER overwrites; NO global default.

#### P24.1 — Agent spec + skill scaffold + classification schema + handbook  ✅ SHIPPED 2026-05-20
- Deliverables (all in place):
  - [`infra/claude-agents/podcast-blueprint.md`](../../infra/claude-agents/podcast-blueprint.md)
  - [`.github/agents/podcast-blueprint.agent.md`](../../.github/agents/podcast-blueprint.agent.md)
  - [`skills-staging/podcast-blueprint/SKILL.md`](../../skills-staging/podcast-blueprint/SKILL.md)
  - [`content/podcast/.skill/handbook/blueprint-protocol.md`](../../content/podcast/.skill/handbook/blueprint-protocol.md)
  - [`content/podcast/.skill/handbook/_schemas/classification.schema.json`](../../content/podcast/.skill/handbook/_schemas/classification.schema.json)
  - [`content/podcast/.skill/handbook/_templates/arc-conventions.template.md`](../../content/podcast/.skill/handbook/_templates/arc-conventions.template.md)
  - [`scripts/podcast/_blueprint_schema.py`](../../scripts/podcast/_blueprint_schema.py)
  - [`scripts/podcast/tests/test_blueprint_schema.py`](../../scripts/podcast/tests/test_blueprint_schema.py) — 28 tests green
- Runner: [`phases/p24_1.py`](../../scripts/podcast/phases/p24_1.py) — verify-only on next launchd tick.
- Cross-link: P23 [`episode-format-contract.md`](../../content/podcast/.skill/handbook/episode-format-contract.md) §2 now references the P24 synergy.

#### P24.2 — Layer 1 (scan/classify)  🟠 BLOCKED on Air handoff
- **Blocker:** the truncated three-layer architecture body from Air session 7768a31c (2026-05-20) ended at `### Three-layer architecture` without describing the layer prompts. Layer 1's prompt skeleton cannot be authored faithfully to Asif's design intent until that text arrives.
- **Assumptions:** Layer 1 runs on Haiku by default (cheap scan); promotes itself if signals warrant. Cost <$0.30 per book for the 260p Kitab al-Riyad scale.
- **Ambiguities (resolve once handoff arrives):**
  - Should Layer 1 self-classification run in TWO passes (cheap scan → confidence score → conditional Sonnet re-scan if confidence low)? Defer to handoff body.
  - How many signals does Layer 1 need to cite in `rationale` (one? three? all that fit in 500 chars)? Defer to handoff body.
- **Operator action:** retransmit the truncated Air handoff section. Once received, the Layer 1 prompt skeleton can be authored against the existing `classification.schema.json` + handbook.

#### P24.3 — Layer 2 (episode planner) + Layer 3 (convention emitter)  🟠 BLOCKED on Air handoff
- **Blocker:** same as P24.2.
- **Assumptions:** Layer 2 uses the model dictated by Layer 1 unless `--force-model` overrides. Layer 3 NEVER overwrites an existing `<book>/arc-conventions.md` — invariant enforced at the `_blueprint.py` call site (file-exists check before write).
- **Ambiguities:**
  - Layer 3 boilerplate for `clinical-wellness` audience_profile — does it differ from `modern-secular` beyond honorifics density? Defer to handoff body.
  - Cross-episode anti-repetition seed count per planning_mode — empirical pick after first live run on tiny-book.
- **Operator action:** unblocked when P24.2 unblocks.

#### P24.4 — Orchestrator wiring + cost-ledger integration  🟠 PARTIALLY-LANDABLE
- **Landable NOW (shell only):** `_phases.py` slot registration; `orchestrate_book.py` flag plumbing (`--force-model`, `--auto-approve-blueprint`, `--approve-blueprint`, `--skip-blueprint-gate`); halt-with-DoR when `_blueprint.py` not yet implemented.
- **Blocked on P24.2/P24.3:** the slot's actual content (Layer 1/2/3 dispatch).
- **Operator action:** P24.4 shell can land on `feat/podcast-w1-foundation` independently; merge gated by W2 done_signal.

#### P24.5 — E2E test + classification stability regression  🟠 BLOCKED on P24.2 + P24.3 + P24.4
- **Blocker:** needs all three layers + orchestrator wiring before E2E can pass.
- **Assumptions:** tiny-book fixture (P2.1) is the cheap exercise target; Ayyuhal Walad is the medium regression target.
- **Operator action:** unblocked when P24.4 shell + P24.2 + P24.3 ship.

#### P24.6 — DoR appendix + acceptance-criteria + P23 cross-link  ✅ SHIPPED 2026-05-20
- THIS section (P24.6.dor) ✅
- [`acceptance-criteria.md`](./acceptance-criteria.md) P24 rows ✅
- [`episode-format-contract.md`](../../content/podcast/.skill/handbook/episode-format-contract.md) §2 P24-synergy note ✅

---

## Wave 3 — Corpus Validation
All phases pending. W3 invocation refuses without `--book <slug>` AND a passing cost-cap pre-flight (already enforced by `run_wave.py 3`).

### P9 — Sample corpus validation (7 books, Ayyuhal Walad → Rasail Ikhwan)
### P10 — ETA model (wall-clock + cost)

---

## Wave 4 — Control Plane

### P11.1 — Multi-Mac decision  ✅
- Deliverable: [`docs/podcast/multi-mac-decision.md`](../../docs/podcast/multi-mac-decision.md) — shipped this session.
- Resolution: primary-only service; secondary Macs SSH-tunneled read-only viewers; locked.

### P12 / P13 / P14 — Mutation API + worker pool / SQLite cache / dashboard mutation UI
All pending.

---

## Wave 5 — Deferred + Self-Learning (trigger-gated)

### P17 / P17.1 / P18 / P19.1 / P19.2 / P19.3 / P20
All trigger-gated; promote individually as their `promote_when` conditions fire.

---

## Cross-wave: open questions

| Q | Status | Notes |
|---|---|---|
| Q1 multi-Mac | CLOSED | Resolved via P11.1 this session. |
| Q2 cost ceiling | RESOLVED | Policy locked ($20 soft / $50 hard); P6.3 implements. |
| Q3 trainer cost-ledger | IMPLEMENTING | Closes when P6.4 lands. |
| Q4–Q7 M&D Ch-02 content | RESOLVED-VIA-LOOP-N | Protocol IS the resolution; flag NEEDS HUMAN REVIEW. |

---

## Summary — autonomous-execution-ready state

| Category | Count | Detail |
|---|---:|---|
| ✅ Shipped (deliverable + runner auto-marks) | **12** | P1.1, P1.2, P1.4, P3.1, P3.2, P4.1, P4.2, P4.3, P4.4, P4.8, P5.1, P5.2, P5.4, P6.1, P6.2, P11.1, P24.1 |
| 🟡 / 🟠 / 🔴 / 🔵 Halt-with-DoR (runner halts with action prompt) | **15** | P2.1, P2.2, P2.3, P2.4, P2.5, P2.6, P4.4b, P4.5, P4.6, P4.7, P5.3, P6.3, P6.4, P24.2, P24.3, P24.4, P24.5 |
| ⚪ Deferred to W2+ | several | P1.3 → P8.8; all W2/W3/W4 P12+ / W5 phases |

**Every W1 phase now has either:**
- a deliverable + verify-only runner that auto-marks acceptance, OR
- a halt-with-DoR runner that prints a precise human-action prompt every tick until the deliverable lands.

**No phase is hidden.** Every blocker, assumption, and ambiguity is in this doc AND in the runner's `DOR` block (which prints to the launchd log on every tick).

**Safe to walk away.** The autonomous loop:
- Marks acceptance for the 11 shipped phases on the first tick after this commit.
- Halts cleanly on the 12 not-yet-shipped phases with action prompts.
- Never silently advances.
- Boundary check enforced every tick.
- W3 + W5 still refuse to fire without explicit flags.
