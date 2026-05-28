# /tell-me — CORTEX Challenger Framework v1 Overlay

**Skill:** `tell-me` (transcript-informed context challenger and response drafter)
**Plugin path:** `~/.claude/skills/tell-me/SKILL.md` (read-only)
**Framework targeted:** CORTEX Challenger Framework v1
**Compliance tier:** SILVER (after overlay applied)
**Reason for SILVER:** /tell-me has the strongest pre-existing enforcement of the user-authored skills (7-stage pipeline, Stage 5 Challenger Gate enforces every-claim-verified). The overlay adds severity tiers + freshness check + DoR formalization. SILVER reflects that the skill is deterministic on stable evidence but time-dependent on live repos.

---

## What this overlay does

The plugin SKILL.md for /tell-me has:
- 7-stage pipeline.
- 5 hard gates.
- 2 CORE rules cited (CORE-002, CORE-048).
- Stage 5 Challenger Gate is the strongest enforcement of any skill (every claim must have source).

Gaps:
- No P0–P3 severity tiers.
- No synthesis freshness check — the silent-failure mode.
- DoR is implicit (Stages 1–5 must pass), not formalized.

The overlay fills these gaps.

---

## Severity tier mapping

### Stage 1 — Input Parse

| Check | Severity |
|---|---|
| Topic summary extracted | P0 |
| Input is parseable | P0 |

### Stage 2 — Evidence Harvest

| Check | Severity |
|---|---|
| `adlc-master-synthesis.md` readable | P0 |
| Knowledge YAMLs readable | P0 |
| Transcripts in evidence trail readable | P1 (degraded but skill can proceed) |
| Evidence read in priority order | P1 |

### Stage 3 — Repo Scan

| Check | Severity |
|---|---|
| `gh` CLI available | P0 (skill cannot verify claims without it) |
| All four repos accessible | P1 (single repo unreachable → skill flags but proceeds for verified-elsewhere claims) |
| Claims with grep-evidence verified | P0 |

### Stage 4 — Settled vs Open Classification

| Check | Severity |
|---|---|
| Every fact classified (SETTLED / OPEN / STALE) | P0 |
| Open items flagged with OQ numbers | P1 |

### Stage 5 — Challenger Gate

| Check | Severity |
|---|---|
| Every claim in brief has a source | P0 |
| Questions verify against evidence | P0 |
| Technical claims grep-verified | P0 |
| Attributions verified in transcripts | P0 |
| **Synthesis freshness verified** | **P0** (overlay-added — see below) |

### Stage 6–7 — Output composition

| Check | Severity |
|---|---|
| Brief format adheres to skill output template | P1 |
| Citations rendered correctly | P0 |

---

## Synthesis freshness check (overlay-added — closes silent-failure mode)

Inserted as the first sub-check of Stage 5 Challenger Gate, before any claim verification:

```
mtime_synthesis = mtime of reference/adlc-master-synthesis.md (or equivalent synthesis file)
mtime_latest_transcript = max mtime across transcripts in evidence directory

IF mtime_latest_transcript > mtime_synthesis:
    # Synthesis is older than latest transcript
    POSSIBLE STALE CONTENT
    
    For each SETTLED claim in the draft brief:
        verify the claim against the transcript(s) created after mtime_synthesis
        IF transcript material would change the claim's status:
            reclassify as STALE
            update editorial-trail with reason
    
    Add to brief header: "⚠ Synthesis last updated [date]; transcripts updated since [date]. Some SETTLED claims reverified against newer transcripts; see Evidence Trail."
ELSE:
    # Synthesis is current
    proceed with normal Challenger Gate
```

This closes the audit-identified silent failure: a "settled" claim that has been overturned by a recent transcript no longer ships as settled.

---

## DoR Gate definition

The DoR for /tell-me is the input parse + evidence accessibility:

| Dimension | Weight | Score 100% when |
|---|---|---|
| Input completeness | 20% | User's question / screenshot / link parseable |
| Context clarity | 30% | Topic summary extracted; scope identifiable |
| Dependency resolution | 35% | Synthesis file readable; knowledge YAMLs readable; `gh` CLI available; at least 3 of 4 repos reachable |
| Risk assessment | 10% | If topic touches financial / security / compliance, escalate severity |
| Output target identified | 5% | Brief format determined (chat draft / email / Teams response) |

