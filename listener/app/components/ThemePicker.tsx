import { Fragment, useEffect, useSyncExternalStore } from "react";

import { Tooltip } from "~/components/Tooltip";
import {
  hydrateTheme,
  setTheme,
  subscribeTheme,
  THEME_LABELS,
  THEMES,
  themeSnapshot,
  type Theme,
} from "~/lib/theme";

/** The tooltip description for each dot — only shown in `compact` mode,
 * where the button carries no visible label of its own. */
const THEME_DESCRIPTIONS: Record<Theme, string> = {
  light: "A bright page, best in daylight",
  sepia: "A warm, paper-toned page that's easier on tired eyes",
  dark: "A dark page for reading in low light",
};

/**
 * The current theme, shared by every control on the page.
 *
 * Mirrors `useReading` in components/useReading.ts, down to passing `themeSnapshot`
 * as both `getSnapshot` and `getServerSnapshot`: the store starts at the same
 * value on both sides, so the first client render agrees with the server's and
 * there is no hydration mismatch. The real value arrives one effect later.
 */
export function useTheme(): Theme {
  const theme = useSyncExternalStore(
    subscribeTheme,
    themeSnapshot,
    themeSnapshot,
  );
  useEffect(hydrateTheme, []);
  return theme;
}

/**
 * Three swatches, not a dropdown.
 *
 * `compact` draws each theme as a DOT in that theme's own paper colour instead
 * of spelling its name. The reader toolbar is one row carrying five control
 * groups, and "Light Sepia Dark" written out is a third of a phone's width for a
 * setting most readers touch once. Letters were tried first and were worse than
 * either: an isolated "S" names nothing, and only the selected one was drawn as
 * a filled shape, so the control read as one dot beside two stray letters.
 *
 * **Each dot carries its own `data-theme`**, which is what lets it be painted in
 * a palette that is not the one currently applied. §3 declares every palette
 * under a `[data-theme="…"]` selector, so putting the attribute on the button
 * re-scopes `--l-bg` and `--l-rule` inside it to that theme's values. The
 * alternative was three more colour tokens duplicating what §3 already says,
 * which is exactly the second home for a palette that the stylesheet exists to
 * prevent. Adding a fourth theme still costs one block in §3 and nothing here.
 *
 * The accessible name is the same either way: the dot is empty and the label
 * rides on the button, so a screen reader always hears "Sepia".
 */
export function ThemePicker({ compact = false }: { compact?: boolean }) {
  const theme = useTheme();

  return (
    <div
      role="group"
      aria-label="Colour theme"
      className={`pf-swatches${compact ? " pf-swatches--dots" : ""}`}
    >
      {THEMES.map((t) => {
        const button = (
          <button
            type="button"
            onClick={() => setTheme(t)}
            aria-pressed={theme === t}
            aria-label={THEME_LABELS[t]}
            // Compact mode gets the custom Tooltip instead — a native `title`
            // alongside it would show both, one on top of the other.
            title={compact ? undefined : THEME_LABELS[t]}
            // Only in compact mode. On the full control the words are the swatch,
            // and re-scoping the palette under them would letter each one in a
            // different theme's ink.
            data-theme={compact ? t : undefined}
            className="pf-swatch"
          >
            {compact ? null : THEME_LABELS[t]}
          </button>
        );

        return compact ? (
          <Tooltip
            key={t}
            header={THEME_LABELS[t]}
            description={THEME_DESCRIPTIONS[t]}
          >
            {button}
          </Tooltip>
        ) : (
          <Fragment key={t}>{button}</Fragment>
        );
      })}
    </div>
  );
}
