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

const CSS = readFileSync(
  new URL("../app/styles/podcast-factory.css", import.meta.url),
  "utf8",
);

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
    for (const decl of body.matchAll(
      /--(l-[a-z-]+)\s*:\s*(#[0-9a-fA-F]{6})\s*;/g,
    )) {
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
  // Page titles are large, so AA-large would technically allow 3:1 — held to
  // the body floor anyway, because a heading is the one thing on a page that
  // everybody reads.
  ["l-display", "l-bg", 4.5],
  ["l-display", "l-surface", 4.5],
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
  // The six topic hues, each held to the BODY floor rather than the 3:1 a shape
  // would allow. They colour a glyph, which is a shape — but the same hue also
  // sets the count under it, and that is words.
  ["l-topic-coral", "l-surface", 4.5],
  ["l-topic-cyan", "l-surface", 4.5],
  ["l-topic-violet", "l-surface", 4.5],
  ["l-topic-green", "l-surface", 4.5],
  ["l-topic-amber", "l-surface", 4.5],
  ["l-topic-blue", "l-surface", 4.5],
  // The four quotation cards. Colour is what tells a reader which of the four a
  // quotation is — scripture, a prophetic tradition, verse, a saying — and for a
  // reader who cannot read the Arabic it is the ONLY thing that tells them, so
  // every ink is held to the body floor on the surface the prose sits on.
  // `--l-quote-gold` is deliberately absent: it is a 2px rule and a gradient
  // highlight, decoration carrying nothing, and a gold light enough to read as
  // gilding cannot clear 3:1 on paper without turning brown.
  ["l-quote-quran", "l-surface", 4.5],
  ["l-quote-quran-tr", "l-surface", 4.5],
  ["l-quote-hadith", "l-surface", 4.5],
  ["l-quote-poem", "l-surface", 4.5],
  ["l-quote-saying", "l-surface", 4.5],
  // Shapes, not words: the card's ornament, and the focus ring where it lands
  // on the most difficult surface.
  ["l-band-ornament", "l-band", 3],
  ["l-accent", "l-sunken", 3],
  // A highlight must not cost the words under it their legibility. The mark is
  // painted on the page surface, so this is the pair a reader actually sees.
  ["l-ink", "l-hl-gold", 4.5],
  ["l-ink", "l-hl-sage", 4.5],
  ["l-ink", "l-hl-sky", 4.5],
  ["l-ink", "l-hl-rose", 4.5],
];

/**
 * The other floor a highlight has to meet, and it runs the opposite way.
 *
 * Every pair above asks "is this legible ON that". A highlight also has to be
 * VISIBLE AGAINST the page — a tint at 1.05:1 is legible precisely because it is
 * barely there, which is the failure mode, not the success. The floor is a mark
 * a reader sees as a band rather than only as a hue, which is what someone who
 * cannot separate gold from sage is left with.
 *
 * 1.2, lowered from 1.3 when every highlight was diluted 35% (Asif, 2026-08-04:
 * "all highlights are very dark"). The number is a LUMINANCE ratio and these
 * tints are strongly chromatic, so it understates how plainly they read on a
 * near-neutral page — but it is still the only measure here that fails when a
 * highlight fades into the paper, so it moved rather than being dropped. The
 * floor that protects the words is the 4.5 above, and every one of them rose.
 *
 * Kept as its own list rather than folded into PAIRS because PAIRS means
 * "readable text on a background" everywhere else, and reusing it for a
 * different question would make both harder to reason about.
 */
const VISIBLE_AGAINST_PAGE: [string, string, number][] = [
  ["l-hl-gold", "l-surface", 1.2],
  ["l-hl-sage", "l-surface", 1.2],
  ["l-hl-sky", "l-surface", 1.2],
  ["l-hl-rose", "l-surface", 1.2],
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
    expect(
      start,
      "the stylesheet must still have a §7 reading column",
    ).toBeGreaterThan(-1);
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
    const langRule = CSS.slice(
      CSS.indexOf(":lang(ar)"),
      CSS.indexOf(":lang(ar)") + 260,
    );
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

  for (const [tint, page, min] of VISIBLE_AGAINST_PAGE) {
    it(`${tint} is visible against ${page} at ${min}:1`, () => {
      expect(colors[tint], `${name} is missing --${tint}`).toBeDefined();
      expect(colors[page], `${name} is missing --${page}`).toBeDefined();

      const ratio = contrast(colors[tint], colors[page]);
      expect(
        Number(ratio.toFixed(2)),
        `${colors[tint]} against ${colors[page]} is only ${ratio.toFixed(2)}:1 — ` +
          `a highlight this faint is invisible without colour vision`,
      ).toBeGreaterThanOrEqual(min);
    });
  }
});

/* ---------------------------------------------------------------------------
 * §3b — the collection overlays.
 *
 * These would otherwise ship UNMEASURED, and the reason is worth stating: the
 * parser above admits a block only if it declares `color-scheme`, which is
 * exactly right for telling a palette from the token `:root` — and exactly
 * wrong here, because a collection overlay deliberately declares no scheme. It
 * is not a scheme. It repaints the accent and the band on a subtree of a page
 * that is already in one.
 *
 * So an overlay is measured as what it actually is at runtime: its base palette
 * with a handful of tokens replaced. Merging is what makes that honest — an
 * overlay setting `--l-accent` and not `--l-on-accent` really does put the new
 * violet under the old palette's on-accent ink, and only the merged view can
 * fail on it.
 *
 * The SAME pair list runs, so a violet accent is held to the identical AA floor
 * as the blue it replaces, in all three modes.
 * ------------------------------------------------------------------------- */

type Overlay = {
  theme: string;
  collection: string;
  colors: Record<string, string>;
};

