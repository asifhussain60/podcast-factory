---
name: repo-surgeon
description: "Holistic repo architecture reviewer, regression hunter, and cleanup enforcer. Runs four sub-agent passes — Structure, Code, Architecture, Brittleness — then generates a repair plan and executes approved fixes. Invoke for 'repo review', 'architectural audit', 'cleanup sweep', 'find regressions', 'root clutter', or 'repo health check'."
---

# repo-surgeon — Architectural Auditor & Repair Skill

Systematic, multi-pass review of the journal repo's architecture, code hygiene, structural integrity, and brittleness. Generates a repair plan, then executes it.

---

## SECTION 0 — CORTEX Compliance (read first)

This skill targets the **CORTEX Challenger Framework v1.0** (`reference/cortex-challenger-framework.md`).
Compliance tier: **BRONZE (target)**. Per-skill compliance contract: [`cortex-compliance.md`](cortex-compliance.md).
Shared SECTION 0 contract: [`reference/skill-bootstrap.md`](../../reference/skill-bootstrap.md).

Before any action, read in order:
1. `reference/cortex-challenger-framework.md`
2. `reference/skill-bootstrap.md`
3. `skills-staging/repo-surgeon/cortex-compliance.md`
4. This file (SKILL.md).
5. The execution-detail companion: [`.github/agents/repo-surgeon.agent.md`](../../.github/agents/repo-surgeon.agent.md) — contains the procedural bash for each pass. This SKILL.md is the contract; the agent file is the procedure.

**Severity is P0–P3.** Legacy labels (Critical, High, Medium, Low) have been mapped inline. The `cortex-compliance.md` mapping table is authoritative when in doubt.

**Run report:** one report per pass at `_workspace/challenger-reports/repo-surgeon-pass<N>-<run_id>.yml` per framework §3 schema.

---

## When to invoke

- After any large feature merge or convergence cycle
- Before a release to main
- On demand: "repo review", "architectural audit", "cleanup sweep", "root clutter"
- Weekly maintenance cadence (recommended)

## Tier

Cowork T3 — requires file system access, git history, search, and edit capabilities.

## Owns

- Repo structural integrity (root hygiene, folder placement)
- Orphaned file detection and cleanup
- Registry alignment (skills, prompts, agents)
- Stale reference detection and repair
- `server/logs/surgeon-log.jsonl` (run log)

## Does NOT own

