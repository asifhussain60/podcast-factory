# Folder consolidation proposal — podcast-factory

**Date:** 2026-05-28
**Status:** Proposal only — no changes made.
**Constraint:** Zero functional regression. Orchestrator, podcast-reader, plan-dashboard, and all `scripts/podcast/*` invocations must continue to work.

---

## At a glance

The repo has **21 visible top-level entries** (10 dirs + 11 files/dotfiles), plus 9 auto-managed dotfile dirs. Of the 10 visible top-level dirs, **7 carry real load-bearing path bindings** (locked by `scripts/podcast/_paths.py`, the plan-dashboard snapshot regenerator, the Makefile, or hardcoded Python imports). The other **3** (`prompts/`, `docs/`, parts of `_workspace/`) are nearly free to consolidate.

Realistic net reduction without code edits: **21 → 18 top-level entries**.
With ≤10 line edits across 4 files: **21 → 15**.
With a documentation reorg (touches CLAUDE.md and ~6 script docstrings): **21 → 13** and a much cleaner mental model.

---

## Current top-level surface (the truth)

| Entry | Type | What's in it | Code refs? |
|---|---|---|---|
| `content/` (`CONTENT/`) | Dir | drafts, published, _shared, knowledge-base, podcast | **LOCKED** — `scripts/podcast/_paths.py` is the canonical resolver; plan-dashboard reads from it. Case-only difference between `CONTENT` and `content` is the macOS case-insensitive filesystem — same inode. |
| `_workspace/` | Dir | plan, audit, runbooks, setup, prompts, chats, proposals, logs, source-library | **PARTIALLY LOCKED** — `_workspace/plan/refactor/{plan.md,plan.yaml}`, `_workspace/plan/debt/pipeline-debt.md`, `_workspace/plan/operations/wave-acceptance-checklist.md`, `_workspace/source-library/extracted` all hardcoded in plan-dashboard. Other subdirs are loose. |
| `scripts/` | Dir | podcast/ (pipeline), git-hooks/ (only README), 4 .sh files | **LOCKED** — Makefile references; many self-references; hundreds of internal imports. |
| `tools/` | Dir | 5 generic Python packages (content_*, source_extractor) | Imported as Python packages; `tools/content_classifier/data/*.yaml` hardcoded in plan-dashboard. |
| `infra/` | Dir | azure, claude-agents, git-hooks, launchd, llm-apis | **LOCKED** — Makefile + `scripts/install-claude-skills.sh` + multiple Python phases reference `infra/claude-agents/*.md` and `infra/azure/*`. |
| `plan-dashboard/` | Dir | Astro SPA over plan.yaml/architecture.md | Self-contained app. |
| `skills-staging/` | Dir | 8 skills (podcast/, podcast-blueprint/, publish-podcast/, clean-commit/, cowork-brief/, tell-me/, usage-auditor/, repo-surgeon/) | `skills-staging/podcast/SKILL.md` + `skills-staging/podcast/references/*` referenced by ~10 `scripts/podcast/_*.py` files. `install-claude-skills.sh` mirrors `skills-staging/podcast/SKILL.md` into the Claude runtime. |
| `docs/` | Dir | azure/ (5 md), podcast/multi-mac-decision.md (1 file — stale) | 1 ref: `scripts/podcast/phases/p11_1.py` references the stale multi-mac-decision file. |
| `reference/` | Dir | 5 md files + skill-overlays/ (4 md) — cortex challenger framework, operating contract, skill bootstrap/registry, steward source corpus | **NO code refs.** Mentioned in CLAUDE.md and in agent .md files (text only). |
| `prompts/` | Dir | gemini-bundle-auditor.md (1 file) | 1 ref: `scripts/podcast/pack_bundle_for_gemini.py` references it by relative path in a hint message. |
| `tests/` | Dir | regression/ (1 .py file + 1 .sh) | Self-contained. Note: `scripts/podcast/tests/` has 24 .py — the bulk of tests live next to the pipeline, not here. |

