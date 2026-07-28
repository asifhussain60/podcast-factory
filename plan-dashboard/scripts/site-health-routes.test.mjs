// site-health-routes.test.mjs — the route manifest may not drift from the pages.
//
// WHY THIS EXISTS. `buildRoutes()` in site-health-smoke.mjs is maintained by
// hand, and on 2026-07-28 the cost of that showed up all at once: `/corpus/
// morphology` had shipped that morning and was ungated, and three of the four
// `[step].astro` surfaces (`intake`, `review`, `publish`) had NEVER been gated —
// invisibly, because `[step].astro` redirects an unknown step to `/edit`, so a
// missing manifest entry could never surface as a 404. The gate reported "32
// clean" the whole time and was telling the truth about the routes it knew.
//
// A hand-maintained list drifts again the next time a page lands. This test is
// the thing that makes the next omission loud: add a page, gate it, or declare
// in NON_VIEW below why it is not a view. There is no fourth option.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve, relative, sep } from "node:path";
import { buildRoutes } from "./site-health-smoke.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PAGES_DIR = resolve(__dirname, "..", "src", "pages");

// Files under src/pages/ that are NOT views. Every entry needs a reason — each
// one is a hole in the sweep, so an unexplained addition here is a defect.
const NON_VIEW = new Map([
  [
    "studio/[slug]/arabic-review.ts",
    "Retired 2026-07-21: a 302 endpoint, not a page. The REDIRECT is still gated " +
      "as a tier-2 route (it must still land on a Composer that renders clean).",
  ],
]);

// Dynamic segments whose domain is finite and known. A wildcard match would let
// `[step]` pass on the strength of one gated step while three went unswept —
// exactly the 2026-07-28 miss. Listing the domain forces all of them to be gated.
const FINITE_PARAMS = new Map([
  // STUDIO_STEPS in src/lib/reader/studio-pipeline.ts
  ["studio/[slug]/[step].astro", { param: "[step]", values: ["intake", "review", "edit", "publish"] }],
]);

// Routes that are gated only when their fixture exists on this checkout. The
// wisdom corpus (content/_shared/wisdom-corpus/) is absent on some machines;
// discoverWisdomLeaf() omits the leaf rather than emitting a permanent skip.
const FIXTURE_CONDITIONAL = new Set(["wisdom/[shelf]/[book].astro"]);

/** Every file under src/pages/, excluding the api/ tree (endpoints, not views). */
function pageFiles(dir = PAGES_DIR, acc = []) {
  for (const entry of readdirSync(dir)) {
    const abs = join(dir, entry);
    if (statSync(abs).isDirectory()) {
      if (relative(PAGES_DIR, abs).split(sep)[0] === "api") continue;
      pageFiles(abs, acc);
    } else if (/\.(astro|ts)$/.test(entry)) {
      acc.push(relative(PAGES_DIR, abs).split(sep).join("/"));
    }
  }
  return acc;
}

/** `library/[slug].astro` -> /^\/library\/[^/]+$/ ; `index.astro` -> /^\/$/ */
function routeMatcher(rel, substitutions = {}) {
  let p = rel.replace(/\.(astro|ts)$/, "");
  p = p.replace(/(^|\/)index$/, "");
  const body = p
    .split("/")
    .filter(Boolean)
    .map((seg) =>
      seg.startsWith("[")
        ? (substitutions[seg] ?? "[^/]+")
        : seg.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"),
    )
    .join("/");
  return new RegExp(`^/${body}$`);
}

test("every page under src/pages/ is covered by the site-health route manifest", () => {
  // A slug with no special characters — the manifest interpolates it verbatim.
  const paths = buildRoutes("fixture-slug").map((r) => r.path);
  const uncovered = [];

  for (const rel of pageFiles()) {
    if (NON_VIEW.has(rel)) continue;
    if (FIXTURE_CONDITIONAL.has(rel)) continue;

    const finite = FINITE_PARAMS.get(rel);
    if (finite) {
      for (const value of finite.values) {
        const re = routeMatcher(rel, { [finite.param]: value });
        if (!paths.some((p) => re.test(p))) {
          uncovered.push(`${rel}  (${finite.param}="${value}")`);
        }
      }
      continue;
    }

    const re = routeMatcher(rel);
    if (!paths.some((p) => re.test(p))) uncovered.push(rel);
  }

  assert.deepEqual(
    uncovered,
    [],
    "These pages render but are never visited by `npm run smoke`. Add each to " +
      "buildRoutes() in site-health-smoke.mjs, or declare it in NON_VIEW / " +
      "FIXTURE_CONDITIONAL here with the reason:\n  " +
      uncovered.join("\n  "),
  );
});

test("the manifest names no route that has no page behind it", () => {
  // The mirror direction. `/studio/<slug>/style` sat in the sentinel's prose
  // manifest for nine days after the page was deleted on 2026-07-19; this is
  // what would have caught it.
  const files = pageFiles();
  const matchers = files.map((rel) => {
    const finite = FINITE_PARAMS.get(rel);
    if (!finite) return routeMatcher(rel);
    // Any of the finite values is enough to prove the page exists.
    return new RegExp(
      finite.values
        .map((v) => routeMatcher(rel, { [finite.param]: v }).source)
        .join("|"),
    );
  });

  const orphans = buildRoutes("fixture-slug")
    .map((r) => r.path)
    .filter((p) => !matchers.some((re) => re.test(p)));

  assert.deepEqual(
    orphans,
    [],
    `The manifest gates routes with no page in src/pages/: ${orphans.join(", ")}`,
  );
});
