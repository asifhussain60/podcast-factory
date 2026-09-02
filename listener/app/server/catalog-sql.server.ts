/**
 * catalog-sql.server.ts — the two rules both catalog readers share.
 *
 * `servable` decides when a media row counts as playable, and `devServesFromDisk`
 * is the one exception to it. They lived in `catalog.server.ts` until the library
 * cards were split out of it on 2026-09-02; both files ask the question, and a
 * second copy of "is this file actually available" is exactly the kind of rule
 * that drifts into two different answers.
 */
export function devServesFromDisk(): boolean {
  return import.meta.env.DEV;
}

/** SQL fragment: "is this column's row playable right now" for the current environment. */
export function servable(column: string): string {
  return devServesFromDisk() ? "1=1" : `${column} IS NOT NULL`;
}
