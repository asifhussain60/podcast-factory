/**
 * The two rules that keep this package reusable, enforced rather than intended.
 *
 * Both failures they prevent are documented history, not hypotheticals. The
 * editor configuration this package replaces reached 4,700 lines by absorbing
 * its host's services one convenience at a time — a file nominally about editor
 * config ended up importing the host's scripture lookup. And this repo has twice
 * blanked a page in production by importing a bare specifier that was not in the
 * bundler's hand-maintained pre-bundle list.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const SRC = join(dirname(fileURLToPath(import.meta.url)), "..", "src");

function sourceFiles(dir: string, acc: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) sourceFiles(p, acc);
    else if (p.endsWith(".ts") || p.endsWith(".tsx")) acc.push(p);
  }
  return acc;
}

/** Vocabulary that belongs to a HOST, never to an editor library. */
const DOMAIN_WORDS =
  /\b(quran|qur'an|hadees|hadith|ahadees|etymology|poetry|surah|ayah|chapter|book\.md|podcast|ksessions|kashkole|notebooklm|composer)\b/i;

test("no host-domain vocabulary appears anywhere in src/", () => {
  const offenders: string[] = [];
  for (const file of sourceFiles(SRC)) {
    const text = readFileSync(file, "utf8");
    text.split("\n").forEach((line, i) => {
      const m = line.match(DOMAIN_WORDS);
      if (m) offenders.push(`${file.slice(SRC.length + 1)}:${i + 1} "${m[0]}"`);
    });
  }
  assert.deepEqual(
    offenders,
    [],
    `Domain vocabulary leaked into a reusable package:\n${offenders.join("\n")}`,
  );
});

/**
 * The import surface is capped at three specifiers, and the cap is the point:
 * every one of them is ALREADY in the consuming app's pre-bundle list, so
 * adopting this package cannot trigger the mid-session re-optimization that
 * 504s already-served chunks. A fourth would have to be added there too — and
 * the two outages on record happened precisely because that step was missed.
 */
const ALLOWED_BARE_IMPORTS = new Set([
  "@tiptap/core",
  "@tiptap/starter-kit",
  "@tiptap/pm/model",
  "@tiptap/pm/state",
  "@tiptap/pm/view",
  "@tiptap/pm/transform",
  // React is imported only by the optional ./react entry point.
  "react",
  "react-dom",
  "react-dom/client",
]);

const IMPORT_RE =
  /(?:^|\n)\s*(?:import|export)[\s\S]*?from\s+["']([^"']+)["']/g;

test("src/ imports nothing outside the allow-listed bare specifiers", () => {
  const offenders: string[] = [];
  for (const file of sourceFiles(SRC)) {
    const text = readFileSync(file, "utf8");
    for (const m of text.matchAll(IMPORT_RE)) {
      const spec = m[1];
      if (!spec) continue;
      if (spec.startsWith(".") || spec.startsWith("node:")) continue;
      if (!ALLOWED_BARE_IMPORTS.has(spec)) {
        offenders.push(`${file.slice(SRC.length + 1)} -> ${spec}`);
      }
    }
  }
  assert.deepEqual(
    offenders,
    [],
    `New bare import(s). Each must also be added to the consuming app's ` +
      `optimizeDeps.include, or an island 504s mid-session:\n${offenders.join("\n")}`,
  );
});

test("the package declares no runtime dependencies", () => {
  const pkg = JSON.parse(
    readFileSync(join(SRC, "..", "package.json"), "utf8"),
  ) as { dependencies?: Record<string, string> };
  assert.deepEqual(
    pkg.dependencies ?? {},
    {},
    "A dependency here becomes a dependency of every consumer.",
  );
});

test("the stylesheet hardcodes no colour outside its defaults block", () => {
  // Pattern B theming: a host aliases its own tokens onto --rte-*. A hardcoded
  // colour further down the file would silently win over the host's palette.
  const css = readFileSync(
    join(SRC, "..", "styles", "prose-editor.css"),
    "utf8",
  );
  const afterDefaults = css.slice(css.indexOf("}", css.indexOf(":root")) + 1);
  const withoutComments = afterDefaults.replace(/\/\*[\s\S]*?\*\//g, "");
  const colours = withoutComments.match(
    /#[0-9a-f]{3,8}\b|\brgba?\(|\bhsla?\(/gi,
  );
  assert.equal(
    colours,
    null,
    `Hardcoded colour(s) outside the defaults block: ${colours?.join(", ")}`,
  );
});
