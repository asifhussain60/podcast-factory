/**
 * One place that knows how to put a number next to a word.
 *
 * Before this existed the site had thirteen bare concatenations — `${n} chapters`,
 * `${n} sessions`, `${n} books` — every one of which read "1 sessions" the moment
 * the number was one. Degrees of Excellence has exactly one session, so its podcast
 * panel announced "1 SESSIONS · 6 EPISODES" on the live site.
 *
 * Four other sites DID handle it, in four different idioms invented independently:
 * a noun-and-verb ternary, a bare noun ternary, a whole-phrase branch, and a
 * suffix branch. All four are folded in here. The point is not that any one of them
 * was wrong — it is that "how do we say this" was answered five times, so a sixth
 * call site had no obvious thing to copy and copied nothing.
 *
 * Deliberately NOT `Intl.PluralRules`. It answers which CATEGORY a number falls in
 * ("one", "other"), not what the English word is, so every call site would still
 * carry its own map from category to text — the same duplication with more
 * ceremony. This site is English-only and its irregulars are two words long.
 */

/**
 * The word that goes with *n*, without the number.
 *
 *   plural(1, "book")            -> "book"
 *   plural(2, "book")            -> "books"
 *   plural(1, "person", "people") -> "person"
 *
 * `many` defaults to *one* + "s", which is right for every regular noun on this
 * site; pass it explicitly for irregulars (person/people) and for anything where
 * the "s" lands in the middle ("episodes planned").
 *
 * VERBS INVERT, and that is not a bug in the caller: English agrees a verb with its
 * subject the other way round, so one match "matches" and two "match". Written as
 * `plural(n, "matches", "match")` it looks backwards and is correct — *one* is
 * always the form used when n is 1, whatever part of speech it is.
 */
export function plural(n: number, one: string, many = `${one}s`): string {
  return n === 1 ? one : many;
}

/**
 * The number and its word together — the form nearly every call site wants.
 *
 *   count(1, "chapter")                     -> "1 chapter"
 *   count(6, "episode")                     -> "6 episodes"
 *   count(1, "episode planned", "episodes planned") -> "1 episode planned"
 *   count(2, "person has", "people have")   -> "2 people have"
 *
 * *one* and *many* are the whole text that FOLLOWS the number, not just a noun, so
 * a phrase whose verb also has to agree is one call rather than a call plus a
 * ternary.
 */
export function count(n: number, one: string, many = `${one}s`): string {
  return `${n} ${plural(n, one, many)}`;
}
