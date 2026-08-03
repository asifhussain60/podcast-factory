import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  DEFAULT_PREFS,
  FAMILIES,
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
  vi.stubGlobal("document", { documentElement: { style: { setProperty: () => {} } } });
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
    setReading({ ...DEFAULT_PREFS, measure: 78, leading: 1.9 });
    setReading({ ...readingSnapshot(), family: "ui" });

    expect(readingSnapshot()).toMatchObject({ family: "ui", measure: 78, leading: 1.9 });
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
    expect(step(SIZES, SIZES[SIZES.length - 1], 1)).toBe(SIZES[SIZES.length - 1]);
  });

  it("moves one step at a time in each direction", () => {
    expect(step(SIZES, SIZES[2], 1)).toBe(SIZES[3]);
    expect(step(SIZES, SIZES[2], -1)).toBe(SIZES[1]);
  });
});

describe("the typeface list", () => {
  it("offers exactly the families the theme declares a token for", () => {
    // The dropdown renders straight from FAMILIES; a name here with no
    // `--l-font-*` behind it would silently fall back to the browser default.
    expect([...FAMILIES]).toEqual(["prose", "ui", "dyslexic"]);
  });
});
