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
    <div
      role="group"
      aria-label="Colour theme"
      className="inline-flex items-center gap-1 rounded-xl border border-pf-rule bg-pf-surface p-1"
    >
      {THEMES.map((t) => {
        const active = theme === t;
        return (
          <button
            key={t}
            type="button"
            onClick={() => choose(t)}
            aria-pressed={active}
            className={[
              "rounded-md px-3 py-1.5 text-sm transition-colors",
              active
                ? "bg-pf-accent text-pf-on-accent"
                : "text-pf-muted hover:bg-pf-sunken hover:text-pf-ink",
            ].join(" ")}
          >
            {THEME_LABELS[t]}
          </button>
        );
      })}
    </div>
  );
}
