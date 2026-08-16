/**
 * Every setting a reader chooses survives closing the tab.
 *
 * Asif's requirement (2026-08-06): "user settings are remembered between
 * sessions — this should be for all sessions." The individual stores each have
 * their own tests; this one asks the question ACROSS them, which is the question
 * he asked and the one nothing was answering.
 *
 * The failure it exists to catch has a shape: a setting added to the UI and to
 * React state, and not to storage. It is invisible in every test that renders a
 * control and presses it, because within one page the setting works perfectly —
 * it is only wrong after a reload, which no unit test performs. The playback
 * speed was exactly this until today: a listener at 1.5x was returned to 1x by
 * every reload, on every episode, and nothing anywhere failed.
 *
 * So the assertion is deliberately structural rather than a list of keys: every
 * store that persists something must WRITE it, must READ it back through a
 * validator, and must apply it before first paint if it affects layout.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";

import {
  DEFAULT_PREFS,
  MEASURE_SHEET,
  MEASURES,
  READING_INIT_SCRIPT,
  READING_STORAGE_KEY,
  applyReading,
  storedReading,
} from "../app/lib/reading";
import { THEME_STORAGE_KEY } from "../app/lib/theme";

const PLAYER = readFileSync(
  new URL("../app/components/player/Player.tsx", import.meta.url),
  "utf8",
);

/** A real store, not a mock that always succeeds: these tests are about what
 *  comes BACK, so the same object has to answer both halves. Same shape the
 *  reading store's own suite uses. */
const store: Record<string, string> = {};
let throwOnWrite = false;

beforeEach(() => {
  for (const key of Object.keys(store)) delete store[key];
  throwOnWrite = false;
  vi.stubGlobal("localStorage", {
    getItem: (k: string) => store[k] ?? null,
    setItem: (k: string, v: string) => {
      if (throwOnWrite) throw new Error("QuotaExceededError");
      store[k] = v;
    },
  });
  vi.stubGlobal("document", {
    documentElement: { style: { setProperty: () => {} } },
  });
});

describe("the reading settings", () => {
  // All five in ONE key, so they cannot half-survive: a reader who set the
  // typeface and the width gets both back or neither, never one.
  const chosen = {
    family: "lexend" as const,
    size: 23,
    leading: 1.9,
    measure: 100,
    showSourceRefs: true,
  };

  it("writes every field a reader can change", () => {
    applyReading(chosen);
    expect(JSON.parse(localStorage.getItem(READING_STORAGE_KEY)!)).toEqual(
      chosen,
    );
  });

  it("reads every field back", () => {
    applyReading(chosen);
    expect(storedReading()).toEqual(chosen);
  });

  it("covers every field of the preferences object", () => {
    // The structural half. A fifth setting added to `ReadingPrefs` and to the
    // toolbar, but never written, fails HERE rather than in a reader's session.
    applyReading(chosen);
    const written = JSON.parse(localStorage.getItem(READING_STORAGE_KEY)!);
    for (const field of Object.keys(DEFAULT_PREFS)) {
      expect(Object.keys(written), `${field} is never persisted`).toContain(
        field,
      );
    }
  });

  it("falls back per field rather than losing the lot", () => {
    // One corrupt value must not reset the other three. A reader who somehow
    // stored an impossible size should keep their typeface.
    localStorage.setItem(
      READING_STORAGE_KEY,
      JSON.stringify({ ...chosen, size: 999 }),
    );
    expect(storedReading()).toEqual({ ...chosen, size: DEFAULT_PREFS.size });
  });

  it("survives a width step being retired", () => {
    // 58ch was a real stored value before 2026-08-06. It must widen to the
    // default, never render a page at a width the scale no longer has.
    localStorage.setItem(
      READING_STORAGE_KEY,
      JSON.stringify({ ...chosen, measure: 58 }),
    );
    expect(storedReading().measure).toBe(DEFAULT_PREFS.measure);
    expect(MEASURES).not.toContain(58);
  });

  it("restores the layout settings before first paint, not after", () => {
    // Size and width move the whole page. Applied only at hydration they reflow
    // the chapter under the reader; applied by the inline script they are simply
    // how the page arrives.
    for (const property of [
      "--l-reading-size",
      "--l-reading-measure",
      "--pf-measure-reader",
    ]) {
      expect(
        READING_INIT_SCRIPT,
        `${property} is not restored pre-paint`,
      ).toContain(property);
    }
    for (const measure of MEASURES) {
      expect(READING_INIT_SCRIPT).toContain(MEASURE_SHEET[measure]);
    }
  });

  it("is unreadable to nobody — a disabled store never throws", () => {
    // Safari private browsing throws on setItem. A reader there must still be
    // able to change a setting for the page they are on.
    throwOnWrite = true;
    expect(() => applyReading(chosen)).not.toThrow();
  });
});

describe("the theme", () => {
  it("has its own key, separate from the reading settings", () => {
    // Deliberately not one store. Theme is a whole-site choice and applies on
    // every page; the reading settings belong to the reading column.
    expect(THEME_STORAGE_KEY).not.toBe(READING_STORAGE_KEY);
  });
});

describe("the listening speed", () => {
  // Asserted against the SOURCE because the player cannot be rendered without an
  // <audio> element, a router and a session. What is being checked is the thing
  // that was actually missing — a write, a read, and a validator — not the DOM.
  it("is written when it is changed", () => {
    expect(PLAYER).toMatch(/localStorage\.setItem\(RATE_KEY/);
  });

  it("is read back and applied on mount", () => {
    expect(PLAYER).toMatch(/function loadRate\(\)/);
    expect(PLAYER).toMatch(/const stored = loadRate\(\)/);
  });

  it("validates against the rates the buttons offer", () => {
    // A stored 0 is a silent, unrecoverable pause; a rate between the buttons
    // lights none of them. It must check membership, not merely finiteness.
    expect(PLAYER).toMatch(
      /RATES as readonly number\[\]\)\.includes\(stored\)/,
    );
  });

  it("re-applies the speed when a new episode starts", () => {
    // Setting `element.src` resets `playbackRate` to 1. Without this the control
    // reads 1.5x while the audio plays at normal speed.
    expect(PLAYER).toMatch(/element\.playbackRate = rate;/);
  });
});
