// ai-routes-rate-limit.test.mjs — every paid AI route pays the same toll.
//
// WHY THIS EXISTS. `rateLimitCheck()` is what stands between a stuck client (a
// retry loop, a held-down button, a page that re-fires on every keystroke) and
// an unbounded run of billed model calls. Nine of the eleven routes under
// `api/ai/` called it; `research.ts` — which reaches Gemini WITH Google-Search
// grounding, the most expensive call the site makes — and `claude.ts` did not,
// and nothing would have said so.
//
// The check is a source scan on purpose: the guard has to be the FIRST thing the
// handler does, before the body is parsed or a model is reached, and that is a
// property of the text. A runtime test would have to mint a real request per
// route and could still pass on a route that called the limiter too late.
//
// Add a route under api/ai/ and it is covered by this test the moment it lands.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const AI_DIR = resolve(__dirname, "..", "src", "pages", "api", "ai");

function aiRoutes() {
  return readdirSync(AI_DIR)
    .filter((f) => f.endsWith(".ts") && !f.endsWith(".test.ts"))
    .sort();
}

test("every api/ai route is rate limited", () => {
  const routes = aiRoutes();
  assert.ok(routes.length > 0, "no routes found — has api/ai/ moved?");

  const missing = [];
  for (const file of routes) {
    const src = readFileSync(join(AI_DIR, file), "utf8");
    const imported = /import\s*\{[^}]*\brateLimitCheck\b[^}]*\}\s*from/.test(
      src,
    );
    const called = /\brateLimitCheck\s*\(\s*\)/.test(src);
    const refuses = /\b429\b/.test(src);
    if (!imported || !called || !refuses) missing.push(file);
  }

  assert.deepEqual(
    missing,
    [],
    `these paid routes spend without a limit: ${missing.join(", ")}`,
  );
});

test("the limit is checked before the request body is read", () => {
  const late = [];
  for (const file of aiRoutes()) {
    const src = readFileSync(join(AI_DIR, file), "utf8");
    const limit = src.search(/\brateLimitCheck\s*\(\s*\)/);
    const body = src.search(/request\.json\s*\(/);
    if (limit === -1 || body === -1) continue;
    if (limit > body) late.push(file);
  }
  assert.deepEqual(
    late,
    [],
    `the toll is paid after the body is parsed in: ${late.join(", ")}`,
  );
});
