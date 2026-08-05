---
mode: agent
description: Full health + integrity check for the podcast-factory pipeline AND the Podcast Factory Astro Site — agents, skills, mirror pairs, tests, views — with repo-surgeon-driven hygiene cleanup, run identify-first behind an approval gate.
---

Run a comprehensive health and integrity check across BOTH surfaces of this repo — the podcast pipeline (`scripts/podcast/`) and the Podcast Factory Astro Site (`plan-dashboard/`) — verify their agents, skills, and cross-cutting contracts, and perform the repo hygiene cleanup through repo-surgeon. Operate **identify-first**: audit and report before mutating anything, and stop at an approval gate before any deletion, move, rename, or fix.

## Operating contract (apply to every non-trivial decision in this run)

- **Ground in real artifacts.** Read the affected files and how components fit before forming any opinion. Never assert a symbol, path, line, or status you have not confirmed by reading it or running a command. If a tool fails, say so — do not infer or invent findings.
- **Test framing, don't default to agreement.** If a stronger, safer, or simpler check exists than what this prompt says, lead with it and say why. Target the root cause, never the symptom. Never manufacture disagreement; if the current approach is sound, say so in one sentence and proceed.
- **Clarify only when it changes the outcome.** Ask at most three blocking questions, one at a time, each with 2–4 options and a recommended default justified in plain language. Otherwise proceed on the best-supported assumption.
- **Generator–discriminator before presenting a fix plan.** Draft the plan, then attack it hostilely (failing input, regressed behavior, contract violation, unjustified complexity, simpler dominating path) for ≤3 rounds; absorb every valid hit; stop at equilibrium. Surface any flaw unresolved after three rounds. Cosmetic/invented attacks are mode collapse — a clean pass is the success signal.
- **Smallest change that fully satisfies the requirement and fits the architecture.** No symptom-patching, no gold-plating, no scope expansion. Ambiguity is never a license to expand scope.
- **Approval before writing.** Present findings + plan and wait for explicit approval before touching a file. Fold in requested changes and reconfirm.

## Guardrails — production state that is OFF-LIMITS to cleanup

Treat these as production, never "scratch" — do NOT delete, move, or rename them:
- `content/**` — per-book `_system/` (incl. `orchestrator-state.json`, `meta.yml`, `series-config.yaml`), `chapters/`, `book/`, `slide-decks/`, `episodes/`.
- `_learning/**` — append-only findings ledgers.
- `_workspace/plan/**` — living plan, capability manifest, standards, prompts.
- Any path computed by `#file:../../scripts/podcast/_paths.py` / `_branching.py` / the `<Bucket>/<slug>` convention — folder layout is contractual.
- Loader/protocol files whose exact names are required: `CLAUDE.md`, `AGENTS.md`, `framework.md`, `README.md`, `CHANGELOG.md`, `.release-please*`.

Authorization tiers (from `#file:../../CLAUDE.md`): reads/dry-runs are Tier 0; commit/push to `develop` is Tier 1 (do, then surface); `rm` of tracked files, moves/renames, force-push, branch deletes are Tier 2 (always ask).

## Steps

### 0. Orient
1. Run `bash scripts/start-session.sh`, then `git log --oneline -20` and `git status`. Note recent programmatic changes and any untracked/modified files.

### 1. Agents integrity (four homes, three generated)
2. Confirm parity with `bash scripts/podcast/sync-agent-wrappers.sh --check` rather than by eye: `infra/claude-agents/` is canonical, and `.github/agents/*.agent.md`, `.claude/agents/*.md` and `.codex/agents/*.toml` are all GENERATED from it. Never hand-edit a generated copy. `.codex/` is a deliberate curated subset, so a missing entry there is not drift (waived in `.repo-audit/waivers.yaml`); a missing `.github/` or `.claude/` entry is.
3. For each agent: valid frontmatter (name/description/tools), and every file path, skill, and script it references actually resolves. Flag `podcast-auditor` as deprecated (superseded by `repo-surgeon --scope podcast`) and confirm nothing still invokes it as canonical.

### 2. Skills integrity
4. Enumerate `skills-staging/*/` rather than hardcoding a count — the set changes (`podcast-blueprint` was retired 2026-07-16; `ui-designer` and `studio-composer` were added since). For each: `SKILL.md` exists and is non-empty, frontmatter is valid, referenced paths / `REQ-NNN` citations (html-view-quality) / probe catalogs resolve, and the skill has a row in `docs/reference/skill-registry.md` whose definition path points at the real file.

