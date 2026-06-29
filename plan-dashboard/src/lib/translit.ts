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

  // 3. Resolve the sentinel: keep an apostrophe only between two letters.
  const arr = Array.from(out);
  let res = "";
  for (let i = 0; i < arr.length; i++) {
    if (arr[i] === SENTINEL) {
      const prev = arr[i - 1] ?? "";
      const next = arr[i + 1] ?? "";
      if (/\p{L}/u.test(prev) && /\p{L}/u.test(next)) res += "'";
    } else {
      res += arr[i];
    }
  }
  return res;
}
