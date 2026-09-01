// The five study-track colours are one set of values, not two, and this copies them.
//
// Source of truth: plan-dashboard/src/styles/study-track-colors.css, whose own
// header explains why it exists. A track's colour is a property of the BOOK —
// Esoteric is the same amber on the Studio shelf and on this site's library card
// — and a reader who learns it on one must not have to relearn it on the other.
//
// Copied at author time rather than imported at build or run time, exactly like
// sync-quote-inks.mjs and sync-fonts.mjs beside it, and for the same reason:
// this app has no coupling to the admin site, and a stylesheet reaching across
// the repo boundary would be the first. The generated region is committed;
// test/study-tracks.test.ts runs this in --check mode, and the repo's pre-commit
// hook runs that test, so a value changed on one side and not the other cannot
// be committed.
//
//   node scripts/sync-study-tracks.mjs [--check]
//
// --check writes nothing and exits non-zero when the region is out of date.
//
// WHAT THIS DOES NOT OWN: which track a book IS. That is `study_track` in the
// book's own meta.yml, read by _listener_book.py on the way in and by the Studio
// card on the way out. This file owns only what each track LOOKS like.
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const LISTENER = resolve(HERE, "..");
const SOURCE = resolve(
  LISTENER,
  "..",
  "plan-dashboard",
  "src",
  "styles",
  "study-track-colors.css",
);
const TARGET = join(LISTENER, "app", "styles", "podcast-factory.css");
const SOURCE_LABEL = "plan-dashboard/src/styles/study-track-colors.css";

/**
 * One generated region: its marker id, and the target token -> source token map.
 *
 * A fixed-length tuple rather than `string[]` so a mapping written with a
 * missing or extra element is a type error here instead of an undefined value
 * reaching the stylesheet — same shape as sync-quote-inks.mjs.
 *
 * @typedef {{ id: string, tokens: [string, string][] }} Region
 */

/**
 * One region only. The ribbon pairs are theme-independent by construction (each
 * badge carries its own ink), so unlike the quotation inks there is no light /
 * dark / sepia split to mirror here.
 *
 * @type {Region[]}
 */
const REGIONS = [
  {
    id: "study-track-colors",
    tokens: [
      ["--l-ribbon-theology-bg", "--track-theology-bg"],
      ["--l-ribbon-theology-ink", "--track-theology-ink"],
      ["--l-ribbon-esoteric-bg", "--track-esoteric-bg"],
      ["--l-ribbon-esoteric-ink", "--track-esoteric-ink"],
      ["--l-ribbon-history-bg", "--track-history-bg"],
      ["--l-ribbon-history-ink", "--track-history-ink"],
      ["--l-ribbon-shariah-bg", "--track-shariah-bg"],
      ["--l-ribbon-shariah-ink", "--track-shariah-ink"],
      ["--l-ribbon-reality-bg", "--track-reality-bg"],
      ["--l-ribbon-reality-ink", "--track-reality-ink"],
      ["--l-ribbon-philosophy-bg", "--track-philosophy-bg"],
      ["--l-ribbon-philosophy-ink", "--track-philosophy-ink"],
    ],
  },
];

/**
 * The `:root` block's `--token: value;` declarations, as a plain map.
 *
 * Scoped to `:root` for the reason sync-quote-inks.mjs gives at length: reading
 * the whole file would let a later, narrower declaration win and copy one
 * surface's variant into every surface. That source file has only a `:root`
 * today, and this keeps it true if it ever grows a second block.
 *
 * @param {string} css
 * @returns {Record<string, string>}
 */
function readTokens(css) {
  const at = css.indexOf(":root {");
  if (at === -1) throw new Error(`${SOURCE_LABEL} has no :root block`);
  const end = css.indexOf("\n}", at);
  if (end === -1)
    throw new Error(`${SOURCE_LABEL}'s :root block is unterminated`);
  /** @type {Record<string, string>} */
  const out = {};
  for (const m of css.slice(at, end).matchAll(/^\s*(--[\w-]+):\s*([^;]+);/gm)) {
    out[m[1]] = m[2].trim();
  }
  return out;
}

/** @param {string} id */
const open = (id) =>
  `  /* >>> ${id} — generated from ${SOURCE_LABEL} by scripts/sync-study-tracks.mjs. ` +
  `Change a value THERE, then run \`npm run study-tracks\`. */`;
/** @param {string} id */
const close = (id) => `  /* <<< ${id} */`;

/**
 * @param {Region} region
 * @param {Record<string, string>} tokens
 * @returns {string}
 */
function body(region, tokens) {
  return region.tokens
    .map(([target, source]) => {
      const value = tokens[source];
      if (!value)
        throw new Error(
          `${SOURCE_LABEL} has no ${source} (needed by ${region.id})`,
        );
      return `  ${target}: ${value};`;
    })
    .join("\n");
}

const check = process.argv.includes("--check");
const tokens = readTokens(readFileSync(SOURCE, "utf-8"));
let css = readFileSync(TARGET, "utf-8");
const stale = [];

for (const region of REGIONS) {
  const re = new RegExp(
    `^ {2}/\\* >>> ${region.id} —[^]*?^ {2}/\\* <<< ${region.id} \\*/$`,
    "m",
  );
  if (!re.test(css)) {
    throw new Error(
      `${TARGET} has no ${region.id} region. The markers are the anchor — ` +
        `restore them rather than letting this file guess where the block goes.`,
    );
  }
  const next = `${open(region.id)}\n${body(region, tokens)}\n${close(region.id)}`;
  const before = css;
  css = css.replace(re, () => next);
  if (css !== before) stale.push(region.id);
}

if (check) {
  if (stale.length) {
    console.error(
      `study-track colours are out of date in ${stale.length} region(s): ${stale.join(", ")}\n` +
        `  run: cd listener && npm run study-tracks`,
    );
    process.exit(1);
  }
  console.log(`study-track colours are current (${REGIONS.length} region)`);
} else {
  if (stale.length) {
    writeFileSync(TARGET, css);
    console.log(`updated ${stale.length} region(s): ${stale.join(", ")}`);
  } else {
    console.log(
      `study-track colours already current (${REGIONS.length} region)`,
    );
  }
}
