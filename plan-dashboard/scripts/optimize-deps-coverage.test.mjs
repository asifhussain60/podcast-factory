/**
 * optimize-deps-coverage.test.mjs — keep optimizeDeps.include honest about the
 * in-repo packages.
 *
 * `optimizeDeps.include` in astro.config.mjs is a HAND-MAINTAINED list, and this
 * repo has twice blanked a page in production because a bare specifier reached
 * by a client island was missing from it: Vite discovers the dep mid-session,
 * re-optimizes, and 504s chunk URLs it has already served.
 *
 * The app's own src/ is covered by the fact that anyone adding a dep there is
 * editing code next to the comment that says to update this list. `packages/*`
 * is not: its imports are written in a different directory, by someone thinking
 * about a reusable library rather than about this app's bundler. So the check is
 * mechanical.
 *
 * Deliberately conservative — it does not try to tell a type-only import from a
 * value one. A type-only import listed here is harmless; a value import NOT
 * listed is an outage.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const PACKAGES = join(ROOT, "packages");

function sourceFiles(dir, acc = []) {
  for (const name of readdirSync(dir)) {
    if (name === "node_modules" || name === "dist" || name === "test") continue;
    const p = join(dir, name);
    if (statSync(p).isDirectory()) sourceFiles(p, acc);
    else if (/\.(ts|tsx|mts|js|mjs)$/.test(p)) acc.push(p);
  }
  return acc;
}

/** [] rather than a throw when the directory is absent — a repo with no
 *  packages, or a package with no src/, is not a failure of this check. */
function sourceFilesOrNone(dir) {
  try {
    return sourceFiles(dir);
  } catch {
    return [];
  }
}

function dirEntriesOrNone(dir) {
  try {
    return readdirSync(dir);
  } catch {
    return [];
  }
}

const IMPORT_RE =
  /(?:^|\n)\s*(?:import|export)[\s\S]*?from\s+["']([^"']+)["']/g;

test("every bare specifier imported by packages/* is pre-bundled", () => {
  const config = readFileSync(join(ROOT, "astro.config.mjs"), "utf8");
  const includeBlock = config.slice(
    config.indexOf("include: ["),
    config.indexOf("]", config.indexOf("include: [")),
  );
  const included = new Set(
    [...includeBlock.matchAll(/'([^']+)'/g)].map((m) => m[1]),
  );

  const missing = [];
  for (const pkg of dirEntriesOrNone(PACKAGES)) {
    for (const file of sourceFilesOrNone(join(PACKAGES, pkg, "src"))) {
      const text = readFileSync(file, "utf8");
      for (const m of text.matchAll(IMPORT_RE)) {
        const spec = m[1];
        if (!spec || spec.startsWith(".") || spec.startsWith("node:")) continue;
        // React is pre-bundled and is only reached from the optional ./react
        // entry, which the app does not use.
        if (!included.has(spec)) {
          missing.push(`${file.slice(ROOT.length + 1)} -> ${spec}`);
        }
      }
    }
  }

  assert.deepEqual(
    missing,
    [],
    `Bare specifier(s) imported by an in-repo package but absent from\n` +
      `astro.config.mjs optimizeDeps.include. Vite will discover them\n` +
      `mid-session and 504 already-served chunks:\n  ${missing.join("\n  ")}`,
  );
});
