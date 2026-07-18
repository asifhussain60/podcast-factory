#!/usr/bin/env node
// site-health-shots.mjs — screenshot capture primitive for the
// `site-health-sentinel` agent's visual-QA loop. Given a route, it captures
// full-page PNGs at a desktop (~1440px) and a mobile (~390px) width into a
// throwaway folder, so the agent can Read the images back and judge them
// against real pixels (never from memory).
//
// It complements site-health-smoke.mjs: smoke = deterministic console-error
// gate; shots = the visual-defect evidence the agent looks at.
//
// Only Playwright (already installed). No new dependencies.
//
// Usage:
//   node scripts/site-health-shots.mjs --route /plan --out .visual-qa
//   node scripts/site-health-shots.mjs --route /studio/SLUG/compose --out .visual-qa --label compose
//   node scripts/site-health-shots.mjs --route /studio/SLUG/book --out .visual-qa \
//        --eval "document.querySelector('.cx-edit-toggle')?.click()" --label book-edit --settle 900
//   node scripts/site-health-shots.mjs --route /plan --out .visual-qa --theme dark
//   node scripts/site-health-shots.mjs --route /plan --out .visual-qa --width 1440 --only desktop
//
// Env: SITE_HEALTH_BASE_URL (default http://localhost:4322).
//
// Prints the exact path of every PNG it writes (one per line) so the caller can
// track files for precise cleanup.

import { mkdirSync } from "node:fs";
import { resolve, join } from "node:path";
import { chromium } from "playwright";

const argv = process.argv.slice(2);
const opt = (name, def = null) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && argv[i + 1] && !argv[i + 1].startsWith("--")
    ? argv[i + 1]
    : def;
};

const BASE = (
  process.env.SITE_HEALTH_BASE_URL || "http://localhost:4322"
).replace(/\/$/, "");
const route = opt("route");
const outDir = resolve(opt("out", ".visual-qa"));
const label = opt(
  "label",
  (route || "root").replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "") ||
    "root",
);
const evalJs = opt("eval");
const theme = opt("theme", "light"); // light | dark
const settle = Number(opt("settle", 700));
const desktopW = Number(opt("width", 1440));
const mobileW = Number(opt("mobile-width", 390));
const only = opt("only"); // desktop | mobile | (both)

if (!route) {
  console.error("site-health-shots: --route is required");
  process.exit(1);
}

const viewports = [];
if (only !== "mobile")
  viewports.push({ name: "desktop", width: desktopW, height: 900 });
if (only !== "desktop")
  viewports.push({ name: "mobile", width: mobileW, height: 844 });

async function shoot(browser, vp) {
  const context = await browser.newContext({
    viewport: { width: vp.width, height: vp.height },
    colorScheme: theme === "dark" ? "dark" : "light",
  });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String((e && e.message) || e)));
  await page.goto(BASE + route, { waitUntil: "networkidle", timeout: 30000 });
  // This site is prefers-color-scheme driven (theme.css @media blocks) — the
  // context colorScheme above is the real trigger. Stamp data-theme too as a
  // belt-and-suspenders for any reader/studio view that also honours it.
  await page.evaluate(
    (t) => document.documentElement.setAttribute("data-theme", t),
    theme,
  );
  if (evalJs) {
    try {
      await page.evaluate(evalJs);
    } catch (e) {
      errors.push(`eval: ${e.message}`);
    }
  }
  await page.waitForTimeout(settle);
  mkdirSync(outDir, { recursive: true });
  const file = join(outDir, `${label}--${vp.name}--${theme}.png`);
  await page.screenshot({ path: file, fullPage: true });
  console.log(file);
  if (errors.length)
    console.error(`  [pageerror on ${vp.name}] ${errors.join(" | ")}`);
  await context.close();
}

const browser = await chromium.launch({ headless: true });
try {
  for (const vp of viewports) await shoot(browser, vp);
} finally {
  await browser.close();
}
