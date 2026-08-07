/**
 * REQ-010's reading floor, pinned.
 *
 * The check landed on 2026-08-06 because the rule had been UNGATED: the lint
 * config carried two documented `_notes` exceptions for it while
 * `lint-html-views.mjs` implemented nothing, so forty-plus sub-floor prose
 * selectors were never reported — including four-sentence FAQ answers at
 * 0.92rem on a blocking-path page. A rule everyone believed was gated, wasn't.
 *
 * These cases exist so it cannot quietly become ungated again, and so the two
 * judgment calls in it stay deliberate rather than accidental:
 *
 *   1. WHAT COUNTS AS PROSE — `th` and `label` are excluded on purpose (mono
 *      column heads are on REQ-010's own EXEMPT list; a `label` here is form
 *      chrome), and chrome-named selectors are exempt even when they contain a
 *      prose element, so `.chip p` stays quiet.
 *   2. WHAT COUNTS AS A VALUE — only `rem` and `px` resolve. `var()`, `calc()`,
 *      `clamp()`, `%` and `em` are SKIPPED, never guessed. A floor rule that
 *      cries wolf on a `clamp()` teaches people to ignore it, and both existing
 *      documented exceptions (select-menu's `.sm-option`, prose-editor's
 *      `var(--rte-font-size)`) fall out of these two rules with no `allow`
 *      entry needed — which is why `allow` is still `{}`.
 *
 * Driven as a subprocess against a fixture because the linter is a CLI that
 * runs its whole sweep on import. The fixture must sit under a configured
 * `css_paths` root to be classified at all, so it is written into src/styles/
 * and removed in a `finally`.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { writeFileSync, unlinkSync, existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPTS = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(SCRIPTS, "..");
const FIXTURE_REL = "src/styles/__reading-floor-fixture.css";
const FIXTURE_ABS = path.join(ROOT, FIXTURE_REL);

const FIXTURE = `
/* --- should be REPORTED: prose elements below the floor --- */
.doc-body p { font-size: 0.92rem; }
.doc-body li { font-size: 14px; }          /* 0.875rem at a 16px root */
.doc-body figcaption { font-size: 0.8rem; }
.callout { font-size: 1.1rem; }

/* --- should be SILENT: at or above the floor --- */
.doc-body blockquote { font-size: 1.2rem; }
.doc-intro p { font-size: 1.35rem; }

/* --- should be SILENT: UI chrome, per REQ-010's EXEMPT list --- */
.chip p { font-size: 0.72rem; }
.breadcrumb li { font-size: 0.72rem; }
.rte-toolbar p { font-size: 0.85rem; }

/* --- should be SILENT: deliberately excluded element selectors --- */
.data-table th { font-size: 0.72rem; }
.form-row label { font-size: 0.85rem; }

/* --- should be SILENT: values the linter refuses to guess at --- */
.doc-body dd { font-size: var(--something-small); }
.doc-body dt { font-size: clamp(0.8rem, 2vw, 1rem); }
.doc-body td { font-size: calc(1rem - 2px); }
.doc-body blockquote.pct { font-size: 90%; }
`;

function runLinter() {
  const out = execFileSync(
    "node",
    [
      path.join(SCRIPTS, "lint-html-views.mjs"),
      "--files",
      FIXTURE_REL,
      "--json",
    ],
    { cwd: ROOT, encoding: "utf8" },
  );
  // --json emits { errors, warns, total }; READING-FLOOR reports at warn.
  const parsed = JSON.parse(out);
  return [...parsed.errors, ...parsed.warns].filter(
    (f) => f.id === "READING-FLOOR",
  );
}

test("REQ-010 reading floor: reports sub-floor prose and nothing else", () => {
  writeFileSync(FIXTURE_ABS, FIXTURE, "utf8");
  try {
    const hits = runLinter();
    const selectors = hits.map((h) => h.selector ?? h.src ?? "").join(" | ");

    assert.equal(
      hits.length,
      4,
      `expected exactly the four sub-floor prose rules, got ${hits.length}: ${selectors}`,
    );

    for (const needle of ["p", "li", "figcaption", "callout"]) {
      assert.ok(
        hits.some((h) => (h.src ?? "").length > 0),
        `finding for ${needle} carried no source line`,
      );
    }

    // The exact failure this rule exists to catch: a value expressed in px.
    assert.ok(
      hits.some((h) => /0\.875/.test(h.msg)),
      `a px value below the floor must be resolved to rem and reported: ${hits.map((h) => h.msg).join(" | ")}`,
    );
  } finally {
    if (existsSync(FIXTURE_ABS)) unlinkSync(FIXTURE_ABS);
  }
});

test("REQ-010 reading floor: the check is actually wired up", () => {
  // Guards the ungated-rule failure directly. If someone removes the call site
  // but leaves scanReadingFloor defined, every other assertion here still needs
  // a finding to exist — this one states the reason out loud.
  writeFileSync(FIXTURE_ABS, ".doc-body p { font-size: 0.5rem; }\n", "utf8");
  try {
    assert.equal(
      runLinter().length,
      1,
      "lint:views reported clean over prose at 0.5rem — REQ-010 is ungated again",
    );
  } finally {
    if (existsSync(FIXTURE_ABS)) unlinkSync(FIXTURE_ABS);
  }
});
