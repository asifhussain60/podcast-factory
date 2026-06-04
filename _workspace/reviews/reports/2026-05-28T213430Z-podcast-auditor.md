# Podcast Auditor Report — 2026-05-28T21:34:30Z

**Auditor version**: 1.1
**Scope**: core
**Since**: full history (focused on ecc1446, 472de6f, 522794c — last 3 commits)
**Run started**: 2026-05-28T21:25:00Z
**Run completed**: 2026-05-28T21:34:30Z
**Verdict**: drift-detected

## Headline summary

- P0 findings: 1
- P1 findings: 4
- P2 findings: 5
- Pre-existing (not introduced by recent work): 4 pipeline unit tests, 7 regression unit tests

---

## Findings by axis

### Axis B — Accuracy

| ID | Severity | Location | Title | Proposed fix |
|---|---|---|---|---|
| AU-A1-001 | P0 | plan-dashboard/src/data/*.json | Snapshots stale — reference 472de6f, HEAD is 522794c | `cd plan-dashboard && npm run snapshot && git add src/data/*.json && git commit -m "chore(dashboard): regen snapshots for Wave K"` |
| AU-A1-002 | P1 | scripts/podcast/_convergence.py:70, plan.yaml K2 | PEQ gate described in plan but not enforced in code | Add `if outcome.peq_total is not None and outcome.peq_total < 70: continue` before convergence return |
| AU-A1-003 | P1 | scripts/podcast/tests/ | 3 stated Wave K test deliverables (test_quality.py ≥10, test_challenger_scoring.py ≥8, test_wisdom_quality_gate.py ≥6) are marked completed in plan.yaml but files do not exist | Create the 3 test files |

### Axis C — Scalability

| ID | Severity | Location | Title | Proposed fix |
|---|---|---|---|---|
| AU-S1-001 | P2 | scripts/podcast/build_episode_txt.py (1563 L), extract_chapter.py (1301 L), tighten_source.py (1051 L), run_wave.py (824 L), _slide_convergence.py (764 L), _slide_authoring.py (652 L), publish_to_library.py (627 L) | DR-005: 7 scripts exceed 600-line limit (pre-existing) | Add to refactor plan — split largest modules into sub-packages |

### Axis D — Extensibility

| ID | Severity | Location | Title | Proposed fix |
|---|---|---|---|---|
| AU-X3-001 | P2 | tools/source_extractor/adapters/wisdom.py:45,126 | Class names `KashkoleAdapter` + `KashkoleQuranCorpus` not renamed during kashkole→wisdom rename; tools/content_reviewer/README.md:66 references `KashkoleQuranCorpus` | Rename classes to `WisdomAdapter` / `WisdomQuranCorpus`; update README.md |
| AU-X3-002 | P2 | tools/content_translator/cli.py:113, tools/content_translator/stages/adapt_auto.py:46 | KASHKOLE in user-facing UX strings and LLM system prompt — not updated by rename | Replace with "Wisdom" (LLM prompt) and "Wisdom Translation Cost Ledger" (CLI) |

### Axis E — Hygiene

| ID | Severity | Location | Title | Proposed fix |
|---|---|---|---|---|
| AU-H1-001 | P2 | _workspace/wisdom-brief.md | Depth-1 file in _workspace root — not in root-legit whitelist | Move to `_workspace/plan/` or appropriate subfolder; delegate to vacuum |
| AU-H1-002 | P2 | _workspace/plan/wisdom-pipeline-efficiency-plan.md | Plan-root file — vacuum.md documents numeric-symbolic-disambiguation-plan.md as the only allowed exception, not this file | Check if content absorbed into plan.yaml; archive or move |

### Pre-existing / confirmed not-new

| ID | Severity | Location | Title | Notes |
|---|---|---|---|---|
| PRE-001 | P1 | tests/regression/test_systemic_fixes.py (7 failures) | _authoring.py → package split (A4) not reflected in tests | Pre-existing since A4; tests hardcode the old flat path |
| PRE-002 | P1 | scripts/podcast/tests/test_cost_ledger.py (2 failures) | parse_usage_from_stdout now returns cost_usd field; tests assert old schema | Pre-existing — introduced by `ba5f6c8` cost-capture wave, tests not updated |
| PRE-003 | P1 | scripts/podcast/tests/test_orchestrate_paths.py:26 (1 failure) | test_books_resolves_flat asserts `p.parent.name == "drafts"` but books now live at `content/drafts/books/<slug>` | Pre-existing since 2026-05-23 content restructure |
| PRE-004 | P1 | scripts/podcast/tests/test_run_wave.py:85 (1 failure) | SAMPLE_ACC fixture Wave 4 has no items but test asserts `len(rows[4]) == 1` | Pre-existing fixture/assertion mismatch |

---

## Detail

### AU-A1-001 — Stale plan-dashboard snapshots (P0) — VERIFIED

**Citation**: `plan-dashboard/src/data/dashboard-snapshot.json` L2–3; `architecture-snapshot.json`; `infrastructure-snapshot.json`

The three JSON snapshot files that the plan-dashboard SPA reads are committed at `source_commit: "472de6f"`. HEAD is `522794c` (feat(wave-k)). Running `npm run snapshot` immediately updates them. The contract defined in `copilot-instructions.md` and `CLAUDE.md` states that any commit touching the four canonical plan files MUST be followed in the same response by snapshot regen + `git add`. The Wave K commit (`522794c`) added plan.yaml entries for Wave K steps K0–K5 but the snapshots were not regenerated and committed.

**Why it matters**: The dashboard SPA reads stale data — Wave K steps do not appear in the roadmap view. Anyone consulting the plan-dashboard is reading a state 1 commit behind.

**Proposed fix**: `cd plan-dashboard && npm run snapshot && git add src/data/*.json && git commit -m "chore(dashboard): regen snapshots for 522794c Wave K"`

**safe_to_auto_fix**: true (pure regen, no logic change)

---

### AU-A1-002 — PEQ gate described in plan.yaml (K2) but not enforced in convergence loop (P1) — VERIFIED

**Citation**: `_workspace/plan/refactor/plan.yaml:2357–2363` (K2 deliverables); `scripts/podcast/_convergence.py:246–256`

Plan.yaml K2 acceptance criteria state:
- `"scripts/podcast/orchestrate_book.py: convergence advancement gated on peq_total >= 70"`
- `"orchestrate_book.py convergence loop reads peq_total from report, not verdict string"`

The Wave K commit message itself says: `_convergence.py records peq_total per iteration` — noting "records," not "gates."

Looking at `_convergence.py` lines 246–256, `peq_total` is extracted from the report and stored in `outcome.peq_total`, but there is no conditional that blocks convergence advancement when `peq_total < 70`. The loop continues to the next outer iteration or returns SHIP-READY solely based on the `verdict` string (from `parse_challenger_report`), not from PEQ. The wisdom seal gate IS enforced in `tools/content_translator/stages/seal.py:107` (`if peq_total < 70 and not force`), but this only applies to the wisdom pipeline's seal stage — it does NOT apply to the podcast convergence loop.

**Why it matters**: The podcast pipeline can advance a chapter to SHIP-READY with a PEQ score of 40 if the challenger verdict happens to say SHIP-READY. The PEQ gate is the contract, not the challenger verdict string. K2 is marked `execution_status: completed` in plan.yaml but the gate is missing from the podcast pipeline.

**Proposed fix**: In `_convergence.py`, after line 252 (where `outcome.peq_total` is set), add:
```python
if outcome.peq_total is not None and outcome.peq_total < 70.0:
    outcome.notes.append(
        f"iter {outer}: PEQ gate FAIL ({outcome.peq_total:.1f} < 70) — forcing retry"
    )
    continue   # Do not return — force another iteration or let the cap fire.
```
Then add to plan.yaml K2's acceptance: mark this specific deliverable as still open (execution_status → in-progress).

**safe_to_auto_fix**: false (requires Asif's architectural sign-off)

---

### AU-A1-003 — Wave K unit tests stated as plan deliverables but files don't exist (P1) — VERIFIED

**Citation**: `_workspace/plan/refactor/plan.yaml:2308, 2365, 2454`; `find . -name "test_quality*" -o -name "test_challenger_scoring*" -o -name "test_wisdom_quality*"` (returns nothing)

Three test files are listed as acceptance criteria for Wave K steps and K1/K2/K5 are all `execution_status: completed`:
- K1 criteria: `"test_quality.py: >= 10 unit tests covering edge cases (empty text, all-zero axes, etc.)"`
- K2 criteria: `"test_challenger_scoring.py: >= 8 tests green"`
- K5 criteria: `"test_wisdom_quality_gate.py: >= 6 tests green"`

None of these files exist anywhere in the repo. The `test_peq_regression.py` (21 tests, all green) does exist and covers regression baselines — but that is not a substitute for unit tests of `_quality.py`'s edge-case behavior, the `challenger_scoring.score_report()` function, or the wisdom seal gate.

**Why it matters**: The `_quality.py` `score()` function has branches for None inputs (voice exemplar, arc rules, etc.) that are untested. `challenger_scoring.py` uses regex parsing of the report file and its error paths are untested. A silent regression in either could produce wrong PEQ scores without any test catching it.

**Proposed fix**: Create the three test files:
- `scripts/podcast/tests/test_quality.py` — min 10 tests: zero inputs, all-PASS axes, FAIL threshold boundary, WARN threshold boundary, None voice_exemplar skips Voice axis, arc_labels_found == required all, arc_labels_found empty, etc.
- `scripts/podcast/tests/test_challenger_scoring.py` — min 8 tests: `score_report()` on a fixture report, idempotent re-score (existing PEQ section replaced not doubled), missing contract path, no chapter text, etc.
- `tests/test_wisdom_quality_gate.py` — min 6 tests: peq_total below threshold blocks, `--force` bypasses, gate passes above threshold, etc.

**safe_to_auto_fix**: false (test content must be reviewed)

---

### AU-X3-001 — Class names not renamed (P2) — VERIFIED

**Citation**: `tools/source_extractor/adapters/wisdom.py:45,126`; `tools/content_reviewer/README.md:66`

The module was renamed `wisdom.py` and `DB = "KASHKOLE"` is correct (the SQL Server database literally has that name). However, the public class names `KashkoleQuranCorpus` and `KashkoleAdapter` inside `wisdom.py` carry the old branding. External callers using `from tools.source_extractor.adapters.wisdom import KashkoleAdapter` still work today, but any caller expecting `WisdomAdapter` would fail. The README cross-reference `tools.source_extractor.adapters.wisdom.KashkoleQuranCorpus` is confusing after the rename.

**Why it matters**: Medium-term confusion; any new code following the naming convention would expect `WisdomAdapter` and get an import error. The class names are the public API of this module.

**Proposed fix**: Rename `KashkoleQuranCorpus → WisdomQuranCorpus`, `KashkoleAdapter → WisdomAdapter` in `wisdom.py`; add backward-compat aliases with deprecation comments; update `README.md:66` and the `__init__.py` alias that imports from `wisdom`.

**safe_to_auto_fix**: false (public class rename; callers need checking)

---

### AU-X3-002 — KASHKOLE in LLM prompt and CLI print (P2) — VERIFIED

**Citation**: `tools/content_translator/stages/adapt_auto.py:46`; `tools/content_translator/cli.py:113`

`adapt_auto.py` line 46 sends: `"You are adapting a chapter from KASHKOLE, an Ismaili scholarly compendium"` to the LLM as the system prompt. After the rename, this should say "Wisdom" (the corpus's new public name). Similarly, `cli.py:113` prints `"\nKASHKOLE Translation Cost Ledger — ..."` to the user console.

**Why it matters**: Low runtime impact (the LLM still adapts correctly), but misleading branding in both machine-readable LLM context and human-readable CLI output. If the LLM uses the compendium name in its output (attributions etc.), it will produce "KASHKOLE" instead of "Wisdom."

**Proposed fix**: Change both strings to "Wisdom" / "Wisdom Translation Cost Ledger".

**safe_to_auto_fix**: true (string replacement, no logic change)

---

### PRE-002 — parse_usage_from_stdout schema drift vs tests (P1) — VERIFIED

**Citation**: `scripts/podcast/tests/test_cost_ledger.py:81,84`; `scripts/podcast/_cost_ledger.py:313`

`parse_usage_from_stdout` returns `{"input": 0, "output": 0, "cache_read": 0, "cache_create": 0, "cost_usd": 0.0}` (5 keys) but two tests assert the old 4-key dict (no `cost_usd`). Introduced in commit `ba5f6c8` (wire real token-count + cost capture) but tests were not updated. **Not introduced by recent commits.**

**Proposed fix**: Update both test assertions to include `"cost_usd": 0.0` in the expected dict. One-line fix each.

**safe_to_auto_fix**: true

---

### PRE-003 — test_books_resolves_flat assertion stale after content restructure (P1) — VERIFIED

**Citation**: `scripts/podcast/tests/test_orchestrate_paths.py:26`

Test asserts `p.parent.name == "drafts"` but `_resolve_book_path("books", slug)` now returns `content/drafts/books/<slug>`, so `p.parent.name == "books"`. The 2026-05-23 content restructure moved books to `content/drafts/books/<slug>` but this test's assertion was not updated. The test was written to pin the infinite-recursion bug fix — the bug fix itself still works, only the path-parent assertion is stale. **Not introduced by recent commits.**

**Proposed fix**: Change assertion to `self.assertEqual(p.parent.name, "books")` and add `self.assertEqual(p.parent.parent.name, "drafts")` for belt-and-suspenders.

**safe_to_auto_fix**: true

---

### PRE-004 — SAMPLE_ACC Wave 4 empty but test asserts 1 item (P1) — VERIFIED

**Citation**: `scripts/podcast/tests/test_run_wave.py:85`

The `SAMPLE_ACC` fixture has `## Wave 4 — Control Plane` followed by a blank line and then `## Wave 5`. Wave 4 has no items. The test `test_parse_wave_rows_counts_match_sample` asserts `self.assertEqual(len(rows[4]), 1)`. Since the implementation correctly returns an empty list (or no key) for Wave 4, the test has a wrong expectation. The related `test_parse_wave_rows_splits_by_wave_heading` asserts `{1, 2, 3, 4, 5}` are all keys — this also appears to fail silently or is checked separately. **Not introduced by recent commits.**

**Proposed fix**: Either add an item to Wave 4 of SAMPLE_ACC, or change the assertion to `self.assertEqual(len(rows.get(4, [])), 0)`.

**safe_to_auto_fix**: true (trivial fixture/assertion fix)

---

## Cross-cohort patterns

**Pattern 1: Test assertions not updated when implementations change.**
Three of the four pre-existing pipeline test failures share the same root: a function's return value or path computation changed (cost_usd added; books subdir added; Wave 4 fixture emptied) but the test assertions were not updated atomically. The pattern suggests test updates are being separated from implementation changes. Recommendation: run `scripts/podcast/tests/` as part of every PR gate.

**Pattern 2: Wave K marked completed before test deliverables exist.**
K1, K2, K5 are `execution_status: completed` in plan.yaml, but the stated test-file deliverables (test_quality.py, test_challenger_scoring.py, test_wisdom_quality_gate.py) don't exist. The regression guard (`test_peq_regression.py`) was created — suggesting the baseline work was done — but the unit-test layer beneath it is missing. This creates a gap: if `_quality.py`'s `score()` function changes, `test_peq_regression.py` would still pass (it uses real chapter text and doesn't test edge cases), while silent behavioral regressions would slip through.

**Pattern 3: Kashkole→wisdom rename is 95% complete, not 100%.**
The SQL database name (KASHKOLE) and SQL query files must stay — these reference the live SQL Server database name. But user-facing UX strings and LLM prompt strings should have been updated and weren't. The class names in `wisdom.py` carry old branding. These are three distinct surfaces that were missed.

---

## What's next

Ranked by impact × effort:

1. **(P0 — 2 min)** Regen and commit plan-dashboard snapshots: `cd plan-dashboard && npm run snapshot && git add src/data/*.json && git commit`. Zero risk, fixes contract violation immediately.

2. **(P1 — 1 hr)** Fix the 4 pre-existing pipeline test failures in `scripts/podcast/tests/` — `test_cost_ledger.py` ×2 (add `cost_usd` to assertions), `test_orchestrate_paths.py` ×1 (fix parent.name assertion), `test_run_wave.py` ×1 (fix Wave 4 assertion). Unblocks `scripts/podcast/tests/` from showing spurious failures and restores meaningful test signal.

3. **(P1 — 2–3 hrs)** Create the three missing Wave K unit test files (`test_quality.py`, `test_challenger_scoring.py`, `test_wisdom_quality_gate.py`). These are acceptance criteria for steps already marked complete — completing them closes the gap.

4. **(P1 — 30 min)** Add the PEQ gate enforcement to `_convergence.py` (add `if peq_total < 70: continue` after extraction). Without this, K2's convergence-advancement gate is a no-op in the podcast pipeline, despite existing correctly in the wisdom seal.

5. **(P2 — 30 min)** Fix KASHKOLE→Wisdom in `adapt_auto.py` system prompt and `cli.py` print string. Low risk, restores naming consistency in LLM context and user console.
