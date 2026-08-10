/**
 * vendor-toolbar-icons.mjs — copy the Book Composer toolbar's glyphs OUT of the
 * Font Awesome package and INTO the repo, as inline SVG.
 *
 * Why this exists. The toolbar wore Font Awesome by CSS class, which resolves
 * against the stylesheet Base.astro pulls from a CDN. That works until it does
 * not: with no network the classes match nothing and every control renders as an
 * empty button. A formatting bar you cannot read is worse than one drawn in a
 * duller set, so the glyphs are vendored — inline SVG in the page, no stylesheet,
 * no font load, no request. They render before anything else has finished
 * loading, and they render offline.
 *
 * Why a generator rather than pasted path data. Thirteen `d` attributes of a few
 * hundred characters each are unreviewable by eye and unattributable once pasted.
 * This script makes their provenance a fact the repo can re-derive: the version
 * is PINNED to what the site's own CDN link serves, so a vendored glyph and the
 * ones the rest of the site draws from the CDN are the same drawing.
 *
 * Licence: Font Awesome Free icons are CC BY 4.0. The attribution rides in the
 * generated file's header, which is why that header is emitted rather than
 * optional.
 *
 *   node scripts/vendor-toolbar-icons.mjs
 *
 * Re-run after changing FA_VERSION (keep it equal to the CDN link in
 * src/layouts/Base.astro) or after adding a control to the bar.
 */
import { readFileSync, writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const PKG = join(
  HERE,
  "..",
  "node_modules",
  "@fortawesome",
  "fontawesome-free",
);
const OUT = join(HERE, "..", "src", "scripts", "toolbar-icons.ts");

/** Must equal the version in the CDN <link> in src/layouts/Base.astro, or the
 *  bar's glyphs stop being the same drawing as the rest of the site's. */
const FA_VERSION = "6.5.0";

/**
 * Toolbar control id → Font Awesome solid icon name.
 *
 * The keys are the package's `data-rte-id`s, so this map IS the bar's icon
 * override — see COMPOSE_TOOLBAR_ICONS in book-composer.ts.
 */
// `code` and `clearFormatting` were removed from the bar on 2026-08-02 and are
// not vendored: an icon nothing renders is a file nobody would notice going
// stale. Re-add the pair here and regenerate if either button comes back.
const ICONS = {
  undo: "rotate-left",
  redo: "rotate-right",
  bold: "bold",
  italic: "italic",
  bulletList: "list-ul",
  orderedList: "list-ol",
  blockquote: "quote-right",
  link: "link",
  horizontalRule: "minus",
  more: "ellipsis",
  // The three alignment buttons.
  alignLeft: "align-left",
  alignCenter: "align-center",
  alignRight: "align-right",
};

const installed = JSON.parse(
  readFileSync(join(PKG, "package.json"), "utf-8"),
).version;
if (installed !== FA_VERSION) {
  console.error(
    `Font Awesome ${installed} is installed but this script vendors ${FA_VERSION} ` +
      `(the version Base.astro's CDN link serves). Install the pinned version, or ` +
      `change BOTH the link and FA_VERSION together.`,
  );
  process.exit(1);
}

/** Pull the viewBox and the path geometry out of one FA source SVG. FA ships one
 *  `<path>` per icon; anything else means the file shape changed and the caller
 *  should look rather than get a silently half-copied glyph. */
function extract(name) {
  const raw = readFileSync(join(PKG, "svgs", "solid", `${name}.svg`), "utf-8");
  const viewBox = raw.match(/viewBox="([^"]+)"/)?.[1];
  const paths = [...raw.matchAll(/<path[^>]*\sd="([^"]+)"/g)].map((m) => m[1]);
  if (!viewBox || paths.length !== 1) {
    throw new Error(
      `fa-${name}: expected one viewBox and one path, got ${paths.length} paths`,
    );
  }
  return { viewBox, d: paths[0] };
}

const entries = Object.entries(ICONS).map(([id, name]) => {
  const { viewBox, d } = extract(name);
  // `fill="currentColor"` so a glyph takes the button's ink in every theme, and
  // `aria-hidden` because each control's accessible name is its aria-label — a
  // screen reader announcing the glyph too would say everything twice.
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}" ` +
    `width="16" height="16" fill="currentColor" aria-hidden="true" ` +
    `focusable="false"><path d="${d}"/></svg>`;
  // Single quotes, so the SVG's own double quotes need no escaping — and so the
  // shape written here is the shape Prettier would settle on. See below.
  return `  /** fa-${name} */\n  ${id}: {\n    svg: '${svg}',\n  },`;
});

const out = `/**
 * toolbar-icons.ts — GENERATED. Do not edit by hand.
 *
 * Source: Font Awesome Free ${FA_VERSION} solid set.
 * Icons licensed CC BY 4.0 — https://fontawesome.com/license/free
 * Copyright Fonticons, Inc.
 *
 * Regenerate with: node scripts/vendor-toolbar-icons.mjs
 *
 * The output is written Prettier-clean, so that command is the whole procedure.
 * It was not, until 2026-08-09: the generator emitted escaped double quotes and
 * a hanging \`{ svg:\` and the committed file had been hand-formatted after the
 * fact, so following the line above left every icon reformatted and the
 * pre-commit hook refusing the result.
 *
 * Inline SVG rather than the CDN stylesheet's classes, so the Book Composer's
 * formatting bar renders with no network and before any font has loaded. See the
 * generator's header for the whole reasoning.
 */

/** Book Composer toolbar glyphs, keyed by the editor package's control id. */
export const TOOLBAR_ICONS = {
${entries.join("\n")}
} as const;
`;

writeFileSync(OUT, out, "utf-8");
console.log(
  `vendored ${entries.length} Font Awesome ${FA_VERSION} icons → src/scripts/toolbar-icons.ts`,
);
