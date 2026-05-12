// middleware/throttle-budget.js — Phase 8 budget throttle.
//
// Reads current-month spend from usage-summary before each request and
// either lets it through, downgrades the body (soft throttle), or returns
// HTTP 429 (hard throttle).
//
// Wired after usage-logger (Phase 1) so the incoming request is still logged
// even when throttled. The X-Budget-State header mirrors throttleState on
// every response.
//
// Budget state thresholds (per getUsageSummary):
//   percentageUsed < 75  → "normal"  — no changes
//   75 ≤ pct      < 90  → "soft"    — edit-intent endpoints return
//                                      { ok: true, throttled: true, ... }
//   pct         ≥ 90    → "hard"    — non-essential endpoints return
//                                      HTTP 429 { throttled: true, ... }
//
// Essentials that always pass (regardless of state): /health, tier-0 reference
// data (GET /api/reference-data/*), and the usage summary itself.

import { getUsageSummary } from "../lib/usage-summary.js";

const ESSENTIAL_PATHS = new Set([
  "/health",
  "/api/usage/summary",
  "/api/config",
]);
const ESSENTIAL_PREFIXES = [
  "/api/reference-data/",
];

// Cost-ful endpoints that fall under hard throttle.
const HARD_DENY_PATHS = new Set([
  "/api/chat",
  "/api/refine",
  "/api/voice-test",
  "/api/theme-swatches",
  "/api/theme-review",
]);

function classifyPath(method, path) {
  if (ESSENTIAL_PATHS.has(path)) return "essential";
  if (ESSENTIAL_PREFIXES.some((p) => path.startsWith(p))) return "essential";
  if (HARD_DENY_PATHS.has(path)) return "expensive";
  return "other";
}

/**
 * Express middleware factory for budget-based throttling.
 *
 * @param {object} opts
 * @param {number} [opts.monthlyCAP=50]
 * @param {() => Promise<{ throttleState: string, spentThisMonth: number, monthlyCAP: number }>} [opts.summaryFn]
 *   Injection point for tests. Defaults to getUsageSummary.
 */
export function throttleBudget({ monthlyCAP = 50, summaryFn } = {}) {
  const load = summaryFn || (() => getUsageSummary({ monthlyCAP }));

  return async function throttleBudgetMiddleware(req, res, next) {
    let state = "normal";
    try {
      const summary = await load();
      state = summary.throttleState || "normal";
    } catch {
      state = "normal";
    }

    res.set("X-Budget-State", state);

    if (state === "normal") return next();

    const kind = classifyPath(req.method, req.path);

    if (kind === "essential") return next();

    // soft state: let everything through with the header so the page can
    // surface a banner. There are no longer any edit-intent endpoints.
    if (state === "soft") return next();

    // state === "hard"
    if (kind === "expensive") {
      return res.status(429).json({
        ok: false,
        throttled: true,
        throttleState: "hard",
        message:
          "Monthly budget limit approaching (≥90% used). Non-essential endpoints are paused until the next billing cycle or cap increase.",
      });
    }
    return next();
  };
}

export { classifyPath };
