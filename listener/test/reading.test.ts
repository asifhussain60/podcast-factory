import { readFileSync } from "node:fs";

import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  DEFAULT_PREFS,
  FAMILIES,
  FAMILY_LABELS,
  FAMILY_VAR,
  MEASURE_LABELS,
  MEASURE_SHEET,
  MEASURES,
  READING_INIT_SCRIPT,
  hydrateReading,
  readingSnapshot,
  setReading,
  SIZES,
  step,
  subscribeReading,
} from "../app/lib/reading";

/**
 * The reading setting is shared, and this is what makes that a fact.
 *
 * There are two controls on a chapter page — the bar above the sheet, and the
 * fuller panel behind "Aa" — and before the store existed each held its own
 * `useState` seeded from the same localStorage key. Raising the size in one left
 * the other reading 19, and whichever was touched last silently overwrote the
 * other's idea of every OTHER field. These tests are the reason that cannot
 * come back.
 */

const store: Record<string, string> = {};

beforeEach(() => {
  for (const key of Object.keys(store)) delete store[key];
  vi.stubGlobal("localStorage", {
    getItem: (k: string) => store[k] ?? null,
    setItem: (k: string, v: string) => {
      store[k] = v;
    },
  });
  vi.stubGlobal("document", {
    documentElement: { style: { setProperty: () => {} } },
  });
  setReading(DEFAULT_PREFS);
});

describe("the shared reading store", () => {
  it("tells every subscriber about a change, not just the one that made it", () => {
    const a = vi.fn();
    const b = vi.fn();
    subscribeReading(a);
    subscribeReading(b);

    setReading({ ...readingSnapshot(), size: 23 });

    expect(a).toHaveBeenCalled();
    expect(b).toHaveBeenCalled();
    expect(readingSnapshot().size).toBe(23);
  });

  it("hands both controls the SAME object, so neither can hold a stale copy", () => {
    setReading({ ...DEFAULT_PREFS, size: 17 });
    expect(readingSnapshot()).toBe(readingSnapshot());
    expect(readingSnapshot().size).toBe(17);
  });

  it("changes one field without dropping the others", () => {
    setReading({ ...DEFAULT_PREFS, measure: 100, leading: 1.9 });
    setReading({ ...readingSnapshot(), family: "ui" });

    expect(readingSnapshot()).toMatchObject({
      family: "ui",
      measure: 100,
      leading: 1.9,
    });
  });

  it("stops notifying once a control unsubscribes", () => {
    const gone = vi.fn();
    subscribeReading(gone)();
    setReading({ ...DEFAULT_PREFS, size: 21 });
    expect(gone).not.toHaveBeenCalled();
  });

  it("never reads storage on its own — only when hydration asks it to", () => {
    // This is what keeps the first client render equal to the server's. A
    // snapshot that quietly picked up a stored 26px would differ from what SSR
    // produced and log a hydration mismatch on every chapter page.
    store["pf-reading"] = JSON.stringify({ ...DEFAULT_PREFS, size: 26 });
    expect(readingSnapshot()).toEqual(DEFAULT_PREFS);
  });

  it("picks up the stored value once hydrated", () => {
    store["pf-reading"] = JSON.stringify({ ...DEFAULT_PREFS, size: 26 });
    const told = vi.fn();
    subscribeReading(told);

    hydrateReading();

    expect(readingSnapshot().size).toBe(26);
    expect(told).toHaveBeenCalled();
  });
});

describe("the size stepper", () => {
  it("clamps at both ends rather than running off the scale", () => {
    expect(step(SIZES, SIZES[0], -1)).toBe(SIZES[0]);
    expect(step(SIZES, SIZES[SIZES.length - 1], 1)).toBe(
      SIZES[SIZES.length - 1],
    );
  });

  it("moves one step at a time in each direction", () => {
    expect(step(SIZES, SIZES[2], 1)).toBe(SIZES[3]);
    expect(step(SIZES, SIZES[2], -1)).toBe(SIZES[1]);
  });
});

describe("the typeface list", () => {
  // Was a hardcoded list of three names, which had to be edited every time a
  // face was added and never checked the thing that actually breaks. This
  // asserts the invariant instead: every choice in the picker resolves to a
  // custom property the stylesheet declares, and carries a name a reader can
  // recognise. A family with no token behind it falls back to the browser's
  // default, which looks like the picker not working.
  const CSS = readFileSync(
    new URL("../app/styles/podcast-factory.css", import.meta.url),
    "utf8",
  );

  it("maps every family to a token the stylesheet declares", () => {
    for (const family of FAMILIES) {
      const token = FAMILY_VAR[family].replace(/^var\(|\)$/g, "");
      expect(FAMILY_VAR[family], `${family} has no token`).toMatch(
        /^var\(--l-font-[a-z-]+\)$/,
      );
      expect(CSS, `${token} is never declared`).toContain(`${token}:`);
    }
  });

  it("gives every family a label, and no two the same", () => {
    const labels = FAMILIES.map((f) => FAMILY_LABELS[f]);
    expect(labels.filter(Boolean)).toHaveLength(FAMILIES.length);
    expect(new Set(labels).size).toBe(FAMILIES.length);
  });

  // The pre-paint script carries its own copy of the map, interpolated rather
  // than written out. This is what proves the interpolation still happens: a
  // hand-written copy that fell behind would show the wrong face until
  // hydration, on every load, with nothing to say the two had drifted.
  it("applies every family before first paint", () => {
    for (const family of FAMILIES) {
      expect(READING_INIT_SCRIPT).toContain(
        `"${family}":"${FAMILY_VAR[family]}"`,
      );
    }
  });
});

