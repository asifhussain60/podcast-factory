# /clean-commit — CORTEX Challenger Framework v1 Overlay

**Skill:** `clean-commit` (folder hygiene and git commit agent)
**Plugin path:** `~/.claude/skills/clean-commit/SKILL.md` (read-only)
**Framework targeted:** CORTEX Challenger Framework v1
**Compliance tier:** BRONZE (after overlay applied)
**Reason for BRONZE:** Pre-existing skill has no CORTEX integration, no severity tiers, and no all-or-none sweep contract. The overlay adds CORE-064 sweep enforcement and severity tier mapping. BRONZE reflects that the skill has 4 hard gates already (so it's not the weakest), but lacks the systemic CORTEX integration the framework requires.

---

## What this overlay does

The plugin SKILL.md for /clean-commit has:
- 4 hard gates (Target resolution → Audit → Propose → Commit).
- Tier 1 (auto-clean) vs Tier 2 (sprawl, confirmation) risk taxonomy.
- 6 internal safety rules (no force-push, no amend, no secrets, etc.).
- Zero CORTEX references.

Gaps:
- Tier 1/Tier 2 is risk-based, not severity-based. Cross-skill coordination needs P0–P3.
- No CORE-064 sweep contract — Tier 2 partial approvals execute as partial sweeps. The silent-failure mode.
- No CORE-068 convergence — single-pass.
- No CORTEX integration at all.

The overlay fills these gaps.

---

## Severity tier mapping

### Pre-flight (Section 1: Target Resolution)

| Check | Severity |
|---|---|
| Folder exists | P0 |
| Folder readable | P0 |
| Git repo detected (or explicit non-git mode) | P0 |
| `git status --porcelain` runs without error | P0 |

### Audit phase (Section 2)

| Check | Severity |
|---|---|
| All files categorized (junk / sprawl / structural / content) | P0 |
| Junk patterns match documented patterns only (no surprise deletions) | P0 |
| Sprawl categorization references explicit folder rules | P1 |
| Structural categorization references framework.md or equivalent | P1 |
| Content files identified and protected | P0 |

### Propose phase (Section 3)

| Check | Severity |
|---|---|
| Report shows every proposed action | P0 |
| Operator can see what will change | P0 |
| Destructive proposals flagged explicitly | P0 |

### Execute phase (Section 4)

| Check | Severity |
|---|---|
| Operator confirmation captured for Tier 2 actions | P0 |
| **Sweep contract honored (overlay-added — see below)** | **P0** |
| Tier 1 auto-cleanups limited to documented patterns | P0 |

### Commit phase (Section 5)

| Check | Severity |
|---|---|
| `git status` shown before commit | P0 |
| Commit message constructed and shown | P0 |
| Operator approves commit message | P0 |
| No force-push, no amend | P0 |
| Secrets scan before staging | P0 |
| Commit succeeds | P1 |

---

## Sweep Completeness contract (overlay-added — closes silent-failure mode)

Before any Tier 2 execution begins, the skill applies the framework's CORE-064 contract per **category**:

```
For each Tier 2 category (e.g., "delete all .swp files in subfolders", "relocate all
loose .md files from root to docs/"):
    
    enumerate ALL matching targets across the entire repo (not just current dir)
    
    present to operator:
        "CATEGORY: [description]
         TARGETS: [list of N files]
         APPROVAL OPTIONS:
           ALL — execute on all N targets atomically
           NONE — skip this category entirely
           CUSTOM — operator manually picks subset (with explicit acknowledgment that
                    this violates the all-or-none contract; will be logged)"
    
    wait for operator decision
    
    IF ALL or NONE: execute deterministically
    IF CUSTOM: log the partial-sweep waiver in commit message
```

This is the **silent-failure fix.** Before overlay: operator could approve "all" and skill might miss files matching the pattern in folders not yet scanned. After overlay: full enumeration + atomic ALL/NONE/explicit CUSTOM with waiver logging.

---

## DoR Gate definition

| Dimension | Weight | Score 100% when |
|---|---|---|
| Input completeness | 20% | Target folder specified or inferable from cwd |
| Context clarity | 25% | Operator's intent clear (clean / commit / both) |
| Dependency resolution | 25% | git available; folder readable; framework.md (if applicable) readable |
| Risk assessment | 20% | If destructive scope > 10 files, escalate to operator before audit |
| Output target identified | 10% | Commit destination known (current branch, no force-push) |

**Pass criterion:** 100%.

**Failure handling:** Halt. Report missing dimensions.

---

## Convergence Gate

Single-pass for the audit-propose-execute flow. The overlay does NOT add iterative convergence for the cleanup itself (cleanup is destructive — you don't iterate a destructive op).

However, the overlay adds a convergence check for the **post-commit verification**:

```
After commit:
    re-run audit (read-only mode)
    IF residual junk / sprawl / structural issues remain:
        report what's left
        offer to run another clean-commit cycle
    IF clean:
        report PASS
```

This is single-cycle convergence (one rescan after commit). It catches: items that should have been cleaned but weren't because pattern matching missed them.

---

## Holistic Validation Gate

Applies to commit:
- Registry check: committed files exist on disk.
- Dependency check: no broken references after commit (e.g., relocated file's old path not referenced anywhere).
- Regression check: existing tests / build still passes (skip if no test infrastructure).
- Governance check: commit message follows convention; no force-push; secrets clean.
- Challenge gate: for Tier 2 with > 5 targets, alternatives offered.

---

## Challenge Gate triggers

- **Scope > 10 files in a single category**: alternatives offered (split into multiple commits, do in stages).
- **Cross-directory relocation**: alternatives offered (relocate vs. leave with .gitignore).
- **Non-git mode**: explicit confirmation that no commit will be made.

---

## Determinism Contract declarations

| Stage | Deterministic? | Why / exception |
|---|---|---|
| Target resolution | YES | |
| Audit | YES given same folder state | Categorization rules are mechanical |
| Propose | YES | Report from audit |
| Execute (Tier 1) | YES | Pattern-matched deletion |
| Execute (Tier 2) | NO (operator-dependent) | Operator chooses ALL/NONE/CUSTOM |
| Commit | YES | git operations |

---

## Applied CORE rules

| Rule | How /clean-commit applies it (post-overlay) |
|---|---|
| **CORE-048** — Holistic Validation | Pre-commit holistic check added |
| **CORE-064** — Sweep Completeness | Added as Tier 2 ALL/NONE/CUSTOM contract |
| **CORE-068** — Convergence | Adapted as post-commit single-rescan |
| **CORE-071** — DoR Enforcement | Added as pre-audit DoR scoring |

---

## Gate Status Schema usage

Every /clean-commit run writes `_workspace/challenger-reports/clean-commit-<target>-<timestamp>.yml`.

---

## Silent-failure mode closed

| Failure mode (from audit) | How overlay closes it |
|---|---|
| Tier 2 partial approval executes as partial sweep — files matching pattern in unscanned folders missed | Full enumeration before execution; ALL/NONE/CUSTOM atomic options; CUSTOM logs waiver in commit message |

---

## How to apply this overlay

**Manual / future plugin rebuild:**
1. Open `~/.claude/skills/clean-commit/SKILL.md`.
2. Add severity tags to every check across Sections 1–5.
3. Insert sweep enumeration in Section 4 (before execution).
4. Add post-commit convergence rescan in Section 5.
5. Add DoR scoring in Section 1.
6. Add gate status schema output at end of commit phase.

**Runtime interim:** Overlay file readable by orchestrating skills.

---

## Framework version targeted

CORTEX Challenger Framework v1.0.
