# /ui-modernizer — CORTEX Challenger Framework v1 Compliance

**Skill:** `ui-modernizer` (four-phase UI refactor: Design System, Architecture, Interactions, Views)
**Path:** `skills-staging/ui-modernizer/`
**Framework targeted:** CORTEX Challenger Framework v1
**Compliance tier:** SILVER (target after retrofit + anchor replacement)
**Reason for SILVER:** Skill has good phase structure, validator integration, and ui-reviewer hook. Overlay adds severity tiers, replaces line-range hardcoding with stable anchors, formalizes DoR. SILVER (not GOLD) because Phase 3 / 4 visual checks remain semi-manual.

---

## Severity tier mapping (replaces single "MAJOR" tag)

| Existing label | New severity | Notes |
|---|---|---|
| (Phase 1b "MAJOR") | **P0** | Opacity rule is a hard design system rule |
| (Locked decisions) | **P0** | Locked = cannot be changed without explicit override |
| (Other phase checks) | **P0/P1/P2** per finding type | Mapped below |

Per-phase severity:

| Phase | Finding | Severity |
|---|---|---|
| Phase 1a | --muted → --text-secondary substitution incomplete | **P0** |
| Phase 1a | All 9 themes consistent | **P0** |
| Phase 1b | Opacity rule violation | **P0** |
| Phase 2 | CSS split (architecture) broke file structure | **P0** |
| Phase 2 | Hardcoded line range (overlay-detected) | **P0** |
| Phase 3 | Accordion children wrapping missed | **P1** |
| Phase 3 | Interaction state inconsistent across components | **P1** |
| Phase 4 | Token audit incomplete (subsection skipped) | **P1** |
| Phase 4 | Widget breathe-room spacing violated | **P2** |

## Anchor replacement (overlay-added — closes silent-failure mode)

Phase 2's current hardcoded line ranges (e.g., lines 698–2163 in app.css) break silently if file is hand-edited. Replacement:

```
Instead of: "extract lines 698–2163 to layout.css"

Use: "extract from anchor:
        /* === BEGIN: Layout section === */
      to:
        /* === END: Layout section === */
      
      If anchors absent in source file:
        Stage 0 of Phase 2 inserts anchors at semantically correct boundaries
        (detected via section comments, h2-style banner comments, or rule grouping)
        Commit anchor insertion separately from extraction
        Then extraction operates on anchors, not line numbers"
```

This makes Phase 2 robust to hand-edits.

---

## Phase 1b opacity check (overlay-added)

Currently flagged but not implemented in validator. Overlay specifies:

```
Add Check 9 to css-theme-sync validator:
    For every CSS rule in theme files and app.css:
        IF rule sets `opacity: <value>`:
            verify value is one of allowed-opacity-tokens (--opacity-low/--opacity-med/--opacity-high)
            OR within explicit exception list (animation keyframes, hover transitions)
        IF not: flag as P0 violation
```

---

## DoR Gate

| Dimension | Weight | Score 100% when |
|---|---|---|
| Input completeness | 20% | Target HTML/CSS files identified |
| Context clarity | 25% | Phase (1–4) explicit; --apply or --preview mode explicit |
| Dependency resolution | 30% | css-theme-sync validator available; ui-reviewer agent reachable; locked-decisions doc readable |
| Risk assessment | 15% | If --apply scope > 10 files, escalate |
| Output target identified | 10% | Target files writable; commit destination known |

**Pass criterion:** 100%.

---

## Convergence Gate

Per-phase convergence:

```
For each phase (1–4):
    cycle = 0
    WHILE cycle < 3:
        run phase in --check mode
        IF no P0/P1 findings:
            BREAK
        IF --apply mode: apply phase fixes; cycle += 1
        IF --preview: report and break
    
    IF cycle == 3 AND P0/P1 remain:
        HALT
    
    POST-PHASE: run css-theme-sync validator + ui-reviewer
    IF either fails:
        HALT
```

---

## Sweep Completeness

Per-phase, all-or-none:
- Phase 1: all 9 themes and all enforced-scope CSS, or none.
- Phase 2: extraction completes for the full anchored range, or rollback.
- Phase 3: all accordions get the wrapping update, or none.
- Phase 4: all 4 subsection token audits complete, or report incomplete and block.

---

## Holistic Validation

After each phase:
1. Registry: changed files match phase plan.
2. Dependency drift: css-theme-sync validator passes.
3. Regression risk: ui-reviewer agent visual check.
4. Governance: phase commit message references framework version, phase number, anchors used.
5. Challenge gate: if phase scope exceeds locked-decision boundaries, alternatives offered.

---

## Challenge Gate triggers

- Locked-decision override: alternatives required.
- Phase 2 anchor placement disagreement (semantic vs. line-number boundary): alternatives offered.
- Phase 4 widget audit deviation from spec: alternatives offered.

---

## Determinism Contract

| Phase | Deterministic? |
|---|---|
| Phase 1a (token replacement) | YES |
| Phase 1b (opacity rule check) | YES post-implementation |
| Phase 2 (CSS split via anchors) | YES (with anchor replacement) |
| Phase 3 (interaction wrapping) | YES given component spec |
| Phase 4 (token audit) | PARTIAL — depends on subjective "breathe-room" judgment |

---

## Applied CORE rules

| Rule | Applied via |
|---|---|
| CORE-035 | One canonical layout file (CSS split per Phase 2) |
| CORE-048 | Per-phase holistic + ui-reviewer hook |
| CORE-064 | Per-phase sweep |
| CORE-068 | Per-phase convergence |
| CORE-071 | Pre-phase DoR |

---

## Outstanding gaps to reach GOLD

1. Phase 4 widget audit needs full spec (4 subsections currently; full coverage not detailed).
2. Phase 1b opacity check implementation in validator.
3. Anchor replacement for Phase 2 (overlay-specified above).

---

## Gate Status Schema

Each phase writes `_workspace/challenger-reports/ui-modernizer-phase<N>-<timestamp>.yml`.

---

## Framework version targeted

CORTEX Challenger Framework v1.0.
