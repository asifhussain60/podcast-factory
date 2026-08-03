/**
 * Derive every brand raster from the one logo file.
 *
 * The original is 1254x1254 and the artwork occupies only 989x599 of it — about
 * 62% of the canvas is white padding, which is why the mark looked lost in the
 * masthead. Rather than trimming by eye once and losing the numbers, the three
 * regions are constants here, measured from the file with an ink-threshold scan:
 * pixels differing from the #fefefe paper by more than 12 per channel were
 * collected into rows, and the rows fell into exactly two bands separated by a
 * 32px gutter — the artwork above, the wordmark below.
 *
 * Backgrounds stay opaque paper white on purpose. Punching the white out to
 * transparency would also hollow the book's pages (they are paper, not ink), and
 * a navy mark on a dark background is invisible anyway. Theming is the SVG mark's
 * job — `app/components/brand/mark.tsx` — and these rasters exist for the places
 * that cannot take an SVG: the favicon fallback, the iOS home screen, and the
 * social preview card.
 *
 *   node scripts/derive-brand-assets.mjs
 */

import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import sharp from "sharp";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..");
const SOURCE = join(ROOT, "brand", "podcast-factory-logo.png");
const OUT = join(ROOT, "public", "brand");

/** The source these constants were measured against. Any other file is a bug. */
const SOURCE_SIZE = 1254;

/** Two pixels of slack so an anti-aliased edge is never clipped. */
const BLEED = 2;

/** @typedef {{left: number, top: number, right: number, bottom: number}} Region */

/** @type {Record<"logo" | "mark" | "wordmark", Region>} */
const REGIONS = {
  /** Mark plus wordmark, white space removed. */
  logo: { left: 134, top: 304, right: 1123, bottom: 903 },
  /** The open book, microphone and waveform alone. */
  mark: { left: 340, top: 304, right: 915, bottom: 743 },
  /** "Podcast Factory" alone — kept for reference and for the wide og card. */
  wordmark: { left: 134, top: 775, right: 1123, bottom: 903 },
};

const PAPER = { r: 255, g: 255, b: 255, alpha: 1 };

/** @param {Region} region */
function extractOf(region) {
  const left = Math.max(0, region.left - BLEED);
  const top = Math.max(0, region.top - BLEED);
  return {
    left,
    top,
    width: Math.min(SOURCE_SIZE, region.right + BLEED) - left,
    height: Math.min(SOURCE_SIZE, region.bottom + BLEED) - top,
  };
}

/**
 * A crop, written at its natural size.
 *
 * @param {string} name
 * @param {Region} region
 */
async function crop(name, region) {
  const box = extractOf(region);
  await sharp(SOURCE)
    .extract(box)
    .png({ compressionLevel: 9 })
    .toFile(join(OUT, `${name}.png`));
  return `${name}.png  ${box.width}x${box.height}`;
}

/**
 * A square icon: the mark centred on paper.
 *
 * `padding` is the share of the square left empty on the tightest axis. iOS and
 * Android both crop icons — Android's maskable spec can take up to 20% off every
 * edge — so the 512 is drawn with far more room around it than the 32 needs.
 *
 * @param {string} name
 * @param {number} size
 * @param {number} padding
 */
async function icon(name, size, padding) {
  const box = extractOf(REGIONS.mark);
  const inner = Math.round(size * (1 - padding * 2));
  const mark = await sharp(SOURCE)
    .extract(box)
    .resize({ width: inner, height: inner, fit: "inside" })
    .toBuffer();

  await sharp({
    create: { width: size, height: size, channels: 4, background: PAPER },
  })
    .composite([{ input: mark, gravity: "centre" }])
    .png({ compressionLevel: 9 })
    .toFile(join(OUT, `${name}.png`));
  return `${name}.png  ${size}x${size}`;
}

/** The 1200x630 card a link preview renders. */
async function socialCard() {
  const box = extractOf(REGIONS.logo);
  const lockup = await sharp(SOURCE)
    .extract(box)
    .resize({ width: 760, fit: "inside" })
    .toBuffer();

  await sharp({
    create: { width: 1200, height: 630, channels: 4, background: PAPER },
  })
    .composite([{ input: lockup, gravity: "centre" }])
    .png({ compressionLevel: 9 })
    .toFile(join(OUT, "og.png"));
  return "og.png  1200x630";
}

const meta = await sharp(SOURCE).metadata();
if (meta.width !== SOURCE_SIZE || meta.height !== SOURCE_SIZE) {
  throw new Error(
    `${SOURCE} is ${meta.width}x${meta.height}, but the crop regions in this ` +
      `script were measured against ${SOURCE_SIZE}x${SOURCE_SIZE}. Re-measure ` +
      `before replacing the source.`,
  );
}

await mkdir(OUT, { recursive: true });

const written = [
  await crop("logo", REGIONS.logo),
  await crop("mark", REGIONS.mark),
  await crop("wordmark", REGIONS.wordmark),
  await icon("icon-32", 32, 0.04),
  await icon("icon-180", 180, 0.08),
  await icon("icon-512", 512, 0.16),
  await socialCard(),
];

await writeFile(
  join(OUT, "README.md"),
  [
    "# Generated brand assets",
    "",
    "Every file here is derived from `listener/brand/podcast-factory-logo.png`",
    "by `listener/scripts/derive-brand-assets.mjs`. Do not edit them by hand —",
    "replace the source and re-run the script.",
    "",
    ...written.map((line) => `- \`${line.split("  ")[0]}\` — ${line.split("  ")[1]}`),
    "",
    "The in-app mark is NOT here: it is `app/components/brand/mark.tsx`, drawn as",
    "SVG so it inherits the theme's colours and stays sharp at 28px.",
    "",
  ].join("\n"),
);

console.log(`Wrote ${written.length} files to public/brand/`);
for (const line of written) console.log(`  ${line}`);
