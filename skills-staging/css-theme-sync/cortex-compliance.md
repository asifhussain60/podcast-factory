# /css-theme-sync — CORTEX Challenger Framework v1 Compliance

**Skill:** `css-theme-sync` (theme parity validator + auto-fix)
**Path:** `skills-staging/css-theme-sync/`
**Framework targeted:** CORTEX Challenger Framework v1 (`reference/cortex-challenger-framework.md`)
**Compliance tier:** SILVER (target after retrofit applied)
**Reason for SILVER:** Skill has strong existing mechanical enforcement (pre-commit hook + validator + deterministic mapping tables). Overlay adds CORTEX-aligned severity tiers, formalizes DoR, adds mapping-table freshness check. Not GOLD because validator is invoked externally (pre-commit hook), not as a primitive of the skill itself.

---

## Severity tier mapping (replaces "Blocker / Warning")

| Check | Old label | New severity | Reason |
|---|---|---|---|
| 1: Hex colors in enforced scope | Blocker | **P0** | Wrong color shipped is a P0 visual defect |
| 2: rgba() colors not using tokens | Blocker | **P0** | Same |
| 3: Inline styles in HTML | Blocker | **P0** | Theme parity violation |
| 4: Switcher registration | Blocker | **P0** | Theme switcher broken if missing |
| 5: All 9 theme files present | Blocker | **P0** | Missing theme breaks the matrix |
| 6: Token presence per theme | Blocker | **P0** | Same |
| 7: color-mix browser support | Blocker | **P0** | Output broken on older browsers |
| 8: Stale CSS variables | Warning | **P2** | Quality issue, not correctness |

## Mapping table freshness (overlay-added — closes silent-failure mode)

Before validator runs, check mapping-table freshness:

```
mtime_mapping = mtime of validator's internal mapping tables (color → token, rgba → token)
mtime_theme_files = max mtime across the 9 theme CSS files

IF mtime_theme_files > mtime_mapping:
    WARN: "Theme files modified since mapping tables last reviewed.
           Auto-fix [AUTO] classifications may be stale.
           Review mapping tables before running with --apply."
    
    For each [AUTO] classification:
        verify the source palette color still maps to the current token
        IF mismatch: downgrade to [JUDGE] (operator review required)
```

This closes the audit-flagged failure: stale mapping table accepts wrong-but-valid `var(--token)` substitution.

---

## DoR Gate

| Dimension | Weight | Score 100% when |
|---|---|---|
| Input completeness | 25% | Theme files and HTML scope identified |
| Context clarity | 25% | --apply or --check mode explicit |
| Dependency resolution | 25% | Validator script accessible; mapping tables readable; npm/node available |
| Risk assessment | 15% | --apply has mapping-table freshness check (above) |
| Output target identified | 10% | If --apply: target CSS/HTML files writable |

**Pass criterion:** 100%.

---

## Convergence Gate

After validator runs with --apply, rescan once:

```
run validator in --check mode after --apply commits
IF residual P0/P1 violations remain:
    HALT — report what's still broken
    suggest next action (manual review of remaining issues)
ELSE:
    PASS
```

Single-cycle convergence appropriate because each --apply pass auto-fixes deterministically; if anything is left, it requires judgment.

---

## Sweep Completeness

All 9 themes checked, all CSS in scope scanned, all HTML recursively scanned. Already enforced; framework declaration confirms compliance with CORE-064.

---

## Holistic Validation

Five-check at end of validator run:
1. Registry: 9 theme files accounted for.
2. Dependency drift: mapping tables fresh per overlay check.
3. Regression risk: theme switcher still functional after --apply (visual smoke test if available).
4. Governance: all 8 validator checks executed.
5. Challenge gate: if --apply scope > 50 files, alternatives offered.

---

## Challenge Gate triggers

- Mapping table proposes a non-trivial change (e.g., introducing a new token): alternatives required.
- `color-mix()` support varies (Chrome 111+, Safari 16.2+, Firefox 113+): if any project user is on older browser, fallback strategy required.

---

## Determinism Contract

| Stage | Deterministic? |
|---|---|
| All 8 checks | YES |
| [AUTO] classification | YES |
| [JUDGE] flagging | YES |
| Auto-fix application | YES (deterministic substitution per mapping table) |

Fully deterministic. SILVER (not GOLD) only because the validator is invoked externally, not embedded as a skill primitive.

---

## Applied CORE rules

| Rule | Applied via |
|---|---|
| CORE-002 | Validator output is inline, no scratch files |
| CORE-048 | Holistic validation step (5-check at end) |
| CORE-064 | All-9-themes sweep, all-scope scan |
| CORE-068 | Post-apply rescan |
| CORE-071 | DoR scoring |

---

## Gate Status Schema

Validator writes `_workspace/challenger-reports/css-theme-sync-<timestamp>.yml` per framework Section 3.

---

## Framework version targeted

CORTEX Challenger Framework v1.0.
