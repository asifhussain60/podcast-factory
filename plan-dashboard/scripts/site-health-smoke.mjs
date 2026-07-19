#!/usr/bin/env node
// site-health-smoke.mjs — deterministic RUNTIME health gate for the Podcast
// Factory Astro Site (plan-dashboard/). This is the cheap, no-LLM half of the
// site-health system: it boots the dev server, visits every page route in a real
// headless browser, and HARD-FAILS on any runtime error the static gates
// (`lint:views`, `astro check`, the html-view-challenger agent) physically
// cannot see — uncaught client exceptions, console errors, failed network
// requests, and 5xx SSR responses.
//
// It is the deterministic companion to the `site-health-sentinel` agent, which
// runs this first and then layers visual-defect judgment on top. Console-error
// catching lives HERE (fast, repeatable, zero model spend); the agent owns the
// screenshot-grounded visual QA.
//
// Uses only Playwright (already a devDependency + chromium is installed) — no
// npm install, no new dependencies.
//
// Usage:
//   node scripts/site-health-smoke.mjs                # boot ephemeral dev server, sweep all routes
//   node scripts/site-health-smoke.mjs --json         # machine-readable summary
//   node scripts/site-health-smoke.mjs --route /plan  # sweep a single route
//   SITE_HEALTH_BASE_URL=http://localhost:4322 node scripts/site-health-smoke.mjs
//                                                     # reuse an already-running server (what the agent does)
//   SITE_HEALTH_SLUG=mukhtasar-ul-asar-2 node ...     # pin the fixture slug
//
// Exit codes: 0 = clean (or warnings only), 1 = one or more FAIL findings.

