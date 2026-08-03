import { useEffect, useState } from "react";
import { applyTheme, currentTheme, THEME_LABELS, THEMES, type Theme } from "~/lib/theme";

/**
 * Three swatches, not a dropdown — the reader settings sheet in phase 5 reuses
 * this control rather than growing a second one.
 */
export function ThemePicker() {
  const [theme, setTheme] = useState<Theme | null>(null);

  // Resolved after mount: the server cannot know what the device prefers, and
  // guessing produces a hydration mismatch.
  useEffect(() => setTheme(currentTheme()), []);

  function choose(next: Theme) {
    applyTheme(next);
    setTheme(next);
  }

  return (
    <div role="group" aria-label="Colour theme" className="pf-swatches">
      {THEMES.map((t) => (
        <button
          key={t}
          type="button"
          onClick={() => choose(t)}
          aria-pressed={theme === t}
          className="pf-swatch"
        >
          {THEME_LABELS[t]}
        </button>
      ))}
    </div>
  );
}