function overlays(css: string): Overlay[] {
  const found: Overlay[] = [];

  for (const match of css.matchAll(/([^{}]*?)\{([^{}]*?)\}/g)) {
    const [, selector, body] = match;
    // A collection overlay, not a palette: `data-collection` present and no
    // `color-scheme`, which is the line between the two.
    if (/color-scheme\s*:/.test(body)) continue;
    const scoped = selector.match(
      /\[data-theme="([a-z-]+)"\][^,{]*?\[data-collection="([a-z-]+)"\]/,
    );
    if (scoped === null) continue;

    const colors: Record<string, string> = {};
    for (const decl of body.matchAll(
      /--(l-[a-z-]+)\s*:\s*(#[0-9a-fA-F]{6})\s*;/g,
    )) {
      colors[decl[1]] = decl[2].toLowerCase();
    }
    if (Object.keys(colors).length === 0) continue;
    found.push({ theme: scoped[1], collection: scoped[2], colors });
  }

  return found;
}

/** One entry per (theme, collection), with the overlay merged over its base. */
const MERGED = (() => {
  const seen = new Map<string, Palette>();

  for (const overlay of overlays(CSS)) {
    const base = FOUND.find((p) => p.name === overlay.theme);
    expect(
      base,
      `overlay [data-collection="${overlay.collection}"] names an unknown theme "${overlay.theme}"`,
    ).toBeDefined();
    seen.set(`${overlay.collection} on ${overlay.theme}`, {
      name: `${overlay.collection} on ${overlay.theme}`,
      colors: { ...base!.colors, ...overlay.colors },
    });
  }

  return [...seen.values()];
})();

describe("the collection overlays", () => {
  it("covers every theme it appears in", () => {
    // A collection painted on two of three themes is worse than one painted on
    // none: the reader who picks the third gets a violet page with a blue
    // accent, and nothing in the build says so.
    const byCollection = new Map<string, Set<string>>();
    for (const overlay of overlays(CSS)) {
      const themes = byCollection.get(overlay.collection) ?? new Set<string>();
      themes.add(overlay.theme);
      byCollection.set(overlay.collection, themes);
    }

    const every = FOUND.map((p) => p.name).sort();
    for (const [collection, themes] of byCollection) {
      expect(
        [...themes].sort(),
        `[data-collection="${collection}"] is declared for some themes but not all`,
      ).toEqual(every);
    }
  });

  it("repaints only the accent and the band, never the page", () => {
    // The page's surfaces and inks belong to the reader's THEME. A collection
    // that moved them would be a fourth theme reached by a different attribute,
    // and the two would then disagree about what the site looks like.
    const allowed =
      /^l-(accent|accent-hover|accent-soft|on-accent|display|band|on-band|band-muted|band-ornament)$/;

    for (const overlay of overlays(CSS)) {
      for (const token of Object.keys(overlay.colors)) {
        expect(
          token,
          `[data-collection="${overlay.collection}"] sets --${token}; a collection may set only accent and band tokens`,
        ).toMatch(allowed);
      }
    }
  });
});

describe.each(MERGED)("$name", ({ name, colors }) => {
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

/* ---------------------------------------------------------------------------
 * §6 — the deck, which must be the COLLECTION's colour and not a grey.
 *
 * The Listen tab's panel was first filled with `--l-sunken`, the palette's
 * recessed surface. It only looked right in the dark: on paper `--l-sunken` is a
 * warm grey a shade off the page, so the deck read as a dull slab with the
 * artwork tiles as the one coloured thing on it (Asif, 2026-08-11).
 *
 * The fix was to derive every surface in it from `--l-accent`, which the
 * collection overlay in §3b has already redefined by the time these resolve —
 * so a session's deck is violet and a book's is blue with no second rule
 * anywhere and no palette value repeated outside §3.
 *
 * That is a property of the STYLESHEET, not of one screenshot, so it is asserted
 * here: a later "tidy" that puts a neutral back would pass every rendering test
 * and quietly undo it.
 * ------------------------------------------------------------------------- */

describe("the deck takes its colour from the collection", () => {
  /**
   * One rule's DECLARATIONS, by selector — comments stripped.
   *
   * Stripped because the assertions below are about what the rule DOES, and
   * every one of these rules explains in a comment which neutral it replaced.
   * A test that reads the explanation as the thing it forbids fails on the
   * sentence saying the failure was fixed.
   */
  const ruleFor = (selector: string): string => {
    const at = CSS.indexOf(`\n  ${selector} {`);
    expect(at, `the stylesheet has no rule for ${selector}`).toBeGreaterThan(
      -1,
    );
    return CSS.slice(at, CSS.indexOf("\n  }", at)).replace(
      /\/\*[\s\S]*?\*\//g,
      "",
    );
  };

  for (const selector of [
    ".pf-deck__list",
    ".pf-track__art",
    ".pf-track:hover",
  ]) {
    it(`${selector} is painted from --l-accent`, () => {
      expect(ruleFor(selector)).toContain("--l-accent");
    });

    it(`${selector} uses no neutral fill and no literal colour`, () => {
      const body = ruleFor(selector);
      // `--l-sunken` is the grey this replaced. A hex here would be a colour
      // declared outside §3, which is the one thing the theme forbids.
      expect(body).not.toContain("--l-sunken");
      expect(body).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
    });
  }

  it("the artwork's depth is a scalar the page sets, never a colour", () => {
    // `--pf-art` carries a NUMBER. If a future change passed a colour instead,
    // a session's tiles would stop following the collection overlay.
    const body = ruleFor(".pf-track__art");
    expect(body).toContain("var(--pf-art");
    expect(body).toContain("calc(var(--pf-art");
  });
});
