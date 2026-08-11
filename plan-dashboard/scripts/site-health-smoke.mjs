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
import { homedir } from "node:os";
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

// Rolling capture of the ephemeral dev server's stdout+stderr. Printed only when
// a route fails — a 5xx is the server's exception, and without this the report
// can name the URL but never the cause.
const serverLog = [];
const SERVER_LOG_MAX = 400;
const serverLogTail = (lines = 60) =>
  serverLog.join("").split("\n").slice(-lines).join("\n").trim();

// Console-error / failed-request patterns that are known-benign in dev and must
// NOT fail the gate. Keep this list SHORT and justified — every entry is a
// blind spot. Anything not matched here is a real finding.
const BENIGN = [
  // `favicon.ico` was suppressed here until 2026-08-02, when a favicon was
  // actually wired (public/favicon.svg, declared in both layouts). The entry is
  // GONE rather than kept harmlessly: an undeclared icon is now a real
  // regression — every page would resume 404ing on it — and this gate should be
  // the thing that says so.
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
  // Pinned to scripts/podcast/_content_types.py::BUCKETS by
  // tests/test_snapshot_regenerator_parity.py. A bucket missing here is a bucket
  // whose books can never be chosen as the smoke fixture, so its routes go unvisited.
  const buckets = [
    "Islamic",
    "Technical",
    "Fiction",
    "Guides",
    "Supplications",
    "Sessions",
  ];
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

// The wisdom leaf (`/wisdom/<shelf>/<book>`) reads a corpus that is NOT part of
// a book bucket and is absent on some checkouts (`content/_shared/wisdom-corpus/`
// does not exist on every machine). Returning null when there is no corpus is
// deliberate: the route is then omitted from the sweep entirely rather than
// added as a permanent "skipped (fixture gap)" line, which would train the eye
// to ignore a skip that is sometimes real. Where the corpus IS present the leaf
// gets gated like any other detail view.
// Path mirrors `EXTRACT_RELPATH` in src/lib/reader/source-extractor.ts.
function discoverWisdomLeaf() {
  const root = join(CONTENT_DIR, "_shared", "wisdom-corpus", "extracted");
  if (!existsSync(root)) return null;
  const dirs = (p) => {
    try {
      return readdirSync(p, { withFileTypes: true })
        .filter((e) => e.isDirectory() && !e.name.startsWith("_"))
        .map((e) => e.name);
    } catch {
      return [];
    }
  };
  for (const source of dirs(root)) {
    for (const shelf of dirs(join(root, source))) {
      for (const book of dirs(join(root, source, shelf))) {
        // findChapter() resolves via loadManifest(), which reads `bundle.yml`;
        // a directory without one 404s by design and is not a fixture.
        if (existsSync(join(root, source, shelf, book, "bundle.yml"))) {
          return { shelf, book };
        }
      }
    }
  }
  return null;
}

/**
 * A plan slug from `~/.claude/plans/`, or null when this checkout has none.
 *
 * Same fixture-conditional shape as discoverWisdomLeaf() above, for the same
 * reason: `/claude-plans/[slug]` reads a MACHINE-GLOBAL directory that lives
 * outside the repo entirely, so it is populated on Asif's machine and empty on
 * every CI runner. Gating it unconditionally would fail a runner for a file it
 * cannot have; leaving it out of the manifest entirely left it unswept from the
 * day it shipped. Discovered, so the sweep covers it exactly where it is real.
 *
 * Mirrors readPlanFiles() in src/lib/claude-plans.ts — top level plus ONE level
 * of subdirectory (the harness's `_done/` archive), slug = filename minus `.md`.
 * Walked with `fs` rather than imported because that module is TypeScript and
 * this script is plain `.mjs`; the wisdom leaf resolves the same way.
 */
function discoverPlanLeaf() {
  const root = join(homedir(), ".claude", "plans");
  if (!existsSync(root)) return null;
  let entries;
  try {
    entries = readdirSync(root, { withFileTypes: true });
  } catch {
    return null;
  }
  for (const entry of entries) {
    if (entry.isFile() && entry.name.endsWith(".md"))
      return entry.name.slice(0, -3);
  }
  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    try {
      for (const sub of readdirSync(join(root, entry.name))) {
        if (sub.endsWith(".md")) return sub.slice(0, -3);
      }
    } catch {
      // unreadable subdirectory — skip it, exactly as the page does.
    }
  }
  return null;
}

