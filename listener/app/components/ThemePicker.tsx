import { useEffect, useSyncExternalStore } from "react";

import {
  hydrateTheme,
  setTheme,
  subscribeTheme,
  THEME_LABELS,
  THEMES,
  themeSnapshot,
  type Theme,
} from "~/lib/theme";

/**
 * The current theme, shared by every control on the page.
 *
 * Mirrors `useReading` in components/useReading.ts, down to passing `themeSnapshot`
 * as both `getSnapshot` and `getServerSnapshot`: the store starts at the same
 * value on both sides, so the first client render agrees with the server's and
 * there is no hydration mismatch. The real value arrives one effect later.
 */
export function useTheme(): Theme {
  const theme = useSyncExternalStore(subscribeTheme, themeSnapshot, themeSnapshot);
  useEffect(hydrateTheme, []);
  return theme;
}

/**
 * Three swatches, not a dropdown.
 *
 * `compact` drops the words for single letters. The reader toolbar is one row
 * carrying five control groups, and "Light Sepia Dark" spelled out is a third of
 * a phone's width for a setting most readers touch once. The full labels stay
 * everywhere the row is not the constraint, and the accessible name is the same
 * either way — the letter is `aria-hidden` and the real label rides on the
 * button, so a screen reader always hears "Sepia".
 */
export function ThemePicker({ compact = false }: { compact?: boolean }) {
  const theme = useTheme();

  return (
    <div
      role="group"
      aria-label="Colour theme"
      className={`pf-swatches${compact ? " pf-swatches--compact" : ""}`}
    >
      {THEMES.map((t) => (
        <button
          key={t}
          type="button"
          onClick={() => setTheme(t)}
          aria-pressed={theme === t}
          aria-label={compact ? THEME_LABELS[t] : undefined}
          title={compact ? THEME_LABELS[t] : undefined}
          className="pf-swatch"
        >
          <span aria-hidden={compact ? "true" : undefined}>
            {compact ? THEME_LABELS[t].charAt(0) : THEME_LABELS[t]}
          </span>
        </button>
      ))}
    </div>
  );
}
