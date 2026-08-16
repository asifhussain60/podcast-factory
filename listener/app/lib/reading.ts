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
export const readingMinutes = (words: number): number =>
  Math.max(1, Math.round(words / 220));

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
export const FAMILIES = [
  "prose",
  "merriweather",
  "ui",
  "atkinson",
  "lexend",
  "dyslexic",
] as const;
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
/**
 * How wide the reading surface runs. Three steps, today's as the smallest
 * (Asif, 2026-08-06).
 *
 * The number is the COLUMN, in `ch`, and it is what a reader sees change. But a
 * column cannot grow past the sheet it is set on, and the sheet had a fixed cap
 * of 56rem — so on a 2000px desktop the widest column available was still
 * printed in the same narrow leaf with the rest of the window empty, and the
 * setting spent its top step doing nothing. `MEASURE_SHEET` moves the sheet with
 * it; the two are one setting with two variables behind it, never two controls.
 *
 * 58ch is gone with the old scale. It was the narrowest of three and this scale
 * starts where that one sat by default, which is what "the current one as the
 * smallest" means. A reader who had chosen it is moved to Standard by
 * `storedReading`, which validates against this list — a silent widening rather
 * than a broken page.
 */
export const MEASURES = [68, 84, 100] as const;

/**
 * The sheet each column width is printed on.
 *
 * Not derived with `calc`. `ch` resolves against the font of the element it is
 * used on, and the sheet is not set in the reading face — so a computed sheet
 * would be measured in the wrong glyph and drift from its own column as the
 * reading typeface changed. These are measured pairs: each keeps the same slack
 * between column and sheet edge that 68ch/56rem has today, so the printer's
 * margin looks the same at every step instead of growing with the page.
 */
export const MEASURE_SHEET: Record<(typeof MEASURES)[number], string> = {
  68: "56rem",
  84: "66rem",
  100: "76rem",
};

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
 * the three spacing buttons. `MEASURE_LABELS` below names a DIFFERENT setting
 * and shares no word with these, so neither control can state its value in a
 * word the other also uses: spacing announces "Wide line spacing", width
 * announces "Widest page width". Two settings that both read "Normal" with
 * nothing to tell them apart is what forced the width control off the toolbar
 * once already.
 */
export const LEADING_LABELS: Record<(typeof LEADINGS)[number], string> = {
  1.5: "Compact",
  1.7: "Normal",
  1.9: "Wide",
};

/**
 * How wide the surface runs. A different question from how far apart its lines
 * sit — and deliberately worded so the two can never be confused by ear.
 *
 * Spacing is Compact/Normal/Wide. If width were Narrow/Standard/Wide the pair
 * would share a "Wide", which is the collision that took the width control off
 * this toolbar once already. Standard/Wider/Widest shares no word with it at
 * all, so no button anywhere in the row needs the other's name to disambiguate.
 */
export const MEASURE_LABELS: Record<(typeof MEASURES)[number], string> = {
  68: "Standard",
  84: "Wider",
  100: "Widest",
};

export interface ReadingPrefs {
  family: Family;
  size: number;
  leading: number;
  measure: number;
  /**
   * The source-reference toggle: shows each chapter's page range in the
   * original source book, under the chapter title, when that chapter has one.
   * Off by default and deliberately not a CSS custom property like the four
   * above it — it does not change how the text is set, only whether one quiet
   * line appears above it — so `applyReading` never touches it and there is no
   * pre-paint script entry for it; the control simply catches up to the
   * stored value the same one effect later that `family`/`size` do.
   */
  showSourceRefs: boolean;
}

export const DEFAULT_PREFS: ReadingPrefs = {
  family: "prose",
  size: 19,
  leading: 1.7,
  measure: 68,
  showSourceRefs: false,
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
 * nothing to show that the two lists had drifted apart. `MEASURE_SHEET` is
 * interpolated for the same reason, and it matters more here: the sheet is the
 * widest thing on the page, so a stored Widest that only arrived at hydration
 * would reflow the whole chapter under the reader rather than one paragraph.
 */
export const READING_INIT_SCRIPT = `(function(){try{var p=JSON.parse(localStorage.getItem(${JSON.stringify(
  READING_STORAGE_KEY,
)})||"{}");var s=document.documentElement.style;var f=${JSON.stringify(
  FAMILY_VAR,
)}[p.family];if(f)s.setProperty("--l-reading-family",f);if(p.size)s.setProperty("--l-reading-size",p.size+"px");if(p.leading)s.setProperty("--l-reading-leading",String(p.leading));if(p.measure){s.setProperty("--l-reading-measure",p.measure+"ch");var w=${JSON.stringify(
  MEASURE_SHEET,
)}[p.measure];if(w)s.setProperty("--pf-measure-reader",w)}}catch(e){}})();`;

export function applyReading(prefs: ReadingPrefs) {
  const style = document.documentElement.style;
  style.setProperty("--l-reading-family", FAMILY_VAR[prefs.family]);
  style.setProperty("--l-reading-size", `${prefs.size}px`);
  style.setProperty("--l-reading-leading", String(prefs.leading));
  style.setProperty("--l-reading-measure", `${prefs.measure}ch`);
  // The sheet moves with its column, or the top of the scale is white space.
  const sheet = MEASURE_SHEET[prefs.measure as keyof typeof MEASURE_SHEET];
  if (sheet) style.setProperty("--pf-measure-reader", sheet);

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
      leading: LEADINGS.includes(raw.leading)
        ? raw.leading
        : DEFAULT_PREFS.leading,
      measure: MEASURES.includes(raw.measure)
        ? raw.measure
        : DEFAULT_PREFS.measure,
      showSourceRefs:
        typeof raw.showSourceRefs === "boolean"
          ? raw.showSourceRefs
          : DEFAULT_PREFS.showSourceRefs,
    };
  } catch {
    return DEFAULT_PREFS;
  }
}

/** The next value in a stepped scale, clamped at both ends. */
export function step<T extends number>(
  scale: readonly T[],
  current: T,
  direction: 1 | -1,
): T {
  const i = scale.indexOf(current);
  const next = Math.min(
    scale.length - 1,
    Math.max(0, (i === -1 ? 0 : i) + direction),
  );
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
