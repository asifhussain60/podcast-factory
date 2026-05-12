---
name: repo-surgeon
description: "Holistic repo architecture reviewer, regression hunter, and cleanup enforcer. Runs four sub-agent passes — Structure, Code, Architecture, Brittleness — then generates a repair plan and executes approved fixes. Invoke for 'repo review', 'architectural audit', 'cleanup sweep', 'find regressions', 'root clutter', or 'repo health check'."
---

# repo-surgeon — Architectural Auditor & Repair Skill

Systematic, multi-pass review of the journal repo's architecture, code hygiene, structural integrity, and brittleness. Generates a repair plan, then executes it.

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
- Queue state (that's `queue-health`)
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

1. **Findings report** — categorized by pass, with severity (Critical / High / Medium / Low)
2. **Repair plan** — actionable fix list grouped by severity
3. **Execution log** — appended to `server/logs/surgeon-log.jsonl`

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
- `queue-health` — reads queue state (Pass 4 manifest check)
- `framework.md` — reads governance rules (Pass 3)
- `skills-staging/README.md` — reads/writes skill registry (Pass 3)
