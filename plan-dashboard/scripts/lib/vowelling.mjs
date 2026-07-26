/**
 * vowelling.ts — proposed Arabic vowelling, and the one rule that makes it safe.
 *
 * THE PROBLEM. This book's Arabic source is a bare critical edition: 1,689 tashkeel
 * marks across 82,237 Arabic characters, and the printed pages themselves carry
 * only occasional disambiguating marks (verified against
 * `_system/source/images/page_0003.png` and `page_0020.png`). So vowelling cannot
 * be recovered — there is nothing to recover. It can only be SUPPLIED.
 *
 * Supplying it from a model, silently, is exactly what BK-N5 forbids: "vowel marks
 * appear on a run whose source form is unvowelled — the diacritics were written
 * from model memory", a P0 under the book-challenger's closing gate. And it is
 * forbidden for a good reason: on an Arabic verb a wrong vowel flips active to
 * passive, and this book's Arabic is largely hadith and reported speech.
 *
 * THE RESOLUTION (locked with Asif 2026-07-21). A model may PROPOSE; only a human
 * may ACCEPT; and an accepted mark is the human's, not the model's. Nothing in this
 * module writes to `book.md`. Proposals live in `_system/vowelling-proposals.json`
 * until a human decides on them, and applying an accepted one goes through the
 * Composer's own chapter-save route — so it lands in `composer-edits.json` and
 * survives the next `compose_book_v2` like any other Composer edit.
 *
 * THE SAFETY PROPERTY. `skeleton()` strips every mark, and a proposal is REJECTED
 * unless its skeleton is byte-identical to the source run's. A model that adds
 * marks passes; a model that "corrects" a letter, drops a word, swaps a hamza form
 * or silently substitutes the mushaf's Uthmani spelling fails and never reaches a
 * human. That check is what bounds the blast radius to vocalisation alone — the one
 * thing a reviewer can actually judge by eye.
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

/** A proposal record, as stored in `_system/vowelling-proposals.json`:
 *    id            stable per source run, so re-proposing updates rather than duplicates
 *    chapter_key   the anchorKey of the chapter the run lives in
 *    chapter_title display title, for the review list
 *    source        the run exactly as it appears in book.md — the replacement target
 *    proposed      the model's vowelled form (same skeleton as `source`, guaranteed)
 *    resolved      what the human settled on; starts as `proposed`, editable
 *    status        pending | accepted | rejected | applied
 *    marks_added   how many marks `resolved` adds over `source`
 *    model         which model proposed it
 *    proposed_at / decided_at / note
 */
export const PROPOSALS_NAME = "vowelling-proposals.json";
const SCHEMA = "book.vowelling-proposals/v1";

/** Combining marks: tashkeel, superscript alif, Quranic annotation signs. Also
 *  tatweel, which is a stretching character rather than a letter and must not make
 *  two otherwise-identical skeletons differ. */
const MARKS_RE = /[ً-ْٓ-ٰٟۖ-ۭـ]/g;

/** Arabic letters, for detecting whether a string contains Arabic at all. */
const ARABIC_RE = /[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]/;

/** The consonantal skeleton: the run with every mark and tatweel removed, and
 *  whitespace collapsed. Two strings with the same skeleton differ ONLY in
 *  vocalisation — which is the entire permitted delta. */
export function skeleton(text) {
  return (text ?? "").replace(MARKS_RE, "").replace(/\s+/g, " ").trim();
}

/** How many combining marks a run carries. Used to tell "already vowelled" from
 *  "bare", and to report what a proposal actually added. */
export function markCount(text) {
  return ((text ?? "").match(MARKS_RE) || []).length;
}

/** Marks per Arabic letter. The source averages ~0.02; a fully vowelled text runs
 *  an order of magnitude higher. Used only to pick candidates, never to judge. */
export function markDensity(text) {
  const letters = ((text ?? "").match(/[؀-ۿ]/g) || []).filter(
    (c) => !MARKS_RE.test(c),
  ).length;
  return letters ? markCount(text) / letters : 0;
}

function filePath(bookDir) {
  return join(bookDir, "_system", PROPOSALS_NAME);
}

export function loadProposals(bookDir) {
  const p = filePath(bookDir);
  if (!existsSync(p)) return [];
  try {
    const parsed = JSON.parse(readFileSync(p, "utf8"));
    return Array.isArray(parsed?.proposals) ? parsed.proposals : [];
  } catch {
    return [];
  }
}

export function saveProposals(bookDir, proposals) {
  const p = filePath(bookDir);
  mkdirSync(join(bookDir, "_system"), { recursive: true });
  writeFileSync(
    p,
    `${JSON.stringify({ schema: SCHEMA, proposals }, null, 2)}\n`,
    "utf8",
  );
  return p;
}

/**
 * The gate. A candidate vowelling is admissible only if it changes NOTHING but
 * marks, and actually adds some.
 *
 * Returns the reason for refusal, or `null` when the candidate is admissible. The
 * reason is surfaced to the reviewer rather than swallowed: a model that keeps
 * failing the skeleton check is telling you something about the passage.
 */
export function rejectionReason(source, candidate) {
  if (!candidate || !candidate.trim()) return "empty";
  if (!ARABIC_RE.test(candidate)) return "no Arabic script in the candidate";
  const a = skeleton(source);
  const b = skeleton(candidate);
  if (a !== b) {
    // Report the first divergence — a reviewer reading "differs at character 12"
    // can see instantly whether the model rewrote a word or dropped a clause.
    let i = 0;
    while (i < a.length && i < b.length && a[i] === b[i]) i++;
    return `letters changed, not just marks (first difference at character ${i + 1}: source "${a.slice(i, i + 12)}" vs proposal "${b.slice(i, i + 12)}")`;
  }
  if (markCount(candidate) <= markCount(source)) return "adds no vowel marks";
  return null;
}

/** A run worth proposing for: it has Arabic, it is long enough to be a real
 *  passage rather than a stray word, and it is not already vowelled. The density
 *  floor is deliberately generous — a run with a couple of disambiguating marks
 *  from the scan is still "bare" for this purpose. */
export function isVowellingCandidate(text) {
  const t = (text ?? "").trim();
  if (!ARABIC_RE.test(t)) return false;
  if (skeleton(t).replace(/\s/g, "").length < 8) return false;
  return markDensity(t) < 0.15;
}
