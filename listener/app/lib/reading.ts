/**
 * Reading preferences — family, size, leading and measure.
 *
 * Colour is NOT here: theme is a whole-site choice and lives in lib/theme.ts.
 * These four are the reader's own typography, applied by overriding the
 * `--l-reading-*` custom properties on `<html>` so the CSS keeps one source of
 * truth and no component reads a preference directly.
 *
 * Everything is a discrete step, never a continuous slider. A slider is
 * unusable one-handed on a phone, which is where most of this reading happens.
 */

export const READING_STORAGE_KEY = "pf-reading";

/**
 * Roughly how long a chapter takes to read, in whole minutes.
 *
 * 220 wpm is a common figure for adult non-fiction, rounded down deliberately —
 * this prose is dense and quoted in two scripts, so a fast estimate would be
 * flattering rather than useful. Never shown as "0 minutes".
 *
 * It lives HERE, not in catalog.server.ts, because the chapter list and the
 * reading header both display it: a component importing a `.server` module for
 * one pure function is a build error, by design.
 */
export const readingMinutes = (words: number): number => Math.max(1, Math.round(words / 220));

/**
 * The faces the reading column can be set in.
 *
 * Ordered as the picker reads them: the two serifs, the two plain sans faces,
 * then the two drawn for a specific difficulty. Every one is self-hosted, so
 * the same six exist on a phone, a tablet and a desktop — a picker whose
 * options depend on the machine offers a setting that does nothing on half of
 * them.
 *
 * `prose` and `ui` are named for their ROLE rather than for the face, and the
 * later ones for the face itself. The inconsistency is deliberate: those two
 * keys are already written into every reader's stored preferences, and renaming
 * them would silently reset the setting of anyone who had chosen one.
 */
export const FAMILIES = ["prose", "merriweather", "ui", "atkinson", "lexend", "dyslexic"] as const;
export type Family = (typeof FAMILIES)[number];

export const FAMILY_LABELS: Record<Family, string> = {
  prose: "Literata",
  merriweather: "Merriweather",
  ui: "Inter",
  atkinson: "Atkinson",
  lexend: "Lexend",
  dyslexic: "OpenDyslexic",
};

/** px. Wide enough to matter on a phone, capped before the measure breaks. */
export const SIZES = [16, 17, 18, 19, 21, 23, 26] as const;
export const LEADINGS = [1.5, 1.7, 1.9] as const;
export const MEASURES = [58, 68, 78] as const;

/**
 * The words for the setting whose values are numbers nobody thinks in.
 *
 * `1.7` is what the CSS wants; "Normal" is what a reader wants. The labels live
 * HERE, beside the scale, because they used to be written out as a positional
 * array at the control — `["Compact", "Normal", "Wide"][i]` — which silently
 * mislabels every value the moment a fourth step is inserted anywhere but the
 * end. Keyed by value, so an inserted step is a compile error rather than a page
 * that calls Wide "Normal".
 *
 * Compact/Normal/Wide are Asif's words (2026-08-04), and they are the ones on
 * the three buttons. `MEASURE_LABELS` below says narrow/standard/wide for a
 * DIFFERENT setting, so neither control ever states its value in a bare word:
 * the buttons announce "Wide line spacing" and the select is labelled "Line
 * width". Two settings that both read "Normal" with nothing to tell them apart
 * is what forced the width control off the toolbar once already.
 */
export const LEADING_LABELS: Record<(typeof LEADINGS)[number], string> = {
  1.5: "Compact",
  1.7: "Normal",
  1.9: "Wide",
};

/** How wide the column runs. A different question from how far apart its lines sit. */
export const MEASURE_LABELS: Record<(typeof MEASURES)[number], string> = {
  58: "Narrow",
  68: "Standard",
  78: "Wide",
};

export interface ReadingPrefs {
  family: Family;
  size: number;
  leading: number;
  measure: number;
}

export const DEFAULT_PREFS: ReadingPrefs = {
  family: "prose",
  size: 19,
  leading: 1.7,
  measure: 68,
};

/**
 * The custom property each choice maps to. Exported so a test can prove every
 * one of them is actually declared in the stylesheet — a family named here with
 * no token behind it silently falls back to the browser's default, which looks
 * like the picker not working rather than like a missing line of CSS.
 */
