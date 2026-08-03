/**
 * articulation.ts — which chapters would a Composer save freeze as machine text?
 *
 * RCA-001 (docs/rca/2026-07-22-composer-snapshots-froze-unarticulated-prose.md)
 * action item AI-3. A Composer save stores the ENTIRE chapter body as a durable
 * human edit, and the pipeline then never re-voices that chapter. On 2026-07-20
 * that froze 8 chapters of raw calqued translation, because the saves happened
 * on a day the articulation (fluency) pass had produced nothing. This module
 * reads the pass's own report (`_system/book-fluency-report.json`) and answers,
 * per chapter: is the CURRENT base articulated prose, or would a save freeze
 * un-articulated machine text?
 *
 * The answer is ADVISORY — the Composer surfaces it as a warning + explicit
 * confirm, never as a block. A book without a fluency report (companion books,
 * pre-v2 books) gets no warnings: the articulation contract does not apply.
 *
 * Statuses written by scripts/podcast/_book_voice.py:
 *   adapted        every window of the articulation pass was kept — safe
 *   partial        some windows reverted to the calqued base — warn
 *   reverted       the whole chapter reverted to the calqued base — warn
 *   skipped        a targeted re-run passed this chapter through — warn
 *   composer-edit  a human save owns the chapter; `superseded_status` carries
 *                  what the last pass said BEFORE the takeover, so a chapter
 *                  frozen after a kept adaptation stays safe while one frozen
 *                  before articulation ever succeeded keeps warning.
 */
import { anchorKey } from "../../../scripts/lib/anchor-key.mjs";

/**
 * The edition's introduction is APPARATUS, not a translated chapter, and the
 * articulation contract does not apply to it — the same exemption a book with no
 * fluency report already gets.
 *
 * It is written by `_book_frontmatter` at the tail of the apparatus, directly
 * under the articulation register (`_book_voice_prompts.ARTICULATION_REGISTER`,
 * the very text the chapters are articulated with). The fluency pass therefore
 * has no record of it and never should: there is no calqued base to de-calque,
 * because nobody translated it.
 *
 * Left in, the warning was wrong twice over. It told a reader the introduction
 * "has not been articulated" on a book whose every chapter had been, which reads
 * as a failure where there is none; and it warned against saving, when a
 * Composer save of the introduction is a SUPPORTED path — `apply_introduction`
 * looks for a human's version first and never writes over it.
 */
const INTRODUCTION_KEY = "introduction to the book";

interface FluencyRecordish {
  title?: unknown;
  status?: unknown;
  superseded_status?: unknown;
}

/** Reason a save of this status would freeze machine text; "" = safe to save. */
function freezeReason(status: string): string {
  switch (status) {
    case "adapted":
      return "";
    case "partial":
      return "articulation kept only part of this chapter — the rest is still the machine base";
    case "reverted":
      return "the articulation pass reverted this chapter to the machine base";
    case "skipped":
      return "the articulation pass skipped this chapter";
    // Stamped by the post-replay reconcile (RCA-001 AI-2): the pass adapted the
    // chapter, then the Composer-edit replay overwrote it in the same compose —
    // so the CURRENT base is not articulated and a save would freeze it again.
    case "adapted-then-overwritten":
      return "the replay discarded this chapter's articulated prose — its current base is not articulated";
    // "composer-edit" as the SUPERSEDED status means the takeover chain never
    // reaches an adaptation — reports written before the _merge_records origin
    // fix (2026-07-22) can also carry it; both read as never-articulated.
    case "":
    case "composer-edit":
      return "this chapter was frozen by a Composer save before articulation ever succeeded";
    default:
      return `the articulation pass left this chapter in state "${status}"`;
  }
}

/**
 * Map each at-risk chapter key to a plain-language reason. Keys with a kept
 * "adapted" status are absent. An empty object means every chapter is safe —
 * or that this book is not on the translation route at all.
 *
 * A missing/unreadable report is ambiguous, so `translationRoute` (the book has
 * a source-crosswalk) disambiguates: on the translation route, no report means
 * the articulation pass has NOT RUN YET and every chapter's base is still the
 * calqued machine translation — every save must warn. Off that route (companion
 * books, whose voice pass writes book-voice-report.json instead), the
 * articulation contract simply does not apply and nothing warns.
 */
export function articulationWarningsFrom(
  report: unknown,
  chapterKeys: string[],
  opts: { translationRoute?: boolean } = {},
): Record<string, string> {
  const records = (report as { chapters?: unknown } | null)?.chapters;
  if (!Array.isArray(records)) {
    if (!opts.translationRoute) return {};
    const out: Record<string, string> = {};
    for (const key of chapterKeys) {
      if (key === INTRODUCTION_KEY) continue;
      out[key] = "the articulation pass has not run for this book";
    }
    return out;
  }
  const statusByKey = new Map<string, string>();
  for (const rec of records as FluencyRecordish[]) {
    const key = anchorKey(String(rec?.title ?? ""));
    if (!key) continue;
    const status = String(rec?.status ?? "");
    // A composer-edit chapter is judged by what the pass said BEFORE the human
    // took it over: frozen-after-adaptation is safe, frozen-before is the RCA.
    statusByKey.set(
      key,
      status === "composer-edit"
        ? String(rec?.superseded_status ?? "")
        : status,
    );
  }
  const out: Record<string, string> = {};
  for (const key of chapterKeys) {
    if (key === INTRODUCTION_KEY) continue;
    // A chapter the report has never heard of is unknown, not safe: the pass
    // has no evidence its prose was ever articulated.
    const reason = statusByKey.has(key)
      ? freezeReason(statusByKey.get(key)!)
      : "the articulation pass has no record of this chapter";
    if (reason) out[key] = reason;
  }
  return out;
}
