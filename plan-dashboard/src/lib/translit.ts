/**
 * translit.ts — Simplify scholarly Arabic transliteration to plain English.
 *
 * TypeScript mirror of scripts/podcast/_translit.py — KEEP THE TWO IN SYNC
 * (see CLAUDE.md "TS↔Python mirror files"). Same rules, same results:
 *
 *   Kimiya al-Sa'ada   (from Kīmiyāʾ al-Saʿāda)
 *   Ihya Ulum al-Din   (from Iḥyāʾ ʿUlūm al-Dīn)
 *   Jawahir al-Qur'an  (from Jawāhir al-Qurʾān)
 *   Minhaj al-Abidin   (from Minhāj al-ʿĀbidīn)
 *
 * - macrons / under-dots / over-dots on LATIN letters -> base letter
 * - ayn and hamza (+ curly-quote variants) -> apostrophe, kept ONLY between two
 *   letters (so leading/trailing ones drop: ʿUlūm -> Ulum, Saʿāda -> Sa'ada)
 * - ARABIC SCRIPT IS NEVER TOUCHED (Arabic harakat are also \p{Mn}, so we only
 *   strip combining marks that sit on a Latin base, decomposing per character).
 *
 * Apply only to DISPLAY text (titles, rendered prose) — never to slugs, ids,
 * or file paths.
 */

const AYN_HAMZA = new Set(Array.from("ʿʾʻʼˈ’‘ʹ׳'"));
const SENTINEL = String.fromCharCode(0);

/** The complete set of word-endings that make an apostrophe genuinely English.
 *  An apostrophe followed by anything else is an ayn/hamza and is dropped.
 *  Mirror of `_ENGLISH_CLITICS` in scripts/podcast/_translit.py. */
const ENGLISH_CLITICS = new Set(["s", "t", "d", "m", "re", "ve", "ll"]);

/** The one common English word whose apostrophe marks an elision rather than a
 *  clitic. Without it, "o'clock" folded to "oclock". Mirror of `_ELISIONS`. */
const ELISIONS = new Set(["o|clock"]);

export function simplifyTransliteration(text: string): string {
  if (!text) return text;

  // 1. Fold ayn/hamza (and apostrophe-like glyphs) to a sentinel.
  let folded = "";
  for (const c of text) folded += AYN_HAMZA.has(c) ? SENTINEL : c;

  // 2. Strip combining marks off LATIN bases only (decompose per character so
  //    Arabic script — whose harakat are also \p{Mn} — is left untouched).
  let out = "";
  let lastBaseLatin = false;
  for (const c of Array.from(folded)) {
    if (/\p{Mn}/u.test(c)) {
      if (!lastBaseLatin) out += c;
      continue;
    }
    const nfd = c.normalize("NFD");
    if (nfd.length > 1 && /\p{Script=Latin}/u.test(nfd[0])) {
      out += nfd[0];
      lastBaseLatin = true;
    } else {
      out += c;
      lastBaseLatin = /\p{Script=Latin}/u.test(c);
    }
  }

  // 3. Resolve the sentinel: keep an apostrophe ONLY where it is genuinely
  //    English. Everywhere else it came from an ayn/hamza and the house style is
  //    plain letters — Quran, not Qur'an. Three ways to earn one:
  //      a) a clitic suffix ending the word — God's, don't, we'll
  //      b) word-final after an s — the plural or name possessive: "the
  //         brothers' books", "Moses' staff". The `s` is what separates them
  //         from a transliteration merely ending in an ayn (sama', Shia'),
  //         which still folds away.
  //      c) a listed elision — o'clock
  //    Mirror of _translit.py step 3 — keep the two in lockstep.
  const arr = Array.from(out);
  let res = "";
  for (let i = 0; i < arr.length; i++) {
    if (arr[i] === SENTINEL) {
      const prev = arr[i - 1] ?? "";
      let j = i + 1;
      while (j < arr.length && /\p{L}/u.test(arr[j])) j++;
      const suffix = arr
        .slice(i + 1, j)
        .join("")
        .toLowerCase();
      const keep =
        (/\p{L}/u.test(prev) &&
          (ENGLISH_CLITICS.has(suffix) ||
            (!suffix && prev.toLowerCase() === "s") ||
            ELISIONS.has(`${prev.toLowerCase()}|${suffix}`))) ||
        // A ROOT RADICAL, not a diacritic: in "(sh-r-\u02bf)" the ayn IS the
        // third consonant, and folding it printed "(sh-r-)". A hyphen before
        // and nothing after marks that position; "al-\u02bfAbidin" has a
        // suffix and still folds. Mirror of _translit.py.
        (prev === "-" && !suffix);
      if (keep) res += "'";
    } else {
      res += arr[i];
    }
  }
  return res;
}
