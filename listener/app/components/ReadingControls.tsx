import { useEffect, useId, useSyncExternalStore } from "react";

import {
  FAMILIES,
  FAMILY_LABELS,
  hydrateReading,
  readingSnapshot,
  setReading,
  SIZES,
  step,
  subscribeReading,
  type Family,
  type ReadingPrefs,
} from "~/lib/reading";

/**
 * The current reading setting, shared by every control on the page.
 *
 * `getServerSnapshot` is the same function as `getSnapshot` on purpose: the
 * store starts at the defaults on both sides, so the first client render agrees
 * with the server's and there is no hydration mismatch. The stored value
 * arrives one effect later — see the note in lib/reading.ts.
 */
export function useReading(): ReadingPrefs {
  const prefs = useSyncExternalStore(subscribeReading, readingSnapshot, readingSnapshot);
  useEffect(hydrateReading, []);
  return prefs;
}

/**
 * Typeface and size, above the page.
 *
 * The two settings a reader actually reaches for, put where they can be reached
 * — the fuller panel behind "Aa" in the header keeps theme, line spacing and
 * line width, and both write through the same store, so neither can show a
 * number the other has changed.
 *
 * A stepper rather than a slider for the size, and the same reason the panel
 * gives: a slider needs a precise drag, and most of this reading happens
 * one-handed. The ends disable at the ends of the scale rather than silently
 * doing nothing.
 */
export function ReadingControls() {
  const prefs = useReading();
  const id = useId();

  const smallest = prefs.size === SIZES[0];
  const largest = prefs.size === SIZES[SIZES.length - 1];

  return (
    <div className="pf-controls">
      {/* The visible label would be a third thing to read in a row whose whole
          job is to be ignorable until wanted; the select's own value already
          names what it is. */}
      <label htmlFor={`${id}-face`} className="sr-only">
        Typeface
      </label>
      <select
        id={`${id}-face`}
        value={prefs.family}
        onChange={(e) => setReading({ ...prefs, family: e.target.value as Family })}
        className="pf-select pf-select--auto"
      >
        {FAMILIES.map((family) => (
          <option key={family} value={family}>
            {FAMILY_LABELS[family]}
          </option>
        ))}
      </select>

      <div role="group" aria-label="Text size" className="pf-stepper">
        <button
          type="button"
          onClick={() => setReading({ ...prefs, size: step(SIZES, prefs.size as never, -1) })}
          disabled={smallest}
          aria-label="Smaller text"
          className="pf-stepper__step"
        >
          &minus;
        </button>

        {/* Announced on change so a screen-reader user who cannot see the text
            reflow still learns what the buttons did. */}
        <span aria-live="polite" className="pf-stepper__value">
          {prefs.size}
        </span>

        <button
          type="button"
          onClick={() => setReading({ ...prefs, size: step(SIZES, prefs.size as never, 1) })}
          disabled={largest}
          aria-label="Larger text"
          className="pf-stepper__step"
        >
          +
        </button>
      </div>
    </div>
  );
}