Top-level files: `CLAUDE.md`, `CHANGELOG.md`, `framework.md`, `Makefile`, `package.json`, `release-please-config.json` (+ dotfile configs).

Auto-managed dirs (out of scope): `.git/`, `.venv/`, `.astro/`, `.pytest_cache/`, `node_modules/`, `.vscode/`, `.claude/`, `.github/`.

---

## Sprawl findings — concrete

### 1. Duplicate `git-hooks` homes (zero-risk to fix)

- `infra/git-hooks/` — real (`install.sh` + `pre-commit`).
- `scripts/git-hooks/` — stub (only `README.md` pointing at `infra/git-hooks/`).
- Plus `scripts/install-git-hooks.sh` — installer alias.

**Fix:** Delete `scripts/git-hooks/`. Single canonical home: `infra/git-hooks/`. No code path edits needed.

### 2. Three `prompts/` locations (one is free to merge)

- `prompts/gemini-bundle-auditor.md` — 1 file, 1 hardcoded ref.
- `_workspace/prompts/` — 2 files, no hardcoded refs.
- `.github/prompts/` — GitHub Copilot convention, must stay.

**Fix:** Move `prompts/gemini-bundle-auditor.md` → `_workspace/prompts/`. Update the one string in `scripts/podcast/pack_bundle_for_gemini.py:174`. Eliminates the top-level `prompts/` dir.

### 3. Stale single-file `docs/podcast/` (zero-risk to remove)

- `docs/podcast/multi-mac-decision.md` — 1 file, references the now-retired multi-mac coordination model. CLAUDE.md explicitly says: *"Post-2026-05-23: this app is machine-agnostic. … The earlier cross-machine coordination model … was retired 2026-05-23."*
- 1 hardcoded ref: `scripts/podcast/phases/p11_1.py:9` (DESCRIPTION string, not a path read).

**Fix:** Archive the .md (move to `_workspace/audit/_archive/`), remove the `docs/podcast/` dir, and either delete the orphaned `p11_1.py` reference or update its DESCRIPTION to a non-stale source.

### 4. `_workspace/chats/` and `_workspace/proposals/` — 1-file each (zero-risk)

- `_workspace/chats/chat01.md` — orphan chat log.
- `_workspace/proposals/planner-sidenav-plan.md` — one-off plan note.

