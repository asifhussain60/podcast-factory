/**
 * Which collection a work belongs to, as the stylesheet spells it.
 *
 * The library carries two kinds of thing and they are read the same way: books
 * the pipeline produced from a printed source, and SPOKEN-SOURCE works — where
 * a recording exists first and the text is timed against it. The only visible
 * difference is the accent — blue for the books, violet for the spoken ones —
 * and §3b of app/styles/podcast-factory.css paints it off a `data-collection`
 * attribute.
 *
 * Two buckets are spoken-source: `Sessions` (lectures Asif delivered and
 * recorded himself) and `Audiobook` (published books read aloud by a narrator),
 * added 2026-09-01. The toggle is deliberately NOT split into a third choice —
 * Asif's call: both are "press play and read along", and a reader choosing
 * between them is choosing by provenance, which the card already shows. What
 * separates them on the shelf is that an audiobook collection stacks into one
 * set card, declared in `content/<Bucket>/_listener-groups/`.
 *
 * The violet therefore means SPOKEN, not "Asif's own". Reading it as the latter
 * is what would make an Audiobook card look like a bug.
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
const SPOKEN_BUCKETS: ReadonlySet<string> = new Set(["Sessions", "Audiobook"]);

export function collectionOf(bucket: string): "sessions" | undefined {
  return SPOKEN_BUCKETS.has(bucket) ? "sessions" : undefined;
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
