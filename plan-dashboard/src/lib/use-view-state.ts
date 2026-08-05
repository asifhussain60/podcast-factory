/**
 * use-view-state.ts — bind a durable view-state entry to React state.
 *
 * The one subtlety worth knowing before using this: the value is NOT read from
 * storage in the useState initializer. Several of this site's islands are
 * server-rendered and then hydrated (`client:load`), and the server has no
 * localStorage — so a value read during the first render would disagree with
 * the HTML the server produced and trip a hydration mismatch. It is applied in
 * an effect after mount instead: one frame at the default, then the remembered
 * value. That is also correct for `client:only` islands, so callers do not
 * have to know which kind they are in.
 */
import { useCallback, useEffect, useState } from "react";

import type { ViewState } from "./view-state";

export function useViewState<T>(
  state: ViewState<T>,
  fallback: T,
  scope?: string,
): [T, (next: T) => void] {
  const [value, setValue] = useState<T>(fallback);

  useEffect(() => {
    const stored = state.read(scope);
    if (stored !== null) setValue(stored);
  }, [state, scope]);

  const set = useCallback(
    (next: T) => {
      setValue(next);
      state.write(next, scope);
    },
    [state, scope],
  );

  return [value, set];
}
