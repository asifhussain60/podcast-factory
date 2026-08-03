import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

/**
 * Every palette is held to the same floor.
 *
 * §3 of app/styles/podcast-factory.css is deliberately the one place a new theme
 * gets added, and the whole value of that is lost if a new palette can ship with
 * grey-on-grey body text. So the ratios written in the comments beside each
 * colour are not decoration — they are re-derived here on every run, and a
 * palette added later is measured by exactly the same rules as the three that
 * shipped with the theme.
 *
 * Two things are checked:
 *
 *   1. Every palette declares the SAME set of colour tokens. A theme that
 *      forgets `--l-band-ornament` does not fall back to a sensible default; it
 *      falls back to whatever the light theme set, because these are custom
 *      properties on overlapping selectors. That is a silent, confusing bug.
 *   2. Every text-on-background pair clears WCAG AA.
 *
 * The thresholds are the real ones: 4.5:1 for body text, 3:1 for the things that
 * are shapes rather than words — the card ornament and the focus ring.
 */

const CSS = readFileSync(new URL("../app/styles/podcast-factory.css", import.meta.url), "utf8");

type Palette = { name: string; colors: Record<string, string> };

/**
 * The palette blocks, read out of the stylesheet.
 *
 * A block counts as a palette only if it declares `color-scheme` — that is what
 * separates the three in §3 from the token `:root` in §2, and it is a property
 * every palette must set anyway so the browser paints form controls and
 * scrollbars to match.
 */
function palettes(css: string): Palette[] {
  const found: Palette[] = [];

  for (const match of css.matchAll(/([^{}]*?)\{([^{}]*?)\}/g)) {
    const [, selector, body] = match;
    if (!/color-scheme\s*:/.test(body)) continue;

    const themed = selector.match(/\[data-theme="([a-z-]+)"\]/);
    if (themed === null) continue;

    const colors: Record<string, string> = {};
    for (const decl of body.matchAll(/--(l-[a-z-]+)\s*:\s*(#[0-9a-fA-F]{6})\s*;/g)) {
      colors[decl[1]] = decl[2].toLowerCase();
    }
    found.push({ name: themed[1], colors });
  }

  return found;
}

function channels(hex: string): [number, number, number] {
  const n = Number.parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

/** WCAG relative luminance. */
function luminance(hex: string): number {
  const [r, g, b] = channels(hex).map((v) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const [light, dark] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (light + 0.05) / (dark + 0.05);
}

/** [foreground, background, minimum]. */
const PAIRS: [string, string, number][] = [
  ["l-ink", "l-bg", 4.5],
  ["l-ink", "l-surface", 4.5],
  ["l-ink", "l-sunken", 4.5],
  ["l-muted", "l-bg", 4.5],
  ["l-muted", "l-surface", 4.5],
  ["l-faint", "l-bg", 4.5],
  ["l-faint", "l-surface", 4.5],
  ["l-accent", "l-bg", 4.5],
  ["l-accent", "l-surface", 4.5],
  ["l-accent", "l-accent-soft", 4.5],
  ["l-accent-hover", "l-surface", 4.5],
  ["l-on-accent", "l-accent", 4.5],
  ["l-on-accent", "l-accent-hover", 4.5],
  ["l-on-band", "l-band", 4.5],
  ["l-band-muted", "l-band", 4.5],
  ["l-ok", "l-surface", 4.5],
  ["l-warn", "l-surface", 4.5],
  ["l-danger", "l-surface", 4.5],
  // Shapes, not words: the card's ornament, and the focus ring where it lands
  // on the most difficult surface.
  ["l-band-ornament", "l-band", 3],
  ["l-accent", "l-sunken", 3],
];

const FOUND = palettes(CSS);

describe("the theme's palettes", () => {
  it("declares more than one, so the shared rules are actually exercised", () => {
    expect(FOUND.length).toBeGreaterThan(1);
  });

  it("names every palette exactly once", () => {
    const names = FOUND.map((p) => p.name);
    expect(new Set(names).size).toBe(names.length);
  });

  it("gives every palette the same tokens", () => {
    const [first, ...rest] = FOUND;
    const expected = Object.keys(first.colors).sort();

    for (const palette of rest) {
      expect(
        Object.keys(palette.colors).sort(),
        `"${palette.name}" does not declare the same colour tokens as "${first.name}" — ` +
          `a missing one silently inherits the previous palette's value`,
      ).toEqual(expected);
    }
  });
});

describe("the two Arabic faces", () => {
  /** Everything inside §7, where the reading column is styled. */
  const readingColumn = (() => {
    const start = CSS.indexOf("* 7. READER");
    expect(start, "the stylesheet must still have a §7 reading column").toBeGreaterThan(-1);
    return CSS.slice(start);
  })();

  it("keeps the display face out of the reading column", () => {
    // Amiri is for titles. The reading column carries fully-vowelled prose and
    // Scheherazade New is engineered for it; a face with Amiri's stroke contrast
    // collides its harakat. This is the assertion that stops someone "tidying"
    // the two tokens into one.
    expect(
      readingColumn,
      "§7 must not reference --l-font-arabic-display; the reader uses --l-font-arabic",
    ).not.toContain("--l-font-arabic-display");
  });

  it("still binds the reading column to a face at all", () => {
    expect(readingColumn).toContain("--l-font-arabic");
  });

  it("never binds the display face to :lang(ar)", () => {
    // That selector drives every Arabic run on the site, prose included.
    const langRule = CSS.slice(CSS.indexOf(":lang(ar)"), CSS.indexOf(":lang(ar)") + 260);
    expect(langRule).not.toContain("--l-font-arabic-display");
  });
});

describe.each(FOUND)("$name", ({ name, colors }) => {
  for (const [fg, bg, min] of PAIRS) {
    it(`${fg} on ${bg} clears ${min}:1`, () => {
      expect(colors[fg], `${name} is missing --${fg}`).toBeDefined();
      expect(colors[bg], `${name} is missing --${bg}`).toBeDefined();

      const ratio = contrast(colors[fg], colors[bg]);
      expect(
        Number(ratio.toFixed(2)),
        `${colors[fg]} on ${colors[bg]} is ${ratio.toFixed(2)}:1`,
      ).toBeGreaterThanOrEqual(min);
    });
  }
});
