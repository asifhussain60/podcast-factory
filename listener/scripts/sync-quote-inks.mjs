// The four quotation cards take their inks from ONE file, and this copies them.
//
// Source of truth: plan-dashboard/src/styles/quote-typography.css, which is the
// printed edition's stylesheet and the one the Book Composer renders through.
// A card's colour is a property of the EDITION, not of a surface: scripture is
// gold in the print PDF, in the Composer, and on the Podcast Factory Library,
// and a reader who learns that on one must not have to relearn it on another.
//
// Copied at author time rather than imported at build or run time, exactly like
// the faces in sync-fonts.mjs and for the same reason: this app has no coupling
// to the admin site, and a stylesheet reaching across the repo boundary would be
// the first. The generated regions are committed; test/quote-inks.test.ts runs
// this in --check mode, and the repo's pre-commit hook runs that test, so a
// value changed on one side and not the other cannot be committed.
//
//   node scripts/sync-quote-inks.mjs [--check]
//
// --check writes nothing and exits non-zero when a region is out of date.
//
// WHAT THIS DOES NOT OWN: the sepia palette's inks. The print stylesheet picks
// against a cream page and a near-black one; the sepia sheet is this app's own
// surface and its inks are warmed a step for it by hand. They are left exactly
// where they are, and a change to a shared ink that should also move sepia has
// to move it deliberately. Inventing a warming transform here would be this file
// asserting a colour nobody measured.
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const LISTENER = resolve(HERE, "..");
const SOURCE = resolve(LISTENER, "..", "plan-dashboard", "src", "styles", "quote-typography.css");
const TARGET = join(LISTENER, "app", "styles", "podcast-factory.css");
const SOURCE_LABEL = "plan-dashboard/src/styles/quote-typography.css";

/**
 * One generated region: its marker id, and the target token -> source token map.
 *
 * The pair is spelled as a fixed-length tuple rather than `string[]` so that a
 * mapping written with a missing or extra element is a type error here instead
 * of an undefined value reaching the stylesheet.
 *
 * @typedef {{ id: string, tokens: [string, string][] }} Region
 */

/**
 * Each generated region: its marker id, and the target token -> source token map.
 *
 * The ids name a PALETTE and a group rather than a line range, so the regions
 * survive edits to the prose around them — which is most of that file.
 *
 * @type {Region[]}
 */
const REGIONS = [
  {
    id: "quote-inks-light",
    tokens: [
      ["--l-quote-quran", "--q-quran-ink"],
      ["--l-quote-quran-tr", "--q-quran-tr-ink"],
      ["--l-quote-hadith", "--q-hadith-ink"],
      ["--l-quote-poem", "--q-poem-ink"],
      ["--l-quote-saying", "--q-said-ink"],
    ],
  },
  {
    id: "quote-inks-dark",
    tokens: [
      ["--l-quote-quran", "--q-quran-ink-dark"],
      ["--l-quote-quran-tr", "--q-quran-tr-ink-dark"],
      ["--l-quote-hadith", "--q-hadith-ink-dark"],
      ["--l-quote-poem", "--q-poem-ink-dark"],
      ["--l-quote-saying", "--q-said-ink-dark"],
    ],
  },
  // Gold is the one ink identical in all three palettes — it reads on cream, on
  // sepia and on near-black alike — so the sepia carve-out above does not apply
  // to it and all three take it from the same pair of source tokens.
  {
    id: "quote-gold-light",
    tokens: [
      ["--l-quote-gold", "--q-gold-rule"],
      ["--l-quote-gold-lift", "--q-gold-lift"],
    ],
  },
  {
    id: "quote-gold-dark",
    tokens: [
      ["--l-quote-gold", "--q-gold-rule"],
      ["--l-quote-gold-lift", "--q-gold-lift"],
    ],
  },
  {
    id: "quote-gold-sepia",
    tokens: [
      ["--l-quote-gold", "--q-gold-rule"],
      ["--l-quote-gold-lift", "--q-gold-lift"],
    ],
  },
];

/**
 * The `:root` block's `--token: value;` declarations, as a plain map.
 *
 * SCOPED TO `:root`, which is not a tidiness point. That stylesheet re-declares
 * several of these tokens inside per-book style classes — `.ari-green` swaps the
 * saying ink to maroon for the one book that would otherwise set scripture and
 * saying in the same colour. Reading the whole file lets the LAST declaration
 * win, so this copied one book's variant into every book on the audience site,
 * turning a green saying card maroon. Caught by diffing the values on the first
 * run; the scope is what stops it recurring.
 *
 * @param {string} css
 * @returns {Record<string, string>}
 */
function readTokens(css) {
  const at = css.indexOf(":root {");
  if (at === -1) throw new Error(`${SOURCE_LABEL} has no :root block`);
  const end = css.indexOf("\n}", at);
  if (end === -1) throw new Error(`${SOURCE_LABEL}'s :root block is unterminated`);
  /** @type {Record<string, string>} */
  const out = {};
  for (const m of css.slice(at, end).matchAll(/^\s*(--[\w-]+):\s*([^;]+);/gm)) {
    out[m[1]] = m[2].trim();
  }
  return out;
}

/** @param {string} id */
const open = (id) =>
  `  /* >>> ${id} — generated from ${SOURCE_LABEL} by scripts/sync-quote-inks.mjs. ` +
  `Change a value THERE, then run \`npm run quote-inks\`. */`;
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
      if (!value) throw new Error(`${SOURCE_LABEL} has no ${source} (needed by ${region.id})`);
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
      `quote inks are out of date in ${stale.length} region(s): ${stale.join(", ")}\n` +
        `  run: cd listener && npm run quote-inks`,
    );
    process.exit(1);
  }
  console.log(`quote inks are current (${REGIONS.length} regions)`);
} else {
  if (stale.length) {
    writeFileSync(TARGET, css);
    console.log(`updated ${stale.length} region(s): ${stale.join(", ")}`);
  } else {
    console.log(`quote inks already current (${REGIONS.length} regions)`);
  }
}
