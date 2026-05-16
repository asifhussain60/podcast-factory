---
name: usage-auditor
description: "Usage + spend auditor for Asif's journal. Invoke when the user says 'usage-auditor', '/usage-auditor', '@usage-auditor', 'audit usage', 'spend audit', 'budget audit', 'where is my money going', 'project monthly spend', 'monthly spend forecast', or 'how much have I spent'. Reads `server/logs/usage.jsonl` (and `GET /api/usage/summary`) to report total spend, per-endpoint cost, projected end-of-month burn, throttle-hit count, and cap recommendations. Accepts `--forecast` to extrapolate spend if the current pace continues, and `--since <ISO>` to scope the window."
---

# usage-auditor — Usage & Spend Auditor

Read-only orchestrator that summarizes `usage.jsonl` into an actionable spend report against the proxy's `MONTHLY_CAP`.

---

## SECTION 0 — CORTEX Compliance (read first)

This skill targets the **CORTEX Challenger Framework v1.0** (`reference/cortex-challenger-framework.md`).
Compliance tier: **BRONZE (target)**. Per-skill compliance contract: [`cortex-compliance.md`](cortex-compliance.md).
Shared SECTION 0 contract: [`reference/skill-bootstrap.md`](../../reference/skill-bootstrap.md).

Before any action, read in order:
1. `reference/cortex-challenger-framework.md`
2. `reference/skill-bootstrap.md`
3. `skills-staging/usage-auditor/cortex-compliance.md`
4. This file.

**Severity is P0–P3** (this skill had no prior taxonomy; the compliance doc establishes mapping).

**Run report:** `_workspace/challenger-reports/usage-auditor-<run_id>.yml` per framework §3 schema.

This skill is **read-only** — Convergence Gate is N/A by declaration. DoR threshold is 80% (read-only ops, per framework §1 Primitive 1).

---

## When to invoke

- On-demand when `/api/usage/summary` shows the monthly cap is being approached
- Monthly retrospective: what did this month cost, what's the trend
- Before tuning rate-limit / throttle middleware

## Inputs

| Source | Path |
|---|---|
| Live summary | `GET http://localhost:3001/api/usage/summary` (preferred when proxy is up) |
| Usage log | `server/logs/usage.jsonl` (fallback / finer-grained filtering) |
| Pricing table | embedded in `server/src/usage-summary.js` |

## Flags

- `--since <ISO-8601>` — start of audit window (default: first of current month).
- `--until <ISO-8601>` — end of window (default: now).
- `--forecast` — extrapolate projected month-end spend from current daily rate.
- `--format text|json|both` — output. Default `both`.
- `--top N` — limit byEndpoint table rows (default 10).

## Output — text shape

```
usage-auditor · {window: YYYY-MM-DD → YYYY-MM-DD} · {n rows}

total spend:    ${X.XX}       ({pct}% of ${monthlyCAP} cap)
throttle state: normal|soft|hard
throttle hits:  {M}           (requests that hit soft/hard gates)

by endpoint (top {N} by spend):
  1. /api/refine                 {calls}  avg ${avg}  total ${total}  ({pct}%)
  2. /api/chat                   {calls}  avg ${avg}  total ${total}  ({pct}%)
  ...

daily trend:
  day 01   $0.11
  day 02   $0.08
  ...
  day {today}   $0.14   (partial)

forecast (--forecast):
  daily avg:       ${Y.YY}
  projected month: ${Z.ZZ}   ({pct}% of cap)
  at current rate, cap hit on {date} or never
  recommendation: {keep cap | lower to ${A} | raise to ${B}}
```

## Output — JSON shape

```json
{
  "window": { "since": "2026-04-01T00:00:00Z", "until": "2026-04-16T18:00:00Z" },
  "totalSpend": 0.037,
  "monthlyCAP": 50,
  "percentageUsed": 0.07,
  "throttleState": "normal",
  "throttleHits": 57,
  "byEndpoint": [
    { "endpoint": "/api/refine", "calls": 21, "avgCost": 0.00125, "totalCost": 0.02625, "percentOfMonth": 69.83, "lastCallAt": "2026-04-16T16:04:15.773Z" }
  ],
  "dailyTrend": [{ "day": "2026-04-15", "spend": 0.011 }],
  "forecast": {
    "dailyAvg": 0.002,
    "projectedMonth": 0.08,
    "projectedPercent": 0.16,
    "capHitOn": null,
    "recommendation": "keep cap"
  }
}
```

## Composition strategy

Reads `usage.jsonl` directly (fast-path: reuses `getUsageSummary` from `server/src/usage-summary.js` when proxy is running; falls back to direct file read when proxy is down so audits still work offline). Forecast is pure Tier 0 math (linear extrapolation of daily average).

## Guardrails

- **Read-only.** Never mutate usage.jsonl or billing state.
- **Timezone-consistent.** All dates UTC unless `--format text`, which renders in America/New_York.
- **No network calls.** Pricing is embedded; no external price-API lookup.
- **Fail loud on malformed rows.** Skip the row, log to stderr, don't crash.
- **Respect privacy.** Never surface full message bodies — only aggregate counts + costs.

## Non-goals

- Not a throttle enforcer (middleware does that server-side).
- Not a billing client — this audits local telemetry only.

## Determinism Contract

Per the shared bootstrap (`reference/skill-bootstrap.md` §4):

- **Findings sort order:** severity (P0 first) → endpoint name (lexicographic) → day (ISO-8601, ascending).
- **Aggregation tiebreaker:** when two rows have identical timestamps, sort by request id (lexicographic); if still tied, by original file offset (ascending).
- **Forecast determinism:** all three projections (`F_linear`, `F_burst`, `F_blended` per `cortex-compliance.md`) are pure functions of (input rows, run-clock, cap). Same input + same clock = same numbers, byte-for-byte. The blend is a fixed `0.6 × linear + 0.4 × burst`.
- **Burst window:** the "worst 3 days" are selected by descending daily-total, then ascending date (the *earliest* day among ties to make output stable). This tiebreaker is named here explicitly to avoid run-to-run variance on ties.
- **Run identifiers:** `run_id` = SHA-256(skill_name + ISO-8601 UTC timestamp + input_hash), truncated to 16 hex chars. `input_hash` = SHA-256 of newline-normalized `usage.jsonl` bytes within the requested window.
- **Locale / clock:**
  - All dates in JSON output: ISO-8601 UTC.
  - All dates in text output (default `--format text`): `en-US` with `America/New_York` timezone, named in the string (e.g., `"2026-05-16 18:42 ET"`).
  - Numeric formatting: `en-US` decimal in JSON; `en-US` with thousands separators in text.
- **No `Math.random()` anywhere.**

## DoR

- **DoR threshold:** 80% (read-only) per framework §1 Primitive 1. Dimensions per `cortex-compliance.md` §DoR Gate.
- **On failure:** `_workspace/usage-auditor-dor-incomplete-<run_id>.md` + halt.

## Run report

After every run, write `_workspace/challenger-reports/usage-auditor-<run_id>.yml` per framework §3 schema.
