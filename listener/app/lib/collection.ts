/**
 * Which collection a work belongs to, as the stylesheet spells it.
 *
 * The library carries two kinds of thing and they are read the same way: books
 * the pipeline produced from a printed source, and lectures Asif delivered and
 * recorded himself. The only visible difference is the accent — blue for the
 * books, violet for the sessions — and §3b of app/styles/podcast-factory.css
 * paints it off a `data-collection` attribute.
 *
 * The rule lives HERE and is called from the card, the book page and the player
 * because those three must agree. They are in three different route trees: the
 * card is in the library grid, the page is under `book.$slug`, and the player is
 * mounted above both in `_authed`, where it survives navigation. Written out
 * three times, the player is exactly the one that would be missed — and a violet
 * session playing in a blue bar is the defect nobody notices until it ships.
 *
 * Undefined rather than "books" for the default case, deliberately: React omits
 * an undefined attribute entirely, so an ordinary book renders with no
 * `data-collection` at all and inherits its theme's palette untouched. Adding
 * `data-collection="books"` everywhere would mean an empty overlay block had to
 * exist to match it, and a rule that does nothing is a rule someone later
 * "fixes" by giving it a colour.
 */
export function collectionOf(bucket: string): "sessions" | undefined {
  return bucket === "Sessions" ? "sessions" : undefined;
}

/**
 * The library find row's "Everything / Books / Sessions" toggle.
 *
 * "Books" is defined as NOT sessions rather than as a list of buckets, so a
 * bucket added later lands with the books instead of vanishing from a library
 * that offers no way to reach it. The failure mode of getting this backwards is
 * silent — the card simply is not there under any filter.
 */
export const COLLECTIONS = ["all", "books", "sessions"] as const;
export type Collection = (typeof COLLECTIONS)[number];

export const inCollection = (bucket: string, choice: Collection): boolean =>
  choice === "all" ||
  (collectionOf(bucket) === "sessions") === (choice === "sessions");