**Pass criterion:** 100%.

**Failure handling:** Halt. Report which dimension is unmet. /tell-me's existing "no assumed context, no assumed scope" ZERO rules already enforce most of this; the overlay formalizes it as a single DoR gate.

---

## Convergence Gate

Single-pass validate-or-reject is the existing pattern. The overlay does NOT add iterative convergence — for a briefing skill, multiple rounds would mean over-refining the brief, not converging to a clean state.

The Challenger Gate at Stage 5 is a *filtering convergence* (claims that fail validation are removed before output), which satisfies the framework's intent for this skill type.

---

## Sweep Completeness

Applies to:

- **Evidence harvest:** all relevant transcripts must be read, not a partial sample. The overlay adds an explicit sweep contract: "If the user's question touches topic X, all transcripts mentioning X must be read, OR the brief must note that the harvest was truncated and why."
- **Repo scan:** all four repos in scope must be checked for the topic, or the brief notes the truncation.

---

## Holistic Validation Gate

The Stage 5 Challenger Gate IS the Holistic Validation in tell-me's case. It includes:
- Registry check (claims map to evidence sources).
- Dependency check (synthesis freshness — overlay-added).
- Governance check (citation discipline).
- Challenge gate (open questions surfaced).

No additional gate needed.

---

## Challenge Gate

The skill already surfaces "OPEN" questions as part of Stage 4. The overlay adds:

- **High-stakes claim Challenge:** if a claim is P0-severity for the operator (security, financial, compliance), present 2+ phrasings of how to communicate it and ask operator to choose.

---

## Determinism Contract declarations

| Stage | Deterministic? | Why / exception |
|---|---|---|
| 1 Parse | YES | |
| 2 Harvest | TIME-DEPENDENT | Live file mtimes; output structure deterministic but content depends on time |
| 3 Repo scan | TIME-DEPENDENT | Live git state |
| 4 Classification | YES given fixed evidence | Classification rules are mechanical |
| 5 Challenger Gate | YES | Verification is mechanical |
| 6–7 Output | YES | Template-driven |

Stages 2–3 are TIME-DEPENDENT (not subjectively non-deterministic) — same input at the same point in time produces the same output. The overlay records the evidence snapshot time in the gate status report so re-runs can be cross-referenced.

---

## Applied CORE rules

| Rule | How /tell-me applies it |
|---|---|
| **CORE-002** — Inline output (pre-existing) | Brief delivered as chat output, no file emission |
| **CORE-048** — Challenger Gate (pre-existing) | Stage 5 verifies every claim |
| **CORE-068** — Convergence | Adapted as filtering convergence at Stage 5 |
| **CORE-071** — DoR Enforcement (overlay-added) | Stages 1–3 formalized as DoR |

The existing 3 ZERO rules (no assumed scope, no assumed context, etc.) are skill-specific. The overlay does not retire them — they complement the CORTEX framework.

---

## Gate Status Schema usage

Every /tell-me run writes `_workspace/challenger-reports/tell-me-<topic-slug>-<timestamp>.yml`.

---

## Silent-failure mode closed

| Failure mode (from audit) | How overlay closes it |
|---|---|
| Synthesis older than latest transcript — SETTLED claim ships as settled when it's actually stale | Synthesis freshness check added as first sub-check of Stage 5; STALE-reclassification triggered if mtime ordering reveals drift |

---

## How to apply this overlay

**Manual / future plugin rebuild:**
1. Open `~/.claude/skills/tell-me/SKILL.md`.
2. Add severity tags to every check across Stages 1–7.
3. Insert synthesis freshness check at start of Stage 5.
4. Formalize DoR scoring across Stages 1–3.
5. Add gate status schema output at end of brief generation.

**Runtime interim:** This overlay file is read by orchestrating skills.

---

## Framework version targeted

CORTEX Challenger Framework v1.0.