import { spawn } from "node:child_process";
import { readdirSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
import { chromium } from "playwright";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SITE_DIR = resolve(__dirname, ".."); // plan-dashboard/
const REPO_ROOT = resolve(SITE_DIR, ".."); // repo root
const CONTENT_DIR = join(REPO_ROOT, "content");

const argv = process.argv.slice(2);
const JSON_OUT = argv.includes("--json");
const ONE_ROUTE = (() => {
  const i = argv.indexOf("--route");
  return i >= 0 && argv[i + 1] ? argv[i + 1] : null;
})();
const PORT = Number(process.env.SITE_HEALTH_PORT || 4322);

// Console-error / failed-request patterns that are known-benign in dev and must
// NOT fail the gate. Keep this list SHORT and justified — every entry is a
// blind spot. Anything not matched here is a real finding.
const BENIGN = [
  /favicon\.ico/i, // no favicon wired; harmless 404
  /\[vite\] (connecting|connected)/i, // HMR socket chatter
  /Download the (React|Vue) DevTools/i, // framework devtools nag
  /\.map\b/i, // sourcemap fetch misses in dev
];
const isBenign = (text) => BENIGN.some((re) => re.test(String(text || "")));

// ---- fixture discovery ----------------------------------------------------
// Pick one real book slug that exists on disk so parameterized routes render
// against live data instead of a 404. Prefer a slug that has both pipeline
// state and a built book/ (the richest surface), then fall back.
function discoverSlug() {
  if (process.env.SITE_HEALTH_SLUG) return process.env.SITE_HEALTH_SLUG;
  const buckets = ["Islamic", "Technical", "Fiction", "Guides"];
  const candidates = [];
  for (const b of buckets) {
    const bdir = join(CONTENT_DIR, b);
    if (!existsSync(bdir)) continue;
    for (const slug of readdirSync(bdir)) {
      const d = join(bdir, slug);
      if (!existsSync(join(d, "_system"))) continue;
      const score =
        (existsSync(join(d, "book")) ? 2 : 0) +
        (existsSync(join(d, "_system", "orchestrator-state.json")) ? 1 : 0);
      candidates.push({ slug, score });
    }
  }
  candidates.sort((a, b) => b.score - a.score);
  return candidates.length ? candidates[0].slug : null;
}

// ---- route manifest -------------------------------------------------------
// tier1 = fixture-free views that must ALWAYS render clean (the architecture
//         views + top-level app index pages).
// tier2 = detail views that need a live fixture; a 4xx here means the fixture
//         didn't match (skipped, not failed) — but console/page errors and 5xx
//         still fail, because those are real runtime bugs.
function buildRoutes(slug) {
  const tier1 = [
    "/",
    "/overview",
    "/how-it-works",
    "/architecture",
    "/infrastructure",
    "/intelligence",
    "/pipeline-paths",
    "/system-map",
    "/db-schema",
    "/corpus",
    "/quality",
    "/security",
    "/plan",
    "/about",
    "/annotation-ops",
    "/library",
    "/studio",
    "/studio/new",
    "/pronunciation",
    "/pre-upload",
    "/wisdom",
  ].map((path) => ({ path, tier: 1 }));

  const tier2 = slug
    ? [
        `/library/${slug}`,
        `/studio/${slug}`,
        `/studio/${slug}/edit`, // the default Edit & Enrich rich-editor island (blank-island blind spot)
        `/studio/${slug}/compose`,
        `/studio/${slug}/book`,
        `/studio/${slug}/live`, // LIVE Session reading view (own CSS + scroll-synced explanations)
        `/studio/${slug}/preview`, // whole-book page-image preview (renders fresh from book.md on demand)
        `/studio/${slug}/arabic-review`,
        // `/studio/<slug>/style` was removed 2026-07-19: it was a standalone
        // duplicate of the Book Composer's Citations tab (same FAMILIES list,
        // same PUT /api/studio/citation-style, same book/citation-style.json)
        // with zero inbound links. The Composer is the one place that choice is
        // made now.
        `/studio/${slug}/view`,
        `/pre-upload/${slug}`,
        `/pronunciation/${slug}`,
      ].map((path) => ({ path, tier: 2 }))
    : [];

  const all = [...tier1, ...tier2];
  return ONE_ROUTE ? all.filter((r) => r.path === ONE_ROUTE) : all;
}

// ---- server lifecycle -----------------------------------------------------
async function waitForServer(baseUrl, timeoutMs = 60000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(baseUrl, { method: "GET" });
      if (res.ok || res.status < 500) return true;
    } catch {
      /* not up yet */
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  return false;
}

async function ensureServer() {
  const provided = process.env.SITE_HEALTH_BASE_URL;
  if (provided) {
    const ok = await waitForServer(provided, 5000);
    if (!ok)
      throw new Error(`SITE_HEALTH_BASE_URL ${provided} is not reachable`);
    return { baseUrl: provided.replace(/\/$/, ""), proc: null };
  }
  const baseUrl = `http://localhost:${PORT}`;
  // Reuse an already-running dev server if present.
  if (await waitForServer(baseUrl, 2000)) return { baseUrl, proc: null };

  // Boot an ephemeral one.
  const proc = spawn("npm", ["run", "dev", "--", "--port", String(PORT)], {
    cwd: SITE_DIR,
    stdio: "ignore",
    detached: false,
  });
  const ok = await waitForServer(baseUrl, 60000);
  if (!ok) {
    try {
      proc.kill("SIGTERM");
    } catch {
      /* noop */
    }
    throw new Error(`dev server never came up on ${baseUrl}`);
  }
  return { baseUrl, proc };
}

// ---- layout invariants ----------------------------------------------------
// Deterministic DOM assertions for defect classes that are visual but
// MEASURABLE — so a regression can't reship on the strength of a screenshot
// nobody looked at. Each invariant runs in-page and returns finding strings.
// Add new invariants here as the site-health-sentinel agent finds recurring,
// measurable defects.
async function checkLayoutInvariants(page) {
  return page.evaluate(() => {
    const out = [];

    // INV-1: multi-volume "series deck" stacked-card. The ::before/::after
    // sheets are inset:0 on the deck; if the front <summary> is materially
    // shorter than the deck (a short card stretched in a tall grid row), the
    // sheets protrude below as an empty panel. Fixed by making the summary fill
    // the cell — assert the leftover gap stays within the intended ~12px peek.
    for (const deck of document.querySelectorAll(
      ".studio-series-deck:not([open])",
    )) {
      const summary = deck.querySelector(".studio-series-summary");
      if (!summary) continue;
      const gap = Math.round(deck.clientHeight - summary.offsetHeight);
      if (gap > 24) {
        const name = (
          summary.querySelector(".card-title-en")?.textContent || ""
        ).trim();
        out.push(
          `series-deck-protrusion: "${name || "deck"}" — front card ${gap}px shorter than its cell (stacked sheets protrude as an empty panel)`,
        );
      }
    }

    return out;
  });
}

// ---- per-route probe ------------------------------------------------------
async function probeRoute(context, baseUrl, route) {
  const page = await context.newPage();
  const findings = [];
  const url = baseUrl + route.path;

  page.on("console", (msg) => {
    if (msg.type() !== "error") return;
    const text = msg.text();
    if (isBenign(text)) return;
    findings.push({ kind: "console-error", detail: text });
  });
  page.on("pageerror", (err) => {
    findings.push({
      kind: "uncaught-exception",
      detail: String((err && err.message) || err),
    });
  });
  page.on("requestfailed", (req) => {
    const failure = req.failure();
    const reason = failure ? failure.errorText : "unknown";
    if (reason === "net::ERR_ABORTED") return; // navigations/cancellations
    if (isBenign(req.url())) return;
    findings.push({
      kind: "request-failed",
      detail: `${req.url()} — ${reason}`,
    });
  });
  page.on("response", (res) => {
    const s = res.status();
    if (s >= 500 && !isBenign(res.url())) {
      findings.push({ kind: "http-5xx", detail: `${s} ${res.url()}` });
    }
  });

  let navStatus = null;
  let skipped = false;
  try {
    const resp = await page.goto(url, {
      waitUntil: "networkidle",
      timeout: 30000,
    });
    navStatus = resp ? resp.status() : null;
    // Let client islands mount + throw if they're going to.
    await page.waitForTimeout(700);
    // Deterministic layout invariants (measurable visual defects).
    for (const detail of await checkLayoutInvariants(page)) {
      findings.push({ kind: "layout-invariant", detail });
    }
  } catch (err) {
    findings.push({
      kind: "navigation-error",
      detail: String((err && err.message) || err),
    });
  }

  // A 4xx on a tier-2 detail route means our fixture slug didn't match this
  // surface's expectations — that's a test-fixture gap, not a site bug. Skip it,
  // but keep any console/exception/5xx findings that fired anyway.
  if (route.tier === 2 && navStatus && navStatus >= 400 && navStatus < 500) {
    skipped = true;
  }
  // A 4xx on a tier-1 fixture-free route IS a real failure.
  if (route.tier === 1 && navStatus && navStatus >= 400) {
    findings.push({ kind: `http-${navStatus}`, detail: `${navStatus} ${url}` });
  }

  await page.close();
  return { route: route.path, tier: route.tier, navStatus, skipped, findings };
}

// ---- main -----------------------------------------------------------------
async function main() {
  const slug = discoverSlug();
  const routes = buildRoutes(slug);
  if (!routes.length) {
    console.error(
      "site-health-smoke: no routes to probe (bad --route filter?)",
    );
    process.exit(1);
  }

  const { baseUrl, proc } = await ensureServer();
  const browser = await chromium.launch({ headless: true });
  const results = [];
  try {
    // Sweep at desktop; the agent handles the mobile/state matrix visually.
    const context = await browser.newContext({
      viewport: { width: 1440, height: 900 },
    });
    for (const route of routes) {
      results.push(await probeRoute(context, baseUrl, route));
    }
    await context.close();
  } finally {
    await browser.close();
    if (proc) {
      try {
        proc.kill("SIGTERM");
      } catch {
        /* noop */
      }
    }
  }

  const failed = results.filter((r) => !r.skipped && r.findings.length);
  const skipped = results.filter((r) => r.skipped);
  const clean = results.filter((r) => !r.skipped && !r.findings.length);

  if (JSON_OUT) {
    console.log(
      JSON.stringify(
        {
          baseUrl,
          slug,
          total: results.length,
          clean: clean.length,
          skipped: skipped.length,
          failed: failed.length,
          results,
        },
        null,
        2,
      ),
    );
  } else {
    console.log(
      `\nsite-health-smoke — ${baseUrl}  (fixture slug: ${slug || "none"})`,
    );
    console.log(
      `  ${clean.length} clean · ${skipped.length} skipped (fixture gap) · ${failed.length} FAILED\n`,
    );
    for (const r of clean)
      console.log(`  ✓ ${r.route}  [${r.navStatus ?? "—"}]`);
    for (const r of skipped)
      console.log(`  – ${r.route}  [${r.navStatus}] skipped: fixture mismatch`);
    for (const r of failed) {
      console.log(`  ✗ ${r.route}  [${r.navStatus ?? "—"}]`);
      for (const f of r.findings) console.log(`      ${f.kind}: ${f.detail}`);
    }
    console.log("");
  }

  process.exit(failed.length ? 1 : 0);
}

main().catch((err) => {
  console.error("site-health-smoke: fatal —", (err && err.message) || err);
  process.exit(1);
});
