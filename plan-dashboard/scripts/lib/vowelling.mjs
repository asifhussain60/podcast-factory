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
const MARKS_RE = /[\u064b-\u065f\u0670\u06d6-\u06ed\u0640]/g;

/** Non-global twin of MARKS_RE. `RegExp.test` on a /g regex advances lastIndex
 *  and so alternates true/false across calls on single characters — which is
 *  exactly how markDensity used it. Kept separate rather than dropping the /g,
 *  which `replace` and `match` above rely on. */
const MARK_RE_ONE = /[\u064b-\u065f\u0670\u06d6-\u06ed\u0640]/;

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
    (c) => !MARK_RE_ONE.test(c),
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

/**
 * `candidate`'s letters and marks, carrying `source`'s exact whitespace.
 *
 * A model asked to vowel one passage hands back one line however many lines the
 * passage occupied. `skeleton` normalises whitespace before comparing,
 * deliberately, so that collapse is INVISIBLE to the gate and a vowelling which
 * silently joined the lines of an OCR page would be admitted as "marks only".
 * Line structure is not cosmetic: `produce_bilingual` slices the Arabic source by
 * line range.
 *
 * The repair is exact rather than heuristic. Once the skeletons agree the
 * non-whitespace characters correspond one for one, so walking both — whitespace
 * from the source, letters-with-their-marks from the candidate — restores the
 * original shape without moving a mark. Returns `candidate` untouched when the
 * two do not align, leaving `rejectionReason` to refuse it and say why.
 *
 * The Python mirror is `_vowelling.reflow_to_source_whitespace`.
 */
export function reflowToSourceWhitespace(source, candidate) {
  if (skeleton(source) !== skeleton(candidate)) return candidate;
  const out = [];
  let i = 0;
  for (const ch of source ?? "") {
    if (MARK_RE_ONE.test(ch)) continue;
    if (/\s/.test(ch)) {
      out.push(ch);
      continue;
    }
    // Advance to the candidate's next LETTER, keeping any orphan marks. A scan
    // can leave a combining mark with no letter under it; consuming one AS a
    // letter puts every later letter off by one, the walk runs off the end, and
    // the repair silently gives up — handing back the model's collapsed line,
    // which `rejectionReason` cannot catch because `skeleton` has already
    // normalised the whitespace away.
    while (
      i < candidate.length &&
      (/\s/.test(candidate[i]) || MARK_RE_ONE.test(candidate[i]))
    ) {
      if (!/\s/.test(candidate[i])) out.push(candidate[i]);
      i++;
    }
    if (i >= candidate.length) return candidate;
    out.push(candidate[i]);
    i++;
    while (i < candidate.length && MARK_RE_ONE.test(candidate[i])) {
      out.push(candidate[i]);
      i++;
    }
  }
  while (i < candidate.length) {
    if (/\s/.test(candidate[i])) i++;
    else if (MARK_RE_ONE.test(candidate[i])) {
      out.push(candidate[i]);
      i++;
    } else return candidate; // real letters left over — the two do not align
  }
  return out.join("");
}

/**
 * `candidate`'s words laid back onto `source`'s whitespace, word for word.
 *
 * The companion to `reflowToSourceWhitespace`, for the one case it cannot serve:
 * a Qur'anic run replaced by the canonical mushaf text. That substitution changes
 * LETTERS — the mushaf is Uthmani — so the skeletons legitimately differ and the
 * character walk correctly refuses to align them. But the canonical lookup joins
 * a verse's words with single spaces, so a verse printed across two lines comes
 * back as one and the file loses a line. Aligning by WORD is safe precisely
 * because the mushaf lookup is itself word-aligned.
 *
 * The Python mirror is `_vowelling.reflow_words_to_source_whitespace`.
 */
export function reflowWordsToSourceWhitespace(source, candidate) {
  const srcWords = (source ?? "").split(/\s+/).filter(Boolean);
  const candWords = (candidate ?? "").split(/\s+/).filter(Boolean);
  if (!srcWords.length || srcWords.length !== candWords.length) return candidate;
  const out = [];
  let idx = 0;
  for (const piece of (source ?? "").split(/(\s+)/)) {
    if (!piece) continue;
    if (/^\s+$/.test(piece)) out.push(piece);
    else out.push(candWords[idx++]);
  }
  return out.join("");
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

/**
 * Predominantly Arabic, not merely containing some.
 *
 * An English paragraph that quotes three Arabic words is not a passage to vowel:
 * sending it would ask the model to hand back English it must not touch, and the
 * skeleton check would then refuse whatever came back — a refusal that reads as a
 * model failure when it was really a bad selection. One or two Latin characters
 * are tolerated because a stray reference marker inside an Arabic line is common.
 *
 * Lives here rather than inline in its callers so the button, the route's own
 * candidate collector and the compose-time pass all draw the line in one place;
 * the Python mirror is `_vowelling.is_arabic_passage`.
 */
export function isArabicPassage(text) {
  const s = text ?? "";
  const latin = (s.match(/[A-Za-z]/g) || []).length;
  const arabic = (s.match(/[؀-ۿ]/g) || []).length;
  return !(latin > 2 || arabic < latin * 4);
}
