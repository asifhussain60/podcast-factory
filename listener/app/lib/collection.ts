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
 * THREE collections, and the third arrived by reversing the second (Asif,
 * 2026-09-01, later the same day). `Audiobook` shipped folded in with `Sessions`
 * under one "spoken" collection, on the reasoning that both are "press play and
 * read along" and a reader choosing between them is choosing by provenance. Asif
 * changed his mind and asked for a third tile: a published novel read by a hired
 * narrator and a talk he gave himself are not the same errand, whatever they
 * share mechanically.
 *
 * So the violet no longer means SPOKEN. It means Sessions — Asif's own recorded
 * teaching — and audiobooks have their own teal. Books keep the base navy by
 * declaring nothing, which is the convention explained below.
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
/** Bucket -> the collection it belongs to. A bucket absent from this map is a
 *  book, and books declare nothing — see the note above. */
const BUCKET_COLLECTION: Readonly<Record<string, "sessions" | "audiobooks">> = {
  Sessions: "sessions",
  Audiobook: "audiobooks",
};

/**
 * What a card, page or player paints itself as — the value `data-collection`
 * takes, or `undefined` for a book, which declares nothing.
 *
 * Exported so no consumer spells the union out. Four of them did, as
 * `"sessions" | undefined`, and adding a third collection was a compile error in
 * each — which is the good outcome, but only because they happened to be typed
 * at all. A named type is what stops the fifth one being typed as `string`.
 */
export type CollectionAccent = "sessions" | "audiobooks" | undefined;

export function collectionOf(bucket: string): CollectionAccent {
  return BUCKET_COLLECTION[bucket];
}

/**
 * The library find row's "Everything / Books / Sessions / Audiobooks" toggle.
 *
 * "Books" is still defined as NOT one of the named collections rather than as a
 * list of buckets, so a bucket added later lands with the books instead of
 * vanishing from a library that offers no way to reach it. The failure mode of
 * getting this backwards is silent — the card simply is not there under any
 * filter, and nobody reports a book they cannot see.
 *
 * That is also why `inCollection` compares against `collectionOf(...) ?? "books"`
 * rather than testing each collection in turn. Written as a chain of equality
 * tests it would need a new branch per collection, and the branch somebody
 * forgets is the one that hides content.
 */
export const COLLECTIONS = ["all", "books", "sessions", "audiobooks"] as const;
export type Collection = (typeof COLLECTIONS)[number];

export const inCollection = (bucket: string, choice: Collection): boolean =>
  choice === "all" || (collectionOf(bucket) ?? "books") === choice;