**Fix:** Collapse both into `_workspace/plan/proposals/` (which doesn't exist yet but logically belongs to plan). Eliminates two single-file dirs.

### 5. Documentation scattered across 4 homes (medium-risk, big payoff)

Today's documentation lives across:
- `docs/` (azure only — 5 files)
- `_workspace/runbooks/` (5 operational md)
- `_workspace/setup/` (2 setup md)
- `reference/` (9 md including skill-overlays)

The `docs/` dir is almost empty while `_workspace/` is overloaded. Inverting this is cleaner mental model: everything documentation-related under `docs/`, everything work-in-progress / planning under `_workspace/`.

**Fix:** Migrate to a single `docs/` tree:
```
docs/
├── azure/          # already there
├── runbooks/       # ← _workspace/runbooks/
├── setup/          # ← _workspace/setup/
└── reference/      # ← reference/ (cortex, operating contract, skill registry, overlays)
```
- Edits needed: CLAUDE.md (~10 link rewrites — the runbook + setup paths it cites in the §"Read these once" section), plus ~6 docstrings in `scripts/podcast/knowledge/*.py` that mention `_workspace/plan/architecture.md` (those are soft references, won't break anything if left).
- `reference/` has zero hardcoded code refs — pure docs. Cleanest of the three to migrate.

### 6. `_workspace/plan/_drivers/` — Python scripts in a plan dir (low-risk)

`_workspace/plan/_drivers/` contains 7 .py files that drive kashkole adaptation, challenger, gate reporting, image dedup, etc. These are operational scripts, not plan documents.

**Fix:** Move `_workspace/plan/_drivers/` → `scripts/kashkole/` (or `tools/kashkole/` if we want it package-style). Update `tools/content_classifier/data/kashkole-r1-decisions.yaml:20` which references `_workspace/plan/_drivers/image_dedupe.py` as a handler.

### 7. `_workspace/audit/` — historical log dumps with zero code refs (low-risk)

`_workspace/audit/kitab-al-riyad/` is ~30 orchestrator log files from a past book run. `_workspace/audit/kashkole/` similarly. No hardcoded references anywhere.

**Fix:** Either:
- (a) Archive to `_workspace/audit/_archive/` per-book and gitignore future logs, or
- (b) Move to `content/drafts/<slug>/_system/audit-logs/` per book (cleaner, lives with the book).

Recommendation: (a) for these historical ones (the books are done); (b) as a forward-going convention.

### 8. `_workspace/source-library/` (23 MB) — book-specific data in the workspace (medium-risk)

Kashkole-specific corpus data lives at `_workspace/source-library/extracted/` and is hardcoded in `plan-dashboard/src/lib/reader/source-extractor.ts:21`. This is book-specific content; structurally it belongs under `content/_shared/kashkole/` or `content/drafts/books/kashkole/_system/source/`.

**Fix:** Move to `content/_shared/source-library/` and update the one TS reference. **Note:** kashkole is itself a multi-book series (per `content/drafts/asbaaq/` which contains `kashkole-asbaaq-r1/`, etc.), so the corpus might genuinely be shared — `content/_shared/` is the right home.

### 9. Test sprawl: 24 tests in pipeline + 1 in top-level `tests/` (out of scope here)

`scripts/podcast/tests/` (24 .py) vs `tests/regression/` (1 .py). The two test homes have different purposes (unit-near-source vs. regression), so collapsing isn't obviously beneficial. **Flag, don't act.**

### 10. `framework.md` at repo root — sole top-level documentation file (cosmetic)

`framework.md` (15 KB pipeline spec) is the only documentation file at repo root alongside CLAUDE.md/CHANGELOG.md. It conceptually belongs under `docs/`, but CLAUDE.md's §"Read these once" section explicitly links to `framework.md` at repo root, and so do ~5 agent .md files. **Move only if doing the broader docs reorg.**

---

## Proposed target structure

```
podcast-factory/
├── CLAUDE.md
├── CHANGELOG.md
├── Makefile
├── package.json
├── framework.md                # stays at root (heavily linked)
│
├── content/                    # locked — _paths.py canonical
├── infra/                      # locked — azure, claude-agents, git-hooks, launchd, llm-apis
├── scripts/
│   ├── podcast/                # locked
│   ├── kashkole/               # ← _workspace/plan/_drivers/
│   └── *.sh                    # start-session, install-*, plan-dashboard-launchd
├── tools/                      # locked — content_*, source_extractor
├── plan-dashboard/             # locked — Astro SPA
├── skills-staging/             # locked — heavily referenced
├── tests/                      # stays
│
├── docs/                       # consolidated documentation home
│   ├── azure/                  # stays
│   ├── runbooks/               # ← _workspace/runbooks/
│   ├── setup/                  # ← _workspace/setup/
│   └── reference/              # ← reference/
│
└── _workspace/                 # working scratch / planning
    ├── plan/                   # locked (architecture, refactor, debt, operations, conventions...)
    │   └── proposals/          # ← _workspace/proposals/ + _workspace/chats/
    ├── audit/
    │   └── _archive/           # ← historical kitab-al-riyad + kashkole logs
    ├── source-library/        # OR move to content/_shared/ (see #8)
    ├── prompts/                # ← absorbs prompts/gemini-bundle-auditor.md
    └── logs/                   # stays
```

**Removed top-level entries:** `prompts/`, `reference/`.
**Net visible top-level count:** 21 → 17 (or 16 with the source-library move).

---

## Phased rollout

### Phase 1 — zero-risk (no code edits, no CLAUDE.md edits)
Estimated time: 15 minutes. Pure file moves.

1. Delete `scripts/git-hooks/` (only contains a README pointing at `infra/git-hooks/`).
2. Move `_workspace/chats/chat01.md` → `_workspace/plan/proposals/chat01-archive.md`.
3. Move `_workspace/proposals/planner-sidenav-plan.md` → `_workspace/plan/proposals/planner-sidenav-plan.md`.
4. Delete now-empty `_workspace/chats/` and `_workspace/proposals/`.
5. Archive `_workspace/audit/kitab-al-riyad/` → `_workspace/audit/_archive/kitab-al-riyad/` (the book is shipped).

**Result:** −2 top-level subdir noise, −1 visible top-level dir.

### Phase 2 — light edits (≤10 line changes, 4 files)
Estimated time: 30 minutes including verification.

1. Move `prompts/gemini-bundle-auditor.md` → `_workspace/prompts/gemini-bundle-auditor.md`.
   - Edit: `scripts/podcast/pack_bundle_for_gemini.py:174` — update the path string.
   - Delete empty top-level `prompts/`.
2. Move `docs/podcast/multi-mac-decision.md` → `_workspace/audit/_archive/multi-mac-decision-2026-05.md` (stale per CLAUDE.md).
   - Edit: `scripts/podcast/phases/p11_1.py:9` — either remove the DESCRIPTION reference (file is being retired) or point to a non-stale source.
   - Delete empty `docs/podcast/`.
3. Move `_workspace/plan/_drivers/` → `scripts/kashkole/`.
   - Edit: `tools/content_classifier/data/kashkole-r1-decisions.yaml:20` — update `handler:` path.

**Result:** −1 visible top-level dir (`prompts/`), cleaner script vs. plan separation.

### Phase 3 — docs consolidation (CLAUDE.md edits + docstring updates)
Estimated time: 1–2 hours including link verification.

1. Move `_workspace/runbooks/*` → `docs/runbooks/*`.
2. Move `_workspace/setup/*` → `docs/setup/*`.
3. Move `reference/*` → `docs/reference/*`.
4. Edit CLAUDE.md — rewrite the §"Read these once" links and the §"Disconnected from journal" path mentions (~10 link rewrites).
5. Soft-update docstrings in `scripts/podcast/knowledge/*.py` that reference `_workspace/plan/architecture.md` (these are doc-comments, will not break execution if left as-is — they're only consumed by humans).
6. Update `.github/agents/project-steward.agent.md` to point at `docs/reference/steward-source-corpus.md`.

**Result:** −2 visible top-level dirs (`reference/`, eventually `_workspace/runbooks/` + `_workspace/setup/` collapse inside `_workspace`). `docs/` becomes the single documentation home.

### Phase 4 — optional (kashkole corpus relocation)
1. Move `_workspace/source-library/extracted/` → `content/_shared/source-library/extracted/`.
2. Edit `plan-dashboard/src/lib/reader/source-extractor.ts:21` — update the relpath constant.
3. Verify plan-dashboard rebuild reads correctly.

**Result:** Book content lives in content/, working scratch lives in _workspace/. Clean mental model.

---

## What to leave alone (and why)

| Entry | Why it stays as-is |
|---|---|
| `content/` | Canonical via `_paths.py`. Multiple readers depend on the exact path. |
| `_workspace/plan/{refactor,debt,operations,architecture.md}` | Plan-dashboard snapshot regenerator hardcodes these. Locked by Tier-0 hook in `.claude/settings.json`. |
| `_workspace/plan/_drivers/` | Moves in Phase 2, not earlier (one yaml edit required). |
| `scripts/podcast/` | Hundreds of internal references; renaming would mean a major refactor. |
| `infra/azure/`, `infra/claude-agents/` | Referenced from Makefile, install-claude-skills.sh, dor_halts.py, learn_propose.py, transcribe_episode.py. |
| `infra/launchd/`, `infra/git-hooks/`, `infra/llm-apis/` | Standalone, conventional locations. No benefit to moving. |
| `skills-staging/podcast/` and `skills-staging/podcast/references/` | Referenced from `_authoring.py`, `_slide_authoring.py`, `_slide_convergence.py` — ~10 files cite these by path in user-facing error messages. |
| `tools/content_*` | Clean package layout. `data/*.yaml` hardcoded in plan-dashboard. |
| `plan-dashboard/`, `tests/`, `Makefile`, `package.json`, `CLAUDE.md`, `framework.md` | Conventional repo-root placement; expected by tooling. |
| `.claude/`, `.github/`, `.venv/`, `.astro/`, `node_modules/`, `.pytest_cache/`, `.vscode/` | Tool-managed. |
| Two test homes (`tests/` + `scripts/podcast/tests/`) | Different purposes (regression vs. unit-near-source). Merging adds friction without obvious win. |

---

## Per-move risk and code-edit table

| # | Move | Files edited | Risk | Phase |
|---|---|---:|:---:|:---:|
| 1 | Delete `scripts/git-hooks/` | 0 | None | 1 |
| 2 | Collapse `_workspace/chats/` → plan/proposals/ | 0 | None | 1 |
| 3 | Collapse `_workspace/proposals/` → plan/proposals/ | 0 | None | 1 |
| 4 | Archive `_workspace/audit/kitab-al-riyad/` | 0 | None | 1 |
| 5 | Move `prompts/gemini-bundle-auditor.md` | 1 (.py) | Low | 2 |
| 6 | Retire `docs/podcast/multi-mac-decision.md` | 1 (.py) | Low | 2 |
| 7 | Move `_workspace/plan/_drivers/` → `scripts/kashkole/` | 1 (.yaml) | Low | 2 |
| 8 | Move `reference/` → `docs/reference/` | ~4 (CLAUDE.md + agent .md) | Medium | 3 |
| 9 | Move `_workspace/runbooks/` → `docs/runbooks/` | ~3 (CLAUDE.md + runbook self-refs) | Medium | 3 |
| 10 | Move `_workspace/setup/` → `docs/setup/` | ~2 (CLAUDE.md) | Medium | 3 |
| 11 | Move `_workspace/source-library/` → `content/_shared/` | 1 (.ts) | Medium | 4 |

**Total code edits across all phases:** ~13 line changes across 8 files. None require Python refactoring; all are path-string updates.

---

## Verification protocol (run after each phase)

```bash
# 1. Pipeline scripts still import cleanly
python3 -c "import sys; sys.path.insert(0, 'scripts/podcast'); import orchestrate_book, _paths, _rules, _phases"

# 2. Plan-dashboard snapshots still build
cd plan-dashboard && npm run snapshot

# 3. Boundary check passes
python3 scripts/podcast/_boundary_check.py

# 4. Regression tests
bash tests/regression/run_all.sh

# 5. Grep for orphaned references to moved paths
grep -rn "OLD_PATH_HERE" scripts/ tools/ plan-dashboard/src CLAUDE.md
```

If any of the above fail, the move is reverted before continuing.

---

## Open questions for Asif

1. **`framework.md` at repo root** — leave it (heavy cross-linking) or move to `docs/framework.md` as part of Phase 3?
2. **`_workspace/source-library/`** — is the corpus genuinely multi-book-shared, or specific to one book? Answer determines whether Phase 4 belongs in `content/_shared/` or `content/drafts/asbaaq/kashkole-*/_system/source/`.
3. **`tools/content_challenger/kashkole/`** — book-specific code inside a "generic" tool package. Hoist to top-level `tools/kashkole/`, or accept the nesting?
4. **`reference/skill-overlays/` content** — overlays for `cowork-brief`, `tell-me`, `clean-commit`, `journal`. The `journal-cortex-overlay.md` references the sibling journal repo. Keep it here as documentation, or move to the sibling repo (where the journal code lives)?
