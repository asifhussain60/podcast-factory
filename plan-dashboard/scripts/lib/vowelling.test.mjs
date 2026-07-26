/**
 * vowelling.test.mjs — the gate that bounds a model to vocalisation.
 *
 * The whole propose-and-review design rests on one claim: an accepted proposal can
 * differ from the source run in MARKS ONLY. If `rejectionReason` is wrong, a model
 * can quietly rewrite a hadith and a reviewer skimming Arabic diacritics will not
 * catch it. So the cases below are the real failure modes, not toy strings — every
 * Arabic fixture is a run from `the-master-and-the-disciple`, and the adversarial
 * cases are the substitutions a model actually tends to make: Uthmani spelling for
 * imla'i, hamza-form drift, a dropped clause, a "corrected" word.
 */
import test from "node:test";
import assert from "node:assert/strict";
import {
  skeleton,
  markCount,
  markDensity,
  rejectionReason,
  isVowellingCandidate,
} from "./vowelling.mjs";

// Real runs from the book (book/book.md).
const BARE_HADITH = "إن أفضل الحسنات إحياء الأموات";
const BARE_SAYING = "فإنه من عمل لله بما يعلم، هداه الله إلى ما لا يعلم";
const VOWELLED_AYAH = "لَيْسَ كَمِثْلِهِ شَيْءٌ";

test("skeleton strips marks and tatweel but keeps every letter", () => {
  assert.equal(skeleton(VOWELLED_AYAH), "ليس كمثله شيء");
  // Tatweel is a stretching character, not a letter: two runs that differ only by
  // it must not read as different words.
  assert.equal(skeleton("العـــلم"), skeleton("العلم"));
  // A bare run is its own skeleton.
  assert.equal(skeleton(BARE_HADITH), BARE_HADITH);
});

test("markCount and markDensity separate a bare run from a vowelled one", () => {
  assert.equal(markCount(BARE_HADITH), 0);
  assert.ok(markCount(VOWELLED_AYAH) > 5);
  assert.ok(markDensity(BARE_HADITH) < 0.05);
  assert.ok(markDensity(VOWELLED_AYAH) > 0.4);
});

test("a pure vowelling of the same letters is ADMISSIBLE", () => {
  const vowelled = "إِنَّ أَفْضَلَ الْحَسَنَاتِ إِحْيَاءُ الْأَمْوَاتِ";
  assert.equal(skeleton(vowelled), skeleton(BARE_HADITH));
  assert.equal(rejectionReason(BARE_HADITH, vowelled), null);
});

test("REJECTS a proposal that changes a letter", () => {
  // "الحسنات" -> "الحسنة": the model rewrote the word while vowelling it.
  const tampered = "إِنَّ أَفْضَلَ الْحَسَنَةِ إِحْيَاءُ الْأَمْوَاتِ";
  const reason = rejectionReason(BARE_HADITH, tampered);
  assert.ok(reason, "a letter change must be refused");
  assert.match(reason, /letters changed/);
  assert.match(reason, /character \d+/, "must point at the divergence");
});

test("REJECTS a silent switch to Uthmani orthography", () => {
  // The mushaf writes the istirja' with a dagger alif (رَٰجِعُونَ) where the book
  // uses the plain alif (راجعون). Substituting it changes the letters, so a model
  // reaching for the canonical spelling is caught here rather than in the PDF.
  const book = "إنا لله وإنا إليه راجعون";
  const uthmani = "إِنَّا لِلَّهِ وَإِنَّآ إِلَيْهِ رَٰجِعُونَ";
  assert.notEqual(skeleton(book), skeleton(uthmani));
  assert.match(rejectionReason(book, uthmani), /letters changed/);
});

test("REJECTS a dropped clause even when every surviving letter is vowelled", () => {
  const truncated = "فَإِنَّهُ مَنْ عَمِلَ لِلَّهِ بِمَا يَعْلَمُ";
  assert.match(rejectionReason(BARE_SAYING, truncated), /letters changed/);
});

test("REJECTS a no-op, empty, or non-Arabic candidate", () => {
  assert.match(
    rejectionReason(BARE_HADITH, BARE_HADITH),
    /adds no vowel marks/,
  );
  assert.match(rejectionReason(BARE_HADITH, "   "), /empty/);
  assert.match(
    rejectionReason(BARE_HADITH, "the best of good deeds"),
    /no Arabic/,
  );
});

test("whitespace differences alone never make a proposal inadmissible", () => {
  const spaced = "إِنَّ  أَفْضَلَ الْحَسَنَاتِ\n إِحْيَاءُ الْأَمْوَاتِ";
  assert.equal(rejectionReason(BARE_HADITH, spaced), null);
});

test("candidate selection skips already-vowelled runs and stray words", () => {
  assert.ok(isVowellingCandidate(BARE_HADITH));
  assert.ok(isVowellingCandidate(BARE_SAYING));
  // Already vowelled — nothing to propose.
  assert.ok(!isVowellingCandidate(VOWELLED_AYAH));
  // Too short to be a passage; a two-word run carries too little context to
  // vowel responsibly (the same reasoning _mushaf.py uses for its word floor).
  assert.ok(!isVowellingCandidate("حزب الله"));
  assert.ok(!isVowellingCandidate("no arabic here"));
});