describe("the page width scale", () => {
  const CSS = readFileSync(
    new URL("../app/styles/podcast-factory.css", import.meta.url),
    "utf8",
  );

  it("starts at the width the reader has today", () => {
    // "The current one as the smallest" (Asif, 2026-08-06). If a narrower step
    // is ever put in front of this one, the setting stops being three ways to
    // use MORE of the window and goes back to being a line-length preference.
    expect(MEASURES[0]).toBe(DEFAULT_PREFS.measure);
    expect(MEASURE_SHEET[MEASURES[0]]).toBe("56rem");
  });

  it("keeps two book-like widths and makes Widest a full reading canvas", () => {
    expect(MEASURE_SHEET).toEqual({
      68: "56rem",
      84: "66rem",
      100: "112rem",
    });
    expect(CSS).toContain("max-width: calc(100vw - 4rem)");
    expect(CSS).toContain(
      "max-width: min(var(--l-reading-measure), calc(100vw - 20rem))",
    );
  });

  it("only ever gets wider", () => {
    const rem = (value: string) => Number.parseFloat(value);
    for (let i = 1; i < MEASURES.length; i++) {
      expect(MEASURES[i]).toBeGreaterThan(MEASURES[i - 1]);
      expect(rem(MEASURE_SHEET[MEASURES[i]])).toBeGreaterThan(
        rem(MEASURE_SHEET[MEASURES[i - 1]]),
      );
    }
  });

  it("moves the sheet with the column, every step", () => {
    // THE reason this is a scale of pairs. A column cannot grow past the sheet
    // it is printed on, so a step that widened only the column would spend
    // itself against a 56rem cap and change nothing a reader could see.
    for (const measure of MEASURES) {
      expect(MEASURE_SHEET[measure], `${measure}ch has no sheet`).toMatch(
        /^\d+rem$/,
      );
    }
  });

  it("overrides a sheet width the stylesheet actually declares", () => {
    // Same invariant the typeface list holds: a custom property written by a
    // control but never declared in the CSS silently does nothing.
    expect(CSS).toContain("--pf-measure-reader:");
    expect(CSS).toContain("max-width: var(--pf-measure-reader)");
  });

  it("only offers width choices when all three sheets can change", () => {
    // From 1024px the three measures receive different responsive caps while
    // the persistent toolbar gutter remains protected. The control therefore
    // stays available without offering two buttons that render the same page.
    expect(CSS).toContain("@media (min-width: 1024px)");
    expect(CSS).toMatch(
      /@media \(min-width: 1024px\)[\s\S]*?\.pf-stepper--wide-only\s*{[\s\S]*?display: inline-flex/,
    );
    for (const measure of MEASURES) {
      expect(CSS).toContain(
        `.pf-reader:has(.pf-toolbar[data-measure="${measure}"]) .pf-reader-page`,
      );
    }
  });

  it("keeps responsive page widths monotonic around toolbar changes", () => {
    // The compact panel lasts until its protected width tier ends. The full
    // panel starts at 1792px and the two-column panel at 2240px, so crossing
    // either boundary changes only the chrome and never makes the reading page
    // narrower.
    expect(CSS).toContain("@media (min-width: 768px) and (max-width: 1791px)");
    expect(CSS).toContain("@media (min-width: 1792px) and (max-width: 2239px)");
    expect(CSS).toContain("@media (min-width: 2240px)");
  });

  it("keeps side-rail actions vertical when the tablet layout moves left", () => {
    // Split into two rules 2026-09-02: an ordinary laptop or monitor at
    // 1024px+ is reliably landscape, so that half is unconditional; a tablet
    // held in portrait at 768-1023px is checked separately, gated on
    // `orientation: portrait` so a phone lying on its side in that same
    // width range is not mistaken for one (see the CSS comment beside
    // `.pf-toolbar-rail`). Both still put the actions back in a column.
    expect(CSS).toMatch(
      /@media \(min-width: 1024px\) and \(max-width: 1791px\)[\s\S]*?\.pf-reader-actions\s*{[\s\S]*?flex-direction: column/,
    );
    expect(CSS).toMatch(
      /@media \(min-width: 768px\) and \(max-width: 1023px\) and \(orientation: portrait\)[\s\S]*?\.pf-reader-actions\s*{[\s\S]*?flex-direction: column/,
    );
  });

  it("applies the sheet before first paint", () => {
    // The sheet is the widest thing on the page. Arriving only at hydration
    // would reflow the whole chapter under the reader rather than one line.
    for (const measure of MEASURES) {
      expect(READING_INIT_SCRIPT).toContain(
        `"${measure}":"${MEASURE_SHEET[measure]}"`,
      );
    }
    expect(READING_INIT_SCRIPT).toContain("--pf-measure-reader");
  });

  it("gives every step a label, and no two the same", () => {
    const labels = MEASURES.map((m) => MEASURE_LABELS[m]);
    expect(labels.filter(Boolean)).toHaveLength(MEASURES.length);
    expect(new Set(labels).size).toBe(MEASURES.length);
  });
});
