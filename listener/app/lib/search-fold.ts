/**
 * Folding a search query down to what the index actually holds.
 *
 * ONE HALF OF A MIRROR PAIR. The other is `fold` in
 * scripts/podcast/_listener_search.py, which folds the passages at publish time,
 * and the two are pinned against each other by test/fixtures/search-fold.fixtures.json.
 *
 * This is the FIFTH such pair in the repo and it was taken on deliberately. The
 * four before it — content paths, quality scores, anchor keys, vowelling — are
 * each pinned because a silent divergence is worse than a loud one, and this is
 * the same shape of hazard in its purest form: if the two folds disagree, no
 * error is raised anywhere. The query simply stops matching, on precisely the
 * vowelled Arabic and Perso-Urdu spelling this library is largely made of, and
 * the results page looks like a complete answer to a question it never asked.
 *
 * WHY FOLD AT ALL, when FTS5's tokenizer can remove diacritics: because the
 * corpus is not uniformly Arabic-typed. Asif's own lectures were transcribed on
 * an Urdu keyboard, so the same word carries a Farsi yeh there and an Arabic yeh
 * in the books — 1,448 against 3,264 across the published editions. No tokenizer
 * flag folds those together; they are different letters, not marked forms of one.
 *
 * The steps and their ORDER are the contract. See the Python for why each exists;
 * the reasoning is written once, there, and not restated here.
 */

/** Mid-word alif maqsura + dagger alif, folded BEFORE any mark is stripped. */
const UTHMANI_MIDWORD_ALIF = /ىٰ(?=[ء-ي])/gu;

/** Latin combining marks, left behind by decomposition. */
const LATIN_COMBINING = /[̀-ͯ]/gu;

/** Arabic marks and tatweel, exactly the ranges _arabic_coverage.py strips. */
const ARABIC_TASHKEEL = /[ؐ-ًؚ-ٰٟۖ-ۭـ]/gu;

/** Orthographic variants. Mirrors `_ARABIC_FOLD` then `_SEARCH_FOLD`. */
const LETTER_FOLD: Record<string, string> = {
  // _ARABIC_FOLD — shared with the provenance code, which must not change.
  "آ": "ا", // آ alef madda
  "أ": "ا", // أ alef hamza above
  "إ": "ا", // إ alef hamza below
  "ٱ": "ا", // ٱ alef wasla
  "ى": "ي", // ى alef maqsura
  "ة": "ه", // ة teh marbuta
  "ؤ": "و", // ؤ waw hamza
  "ئ": "ي", // ئ yeh hamza
  // _SEARCH_FOLD — Perso-Urdu forms, search only. See the Python for why these
  // are NOT pushed up into the shared table.
  "ی": "ي", // ی farsi yeh
  "ے": "ي", // ے yeh barree
  "ک": "ك", // ک keheh
  "گ": "ك", // گ gaf
  "ہ": "ه", // ہ heh goal
  "ۃ": "ه", // ۃ teh marbuta goal
  "ھ": "ه", // ھ heh doachashmee
  "ٹ": "ت", // ٹ tteh
  "ڈ": "د", // ڈ ddal
  "ڑ": "ر", // ڑ rreh
  "ں": "ن", // ں noon ghunna
  "ژ": "ز", // ژ
  "پ": "ب", // پ
  "چ": "ج", // چ
};

/**
 * Lower-case, diacritic-free, word-preserving form used for matching.
 *
 * Everything that is not a letter or a digit becomes a space, so punctuation
 * separates tokens and can never become part of one. That also means the caller
 * gets back something safe to put in an FTS5 query: no quote, asterisk, colon or
 * parenthesis survives to be read as query syntax. `queryFor` below leans on
 * that rather than escaping, because an escape someone forgets is a bug and a
 * character class someone widens is a review.
 */
export function fold(text: string): string {
  if (!text) return "";

  let out = text.replace(UTHMANI_MIDWORD_ALIF, "ا");
  out = out.normalize("NFD");
  out = out.replace(LATIN_COMBINING, "");
  out = out.replace(ARABIC_TASHKEEL, "");
  // Spacing modifier letters — the ayn and hamza of scholarly transliteration.
  // See the Python for why these are dropped rather than kept.
  out = out.replace(/\p{Lm}/gu, "");
  // Apostrophes are removed rather than separated, so `Qur'an` folds to one
  // token and finds `Quran`. See the Python for the full reasoning.
  out = out.replace(/['‘’´`]/gu, "");
  out = out.replace(/[آأإٱىةؤئیےکگہۃھٹڈڑںژپچ]/gu, (c) => LETTER_FOLD[c] ?? c);
  out = out.toLowerCase();
  out = out.replace(/[^\p{L}\p{N}]+/gu, " ");
  return out.trim().replace(/\s+/g, " ");
}

/* -------------------------------------------------------------------------- */
/* Turning what somebody typed into a query the index understands              */
/* -------------------------------------------------------------------------- */

/** `2:255`, `2 : 255`, `q2:255` — a reference, not a phrase to look for. */
const REFERENCE = /^(?:q\s*)?(\d{1,3})\s*[:.\s]\s*(\d{1,3})$/i;

export interface ParsedQuery {
  /** What to run against the index, already folded and escaped by folding. */
  terms: string[];
  /** A verse reference, when that is unambiguously what was typed. */
  reference: { surah: number; ayah: number } | null;
  /** The query had characters but nothing survived folding — e.g. only symbols. */
  empty: boolean;
}

/**
 * Read a raw query.
 *
 * A REFERENCE IS A DIFFERENT QUESTION and is recognised before anything else.
 * `2:255` as free text would fold to the tokens `2` and `255` and return every
 * passage carrying either number, which is not what anybody typing it meant.
 * Surah 1–114 and ayah 1–286 are the real bounds, but they are NOT enforced
 * here: `999:1` is still a reference, and a reference with no rows is a clean
 * empty result rather than a silent fallback to a text search for "999 1".
 */
export function parseQuery(raw: string): ParsedQuery {
  const trimmed = (raw ?? "").trim();
  if (trimmed === "") return { terms: [], reference: null, empty: true };

  const ref = REFERENCE.exec(trimmed);
  if (ref !== null) {
    return {
      terms: [],
      reference: { surah: Number(ref[1]), ayah: Number(ref[2]) },
      empty: false,
    };
  }

  const terms = fold(trimmed).split(" ").filter(Boolean);
  return { terms, reference: null, empty: terms.length === 0 };
}

/**
 * The FTS5 MATCH expression for a parsed query, or null when there is nothing
 * to ask.
 *
 * Every term is required — an AND, not an OR — because with four content types
 * in one index an OR turns a two-word query into a page of passages carrying
 * only the commoner word. Each term is also given a prefix wildcard so that
 * typing `intellec` finds `intellect` while the reader is still typing.
 *
 * `column` narrows to one indexed field, which is how the scope toggle is
 * implemented: it changes WHERE the query looks, never what may be returned.
 * Access is decided elsewhere and only elsewhere.
 */
export function matchExpression(
  terms: string[],
  column?: "heading_fold" | "body_fold" | "arabic_fold",
): string | null {
  if (terms.length === 0) return null;
  const body = terms.map((t) => `"${t}"*`).join(" AND ");
  return column === undefined ? body : `${column} : (${body})`;
}
