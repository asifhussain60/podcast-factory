# /usage-auditor — CORTEX Challenger Framework v1 Compliance

**Skill:** `usage-auditor` (Anthropic API spend monitor + forecast)
**Path:** `skills-staging/usage-auditor/`
**Framework targeted:** CORTEX Challenger Framework v1
**Compliance tier:** BRONZE (target after retrofit + burst-aware forecast)
**Reason for BRONZE:** Read-only monitoring skill. No multi-file modifications, no DoR risk (read-only), no convergence needed (single-pass aggregation). Bronze appropriate. Overlay primarily adds severity tiers + burst-aware forecast to close the silent-failure mode.

---

## Severity tier mapping (no prior taxonomy)

| Finding type | Severity | Notes |
|---|---|---|
| Source files unreadable / API unreachable | **P0** | Cannot produce report without data |
| Malformed log rows | **P2** | Skip and log; report count of skipped |
| Pricing table mismatch with API current pricing | **P1** | Output incorrect; user has no warning otherwise |
| Forecast projects exceeding monthly cap | **P0** | Operator must see this |
| Forecast within 20% of cap | **P1** | Heads-up |
| Forecast comfortable (<80% of cap) | **P3** | Informational |
| Single endpoint accounts for > 80% of spend | **P2** | Possibly worth attention |

## Burst-aware forecast (overlay-added — closes silent-failure mode)

Current forecast: linear extrapolation (`daily_avg × remaining_days`). Silent failure: end-of-month bursts not detected; cap silently breached.

Replacement:

```
Compute three forecasts:
    F_linear = daily_avg × remaining_days
    F_burst = (worst-3-day-burst-rate) × remaining_days
    F_blended = (F_linear × 0.6) + (F_burst × 0.4)

Report all three:
    "Linear projection: $X"
    "Burst-aware projection (assumes worst-3-day rate continues): $Y"
    "Blended projection (60% linear, 40% burst): $Z"

For cap-alert logic:
    use F_blended (not F_linear) as the trigger.
    
IF F_blended > cap:
    severity P0 — alert
ELIF F_blended > 0.8 × cap:
    severity P1
ELSE:
    severity P3 (informational)
```

This closes the audit-flagged failure: late-month bursts no longer silently breach cap.

---

## Pricing table freshness check (overlay-added)

```
Pricing table is embedded (no live API lookup, less fragile).
But: pricing can change.

Overlay adds:
    On every run, log the embedded pricing's revision date.
    IF revision date > 90 days old:
        WARN: "Pricing table last updated [date]. If Anthropic API pricing has changed,
               this report may be inaccurate. To verify: check
               https://www.anthropic.com/api#pricing and update reference/pricing-table.yml."
```

---

## DoR Gate

| Dimension | Weight | Score 100% when |
|---|---|---|
| Input completeness | 25% | usage.jsonl readable AND/OR API summary reachable |
| Context clarity | 25% | Time window specified (default: current month) |
| Dependency resolution | 25% | Pricing table loadable; clock available; output format determined |
| Risk assessment | 15% | Cap-alert threshold configured |
| Output target identified | 10% | Output destination (stdout / file) determined |

**Pass criterion:** 80% (read-only skill, lower threshold than code-touching ops per framework Section 2 Primitive 1).

---

## Convergence Gate

NOT APPLICABLE — read-only. Declared exception per framework Primitive 2.

---

## Sweep Completeness

YES — all rows scanned, all endpoints tallied, all days in window covered. Framework declaration confirms compliance.

---

## Holistic Validation

End-of-run 5-check:
1. Registry: rows-read count matches expectations.
2. Dependency drift: pricing table fresh (overlay check).
3. Regression risk: N/A (read-only).
4. Governance: forecast methodology documented.
5. Challenge gate: if F_blended close to cap, alternatives surfaced (manual review, throttle suggestion).

---

## Challenge Gate triggers

- F_blended > cap: alternatives surfaced ("reduce burst usage by 30%", "request cap increase", "schedule expensive operations earlier").

---

## Determinism Contract

| Step | Deterministic? |
|---|---|
| Source aggregation | YES |
| Pricing application | YES |
| Forecast computation | YES given same clock |
| Cap-alert logic | YES |

Fully deterministic.

---

## Applied CORE rules

| Rule | Applied via |
|---|---|
| CORE-002 | Output inline (stdout); optional file output is the deliverable, not noise |
| CORE-048 | End-of-run holistic check |
| CORE-064 | All rows / all endpoints swept |
| CORE-068 | N/A (read-only) |
| CORE-071 | DoR scoring |

---

## Outstanding gaps to reach SILVER

1. Implement burst-aware forecast per overlay.
2. Implement pricing-table freshness check.
3. Decide whether cap-alert escalation should integrate with system notifications (out of scope for skill itself; flag for separate decision).

---

## Gate Status Schema

Each run writes `_workspace/challenger-reports/usage-auditor-<timestamp>.yml`.

---

## Framework version targeted

CORTEX Challenger Framework v1.0.
