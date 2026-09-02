/**
 * same.ts — value equality for the two shapes a React dependency array compares
 * by reference.
 *
 * Split out of `book.$slug.read.$chapter.tsx` on 2026-09-02 for its size ceiling,
 * and they belong together: both exist for the same reason, which is that a
 * freshly-built array or Set is a new object every render even when it holds
 * exactly what it held before. Keeping the previous value when nothing changed
 * is what stops a state setter re-rendering the reader on every scroll.
 */
/** Whether two id lists are the same, in the same order. Same purpose as below. */
export function sameList(a: string[], b: string[]): boolean {
  return a.length === b.length && a.every((v, i) => v === b[i]);
}

/** Whether two id sets hold the same members — used to avoid a needless render. */
export function sameSet(a: Set<string>, b: Set<string>): boolean {
  if (a.size !== b.size) return false;
  for (const v of a) if (!b.has(v)) return false;
  return true;
}
