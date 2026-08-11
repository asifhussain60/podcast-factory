#!/usr/bin/env node
// check-frontend-ratchets.mjs — the two gates the browser surfaces never had.
//
// The pipeline side has ruff and an enforceable DR-005 line gate. The Astro site
// had ESLint but nothing that made its WARNINGS matter (they are advisory by
// design, so 93 of them accumulated where nobody had to look), and no size rule
// at all — `.repo-audit/profile.yaml` recorded that gap deliberately, noting the
// right ceiling for JSX is not the Python 600 and that the number is the owner's
// call rather than the audit's.
//
// Both gates here are RATCHETS, the same shape as infra/git-hooks/check-dr005.py:
// today's numbers are the baseline, they may shrink, and they may never grow. A
// ratchet is what lets an existing debt be recorded honestly without either
// pretending it is fixed or blocking every commit until it is.
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
const SITE_DIR = resolve(__dirname, "..");
const BASELINE = join(SITE_DIR, "frontend-ratchets.json");
const UPDATE = process.argv.includes("--update");

const LINT_TARGETS = ["src", "scripts", "packages"];

// Source files the size ratchet governs. Tests are excluded on purpose: a test
// file is long because it enumerates cases, and shortening one by dropping cases
// is the opposite of the thing this is for.
const SIZED_EXT = [".ts", ".tsx", ".astro", ".mjs"];
const isSized = (p) =>
  SIZED_EXT.some((e) => p.endsWith(e)) &&
  !p.includes(".test.") &&
  !p.endsWith(".d.ts");

function readBaseline() {
  if (!existsSync(BASELINE)) {
    console.error(`missing baseline: ${relative(SITE_DIR, BASELINE)}`);
    console.error("run with --update to create it from the current tree.");
    process.exit(2);
  }
  return JSON.parse(readFileSync(BASELINE, "utf-8"));
}

/** eslint warning counts per rule, over the same targets `npm run lint` uses. */
function lintCounts() {
  let out;
  try {
    out = execFileSync("npx", ["eslint", ...LINT_TARGETS, "-f", "json"], {
      cwd: SITE_DIR,
      encoding: "utf-8",
      maxBuffer: 64 * 1024 * 1024,
    });
  } catch (err) {
    // eslint exits non-zero when there are ERRORS. Its JSON is still on stdout,
    // and errors are already blocking in `npm run lint` — this gate is about the
    // warnings, so parse and carry on rather than double-reporting.
    out = err.stdout;
    if (!out) throw err;
  }
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
 * from failing someone's gate. Worth knowing before testing it by hand: an
 * unstaged probe file passes, and that is not the gate being broken.
 */
function fileSizes() {
  const tracked = execFileSync("git", ["ls-files", ...LINT_TARGETS], {
    cwd: SITE_DIR,
    encoding: "utf-8",
  })
    .split("\n")
    .filter((p) => p && isSized(p));
  const sizes = {};
  for (const p of tracked) {
    try {
      sizes[p] = readFileSync(join(SITE_DIR, p), "utf-8").split("\n").length;
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
        .map(([rule, _]) => [
          rule,
          Math.min(
            baseline.lintWarnings?.[rule] ?? Infinity,
            counts[rule] ?? 0,
          ),
        ])
        .filter(([, n]) => Number.isFinite(n))
        .sort(([a], [b]) => a.localeCompare(b)),
    ),
    fileSize: {
      ...baseline.fileSize,
      grandfathered: Object.fromEntries(
        Object.entries(grandfathered)
          .filter(([p]) => p in sizes) // a deleted file leaves the list
          .map(([p, c]) => [p, Math.min(c, sizes[p])])
          .sort(([a], [b]) => a.localeCompare(b)),
      ),
    },
  };
  writeFileSync(BASELINE, JSON.stringify(next, null, 2) + "\n", "utf-8");
  console.log(
    `re-baselined ${relative(SITE_DIR, BASELINE)} (improvements only).`,
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
