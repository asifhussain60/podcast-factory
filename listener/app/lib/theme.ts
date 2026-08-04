/**
 * Every theme this build ships, in the order the picker offers them.
 *
 * This array is the ONLY list. The init script below serialises it rather than
 * repeating the names, and `isTheme` is what every other check calls — because
 * the names used to be written out again in two more places, which meant adding
 * a fourth theme silently produced one the picker offered and the pre-paint
 * script refused to restore. Adding a theme is now this line plus a palette
 * block in §3 of app/styles/podcast-factory.css.
 */
export const THEMES = ["light", "sepia", "dark"] as const;
export type Theme = (typeof THEMES)[number];

export const THEME_STORAGE_KEY = "pf-theme";

export const THEME_LABELS: Record<Theme, string> = {
  light: "Light",
  sepia: "Sepia",
  dark: "Dark",
};

/**
 * Runs before first paint, inlined into <head>. Without it the page renders in
 * the default light theme and then snaps to the reader's choice — exactly the
 * flash a dark-theme reader notices at night.
 *
 * It ALWAYS stamps `data-theme`, resolving the stored choice first and falling
 * back to the system preference. theme.css has no `prefers-color-scheme` block
 * precisely because this runs — which keeps each palette declared exactly once
 * instead of twice, so a colour fix cannot land on half of them.
 *
 * Deliberately tiny and dependency-free: it is the only script that must
 * execute before hydration.
 */
export const THEME_INIT_SCRIPT = `(function(){try{var k=${JSON.stringify(
  THEME_STORAGE_KEY,
)};var a=${JSON.stringify(
  THEMES,
)};var t=localStorage.getItem(k);if(a.indexOf(t)<0){t=window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"}document.documentElement.setAttribute("data-theme",t)}catch(e){document.documentElement.setAttribute("data-theme","light")}})();`;

/** Whether a stored or stamped value is one of the themes this build ships. */
export function isTheme(value: string | null): value is Theme {
  return value !== null && (THEMES as readonly string[]).includes(value);
}

export function applyTheme(theme: Theme) {
  document.documentElement.setAttribute("data-theme", theme);
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // Private browsing, or storage disabled. The theme still applies for this
    // page view; only the memory of it is lost.
  }
}

/** What the document is showing right now. */
export function currentTheme(): Theme {
  const attr = document.documentElement.getAttribute("data-theme");
  if (isTheme(attr)) return attr;
  // Only reachable if the init script was blocked; mirror its fallback.
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/* ---------------------------------------------------------------------------
 * One copy of the current theme, for however many controls are on screen.
 *
 * This is the same external store `lib/reading.ts` uses, and it is here for the
 * same reason. Until now the theme picker held its own `useState`, which was
 * fine while it appeared once — inside the settings panel. The reader toolbar now
 * carries theme alongside typography, so two pickers can be mounted at once and
 * two independent `useState`s would let one show Sepia while the document, and
 * the other picker, said Dark.
 *
 * The snapshot starts at `light` on BOTH server and client, exactly as the
 * reading store starts at its defaults: the first client render has to match the
 * server's or React logs a hydration mismatch. `hydrateTheme` reads the real
 * value from an effect. The page is never wrong in the meantime — THEME_INIT_
 * SCRIPT stamped `data-theme` before first paint, so only the highlighted chip
 * in the control catches up.
 * ------------------------------------------------------------------------- */

let snapshot: Theme = "light";
const listeners = new Set<() => void>();

export const themeSnapshot = (): Theme => snapshot;

export function subscribeTheme(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Apply, persist, and tell every control on screen. */
export function setTheme(theme: Theme) {
  snapshot = theme;
  applyTheme(theme);
  for (const listener of listeners) listener();
}

/** Called once after mount, to pick up what the pre-paint script resolved. */
export function hydrateTheme() {
  snapshot = currentTheme();
  for (const listener of listeners) listener();
}
