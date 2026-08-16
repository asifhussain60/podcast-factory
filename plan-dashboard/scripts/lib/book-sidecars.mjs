/**
 * book-sidecars.mjs — the `_system/` sidecars a composed book is printed WITH.
 *
 * Which Arabic runs the audit resolved against the canonical mushaf, what each
 * one's citation reads, the visual-assets index, and the source crosswalk.
 *
 * Split out of book-html.mjs on 2026-08-16, when that file passed its size
 * ratchet — the same shape as the book-style-settings.mjs split before it, and
 * for the same reason: these four take a book directory, read one JSON file, and
 * return data. No markdown parsing, no shared state, nothing reaching back into
 * the renderer.
 *
 * Every one TOLERATES ABSENCE by design. A book with no audit, no index or no
 * crosswalk is not a broken book, it is a book at an earlier stage — a loader
 * that threw would stop the print rather than print less.
 */

import { readFileSync, existsSync } from "node:fs";
import path from "node:path";

/** The Arabic runs this book has resolved against the CANONICAL MUSHAF, as a set
 *  of their exact text.
 *
 *  Why exact text rather than a recomputed skeleton: the classification lives in
 *  `_system/book-arabic-audit.json`, written by the Python audit, and the only
 *  honest way to recompute it here would be a JavaScript mirror of
 *  `_arabic_coverage.normalize_arabic` — a fold table that must then be kept in
 *  step with the Python forever, with a silent misclassification as the failure
 *  mode. The audit already stores each run's verbatim text, and all 52 runs of
 *  this book match `book.md` byte-for-byte, so a plain string set is both simpler
 *  and impossible to drift.
 *
 *  Consumers use it to pick the Arabic FACE: scripture is set in the Uthmanic
 *  face, everything else in Scheherazade New. An absent or stale audit yields an
 *  empty set, and every run then renders in the non-Qur'anic face — the
 *  conservative direction, since it never dresses ordinary prose as scripture. */
export function readQuranicRuns(bookContentDir) {
  const p = path.join(bookContentDir, "_system", "book-arabic-audit.json");
  const set = new Set();
  if (!existsSync(p)) return set;
  try {
    const data = JSON.parse(readFileSync(p, "utf-8"));
    for (const ch of data?.chapters || []) {
      for (const run of ch?.runs || []) {
        if (run?.resolution === "canonical-mushaf" && run?.text)
          set.add(String(run.text).trim());
      }
    }
  } catch {
    /* tolerant: a bad audit just means everything reads as non-Qur'anic */
  }
  return set;
}

/** Map visual_id -> { src, embeddedTitle } from book/visuals/index.json (v2).
 *  Absent index (today's state) yields an empty map — the layout applier then
 *  no-ops, so rendering is unchanged. */
/** Each mushaf-resolved run's printable citation — `"Al-Ahzab: 6"` — by the run's
 *  exact text, from the same audit file and the same `runs` array readQuranicRuns
 *  walks. The label is FORMATTED IN PYTHON (`_mushaf.mushaf_reference_label`),
 *  where the surah names already live, so no JavaScript copy of that table has to
 *  be kept in step for the sake of a header line.
 *
 *  A Qur'an card has no state without one: the reference always shows (Asif,
 *  2026-08-09). An audit written before this field existed yields an empty map
 *  and the band falls back to its ornament alone — which is why
 *  `provenance_drift` reports a scripture run with no reference as drift, so
 *  `--refresh-provenance` fills it. */
export function readQuranicRefs(bookContentDir) {
  const p = path.join(bookContentDir, "_system", "book-arabic-audit.json");
  const map = {};
  if (!existsSync(p)) return map;
  try {
    const data = JSON.parse(readFileSync(p, "utf-8"));
    for (const ch of data?.chapters || []) {
      for (const run of ch?.runs || []) {
        if (
          run?.resolution === "canonical-mushaf" &&
          run?.text &&
          run?.reference
        )
          map[String(run.text).trim()] = String(run.reference);
      }
    }
  } catch {
    /* tolerant: no reference just means the band shows its mark alone */
  }
  return map;
}

export function readVisualAssets(bookContentDir) {
  const p = path.join(bookContentDir, "book", "visuals", "index.json");
  const map = new Map();
  if (!existsSync(p)) return map;
  try {
    const data = JSON.parse(readFileSync(p, "utf-8"));
    for (const v of data?.visuals || []) {
      if (!v?.id || !v?.file) continue;
      map.set(String(v.id), {
        src: `/book/visuals/${v.file}`,
        embeddedTitle: String(v.embedded_title || ""),
      });
    }
  } catch {
    /* tolerant: a bad index just means no contract-driven figures */
  }
  return map;
}

/**
 * Read the source crosswalk. Accepts BOTH the `{schema, book, chapters}` object
 * and a bare array of chapter rows.
 *
 * The strict-and-silent version of this cost a whole apparatus page. A
 * regeneration wrote the rows as a top-level array, this returned `[]`, the
 * crosswalk page rendered as an empty string, the same empty map starved the
 * per-chapter "Arabic source pp." lines, and the book printed one page shorter
 * with no error anywhere in the pipeline. Nothing but a human reading the PDF
 * caught it.
 *
 * So: tolerate the shape, and refuse to be silent. A crosswalk file that exists
 * but yields no rows is a broken artifact, not an absent one, and it throws —
 * an empty return here is reserved for "there is no crosswalk", which is a
 * legitimate state for the companion route.
 */
export function readCrosswalk(bookContentDir) {
  const p = path.join(bookContentDir, "book", "source-crosswalk.json");
  if (!existsSync(p)) return [];
  let data;
  try {
    data = JSON.parse(readFileSync(p, "utf-8"));
  } catch (err) {
    throw new Error(`source-crosswalk.json is not valid JSON (${p})`, {
      cause: err,
    });
  }
  const rows = Array.isArray(data)
    ? data
    : Array.isArray(data?.chapters)
      ? data.chapters
      : null;
  if (!rows || rows.length === 0) {
    throw new Error(
      `source-crosswalk.json yielded no chapter rows (${p}) — expected an object with a ` +
        "`chapters` array, or a bare array. Refusing to render a book that silently drops its " +
        "Source Crosswalk page and every per-chapter provenance line.",
    );
  }
  return rows;
}
