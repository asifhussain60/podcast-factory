# /journal — CORTEX Challenger Framework v1 Overlay

**Skill:** `journal` (memoir writing agent)
**Plugin path:** `~/.claude/skills/journal/SKILL.md` (read-only — overlay applies separately)
**Framework targeted:** CORTEX Challenger Framework v1 (`reference/cortex-challenger-framework.md`)
**Compliance tier:** SILVER (after overlay applied)
**Reason for SILVER (not GOLD):** Journal is a craft skill — Phase 2 interactive review is human-judgment-based and declared non-deterministic. SILVER reflects that some primitives are documented-but-not-fully-enforced because the medium (memoir writing) genuinely requires human judgment.

---

## What this overlay does

The plugin SKILL.md for `/journal` defines 45 quality checks across 5 loops + 12 SECTION 8 final-gate checks. Without this overlay, none of those checks have severity tiers, the skill has no DoR gate, and there is no convergence loop. The overlay:

1. Maps every check to P0–P3.
2. Defines a memoir-appropriate DoR gate.
3. Adds a bounded voice-rewrite convergence loop.
4. Lists applicable CORE rules.
5. Declares determinism exceptions.
6. Closes the silent-failure mode the audit caught (33 advisory checks can ship voice violations).

---

## Severity tier mapping for all 45+12 checks

### LOOP 1 — Voice Integrity (7 checks)

| Check | Severity | Reason |
|---|---|---|
| Sentence authenticity (voice DNA) | **P0** | Misrepresents author — non-negotiable |
| Humor patterns (6 documented types) | **P1** | Material quality loss but recoverable |
| Emotional register | **P0** | Same as sentence authenticity |
| Vocabulary DNA (preferred/banned words) | **P1** | Materially wrong word choice |
| Contractions | **P2** | Style preference |
| Sentence openers | **P2** | Style preference |
| Paragraph length rules | **P2** | Style preference |

### LOOP 2 — Narrative Architecture (6 checks)

| Check | Severity | Reason |
|---|---|---|
| Emotional arc flow | **P1** | Material storytelling defect |
| Scene necessity | **P1** | Material — extra scenes drag pacing |
| Three-phase balance (50-60% / 20-30% / 15-20%) | **P2** | Guideline; exceptions OK with reason |
| Organic transitions | **P1** | Material — abrupt transitions break the read |
| Narrative Constant (no victim framing) | **P0** | Memoir governance — non-negotiable |
| Babu's Advice register | **P0** | Voice fidelity for the dedication subject |

### LOOP 3 — Craft & Pacing (9 checks)

| Check | Severity | Reason |
|---|---|---|
| Emotional pacing | **P1** | Material — pacing failures are felt by reader |
| Transition speed | **P1** | Material |
| Documented bridge patterns (6 types) | **P2** | Preferred patterns; exceptions OK |
| Insight emergence | **P1** | Material — forced insight breaks craft |
| Emotion build | **P1** | Material |
| Punctuation rules (no em dashes) | **P0** | Hard rule — em dashes are banned |
| Markdown prohibition | **P0** | Final output must be plain text |
| Jargon prohibition | **P0** | Voice violation — author does not use AI/therapy jargon |
| Voice extraction completed | **P3** | Informational |

### LOOP 4 — Governance Compliance (9 checks)

| Check | Severity | Reason |
|---|---|---|
| Ali (AS) notation | **P0** | Religious-respect rule — non-negotiable |
| Temporal guardrails | **P0** | Factual accuracy of memoir timeline |
| Atif contrast limits | **P1** | Material — over-contrast against brother is unfair |
| Translation rules | **P0** | Glossary canonical — single source of truth |
| Repetition audit | **P1** | Material — repetition across chapters dilutes |
| Sacred quote limits | **P0** | Religious-respect rule |
| Quote once-only rule | **P1** | Editorial discipline |
| Locked paragraph protection | **P0** | Asif-locked content cannot be modified silently |
| Delta-protected paragraph rules | **P0** | Same |

### LOOP 5 — Voice Extraction (2 checks)

| Check | Severity | Reason |
|---|---|---|
| Extract new patterns | **P3** | Informational — improves the skill but doesn't affect this chapter |
| Update voice-deep-analysis.md | **P3** | Informational |

### SECTION 8 — Final Quality Gate (12 hard checks)

