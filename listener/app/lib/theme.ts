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
)};var t=localStorage.getItem(k);if(t!=="light"&&t!=="dark"&&t!=="sepia"){t=window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"}document.documentElement.setAttribute("data-theme",t)}catch(e){document.documentElement.setAttribute("data-theme","light")}})();`;

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
  if (attr === "light" || attr === "dark" || attr === "sepia") return attr;
  // Only reachable if the init script was blocked; mirror its fallback.
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}
