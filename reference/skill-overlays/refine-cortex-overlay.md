# /refine — CORTEX Challenger Framework v1 Overlay

**Skill:** `refine` (prompt refinement agent)
**Plugin path:** `~/.claude/skills/refine/SKILL.md` (read-only)
**Framework targeted:** CORTEX Challenger Framework v1
**Compliance tier:** BRONZE (after overlay applied)
**Reason for BRONZE:** Refine is a single-pass conversational skill. The overlay adds severity tiers + operator-validation loop + missing primitives, but the skill is fundamentally a Q&A workflow, not a long-running pipeline. BRONZE reflects that some primitives (Convergence, Sweep Completeness) are not naturally applicable.

---

## What this overlay does

The plugin SKILL.md for `/refine` has 3 gates (1 hard, 2 soft) and cites 4 CORE rules in its output but does not enforce them during its own execution. The overlay:

1. Maps existing gates to P0–P3.
2. Adds an **operator-validation loop** to close the silent-failure mode: phantom scope expansion from Phase 2 inferred items.
3. Defines a lightweight DoR (Q1–Q4 responses).
4. Declares which CORE rules apply to the skill's execution (not just to the brief it produces).
5. Adds gate status schema output.

---

## Severity tier mapping

### Phase 1 — Qualifying Questions (mandatory)

| Check | Severity |
|---|---|
| Q1 answered (scope) | P0 |
| Q2 answered (file patterns) | P0 |
| Q3 answered (acceptance criteria) | P0 |
| Q4 answered (priority) | P0 |

All four are P0: skill cannot generate a brief without complete answers. This makes Phase 1 the de facto DoR.

### Phase 2 — Scope expansion (soft)

| Check | Severity |
|---|---|
| Inferred items marked as `INFERRED` in output | **P0** (overlay-promoted from soft to hard) |
| Each inferred item references the raw input span that triggered the inference | **P1** |
| Operator confirms each inferred item before brief is finalized | **P0** (overlay-added) |

This is the **silent-failure fix.** Before overlay: inferred items silently shipped. After overlay: inferred items require explicit operator confirmation.

### Phase 3 — Authority grounding (soft → hard)

| Check | Severity |
|---|---|
| Every issue references a specific authority (spec, file path, git history) | **P0** (overlay-promoted) |
| Authority is verifiable (file exists, spec section exists) | **P1** |

---

## DoR Gate definition

The DoR for /refine is the four qualifying questions:

| Dimension | Weight | Score 100% when |
|---|---|---|
| Input completeness | 25% | Raw input present and parseable |
| Context clarity | 35% | All four Q1–Q4 answers provided |
| Dependency resolution | 15% | Files / specs referenced in input are accessible |
| Risk assessment | 15% | Priority (Q4) reflects realistic P0/P1/P2/P3 mapping |
| Output target identified | 10% | Skill knows the brief is for Cowork paste (default) or alternate destination |

**Pass criterion:** 100%.

**Failure handling:** If user attempts to skip a Q1–Q4 answer, skill re-prompts. Does not generate brief until DoR is 100%.

---

## Operator-validation loop (overlay-added)

After Phase 2 inferred items are generated, before Phase 3 authority grounding:

```
inferred = list of inferred scope items
IF len(inferred) > 0:
    present each inferred item to operator:
        "INFERRED ITEM N: [item text]
         BASIS: [raw input span that triggered this inference]
         CONFIRM: [accept / reject / edit]"
    wait for operator decision per item
    accepted = items operator confirmed
    rejected_or_edited = remainder
    proceed to Phase 3 with operator-confirmed items only
ELSE:
    proceed directly to Phase 3
```

This is the operator-validation loop. It is mandatory when inferred items exist. The skill cannot ship a brief containing unconfirmed inferred items.

---

## Convergence Gate

NOT APPLICABLE. /refine is a single-pass workflow; there is no detect-fix-rescan cycle.

The overlay explicitly declares Convergence as inapplicable per framework Primitive 2 ("Optional when: The skill is purely read-only and does not generate artifacts that require self-validation.").

---

## Sweep Completeness

NOT APPLICABLE. /refine operates on a single brief, not across multiple targets.

---

## Holistic Validation Gate

NOT APPLICABLE in full form. The skill produces a brief, not code or content modifications. However, the overlay adds a lightweight validation:

- Authority grounding check (every issue grounded in spec / file / git).
- No-fabrication check (every issue traceable to raw input or operator-confirmed inference).

This serves the Holistic Validation purpose at appropriate scope for a conversational skill.

---

## Challenge Gate

The overlay adds a Challenge Gate trigger for:

- **Scope > 5 files or unbounded scope:** skill must present 2+ alternative scoping approaches before finalizing brief.
- **Priority Q4 = P0 for non-trivial change:** skill must confirm by re-reading the input back to operator with explicit "this is being treated as P0 because [reason]".

---

## Determinism Contract declarations

| Phase | Deterministic? | Why / exception |
|---|---|---|
| Phase 1 questions | YES | Same questions for same input type |
| Phase 2 inferred items | NO (declared exception) | Inference is heuristic |
| Phase 3 authority grounding | YES | Mechanical lookup |
| Phase 4 brief output | YES given confirmed inputs | Template-driven |

BRONZE is appropriate.

---

## Applied CORE rules

| Rule | How /refine applies it (post-overlay) |
|---|---|
| **CORE-002** — Inline output | Skill produces brief as conversational output, not as files in workspace |
| **CORE-048** — Challenge Gate | Added for scope expansion (above) |
| **CORE-064** — Sweep Completeness | Cited in brief output; applies to the operator's downstream work, not refine itself |
| **CORE-068** — Convergence | Cited in brief output; applies downstream |
| **CORE-071** — DoR Enforcement | Added as Q1–Q4 gate (mandatory) |

The four CORE rules cited in the existing plugin output are correct citations for the downstream work; the overlay adds CORE-071 enforcement for refine itself.

---

## Gate Status Schema usage

Every /refine run writes `_workspace/challenger-reports/refine-<topic-slug>-<timestamp>.yml` per framework Section 3.

---

## Silent-failure mode closed

| Failure mode (from audit) | How overlay closes it |
|---|---|
| Phantom scope expansion: Phase 2 inferred items ship without operator validation | Operator-validation loop added; inferred items require explicit confirmation before brief is finalized |

---

## How to apply this overlay

**Manual / future plugin rebuild:**
1. Open `~/.claude/skills/refine/SKILL.md`.
2. Add severity tags to Q1–Q4 (P0) and Phase 2/3 checks.
3. Insert operator-validation loop between Phase 2 and Phase 3.
4. Add Challenge Gate triggers for scope expansion.
5. Add gate status schema output at end of brief generation.

**Runtime interim:** This overlay file is read by orchestrating skills to know /refine's compliance state.

---

## Framework version targeted

CORTEX Challenger Framework v1.0.
