/**
 * arabic-fold.ts — TS mirror of the pipeline's Arabic skeleton + romanization folds.
 *
 * Python owners: scripts/podcast/_arabic_coverage.py (normalize_arabic) and
 * scripts/podcast/_buckwalter.py (arabic_fold / latin_fold / folds_match).
 * Pinned by the shared fixture plan-dashboard/scripts/lib/buckwalter.fixtures.json
 * (read by tests/test_buckwalter.py AND scripts/lib/arabic-fold.test.mjs) — a
 * one-sided edit fails a test rather than silently changing which terms the
 * morphology lookups resolve. Keep both sides in sync in the same commit
 * (CLAUDE.md, TS↔Python mirror rule).
 *
 * The fold space is deliberately LOSSY: agreement is necessary, never sufficient,
 * evidence of identity. Consumers treat a match as a candidate and a non-match as
 * "decline to judge" — so the lossiness only ever under-fires.
 */

/** Combining marks + tatweel the skeleton drops (exact Python codepoint set). */
const TASHKEEL_RE = /[ؐ-ًؚ-ٰٟۖ-ۭـ]/g;
/** Uthmani mid-word maqsura+dagger spells a long /a/ modern text writes as alif. */
const MIDWORD_ALIF_RE = /ىٰ(?=[ء-ي])/g;
const LETTERS_ONLY_RE = /[^ء-ي]/g;
const FOLD: Record<string, string> = {
  آ: "ا",
  أ: "ا",
  إ: "ا",
  ٱ: "ا",
  ى: "ي",
  ة: "ه",
  ؤ: "و",
  ئ: "ي",
};

/** The consonantal skeleton of an Arabic run — normalize_arabic's exact fold. */
export function normalizeArabic(text: string): string {
  const folded = (text ?? "").replace(MIDWORD_ALIF_RE, "ا");
  const stripped = folded.replace(TASHKEEL_RE, "");
  let out = "";
  for (const ch of stripped) out += FOLD[ch] ?? ch;
  return out.replace(LETTERS_ONLY_RE, "");
}

/** Arabic consonant classes -> the shared ASCII fold space (_buckwalter._ARABIC_TO_FOLD). */
const ARABIC_TO_FOLD: Record<string, string> = {
  ب: "b",
  ت: "t",
  ث: "th",
  ج: "j",
  ح: "h",
  خ: "kh",
  د: "d",
  ذ: "dh",
  ر: "r",
  ز: "z",
  س: "s",
  ش: "sh",
  ص: "s",
  ض: "d",
  ط: "t",
  ظ: "z",
  غ: "gh",
  ف: "f",
  ق: "q",
  ك: "k",
  ل: "l",
  م: "m",
  ن: "n",
  ه: "h",
  و: "w",
  ي: "y",
  ع: "",
  ء: "",
  ا: "",
};

function collapse(s: string): string {
  let out = "";
  for (const ch of s) if (!out.endsWith(ch)) out += ch;
  return out;
}

/** A normalize-arabic skeleton -> the shared ASCII fold space. */
export function arabicFold(skeleton: string): string {
  let out = "";
  for (const ch of skeleton ?? "") out += ARABIC_TO_FOLD[ch] ?? "";
  return collapse(out);
}

/** A plain-English romanized term/root -> the shared ASCII fold space. */
export function latinFold(term: string): string {
  const letters = (term ?? "")
    .toLowerCase()
    .replace(/[^a-z]/g, "")
    .replace(/[aeiou]/g, "");
  return collapse(letters);
}

/** Class-level agreement, incl. the silent ta-marbuta allowance (trailing ه). */
export function foldsMatch(latin: string, arabicSkeletonFold: string): boolean {
  if (!latin || !arabicSkeletonFold) return false;
  return arabicSkeletonFold === latin || arabicSkeletonFold === latin + "h";
}
