#!/usr/bin/env node
// check-frontend-ratchets.mjs — the two gates this app never had (2026-08-16
// repo audit: CQ-NO-LINT, CQ-NO-SIZE-GATE).
//
// Adapted from plan-dashboard/scripts/check-frontend-ratchets.mjs — same shape,
// scoped to this app's own targets and its own baseline file. NOT shared code:
// this app "imports NOTHING from plan-dashboard/ at runtime" (CLAUDE.md) and
// that boundary holds for dev tooling too, so each app owns its own copy rather
// than one reaching into the other's scripts/ directory.
//
// Both gates are RATCHETS, the same shape as infra/git-hooks/check-dr005.py:
// today's numbers are the baseline, they may shrink, and they may never grow.
//
//   node scripts/check-frontend-ratchets.mjs           # gate (exit 1 on regression)
//   node scripts/check-frontend-ratchets.mjs --update  # re-baseline AFTER improving
//
// --update only ever writes numbers that are better than or equal to the
// recorded ones; it refuses to record a regression, so it cannot be used to make
// a red gate green.

import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve, relative, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const APP_DIR = resolve(__dirname, "..");
const BASELINE = join(APP_DIR, "frontend-ratchets.json");
const UPDATE = process.argv.includes("--update");

const LINT_TARGETS = ["app", "scripts", "workers"];

// Source files the size ratchet governs. Tests are excluded on purpose: a test
// file is long because it enumerates cases, and shortening one by dropping cases
// is the opposite of the thing this is for.
const SIZED_EXT = [".ts", ".tsx", ".mts", ".mjs"];
/** @param {string} p */
const isSized = (p) =>
  SIZED_EXT.some((e) => p.endsWith(e)) &&
  !p.includes(".test.") &&
  !p.endsWith(".d.ts");

/** @typedef {{ lintWarnings?: Record<string, number>, fileSize?: { ceiling?: number, enforced?: boolean, grandfathered?: Record<string, number> } }} Baseline */

/** @returns {Baseline} */
function readBaseline() {
  if (!existsSync(BASELINE)) {
    console.error(`missing baseline: ${relative(APP_DIR, BASELINE)}`);
    console.error("run with --update to create it from the current tree.");
    process.exit(2);
  }
  return JSON.parse(readFileSync(BASELINE, "utf-8"));
}

/**
 * eslint warning counts per rule, over the same targets `npm run lint` uses.
 * @returns {Record<string, number>}
 */
function lintCounts() {
  /** @type {string | undefined} */
  let out;
  try {
    out = execFileSync("npx", ["eslint", ...LINT_TARGETS, "-f", "json"], {
      cwd: APP_DIR,
      encoding: "utf-8",
      maxBuffer: 64 * 1024 * 1024,
    });
  } catch (err) {
    // eslint exits non-zero when there are ERRORS. Its JSON is still on stdout,
    // and errors are already blocking in `npm run lint` — this gate is about the
    // warnings, so parse and carry on rather than double-reporting.
    out = /** @type {{ stdout?: string }} */ (err).stdout;
    if (!out) throw err;
  }
  /** @type {Record<string, number>} */
  const counts = {};
  for (const file of JSON.parse(out)) {
    for (const m of file.messages) {
      if (m.severity !== 1 || !m.ruleId) continue;
      counts[m.ruleId] = (counts[m.ruleId] || 0) + 1;
    }
  }
  return counts;
}

/**
 * Line counts for every TRACKED, sized source file.
 *
 * Tracked, which means `git ls-files` — so a brand-new file is invisible here
 * until it is staged. That is the right scope for the two places this actually
 * runs (CI, where everything is committed, and a pre-commit hook, where the
 * work is staged by definition) and it keeps a scratch file in the working tree
 * from failing someone's gate.
 * @returns {Record<string, number>}
 */