- CSS/theme audit (delegates to `css-theme-sync` / `ui-reviewer`)
- Memoir content quality (that's `journal` skill)
- Spend/budget (that's `usage-auditor`)

## Sub-Agent Passes

The skill executes four passes in order. Each pass is a focused sub-agent concern.

### Pass 1 — Structure Auditor

Scans physical repo structure for violations:

| Check | What |
|---|---|
| Root clutter | Only governed files at root. Everything else → `_workspace/scratch/` or delete. |
| Misplaced files | Files outside their governed location (e.g., prompts outside `server/src/prompts/`). |
| Empty directories | Tracked empty dirs are violations. |
| `.DS_Store` leaks | Must be covered by `.gitignore`. |
| Temp files | `*.prompt.md`, `scratchpad-*`, `tmp-*`, `debug-*` at root. |

### Pass 2 — Code Auditor

Scans for dead and redundant code:

| Check | What |
|---|---|
| Orphaned CSS | `.css` files not linked from any HTML. |
| Orphaned JS | `.js` files not referenced from any HTML or JS. |
| Dead server routes | Routes with no client caller. |
| Orphaned prompts | Prompt files not in registry. |
| Orphaned shared modules | `shared/*.js` not imported anywhere. |
| Console.log leaks | Unguarded `console.log` in production JS. |

### Pass 3 — Architecture Auditor

Validates governance alignment:

| Check | What |
|---|---|
| Skill registry completeness | Every `skills-staging/*/` in README, every README entry has `skill.md`. |
| Agent registry | Every agent file listed in `framework.md` or marked DEPRECATED. |
| Prompt ↔ Skill map | Bidirectional sync between prompt files and skill registry map. |
| Canonical write violations | App commits touching Cowork-only paths in recent history. |
| Framework.md staleness | Folder tree in framework.md matches reality. |

### Pass 4 — Brittleness Scanner

Finds fragile patterns that will break on next change:

| Check | What |
|---|---|
| Hardcoded paths | Absolute paths in JS/HTML/CSS. |
| Stale branch refs | References to completed feature branches. |
| Missing error boundaries | Server routes without try/catch. |
| Broken internal links | Markdown links to nonexistent files. |
| Trip/daybook residue | References to removed v3.0 surfaces (`trips/`, `trip-edit`, `dayone-publish`, daybook routes). |
| Zombie TODOs | `TODO`/`FIXME` older than 30 days. |

## Output

Each run produces:

1. **Findings report** — categorized by pass, with severity **P0 / P1 / P2 / P3** (legacy: Critical → P0, High → P1, Medium → P2, Low → P3).
2. **Repair plan** — actionable fix list grouped by severity.
3. **Execution log** — appended to `server/logs/surgeon-log.jsonl`.
4. **Per-pass run report** — `_workspace/challenger-reports/repo-surgeon-pass<N>-<run_id>.yml` per framework §3 schema.

## Determinism Contract

Per the shared bootstrap (`reference/skill-bootstrap.md` §4):

- **Findings sort order:** severity (P0 first) → pass number (1–4) → rule ID (R1/C1/A1/B1 etc., lexicographic) → file path (lexicographic POSIX) → line number.
- **Orphan-detection tiebreaker (Pass 2):** before flagging a file as orphan, run the static + dynamic-import detection per `cortex-compliance.md`. Any dynamic-pattern hit downgrades to "POSSIBLE ORPHAN — verify before deletion" / P2 (never P0/P1). **Never silently delete on a single static-analysis miss.**
- **TODO age threshold (Pass 4):** 30 days (configurable; current default). Age is computed against the run's clock-source timestamp (UTC), not local time. Time-dependence is declared per `cortex-compliance.md` §Determinism Contract.
- **Run identifiers:** `run_id` = SHA-256(skill_name + pass_number + ISO-8601 UTC timestamp + input_hash), truncated to 16 hex chars. `input_hash` = SHA-256 of `git rev-parse HEAD` + `git status --porcelain` output (newline-normalized).
- **Locale / clock:** dates ISO-8601 UTC; numeric formatting `en-US` decimal.
- **No `Math.random()` or unseeded RNG anywhere.**

## DoR, Convergence, Sweep

- **DoR:** 100% required before `--fix` per `cortex-compliance.md`. On failure: `_workspace/repo-surgeon-dor-incomplete-<run_id>.md` + halt.
- **Convergence:** max 3 cycles per pass. On exceed: halt + report.
- **Sweep:** per pass, per category — Pass 2 deletes all confirmed orphans in approved scope or none; Pass 1 moves all root violations or none. No partial sweeps.

## Challenge Gate triggers

Per `cortex-compliance.md` §Challenge Gate: any pass touching > 10 files OR > 5 root moves OR > 10 orphan deletions surfaces 2+ alternatives before commit.

## Flags

| Flag | Effect |
|---|---|
| `--preview` | Findings + plan only, no execution. **Default.** |
| `--fix` | Execute the repair plan (destructive ops need confirmation). |
| `--pass <1-4>` | Run only one pass. |
| `--root-only` | Shortcut: only Pass 1 Rule R1 (root hygiene). |

## Commit Convention

Fixes are committed per-pass: `fix(surgeon-P{N}): {summary}`

## Dependencies

- `css-theme-sync` — defers CSS/theme audit
- `ui-reviewer` — defers CSS review detail
- `framework.md` — reads governance rules (Pass 3)
- `skills-staging/README.md` — reads/writes skill registry (Pass 3)
