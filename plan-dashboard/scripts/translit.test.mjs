/**
 * translit.test.mjs — the TS half of the translit mirror pair.
 * Run with:  node --test scripts/translit.test.mjs   (from plan-dashboard/)
 *
 * src/lib/translit.ts and scripts/podcast/_translit.py must agree character for
 * character: the pipeline folds the book's prose with the Python one, and the
 * site renders titles with the TS one, so a divergence shows up as the same term
 * spelled two ways between the page and the PDF. These cases are copied from the
 * Python self-test on purpose — when one side changes, this fails until both do.
 *
 * The module is dependency-free, so Node's type stripping runs it directly.
 */
import assert from "node:assert/strict";
import test from "node:test";

import { simplifyTransliteration as f } from "../src/lib/translit.ts";

test("scholarly diacritics fold to plain letters", () => {
  assert.equal(f("Kīmiyāʾ al-Saʿāda"), "Kimiya al-Saada");
  assert.equal(f("Iḥyāʾ ʿUlūm al-Dīn"), "Ihya Ulum al-Din");
  assert.equal(f("Minhāj al-ʿĀbidīn"), "Minhaj al-Abidin");
  assert.equal(f("Ḥasan al-Baṣrī"), "Hasan al-Basri");
});

test("an ayn or hamza never leaves an apostrophe behind", () => {
  assert.equal(f("Jawāhir al-Qurʾān"), "Jawahir al-Quran");
  assert.equal(f("Qur'an and Qur'anic"), "Quran and Quranic");
  assert.equal(
    f("du'at, Ka'b, ta'wil, da'wa, Ja'far, Shu'ayb"),
    "duat, Kab, tawil, dawa, Jafar, Shuayb",
  );
  assert.equal(f("Bayt al-Ma'mur"), "Bayt al-Mamur");
});

test("English contractions and singular possessives keep theirs", () => {
  assert.equal(f("God's mercy"), "God's mercy");
  assert.equal(f("the book's own voice"), "the book's own voice");
  assert.equal(f("don't and we'll and I've"), "don't and we'll and I've");
  assert.equal(f("Salih's road"), "Salih's road");
});

test("plural and name possessives keep theirs", () => {
  // An earlier rule deleted these outright: "the scholars' books" came out as
  // "the scholars books". Both forms occur in the live edition.
  assert.equal(f("the brothers' books"), "the brothers' books");
  assert.equal(f("Moses' staff"), "Moses' staff");
  assert.equal(f("the scholars' obligation"), "the scholars' obligation");
});

test("a transliteration merely ending in an ayn still folds away", () => {
  // The `s` before a word-final apostrophe is what distinguishes a possessive
  // from this — without that test these would wrongly keep their apostrophe.
  assert.equal(f("sama' and Shia'"), "sama and Shia");
});

test("the one listed elision survives", () => {
  assert.equal(f("five o'clock"), "five o'clock");
});

test("a root radical survives, an ordinary prefix still folds", () => {
  // "(sh-r-\u02bf)" printed as "(sh-r-)" — a two-letter root with a dangling
  // hyphen, a claim the reader can see is false.
  assert.equal(
    f("The root of Sharia (sh-r-\u02bf)"),
    "The root of Sharia (sh-r-')",
  );
  assert.equal(f("Minh\u0101j al-\u02bf\u0100bid\u012bn"), "Minhaj al-Abidin");
});

test("Arabic script and its vowel marks are never touched", () => {
  assert.equal(f("وَأَنْ لَيْسَ"), "وَأَنْ لَيْسَ");
  assert.equal(f("the centre of البيت المعمور"), "the centre of البيت المعمور");
});

test("empty input is returned unchanged", () => {
  assert.equal(f(""), "");
});