All twelve are **P0**. These were already hard gates in the plugin SKILL.md; the overlay makes their severity explicit.

| Check | Severity |
|---|---|
| Voice authenticity | **P0** |
| Em dashes | **P0** |
| Therapy jargon | **P0** |
| Insight emergence | **P0** |
| Emotion gradation | **P0** |
| Invented details | **P0** |
| Paragraph splits | **P0** |
| Translation canonicity | **P0** |
| Quote integration | **P0** |
| Day One compatibility | **P0** |
| Narrative Constant | **P0** |
| Loop passage (all loops returned PASS for P0/P1 checks) | **P0** |

### Total tally

| Severity | Count |
|---|---|
| P0 | 21 |
| P1 | 12 |
| P2 | 6 |
| P3 | 5 (3 advisory + 2 extraction-related) |
| Other (SECTION 8 already-hard checks) | 12 (all P0) |
| **Total** | **45 + 12 = 57** checks |

After overlay, **33 checks are P0/P1 and block delivery if they fail.** Before overlay, only 12 blocked delivery (SECTION 8). The overlay catches the silent-failure mode the audit identified: advisory checks no longer ship voice violations because P0/P1 checks now block.

---

## DoR Gate definition (memoir-appropriate)

Before Phase 1 (rebuild in scratchpad), the journal skill verifies these DoR dimensions:

