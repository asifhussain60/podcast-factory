# /repo-surgeon — CORTEX Challenger Framework v1 Compliance

**Skill:** `repo-surgeon` (4-pass repo audit: Structure, Code, Architecture, Brittleness)
**Path:** `skills-staging/repo-surgeon/`
**Framework targeted:** CORTEX Challenger Framework v1
**Compliance tier:** BRONZE (target after retrofit + dynamic-import detection added)
**Reason for BRONZE:** The skill's 4 passes are designed but execution logic is sketched, not playbooked. Pass 2 orphan detection has false-positive risk (no dynamic-import handling). BRONZE is appropriate until: (a) Pass 1–4 have full playbooks, (b) Pass 2 handles dynamic imports, (c) framework primitives are wired in.

---

## Severity tier mapping (replaces "Critical / High / Medium / Low")

| Old label | New severity | Notes |
|---|---|---|
| Critical | **P0** | Halt and require operator action |
| High | **P1** | Halt the pass; surface for review |
| Medium | **P2** | Warn but proceed |
| Low | **P3** | Advisory in final report |

Per-pass examples:

| Pass | Finding type | New severity |
|---|---|---|
| Pass 1 (Structure) | Root has > 20 files; canonical structure violated | **P1** |
| Pass 1 | Misplaced file (e.g., `.env` in root) | **P0** if it's a secrets file; **P2** otherwise |
| Pass 2 (Code) | Orphan file (truly unreachable) | **P1** |
| Pass 2 | Orphan candidate that might be reached via dynamic import | **P2** (not P0/P1 — requires verification) |
| Pass 3 (Architecture) | File violates framework.md folder placement | **P1** |
| Pass 4 (Brittleness) | Hardcoded path in code | **P1** |
| Pass 4 | TODO older than 30 days | **P2** |
| Pass 4 | TODO older than 180 days | **P1** |

## Dynamic-import detection (overlay-added — closes silent-failure mode)

Pass 2 orphan detection currently uses static import analysis only. Silent failure: files reached via `import()`, `require(name)`, or dynamic registry lookup are marked orphan and silently deleted on --fix.

Fix:

```
For each candidate orphan:
    static check: file not imported by any other file via static import.
    
    dynamic check (overlay-added):
        grep the entire repo for the file's basename as a string literal.
        grep for the file's module name (without extension) as a string literal.
        check known dynamic-import patterns:
            – import(`...${var}...`)
            – require(varname)
            – glob-based loaders (require.context, fs.readdirSync of plugins/skills dirs)
            – registries that map names to file paths
    
    IF dynamic check finds ANY references:
        downgrade orphan to "POSSIBLE ORPHAN — verify before deletion"
        severity: P2 (not P1 or P0)
        --fix does NOT delete; operator review required
    ELSE:
        confirmed orphan
        severity: P1
        --fix can delete with operator confirmation
```

This closes the audit-flagged failure: false-positive orphan deletion.

---

## DoR Gate

| Dimension | Weight | Score 100% when |
|---|---|---|
| Input completeness | 20% | Target repo specified and readable |
| Context clarity | 25% | --preview or --fix mode explicit; --pass N if scoped |
| Dependency resolution | 25% | framework.md or canonical-structure spec readable; git available |
| Risk assessment | 20% | If --fix scope > 20 files, escalate before execution |
| Output target identified | 10% | Repo path resolved; commit will be made per pass |

**Pass criterion:** 100%.

---

## Convergence Gate

Per-pass convergence:

```
For each pass (1–4):
    cycle = 0
    WHILE cycle < 3:
        run pass in --check mode
        IF no P0/P1 findings:
            BREAK
        IF --fix mode: apply fixes; cycle += 1
        IF --preview mode: report and break (no convergence in preview)
    
    IF cycle == 3 AND P0/P1 still present:
        HALT pass
        report what didn't converge
```

---

## Sweep Completeness

Per-pass, per-category. Example: Pass 2 either deletes all confirmed orphans in the approved scope or none. No partial deletion.

---

## Holistic Validation

After each pass commits, run a 5-check:
1. Registry: changed files in expected paths.
2. Dependency drift: framework.md still parses; no broken references.
3. Regression risk: tests still pass (if test infra exists).
4. Governance: commit message follows convention; sweep contract honored.
5. Challenge gate: if pass touched > 10 files, alternatives offered.

---

## Challenge Gate triggers

- Pass 1 root-only refactor with > 5 files moved: alternatives offered.
- Pass 2 orphan deletion of > 10 files: alternatives offered.
- Pass 3 architectural relocation: alternatives offered.
- Pass 4 hardcoded-path fix that would touch > 5 files: alternatives offered.

---

## Determinism Contract

| Pass | Deterministic? | Why / exception |
|---|---|---|
| Pass 1 (Structure) | YES given same framework.md | |
| Pass 2 (Code, static) | YES | AST analysis is deterministic |
| Pass 2 (Code, dynamic) | YES given same grep patterns | |
| Pass 3 (Architecture) | YES given framework.md | |
| Pass 4 (Brittleness) | TIME-DEPENDENT | TODO ages depend on git dates |

BRONZE acceptable. Time-dependence is declared, not subjective.

---

## Applied CORE rules

| Rule | Applied via |
|---|---|
| CORE-028 | Pass 1 enforces snake_case for new files |
| CORE-035 | Pass 2 enforces single canonical implementation (orphans = duplicates that lost) |
| CORE-048 | Per-pass holistic validation |
| CORE-064 | Per-pass sweep completeness |
| CORE-068 | Per-pass convergence (max 3 cycles) |
| CORE-071 | Per-skill-invocation DoR |

---

## Outstanding gaps to reach SILVER

1. Write full playbooks for Pass 1, 2, 3, 4 (currently designed but not executable).
2. Implement dynamic-import detection per the overlay-added section.
3. Make TODO-age threshold configurable (currently hardcoded 30 days).

When all three are addressed, skill graduates to SILVER.

---

## Gate Status Schema

Each pass writes `_workspace/challenger-reports/repo-surgeon-pass<N>-<timestamp>.yml` per framework Section 3.

---

## Framework version targeted

CORTEX Challenger Framework v1.0.