### 3. Pipeline health (`scripts/podcast/`)
5. Full suite: `.venv/bin/python -m pytest scripts/podcast/tests tests -q` (fall back to `python3 -m pytest -q` if no venv). Report pass/skip/fail counts; investigate any failure to a root cause (real regression vs environment/test-robustness).
6. Boundary check: `python3 scripts/podcast/_boundary_check.py` (pipeline must not write into the sibling `journal` repo).
7. PHASES spine: confirm the `_progress.py:PHASES` drift-guard test passes (single source of truth for phase order).
8. Mirror-pair sync — confirm each pair is consistent (a change on one side must be reflected on the other): `_paths.py` ↔ `plan-dashboard/src/lib/content-paths.ts`; `_quality.py`/`intelligence/challenger_scoring.py` ↔ `plan-dashboard/src/lib/peq-scores.ts`; the `_system/` JSON schema ↔ `plan-dashboard/src/lib/reader/editorial.ts`/`stage-review.ts`.
9. Ship-gate dry run (read-only): `python3 scripts/podcast/validate_ship_ready.py <slug>` for any book at `phase=finalize`.

### 4. Podcast Factory Astro Site health (`plan-dashboard/`)
10. `cd plan-dashboard && npm run check` (astro/type check) and `npm run lint:views` (Cortex §11 mechanical MUST checks; `lint:views:strict` for warnings-as-errors on a full pass).
11. Snapshot freshness: run `cd plan-dashboard && npm run snapshot` (or `python3 plan-dashboard/scripts/regenerate-snapshots.py`) and `git diff --stat` the three snapshot JSONs; a non-empty diff means a snapshot-trigger file (`architecture.md`, `refactor/plan.{md,yaml}`, `debt/pipeline-debt.md`) changed without regeneration — flag it.
12. Any view/page/component touched must pass the `html-view-quality` standard and the `html-view-challenger` agent. Optionally run `npm run build` (heavier) if build integrity is in scope.

### 5. repo-surgeon holistic audit + hygiene cleanup
13. Run `python3 scripts/repo_surgeon_probe.py` FIRST — it is deterministic, costs nothing, and machine-checks contract integrity, root membership, the retired-surface ban, agent-mirror and skill-registry parity, mirror pins, the pipeline and book-pipeline invariants, and plan conformance. Then invoke repo-surgeon for the judgment half. Note the structure changed on 2026-07-27: the generic passes (root sprawl, dead code, duplicates, debris) are DELEGATED to the `repo-audit` skill, which reads the tracked contract at `.repo-audit/profile.yaml`; repo-surgeon adds only this repo's project-specific probes. Do not ask it for the old Pass 1–4 rules — several audited directories deleted in the May 2026 split, and the plan-view parity rule manufactured 35 false findings per run. Both are gone.
14. **The cleanup is the `repo-audit` skill's Phase 6** — debris deletion (`*.bak/*.tmp/*.orig/*.swp`, loose `*.log`, stray archives, OS/editor artifacts), root-sprawl relocation, casing normalization (kebab-case folders; repo file convention), and empty-dir collapse. For every candidate: verify it is not in the OFF-LIMITS set above, and scan the ENTIRE repo for references (imports, `sys.path`, manifest/config keys, README/doc links, `.github/` + `Makefile` + `pytest.ini` CI paths, and string-literal paths in both Python and the Astro/TS mirror). Harden `.gitignore` where a stray artifact type slipped an existing pattern.
15. **Agent-unavailable fallback:** if the repo-surgeon agent cannot run in this environment, run `python3 scripts/repo_surgeon_probe.py` (which needs no agent) and then work the judgment-half catalog inline from `#file:../../skills-staging/repo-surgeon/SKILL.md`, saying you did so — do not skip the cleanup, and do not report agent output you did not actually get.

### 6. Approval gate
16. Consolidate everything into one report with four sections — **Deleted** (debris removed), **Moved** (relocations with reference patches staged), **Renamed** (casing corrections), **Remaining Actions** (anything needing human judgment) — plus a severity-sorted (P0–P3) risk register with `file:line` evidence. **Stop here and wait for explicit approval.** A pure read-only audit that ends here is a valid, complete outcome.

### 7. Apply + verify (only after approval)
17. Apply only approved items, smallest change first, in order: debris deletion → moves → renames → fixes. Patch every recorded reference before finalizing any move.
18. Re-run the affected validations: `pytest`, `npm run lint:views`, and `npm run snapshot`; confirm no regression.
19. `git diff --stat`, then commit with an **accurate** message reflecting what actually changed (do not claim sprawl/structure work that the audit did not find). Separate hygiene and code-fix commits if both are present. Leave pushing to `develop` (Tier 1) and any `develop`→`main` promotion (Tier 2) to explicit instruction.