| Dimension | Weight | Score 100% when |
|---|---|---|
| Input completeness | 25% | Chapter target file exists and is readable |
| Context clarity | 25% | Asif has specified the chapter (e.g., "ch01-man") and the scope (full rewrite / specific section) |
| Dependency resolution | 25% | `reference/voice-fingerprint.md`, `reference/memoir-rules-supplement.txt`, `reference/translations-glossary.md`, `reference/incident-bank.md`, `reference/temporal-guardrail.md`, `reference/locked-paragraphs.md` all readable; delta protocol has run (or doesn't need to) |
| Risk assessment | 15% | If chapter contains locked paragraphs or delta-protected paragraphs, Asif is aware they will not be modified |
| Output target identified | 10% | Scratchpad path determined |

**Pass criterion:** 100%.

**Failure handling:** Write `_workspace/journal-dor-incomplete-<chapter>.md` listing every unmet dimension. Halt. Do not begin Phase 1.

---

## Convergence loop (voice-rewrite, max 3 cycles)

When LOOP 3 quality checks flag P0 voice violations in a rewritten section, the overlay adds a bounded convergence loop:

```
cycle = 0
WHILE cycle < 3:
    re-run the affected section's rewrite (Phase 1 for that section only)
    re-run all P0 + P1 checks
    IF no P0 AND no P1 violations:
        BREAK (converged)
    cycle += 1

IF still P0/P1 after 3 cycles:
    HALT
    write _workspace/journal-convergence-failed-<chapter>.md
    summarize which checks failed across the 3 cycles
    ask Asif: continue with violations (with explicit acknowledgment), or accept skill's recommendation to rework the section
```

This replaces the old behavior of running checks once and asking Asif to manually revise.

---

## Sweep Completeness contracts

| Sweep target | All-or-none unit |
|---|---|
| Translation glossary updates | All instances of a translation change in a chapter, or none (already enforced via delta protocol) |
| Locked paragraph protection | All locked paragraphs in the chapter, or halt |
| Delta-protected paragraph protection | All delta-protected paragraphs, or halt |
| Cross-chapter repetition check | All chapters scanned, or none |

The overlay does NOT add new sweep contracts beyond what the plugin SKILL.md already enforces. Existing sweep behavior is acknowledged as compliant.

---

## Determinism Contract declarations

| Stage | Deterministic? | Why / exception |
|---|---|---|
| Delta detection | YES | Mechanical diff |
| Phase 1 rebuild | NO (declared exception) | Voice rewrite involves judgment; same input + same Asif state can produce structurally different output. Captured by Phase 2 interactive review. |
| Phase 2 interactive review | NO (declared exception) | Human-in-the-loop by design |
| Phase 2a qualifying questions | YES | Multi-choice answers are user-supplied |
| Phase 3 quality loops | YES | Mechanical checks against rules |
| Phase 4 finalization | YES | File operations, registry updates |
| SECTION 8 final gate | YES | Mechanical checks |

The journal skill is **SILVER tier** because Phases 1 and 2 are intentionally non-deterministic. SILVER is appropriate for human-judgment creative work; GOLD requires full determinism which is incompatible with memoir craft.

---

## Applied CORE rules

| Rule | How journal applies it (post-overlay) |
|---|---|
| **CORE-002** — Inline output | Journal produces chapter file as deliverable; scratchpad is intermediate state, not output noise |
| **CORE-048** — Holistic Validation | Phase 3's 5 loops + SECTION 8 are the holistic validation; risk score not formally computed but P0/P1 counts serve the same purpose |
| **CORE-068** — Convergence Gate | Added by this overlay — voice-rewrite loop, max 3 cycles |
| **CORE-071** — DoR Enforcement | Added by this overlay — memoir-appropriate DoR, 100% required before Phase 1 |

CORE rules NOT applied by journal:
- **CORE-008** (TDD) — N/A; journal does not write code
- **CORE-011/012** (type hints, docstrings) — N/A; journal does not write code
- **CORE-028** (snake_case file naming) — Journal uses its own naming convention (`ch01-man.txt`), grandfathered
- **CORE-035** (single canonical implementation) — N/A in code sense; journal does enforce canonical voice in narrative sense via voice-fingerprint
- **CORE-064** (Sweep Completeness) — Implicitly enforced via delta protocol; no formal contract added by overlay

---

## Challenge Gate triggers

The overlay adds Challenge Gate triggers for:

- **Major narrative restructuring** (Phase 2 review where Asif requests structural change to a chapter): skill must propose 2+ structural alternatives with pros/cons before applying.
- **Locked-paragraph override**: if Asif requests modification of a locked paragraph, skill must present the lock reason, alternatives, and require explicit "override locked" command.
- **Translation deviation from glossary**: if Asif rewords a glossary-canonical translation, skill must surface the deviation and propose updating the glossary OR reverting the wording.

---

## Gate Status Schema usage

Every journal run writes `_workspace/challenger-reports/journal-<chapter>-<timestamp>.yml` per the framework's Section 3 schema. The schema is canonical.

---

## How to apply this overlay

This overlay describes contracts the plugin SKILL.md does not currently encode. To apply:

**Manual / future plugin rebuild:**
1. Open `~/.claude/skills/journal/SKILL.md`.
2. Add a SECTION 0 referencing this overlay (`reference/skill-overlays/journal-cortex-overlay.md`).
3. Add severity tags to each check in LOOPs 1–5 per the mapping above.
4. Add the DoR gate as a new SECTION inserted before Phase 1.
5. Add the convergence loop wrapper in LOOP 3.
6. Add `_workspace/challenger-reports/` write at end of Phase 4.

**Runtime interim (until plugin rebuild):**
- This overlay file is read by orchestrating skills (e.g., podcast, future skill-coordinator) to know journal's compliance state.
- Asif can read this overlay alongside the plugin SKILL.md when invoking `/journal` to know what the post-compliance behavior would be.

---

## Silent-failure modes closed by this overlay

| Failure mode (from audit) | How overlay closes it |
|---|---|
| 33 advisory checks can ship voice violations | All 33 now have explicit P0/P1/P2/P3 tags; P0/P1 block delivery |
| Phase 3 runs once; no convergence | Convergence loop added (max 3 cycles) |
| No DoR — work can start incomplete | DoR gate added with 5 weighted dimensions, 100% required |
| No CORTEX alignment — isolated governance | Overlay maps to applicable CORE rules; framework v1.0 declared |

---

## Verification

To verify journal meets framework v1.0 (post-overlay):

1. Read this overlay end to end.
2. Confirm every plugin SKILL.md check is tagged with severity.
3. Confirm DoR gate definition is implementable.
4. Confirm convergence loop pseudocode is unambiguous.
5. Run `/journal` against a chapter. Verify `_workspace/challenger-reports/journal-<chapter>-<timestamp>.yml` is produced.

Compliance is **active** when overlay is applied to the plugin SKILL.md (manual step) OR when the skill runtime reads this overlay alongside the plugin file (automated, requires orchestrator).

---

## Framework version targeted

This overlay targets **CORTEX Challenger Framework v1.0**. Future framework versions require overlay updates per the framework's Section 8 versioning policy.
