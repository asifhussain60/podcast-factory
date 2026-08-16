import { useEffect, useSyncExternalStore } from "react";

import {
  hydrateReading,
  readingSnapshot,
  subscribeReading,
  type ReadingPrefs,
} from "~/lib/reading";

/**
 * The current reading setting, shared by every control on the page.
 *
 * `getServerSnapshot` is the same function as `getSnapshot` on purpose: the
 * store starts at the defaults on both sides, so the first client render agrees
 * with the server's and there is no hydration mismatch. The stored value
 * arrives one effect later — see the note in lib/reading.ts.
 *
 * This used to live in `ReadingControls.tsx` alongside the bar it fed. That bar
 * and the "Aa" panel were both replaced by `reader/ReaderToolbar.tsx`, and a hook
 * exported from a deleted component's file would have been a component file with
 * no component in it. `useTheme` sits beside `ThemePicker` for the same reason —
 * there, the component still exists.
 */
export function useReading(): ReadingPrefs {
  const prefs = useSyncExternalStore(
    subscribeReading,
    readingSnapshot,
    readingSnapshot,
  );
  useEffect(hydrateReading, []);
  return prefs;
}