// ---- route manifest -------------------------------------------------------
// tier1 = fixture-free views that must ALWAYS render clean (the architecture
//         views + top-level app index pages).
// tier2 = detail views that need a live fixture; a 4xx here means the fixture
//         didn't match (skipped, not failed) — but console/page errors and 5xx
//         still fail, because those are real runtime bugs.
export function buildRoutes(slug) {
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
    // Root-first morphology explorer under the Corpus domain (shipped 2026-07-28,
    // commit 4aa8928). Fixture-free: it opens the committed morphology.db /
    // lexicon.jsonl readonly and degrades to an empty state, so it must ALWAYS
    // render clean — tier 1, not tier 2.
    "/corpus/morphology",
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
    "/snag-list",
    "/claude-plans",
  ].map((path) => ({ path, tier: 1 }));

  // Routes that legitimately redirect, and where to. Declared rather than
  // inferred: a route that redirects somewhere UNDECLARED is the failure mode
  // this exists to catch — on 2026-07-26 an unresolvable CSS import made the
  // Composer answer 302 to /edit, and because the browser follows redirects the
  // check reported the route clean while the page was unreachable.
  const EXPECTED_REDIRECTS = {
    "/library": "/studio",
    [`/library/${slug}`]: `/studio/${slug}`,
    // Retired 2026-07-21; the Composer's Arabic drawer holds both its panels.
    [`/studio/${slug}/arabic-review`]: `/studio/${slug}/compose`,
    // Retired 2026-08-01; the Composer's Read mode carries the reading view.
    [`/studio/${slug}/live`]: `/studio/${slug}/compose`,
    [`/studio/${slug}/book`]: `/studio/${slug}/compose`,
    [`/studio/${slug}/view`]: `/studio/${slug}`,
    [`/pre-upload/${slug}`]: "/pre-upload",
  };

  const wisdom = discoverWisdomLeaf();

  const tier2 = slug
    ? [
        `/library/${slug}`,
        `/studio/${slug}`,
        // The four sequential pipeline steps `[step].astro` serves
        // (STUDIO_STEPS in src/lib/reader/studio-pipeline.ts). Only `edit` was
        // listed until 2026-07-28, so three live surfaces — each mounting its own
        // island stack — were never gated. `[step].astro` bounces an UNKNOWN step
        // to `/edit`, which is why a missing entry here never showed up as a 404.
        `/studio/${slug}/intake`,
        `/studio/${slug}/review`,
        `/studio/${slug}/edit`, // the default Edit & Enrich rich-editor island (blank-island blind spot)
        `/studio/${slug}/publish`,
        `/studio/${slug}/compose`,
        `/studio/${slug}/book`,
        // `/studio/<slug>/live` (the LIVE Session) was retired 2026-08-01 and now
        // 302s to the Composer, whose Read mode carries the reading view. STAYS in
        // this list for the same reason arabic-review below does: the browser
        // follows the redirect, so a pass proves it still lands somewhere that
        // renders. Without the redirect the path would fall through to
        // `[step].astro` and bounce to `/edit` — a different deliverable's editor.
        `/studio/${slug}/live`,
        `/studio/${slug}/preview`, // whole-book page-image preview (renders fresh from book.md on demand)
        // `/studio/<slug>/arabic-review` was retired 2026-07-21 and now 302s to
        // the Composer, whose new Arabic drawer surface holds both of its panels.
        // The entry STAYS in this list on purpose: the browser follows the
        // redirect, so a pass here proves the redirect still lands somewhere that
        // renders clean rather than proving a page exists. Same reasoning as the
        // `/style` removal below, one step further — that route reached the
        // Composer's Citations tab; this one reached book.md itself.
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

  // Present only where the wisdom corpus is on disk — see discoverWisdomLeaf().
  const tier2Wisdom = wisdom
    ? [{ path: `/wisdom/${wisdom.shelf}/${wisdom.book}`, tier: 2 }]
    : [];

  // Present only where `~/.claude/plans/` holds a plan — see discoverPlanLeaf().
  const planSlug = discoverPlanLeaf();
  const tier2Plans = planSlug
    ? [{ path: `/claude-plans/${encodeURIComponent(planSlug)}`, tier: 2 }]
    : [];

  const all = [...tier1, ...tier2, ...tier2Wisdom, ...tier2Plans].map((r) =>
    EXPECTED_REDIRECTS[r.path]
      ? { ...r, redirectsTo: EXPECTED_REDIRECTS[r.path] }
      : r,
  );
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
  // Reuse an already-running dev server if present. Nothing is captured in that
  // case — the output belongs to whoever started it, and it is on their terminal.
  if (await waitForServer(baseUrl, 2000)) return { baseUrl, proc: null };

  // Boot an ephemeral one.
  //
  // stdio was "ignore", which threw away the ONE thing that explains a 5xx: the
  // server's own stack trace. On 2026-08-01 five Studio routes 500'd on the CI
  // runner and nowhere else, and the log could say only "500" — not reproducible
  // on the author's machine from a fresh clone, so there was no other way to see
  // the exception. Captured into a bounded buffer and printed only when a route
  // actually fails, so a green run stays quiet.
  const proc = spawn("npm", ["run", "dev", "--", "--port", String(PORT)], {
    cwd: SITE_DIR,
    stdio: ["ignore", "pipe", "pipe"],
    detached: false,
  });
  const collect = (stream) => {
    if (!stream) return;
    stream.setEncoding("utf8");
    stream.on("data", (chunk) => {
      serverLog.push(chunk);
      // Keep the tail, not the whole build: a dev server is chatty at boot and
      // the interesting lines are always the most recent ones.
      while (serverLog.length > SERVER_LOG_MAX) serverLog.shift();
    });
  };
  collect(proc.stdout);
  collect(proc.stderr);

  const ok = await waitForServer(baseUrl, 60000);
  if (!ok) {
    try {
      proc.kill("SIGTERM");
    } catch {
      /* noop */
    }
    throw new Error(
      `dev server never came up on ${baseUrl}\n${serverLogTail() || "(no server output captured)"}`,
    );
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
  // INV-1..4 measure the 1440px layout this gate navigates at; INV-5 below
  // re-measures at phone width, so the desktop findings are collected first and
  // the two sets are returned together.
  const out = await page.evaluate(() => {
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

    // INV-2: the Book Composer's floating button row (.cx-fabs) is fixed over the
    // drawer's bottom-right corner and the drawer is sticky, so once the page
    // scrolls the two are pinned together — and whatever sits at the END of a
    // panel's scroll ends up UNDER the buttons, where no further scrolling can
    // reveal it. Each drawer scroller reserves --cx-fab-clear after its content
    // (book-composer.css); this asserts the reserve is actually enough, measured
    // at the one position where it matters: the bottom of the scroll.
    const fabs = document.querySelector(".cx-fabs");
    if (fabs && getComputedStyle(fabs).position === "fixed") {
      window.scrollTo(0, 600); // put the sticky drawer in its steady state
      const f = fabs.getBoundingClientRect();
      const scrollers = document.querySelectorAll(
        ".cx-tabpanel:not([hidden]), #cx-surface-companion:not([hidden]), #cx-surface-scholar:not([hidden])",
      );
      for (const sc of scrollers) {
        if (!sc.clientHeight || sc.scrollHeight <= sc.clientHeight) continue;
        sc.scrollTop = sc.scrollHeight;
        const last = sc.lastElementChild;
        if (!last) continue;
        const r = last.getBoundingClientRect();
        const covered = Math.round(
          Math.min(r.bottom, f.bottom) - Math.max(r.top, f.top),
        );
        if (covered > 0 && r.right > f.left && r.left < f.right) {
          out.push(
            `composer-fab-covers-panel-tail: #${sc.id || sc.className} — the last ${covered}px of its scroll sits under the floating button row`,
          );
        }
      }
      window.scrollTo(0, 0);
    }

    // INV-3: REQ-015 list rendering, on the prose hosts that render the shared
    // read-only renderer's output. Tailwind's preflight sets `list-style: none`
    // with no padding on every ol/ul, so a host that does not RESTORE both ships
    // a real <ol> with invisible markers and zero indent — the enumeration is
    // simply gone, and the DOM looks perfectly correct while the page does not.
    // That is how it escaped review: `.src-view-prose` was fixed and `.se-prose`
    // (the Urdu bilingual dual-panel, same renderer) was not, because only the
    // first was screenshotted. Measured from computed style so it holds for any
    // host, in either writing direction.
    // It asserts the STYLESHEET contract, with a canary list it inserts and
    // removes, rather than waiting for a host to happen to contain a list: the
    // thing that regresses is the CSS, and a check that only fires when live
    // content includes an enumeration is a check that was dormant on exactly the
    // day the reset landed. Any list already present is measured in preference
    // to the canary, so real content is judged when it is there.
    //
    // SELF-CALIBRATION, and it is load-bearing: in dev the page can be served in
    // the window after a stylesheet write and before Vite has re-applied it, and
    // in that window EVERY computed-style assertion legitimately reads unstyled
    // values. This check ran flaky for exactly that reason — twice, both times in
    // the run right after a CSS edit, which is precisely when the turn-end hook
    // runs it. So the reset itself is the readiness signal: a bare <ol> outside
    // any prose host must compute `list-style-type: none`, because that is what
    // Tailwind's preflight does. If it computes the UA default instead, no CSS is
    // in effect yet and the invariant ABSTAINS rather than reporting a defect it
    // cannot distinguish from a cold stylesheet. The assertion that survives is
    // the true one: the reset is applied AND the restore is missing.
    const probe = document.createElement("ol");
    probe.style.position = "absolute";
    probe.style.visibility = "hidden";
    probe.innerHTML = "<li>probe</li>";
    document.body.appendChild(probe);
    const resetApplied = getComputedStyle(probe).listStyleType === "none";
    probe.remove();

    // Every host that renders either shared renderer's output. Deliberately
    // includes hosts NOT yet known to be broken: listing only the three that were
    // already fixed would let this check confirm the fix and never find the next
    // instance — which is precisely how `.se-prose` and `.bookv-body` each shipped
    // unmarked lists after the sibling host was repaired.
    // Every host that renders markdown prose. `.cx-prose` — the Book Composer's
    // EDIT canvas — was added 2026-07-26 as the sixth: it had never carried the
    // marker reset, and this check could not have found that while it listed
    // only hosts already repaired. Add a host here the moment one is created.
    const PROSE_HOSTS =
      ".src-view-prose, .se-prose, .cx-podcast-body, .bookv-body, .cx-body, .cx-prose";
    for (const host of resetApplied
      ? document.querySelectorAll(PROSE_HOSTS)
      : []) {
      let list = host.querySelector("ol, ul");
      let canary = null;
      if (!list) {
        // A SIBLING stand-in carrying the host's own classes, never a child of
        // the live host: one of these hosts is the Book Composer's, and nothing
        // in a read-only gate should insert nodes into the Composer's subtree.
        // Same parent chain and same class list, so ancestor-scoped list rules
        // (and any override of them) still apply.
        canary = document.createElement(host.tagName);
        canary.className = host.className;
        canary.style.position = "absolute";
        canary.style.visibility = "hidden";
        canary.innerHTML = "<ol><li>canary</li></ol>";
        host.parentElement?.appendChild(canary);
        list = canary.firstElementChild;
        if (!list) {
          canary.remove();
          continue;
        }
      }
      const s = getComputedStyle(list);
      const pad = parseFloat(s.paddingInlineStart) || 0;
      const why = [];
      if (s.listStyleType === "none")
        why.push("list-style-type is none (markers invisible)");
      if (pad < 28) why.push(`padding-inline-start ${pad}px < 1.75rem`);
      if (s.listStylePosition !== "outside")
        why.push(`list-style-position ${s.listStylePosition}, not outside`);
      canary?.remove();
      if (why.length) {
        const where = (host.className || host.id || "prose host")
          .toString()
          .trim();
        out.push(
          `prose-list-unstyled: ${canary ? "canary" : "live"} <${list.tagName.toLowerCase()}> in "${where}" — ${why.join("; ")} (REQ-015)`,
        );
      }
    }

    // INV-6: a hover popover swallowed by an ancestor's `overflow: hidden`.
    // Found twice on 2026-08-06, from the same cause each time: a card that
    // clips itself ONLY to keep a decorative ::before glow inside its rounded
    // corners, and takes every popover anchored inside it down with the glow.
    // /infrastructure's vendor cost cards cut the per-service tooltip to a
    // ~20px black sliver (up to 353px of it gone), and /plan's wave bands cut
    // the .step-hover-card on the LAST step of every expanded wave to its
    // heading. Neither is visible until something is HOVERED, which is why the
    // screenshots looked clean — so this measures geometry against the clipping
    // ancestor rather than waiting for a hover state to be captured.
    // The popover need not be visible right now: it is positioned at author
    // time, so the overhang is measurable in its resting state too.
    const POPOVERS = ".hover-tip, .step-hover-card, [role='tooltip']";
    for (const tip of document.querySelectorAll(POPOVERS)) {
      const tb = tip.getBoundingClientRect();
      if (tb.width < 1 || tb.height < 1) continue;
      let clipper = null;
      for (
        let a = tip.parentElement;
        a && a !== document.body;
        a = a.parentElement
      ) {
        const cs = getComputedStyle(a);
        if (/(hidden|clip)/.test(cs.overflow + cs.overflowX + cs.overflowY)) {
          clipper = a;
          break;
        }
      }
      if (!clipper) continue;
      const ab = clipper.getBoundingClientRect();
      const lost = Math.round(
        Math.max(
          tb.bottom - ab.bottom,
          ab.top - tb.top,
          tb.right - ab.right,
          ab.left - tb.left,
        ),
      );
      if (lost <= 2) continue;
      const who = (tip.className || tip.tagName).toString().split(" ")[0];
      const by = (clipper.className || clipper.tagName)
        .toString()
        .split(" ")[0];
      out.push(
        `popover-clipped-by-ancestor: .${who} loses ${lost}px to .${by}'s overflow (the tooltip is unreadable once opened)`,
      );
    }

    // INV-4 asserted the same overlap as INV-2 one surface over: the LIVE
    // Session's sticky companion panel against the site-wide back-to-top
    // control. It went with that route on 2026-08-01. Not re-pointed at the
    // Composer's Scholar panel, which is a DOCKED drawer rather than a sticky
    // corner element and so cannot reproduce the failure — a check rewritten to
    // pass by construction is worse than no check. INV-2 still guards the
    // corner-overlap class of defect on the surfaces that can exhibit it.

    return out;
  });

  // INV-5: a control that no scroll can reach at PHONE width. Every other
  // invariant here runs at the 1440px viewport this gate uses, which is exactly
  // why this class kept shipping: a fixed-width control inside a container that
  // CLIPS rather than scrolls looks perfect at desktop and simply has no right
  // half on a phone. Two shipped that way during the 2026-07-27..08-01 CI outage
  // — the Composer's view-preference cluster (nowrap, 610px of controls in a
  // 340px column, so the Paper picker and "Show changes" were gone) and the LIVE
  // Session's book/chapter pickers (a flat `width: 18rem` pushing their own
  // chevrons past the card border and off the screen).
  //
  // The discriminator is REACHABILITY, not overflow. This site uses horizontal
  // scrollers deliberately and often — the top nav's sections, the architecture
  // subnav rail, the studio step-stepper, the library tab strip — and every one
  // of those legitimately extends past 390px. So an off-screen control is only a
  // finding when NO ancestor can scroll it back into view. Measured that way it
  // reported zero across all 33 page routes with the two fixes in, and exactly
  // those two with them reverted.
  const restore = page.viewportSize();
  await page.setViewportSize({ width: 390, height: 844 });
  // Reflow + any width-driven island re-render before measuring.
  await page.waitForTimeout(400);
  const narrow = await page.evaluate(() => {
    const W = document.documentElement.clientWidth;
    const out = [];
    for (const el of document.querySelectorAll(
      "button, select, input, textarea, a[href]",
    )) {
      const cs = getComputedStyle(el);
      if (cs.visibility === "hidden" || cs.display === "none") continue;
      // offsetParent is null for a fixed element as well as a hidden one.
      if (el.offsetParent === null && cs.position !== "fixed") continue;
      const rc = el.getBoundingClientRect();
      if (rc.width < 1 || rc.height < 1) continue;
      if (rc.right <= W + 1 && rc.left >= -1) continue;
      let reachable = false;
      for (let a = el.parentElement; a; a = a.parentElement) {
        const acs = getComputedStyle(a);
        if (
          /(auto|scroll)/.test(acs.overflowX) &&
          a.scrollWidth > a.clientWidth + 1
        ) {
          reachable = true;
          break;
        }
      }
      if (reachable) continue;
      const label = (
        el.textContent ||
        el.getAttribute("aria-label") ||
        el.getAttribute("placeholder") ||
        ""
      )
        .replace(/\s+/g, " ")
        .trim()
        .slice(0, 28);
      const cls = (el.className || "").toString().split(" ")[0] || el.tagName;
      out.push(
        `${cls} "${label}" spans [${Math.round(rc.left)},${Math.round(rc.right)}] of a ${W}px viewport`,
      );
    }
    return out;
  });
  if (restore) await page.setViewportSize(restore);
  for (const n of narrow) {
    out.push(`control-unreachable-at-390px: ${n} — no scrollable ancestor`);
  }

  return out;
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
    // A route that REDIRECTS AWAY is not a healthy route, but page.goto follows
    // the redirect and reports the destination's 200 — so the check passed while
    // the requested page was in fact unreachable. That is exactly how a broken
    // /studio/<slug>/compose (an unresolvable CSS import, answered with a 302 to
    // /edit) was reported clean on 2026-07-26. Compare the landed path with the
    // one asked for; query strings and a trailing slash are not a redirect.
    const landed = new URL(page.url()).pathname.replace(/\/$/, "");
    const asked = new URL(url).pathname.replace(/\/$/, "");
    const allowed = (route.redirectsTo ?? "").replace(/\/$/, "");
    if (landed !== asked && landed !== allowed) {
      findings.push({
        kind: "unexpected-redirect",
        detail: allowed
          ? `asked for ${asked}, expected ${allowed}, landed on ${landed}`
          : `asked for ${asked}, landed on ${landed} (no redirect declared)`,
      });
    }
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
    // The server's own words. Only on failure, and only when this run booted the
    // server — a reused one logs to its owner's terminal, not here.
    const tail = serverLogTail();
    if (failed.length && tail) {
      console.log(
        "  ── dev server output (tail) ─────────────────────────────",
      );
      for (const line of tail.split("\n")) console.log(`  ${line}`);
      console.log("");
    }
  }

  process.exit(failed.length ? 1 : 0);
}

// Run the sweep ONLY when executed directly. The route manifest above is also
// imported by site-health-routes.test.mjs, which asserts it still covers every
// page in src/pages/ — without this guard that import would boot a browser.
const isDirectRun =
  process.argv[1] &&
  resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (isDirectRun) {
  main().catch((err) => {
    console.error("site-health-smoke: fatal —", (err && err.message) || err);
    process.exit(1);
  });
}
