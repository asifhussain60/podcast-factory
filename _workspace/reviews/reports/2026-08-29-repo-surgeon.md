# repo-surgeon — 2026-08-29, `develop`

> **Resolution update (same day, same session).** P0 AU-A3, P1 AU-S3, and P1 AU-S1
> (the one verbatim duplicate) fixed and backfilled — see commits `5c36edb`, `75dea90`,
> `047c8e7`, `63586ee`. Also fixed since this report: the deterministic probe's P1
> CT-VERIFY, P2 SD-ORPHAN, and P3 L2-DUP (commits `e03a2f4`, `dcf7609`, `7c07813`).
> Left open, pending Asif: AU-E1 (dead-vs-document call on `articulation_metrics.py`)
> and AU-H1 (delegate to vacuum, per this report's own scope boundary). The three
> "Not reported" axes and the RCA-gap line are unchanged.

Scope: Pass 2b pipeline probes (`--scope podcast`), the judgment half the deterministic
probe cannot run. Phase 3 (findings) only — no fixes applied, no approval gate crossed,
working tree untouched.

Deterministic probe (`python3 scripts/repo_surgeon_probe.py`, run earlier this session):
P1 `CT-VERIFY` (numpy pin in `requirements.txt`), P2 `SD-ORPHAN`
(`docs/standards/chapter-density-eval-prompt.md`), P3 `L2-DUP` (waves G/H/I/J/K reused
harmlessly). `make lint`, `pytest` (4,598 passed), `_boundary_check.py`, doc-links all
green. L6 clear — no book in flight.

This pass adds 6 judgment findings: 1 P0, 4 P1, 1 P1 (standing obligation).

---

## P0

### AU-A3 — Registry/disk drift, root-caused to a dead legacy path

`_system/registry.md` exists to satisfy framework.md INVARIANT 6 ("each chapter... title
mirrored in the book's `_system/registry.md`"). Sampling eleven books across three buckets
found it silently unpopulated on every book scaffolded after the 2026-06-04 type-first
content restructure:

| Book | Chapters on disk | Registry rows | Pipeline state |
|---|---|---|---|
| `content/Islamic/degrees-of-excellence` | 6 | 0 (header only) | `reader-narration` completed |
| `content/Islamic/spiritual-ethos` | 13 | 0 (header only) | `publish` pending |
| `content/Islamic/sharh-al-masail-ghulam-hussain` | 5 | 0 (header only) | `audio-ingest` halted |
| `content/Islamic/kunooz-al-hikmah` | 13 | no `registry.md` at all | `0book-render` failed |
| `content/Islamic/the-master-and-the-disciple` | 20 | no `registry.md` at all | **published** |

(`content/Islamic/kitab-al-riyad`, authored 2026-05-20 before the restructure, is fully
populated — 15/15 rows match `chapters/ch##-<slug>.txt`, which is the control case that
shows this is a regression, not a format nobody ever filled in.)

**Root cause:** [scripts/podcast/phases/series_plan.py:427](../../../scripts/podcast/phases/series_plan.py) —
`phase_0g_register()` writes to `REPO_ROOT / "content" / "podcast" / ".skill" / "registry.md"`,
a pre-restructure cross-book path. `content/podcast/` does not exist under the current
`content/<Bucket>/<slug>/` layout. Line 428's guard, `if not registry.exists(): return`,
makes this a **silent no-op** — no error, no log line, nothing in the orchestrator state.
The function is not dead code: `scripts/podcast/phases/post_chapter_driver.py:63` calls it
on every completed chapter. `scripts/podcast/scaffold_book.py:228` writes the header-only
stub at book creation, and nothing downstream has appended to it since. `validate_registry.py`
and `new_episode.py` both still read the per-book path and would catch this if run against
one of the affected books — nothing runs them automatically.

**Why P0:** the framework invariant is presented as enforced ("mirrored... per INVARIANT 6"),
and one of the five affected books is already `status=published`. Silent-degrade-on-missing-
path is exactly the failure class CLAUDE.md's `repo-surgeon` history warns about elsewhere in
this repo.

---

## P1

### AU-E1 — Dead script

[scripts/podcast/sessions/articulation_metrics.py](../../../scripts/podcast/sessions/articulation_metrics.py) —
a standalone CLI (`summarize()` + `argparse` `main()`) with zero references anywhere in the
tracked tree: no `import`, no `python3 .../articulation_metrics.py` invocation in any `.md`,
no test. Confirmed by both a repo-wide stem grep (429 podcast modules checked; this is the
only one with zero hits outside itself) and a direct `articulation_metrics` grep. Its sibling
diagnostics (`chapter_density_audit.py`, `cost_ledger_summary.py`, `cross_book_dashboard.py`)
are all named in `CLAUDE.md` or `framework.md`; this one is named nowhere.

### AU-S3 — Cost-cap leakage on two live Gemini call sites

Every other direct Gemini caller in the repo routes its cost through
`_cost_ledger.append_gemini_cost()` — confirmed present in `_review_ai.py`,
`narrator_additions.py`, `transcribe_audio_book.py`, `build_fiction_book_pdf.py`,
`vowel_book.py`, `gemini_refine.py`, `_gemini_text.py`, `align_arabic_paragraphs.py`, and
`generate_video_layer.py`. Two do not:

- [scripts/podcast/composer_visual.py](../../../scripts/podcast/composer_visual.py) — live
  production path: the Astro Book Composer's `/api/studio/visual-op` route calls this on
  every human-triggered `generate`/edit, hitting `gemini-3.1-flash-image` (line 30) directly
  via `genai.Client()`. No `cost`, `usage_metadata`, or ledger reference anywhere in the file.
- [scripts/podcast/audit_bundle_gemini.py](../../../scripts/podcast/audit_bundle_gemini.py) —
  the documented "two-model audit gate" run per chapter (`_run_gemini()`, line ~84). Calls
  `engine_guard(TASK_AUDIT, ENGINE_GEMINI)` (a policy-mismatch diagnostic only — confirmed by
  reading `_engine.py:196`, it never touches cost) then `client.models.generate_content()`
  directly. No cost-ledger reference in the file.

Neither writes to the orchestrator state's cost dict, so per-chapter and per-image-edit
Gemini spend on these two paths is invisible to `cost_ledger_summary.py` / the cost caps.

### AU-S1 — Uncentralized timeout/budget constants

`_rules.py` is the documented home for cross-cutting pipeline config, but ~35 modules each
define a private `_CLAUDE_TIMEOUT` / `_COMPOSE_TIMEOUT` / `*_TIMEOUT` constant instead,
clustering on a handful of values (900/600/1800/1200/1350/3600) that look like they should be
one shared set. Two concrete duplicates:

- `_COMPOSE_TIMEOUT = 900` and `_RETRY_TIMEOUT = 1350` are defined **verbatim, same names,
  same values**, in both [scripts/podcast/_translation_chunk.py:41-42](../../../scripts/podcast/_translation_chunk.py)
  and [scripts/podcast/_book_compose.py:29-30](../../../scripts/podcast/_book_compose.py) —
  two different lanes independently arrived at (or copy-pasted) the same pair.
- Three different, uncoordinated per-book AI cost caps: `BOOK_AI_BUDGET_USD = 2.00`
  ([_review_ai.py:86](../../../scripts/podcast/_review_ai.py)), `DEFAULT_BUDGET_USD = 3.00`
  ([_tighten_helpers.py:44](../../../scripts/podcast/_tighten_helpers.py)),
  `DEFAULT_COST_CAP_USD = 5.0`
  ([intelligence/tag_doctrine_concepts.py:40](../../../scripts/podcast/intelligence/tag_doctrine_concepts.py)).

None of these six are re-exports of a `_rules.py` constant; each is a fresh module-level
literal. Not reported as AU-E3 (validation duplication) because these are config values, not
duplicated *check logic*.

### AU-H1 — `_workspace/plan/` root sprawl (delegate_to: vacuum)

`infra/claude-agents/vacuum.md`'s own "Canonical shape of `_workspace/plan/`" section states
there is exactly **one** documented exception file allowed to sit at the plan root
(`numeric-symbolic-disambiguation-plan.md`, pending refactor step A4) — everything else is
supposed to live in `conventions/`, `debt/`, `operations/`, `postprod-vacuum/`, `reader/`,
`refactor/`, `research/`, `view/`, `_drivers/`, or `_archive/`. `ls _workspace/plan/` today
shows 38 files at root beyond `README.md` (root-legit) and the one documented exception —
prompt/continuation/handoff/status/spike docs that match the vacuum-owned bucket categories
verbatim (e.g. `copilot-handoff.md`, `session-handoff-2026-07-21.md`,
`continuation-2026-07-20.md`, `book-pipeline-continue-prompt.md`,
`audio-engine-execution-prompt.md`, `site-work-status.md`, `wave8-section0-review.md`,
`capabilities-manifest.yml`, `pending-work.yaml`, plus ~29 more). This is either drift since
the 2026-05-26 lock or a bucket list vacuum.md never updated to match — either way it's
vacuum's call, not this probe's, to sort which.

---

## P1 — Standing obligation (Tier 0 snapshot regen)

Commit `0e25e3c` (2026-08-28, `fix(gates): widen the Python size gate...`) edited
`_workspace/plan/debt/pipeline-debt.md`, closing an open debt entry (`~~scripts/ has no size
ceiling...~~ — RESOLVED 2026-08-28`). Per CLAUDE.md's Tier 0 rule and SKILL.md's standing-
obligations table, an edit to `debt/pipeline-debt.md` must regenerate the three snapshot
JSONs in the same response. `git show --stat 0e25e3c` touches only
`.repo-audit/profile.yaml`, `_workspace/plan/debt/pipeline-debt.md`,
`infra/git-hooks/check-dr005.py`, and `infra/git-hooks/dr005-grandfather.txt` — none of
`plan-dashboard/src/data/{dashboard,infrastructure,architecture}-snapshot.json`.
`dashboard-snapshot.json`'s last regen (`git log`, 2026-08-25) predates the debt edit by
three days.
`plan-dashboard/scripts/regenerate-snapshots.mjs` documents itself as reading
`pipeline-debt.md` "for the open debt list," so this is the exact obligation the rule names,
not an edit outside its trigger. (No visible content drift resulted — the snapshot's `debt`
array is currently `[]` regardless — but the rule is about the process running, not about
whether this particular edit happened to move a rendered number.)

---

## Not reported

- **AU-E2 / AU-E3** — no duplicate-script or duplicated-check-logic finding met the bar for
  concrete evidence. The one candidate investigated (`detect_em_dash` in
  `test_challenger.py` vs `check_em_dashes` in `build_slide_deck.py`) checks different
  artifact classes (a test-harness mirror of the chapter-prose auto-fix regex vs. a
  production gate on NotebookLM slide-deck text) and each is a single-line regex — too thin
  to call a defect.
- **AU-X1 / AU-X2** — the one enum checked closely (the six content buckets) is already
  single-sourced in `_content_types.py` and re-exported by `_rules.py`; `_paths.py`'s
  `_CATEGORY_TO_BUCKET` is a deliberately different (legacy-category-to-bucket) mapping per
  CLAUDE.md, not a second copy of the same enum. No other enum candidate was verified
  duplicated within the time available for this pass.
- **AU-X3** — the `git log --since` "recently added" heuristic returned nearly the entire
  `scripts/podcast/` tree (a bulk history event, not real churn), so it produced no usable
  signal; not pursued further rather than reported on noise.
- **RCA gap** — no specific undocumented incident since the 2026-08-15 RCA was confirmed;
  not flagged, per instruction to require concrete evidence rather than speculate.

---

0 finding(s) suppressed by waiver.
1 stale contract entry/entry (the numpy version pin in `requirements.txt`, `CT-VERIFY` —
already surfaced by the deterministic probe run this session, not re-litigated here).