export const FAMILY_VAR: Record<Family, string> = {
  prose: "var(--l-font-prose)",
  merriweather: "var(--l-font-merriweather)",
  ui: "var(--l-font-ui)",
  atkinson: "var(--l-font-atkinson)",
  lexend: "var(--l-font-lexend)",
  dyslexic: "var(--l-font-dyslexic)",
};

/**
 * Runs before first paint, inlined into <head> beside the theme script.
 *
 * Without it a stored 23px setting renders at 19px and jumps on hydration —
 * mid-paragraph, which loses the reader's place. Same reasoning as the theme
 * script, and the same deliberate lack of dependencies.
 *
 * The face map is INTERPOLATED from `FAMILY_VAR` rather than written out again.
 * It used to be a second copy of it, hand-kept in a string — so adding a face
 * left anyone who chose it seeing Literata until hydration, on every load, with
 * nothing to show that the two lists had drifted apart.
 */
export const READING_INIT_SCRIPT = `(function(){try{var p=JSON.parse(localStorage.getItem(${JSON.stringify(
  READING_STORAGE_KEY,
)})||"{}");var s=document.documentElement.style;var f=${JSON.stringify(
  FAMILY_VAR,
)}[p.family];if(f)s.setProperty("--l-reading-family",f);if(p.size)s.setProperty("--l-reading-size",p.size+"px");if(p.leading)s.setProperty("--l-reading-leading",String(p.leading));if(p.measure)s.setProperty("--l-reading-measure",p.measure+"ch")}catch(e){}})();`;

export function applyReading(prefs: ReadingPrefs) {
  const style = document.documentElement.style;
  style.setProperty("--l-reading-family", FAMILY_VAR[prefs.family]);
  style.setProperty("--l-reading-size", `${prefs.size}px`);
  style.setProperty("--l-reading-leading", String(prefs.leading));
  style.setProperty("--l-reading-measure", `${prefs.measure}ch`);

  try {
    localStorage.setItem(READING_STORAGE_KEY, JSON.stringify(prefs));
  } catch {
    // Storage disabled. The setting still applies to this page view.
  }
}

/** What is stored, falling back per-field so a partial or corrupt value is safe. */
export function storedReading(): ReadingPrefs {
  try {
    const raw = JSON.parse(localStorage.getItem(READING_STORAGE_KEY) || "{}");
    return {
      family: FAMILIES.includes(raw.family) ? raw.family : DEFAULT_PREFS.family,
      size: SIZES.includes(raw.size) ? raw.size : DEFAULT_PREFS.size,
      leading: LEADINGS.includes(raw.leading) ? raw.leading : DEFAULT_PREFS.leading,
      measure: MEASURES.includes(raw.measure) ? raw.measure : DEFAULT_PREFS.measure,
    };
  } catch {
    return DEFAULT_PREFS;
  }
}

/** The next value in a stepped scale, clamped at both ends. */
export function step<T extends number>(scale: readonly T[], current: T, direction: 1 | -1): T {
  const i = scale.indexOf(current);
  const next = Math.min(scale.length - 1, Math.max(0, (i === -1 ? 0 : i) + direction));
  return scale[next];
}

/* ---------------------------------------------------------------------------
 * One copy of the current setting, for however many controls are on screen.
 *
 * There is one today — the reader's toolbar — but there were two, and the reason
 * for a shared store outlives them: each holding its own `useState` seeded from
 * localStorage would mean raising the size in one and watching the other still
 * read 19, both writing the same key and disagreeing about what it said.
 *
 * Deliberately NOT seeded from storage at module load. The first render has to
 * match what the server produced or React logs a hydration mismatch, so the
 * snapshot starts at the defaults and `hydrateReading` swaps in the stored
 * value from an effect. The text itself is never wrong in the meantime —
 * READING_INIT_SCRIPT applied the real values to the custom properties before
 * first paint; it is only the NUMBER in the control that catches up.
 * ------------------------------------------------------------------------- */

let snapshot: ReadingPrefs = DEFAULT_PREFS;
const listeners = new Set<() => void>();

export function readingSnapshot(): ReadingPrefs {
  return snapshot;
}

export function subscribeReading(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Apply, persist, and tell every control on screen. */
export function setReading(prefs: ReadingPrefs) {
  snapshot = prefs;
  applyReading(prefs);
  for (const listener of listeners) listener();
}

/** Called once after mount, to pick up what the last visit chose. */
export function hydrateReading() {
  snapshot = storedReading();
  for (const listener of listeners) listener();
}