function fileSizes() {
  const tracked = execFileSync("git", ["ls-files", ...LINT_TARGETS], {
    cwd: APP_DIR,
    encoding: "utf-8",
  })
    .split("\n")
    .filter((p) => p && isSized(p));
  /** @type {Record<string, number>} */
  const sizes = {};
  for (const p of tracked) {
    try {
      sizes[p] = readFileSync(join(APP_DIR, p), "utf-8").split("\n").length;
    } catch {
      // A tracked path that cannot be read is git's problem, not this gate's.
    }
  }
  return sizes;
}

const baseline = readBaseline();
const counts = lintCounts();
const sizes = fileSizes();
const failures = [];

// ---- gate 1: lint warnings, per rule ---------------------------------------
// Per RULE rather than one total, because a single number lets a new `any`
// hide behind someone else's fixed hook warning and still read as progress.
for (const [rule, budget] of Object.entries(baseline.lintWarnings ?? {})) {
  const now = counts[rule] ?? 0;
  if (now > budget) {
    failures.push(
      `lint: ${rule} rose to ${now}, budget is ${budget}. ` +
        `Fix the new warning, or improve elsewhere in the same rule first.`,
    );
  }
}
for (const [rule, now] of Object.entries(counts)) {
  if (!(rule in (baseline.lintWarnings ?? {}))) {
    failures.push(
      `lint: ${rule} is new (${now}) and has no budget. Fix it, or record it deliberately.`,
    );
  }
}

// ---- gate 2: file size ------------------------------------------------------
const { ceiling, enforced, grandfathered = {} } = baseline.fileSize ?? {};
for (const [path, lines] of Object.entries(sizes)) {
  const ceilingFor = grandfathered[path];
  if (ceilingFor !== undefined) {
    if (lines > ceilingFor) {
      failures.push(
        `size: ${path} is ${lines} lines, past its grandfathered ceiling of ${ceilingFor}. ` +
          `Grandfathered files may shrink, never grow — split instead of extending.`,
      );
    }
  } else if (enforced && ceiling && lines > ceiling) {
    failures.push(
      `size: ${path} is ${lines} lines, over the ${ceiling}-line ceiling for new files.`,
    );
  }
}

if (UPDATE) {
  const next = {
    ...baseline,
    lintWarnings: Object.fromEntries(
      Object.entries({ ...baseline.lintWarnings, ...counts })
        .map(
          ([rule]) =>
            /** @type {[string, number]} */ ([
              rule,
              Math.min(
                baseline.lintWarnings?.[rule] ?? Infinity,
                counts[rule] ?? 0,
              ),
            ]),
        )
        .filter(([, n]) => Number.isFinite(n))
        .sort(([a], [b]) => a.localeCompare(b)),
    ),
    fileSize: {
      ...baseline.fileSize,
      grandfathered: Object.fromEntries(
        Object.entries(grandfathered)
          .filter(([p]) => p in sizes) // a deleted file leaves the list
          .map(
            ([p, c]) =>
              /** @type {[string, number]} */ ([p, Math.min(c, sizes[p])]),
          )
          .sort(([a], [b]) => a.localeCompare(b)),
      ),
    },
  };
  writeFileSync(BASELINE, JSON.stringify(next, null, 2) + "\n", "utf-8");
  console.log(
    `re-baselined ${relative(APP_DIR, BASELINE)} (improvements only).`,
  );
  process.exit(0);
}

if (failures.length) {
  console.error("frontend ratchets FAILED:\n");
  for (const f of failures) console.error(`  ${f}`);
  console.error(
    `\nAfter genuinely improving a number: npm run ratchets:update`,
  );
  process.exit(1);
}

const warnTotal = Object.values(counts).reduce((a, b) => a + b, 0);
console.log(
  `frontend ratchets: clean — ${warnTotal} lint warning(s) within budget, ` +
    `${Object.keys(grandfathered).length} file(s) within their size ceiling` +
    `${enforced ? `, new files capped at ${ceiling} lines` : ""}.`,
);
