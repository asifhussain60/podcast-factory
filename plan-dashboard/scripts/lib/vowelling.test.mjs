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
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";
import {
  skeleton,
  markCount,
  markDensity,
  rejectionReason,
  reflowToSourceWhitespace,
  reflowWordsToSourceWhitespace,
  transferMarks,
  isVowellingCandidate,
  isArabicPassage,
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

test("a digit is not a mark", () => {
  // Arabic-Indic digits sit inside the U+0653-U+0670 span the mark class used to
  // cover, so skeleton() deleted them from both sides and a vowelling that
  // dropped every footnote number was admitted as marks-only. Real OCR line.
  const line = "تأليف ١ سيدنا جعفر بن منصور ٢ اليمن٣";
  assert.equal(markCount(line), 0);
  assert.equal(skeleton(line), line);
  assert.match(
    rejectionReason(line, "تَأْلِيف سَيِّدنَا جَعْفَر بْن مَنْصُور اليَمَن"),
    /letters changed/,
  );
});

test("markDensity is not corrupted by the /g regex lastIndex", () => {
  // markDensity filtered letters with MARKS_RE.test(c) on a /g regex, whose
  // lastIndex advances on a match — so the same character alternated true/false
  // across calls and the letter count depended on position. A bare run must read
  // as bare however many characters precede it.
  assert.equal(markDensity(BARE_HADITH), 0);
  assert.ok(markDensity(VOWELLED_AYAH) > 0.4);
});

test("reflow restores the source's line structure without moving a mark", () => {
  const source = "قال العالم\nودموعه تنحدر\nعلى لحيته";
  const collapsed = "قَالَ الْعَالِمُ وَدُمُوعُهُ تَنْحَدِرُ عَلَى لِحْيَتِهِ";
  const out = reflowToSourceWhitespace(source, collapsed);
  assert.equal(out.split("\n").length, source.split("\n").length);
  assert.equal(skeleton(out), skeleton(source));
  assert.equal(markCount(out), markCount(collapsed));
  assert.equal(rejectionReason(source, out), null);
  assert.equal(reflowToSourceWhitespace(source, out), out);
  assert.equal(reflowToSourceWhitespace(source, "كلام آخر"), "كلام آخر");
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

// ── The mirror pair ────────────────────────────────────────────────────────
// Everything above is this half's own coverage. What follows runs the SHARED
// fixtures that scripts/podcast/tests/test_vowelling.py runs too, so the
// Composer's Diacritics button and the compose-time vowelling pass cannot drift
// into admitting different things — a divergence there would put text into
// book.md that one side considers inadmissible.
const FX = JSON.parse(
  readFileSync(
    join(dirname(fileURLToPath(import.meta.url)), "vowelling.fixtures.json"),
    "utf8",
  ),
);

test("mirror: skeleton matches the shared fixtures", () => {
  for (const c of FX.skeleton) assert.equal(skeleton(c.in), c.out, c.in);
});

test("mirror: markCount matches the shared fixtures", () => {
  for (const c of FX.markCount) assert.equal(markCount(c.in), c.out, c.in);
});

test("mirror: isVowellingCandidate matches the shared fixtures", () => {
  for (const c of FX.isCandidate)
    assert.equal(isVowellingCandidate(c.in), c.out, c._why ?? c.in);
});

test("mirror: isArabicPassage matches the shared fixtures", () => {
  for (const c of FX.isArabicPassage)
    assert.equal(isArabicPassage(c.in), c.out, c._why ?? c.in);
});

test("mirror: reflowToSourceWhitespace matches the shared fixtures", () => {
  for (const c of FX.reflow)
    assert.equal(
      reflowToSourceWhitespace(c.source, c.candidate),
      c.out,
      c._why ?? c.source,
    );
});

test("an orphan mark does not derail the reflow", () => {
  // The defect that cost a 45-minute paid run: a scan can leave a combining mark
  // with no letter under it, and consuming it AS a letter put every later letter
  // off by one until the walk ran off the end and gave up — returning the
  // collapsed line, which rejectionReason cannot catch.
  const source = "ْ توكل على الله\nإذا عزمت";
  const collapsed = "ْ تَوَكَّلْ عَلَى اللهِ إِذَا عَزَمْتَ";
  const out = reflowToSourceWhitespace(source, collapsed);
  assert.equal(out.split("\n").length, source.split("\n").length);
  assert.equal(skeleton(out), skeleton(source));
  assert.equal(markCount(out), markCount(collapsed));
});

test("a mushaf verse keeps the line break the book printed", () => {
  const source = "ليس كمثله\nشيء";
  const canonical = "لَيْسَ كَمِثْلِهِۦ شَىْءٌۭ";
  // Uthmani letters differ, so the character walk must decline.
  assert.equal(reflowToSourceWhitespace(source, canonical), canonical);
  const out = reflowWordsToSourceWhitespace(source, canonical);
  assert.equal(out.split("\n").length, source.split("\n").length);
  assert.deepEqual(out.split(/\s+/), canonical.split(/\s+/));
  assert.equal(reflowWordsToSourceWhitespace(source, "لَيْسَ"), "لَيْسَ");
});

test("mirror: transferMarks matches the shared fixtures", () => {
  // Each case is a real refusal recorded by a book before this recovery existed.
  // A null is as load-bearing as a string: the gate still refusing where it must.
  for (const c of FX.transfer)
    assert.equal(
      transferMarks(c.source, c.candidate),
      c.out,
      c._why ?? c.source,
    );
});

test("a transferred vowelling always passes the gate", () => {
  // Structural, not a second check that could disagree: the result carries the
  // SOURCE's letters, so its skeleton is source-identical by construction.
  for (const c of FX.transfer) {
    const got = transferMarks(c.source, c.candidate);
    if (got === null) continue;
    assert.equal(skeleton(got), skeleton(c.source));
    assert.equal(rejectionReason(c.source, got), null);
  }
});

test("mirror: reflowWordsToSourceWhitespace matches the shared fixtures", () => {
  for (const c of FX.reflowWords)
    assert.equal(
      reflowWordsToSourceWhitespace(c.source, c.candidate),
      c.out,
      c._why ?? c.source,
    );
});

test("mirror: rejectionReason matches the shared fixtures", () => {
  for (const c of FX.rejection) {
    const got = rejectionReason(c.source, c.candidate);
    if (c.outStartsWith !== undefined)
      assert.ok(
        String(got ?? "").startsWith(c.outStartsWith),
        `${c._why ?? c.source}: got ${got}`,
      );
    else assert.equal(got, c.out, c._why ?? c.source);
  }
});
