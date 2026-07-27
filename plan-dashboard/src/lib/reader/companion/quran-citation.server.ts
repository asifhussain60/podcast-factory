/**
 * quran-citation.server.ts — turn the persona's `Q|18:65` into what a reader
 * needs, using the repo's own mushaf rather than the model's memory.
 *
 * Two changes to a finished card (Asif, 2026-07-26):
 *   1. `Q|18:65` becomes `Al-Kahf 18:65`, on its own line under the verse. The
 *      machine form is a citation format, not something a reader should have to
 *      decode.
 *   2. An Arabic verse is followed by its ENGLISH rendering — looked up in
 *      content/knowledge-base/mirror.db (the Pickthall column), never generated.
 *      A model paraphrase of scripture beside the scripture is the one thing a
 *      teaching card must not invent, and the canonical text is already here.
 *
 * Applied ONCE, when the card is written, so what is stored is what both surfaces
 * show — no display-time rewriting that the editor would have to round-trip.
 *
 * Every step degrades to "leave the text exactly as it was": an unknown surah, a
 * verse the mirror does not carry, a missing database. Nothing here may delete or
 * garble a line it does not understand.
 *
 * SERVER ONLY (better-sqlite3).
 */
import Database from "better-sqlite3";
import { join } from "node:path";
import { surahName, surahNumber } from "./surah-names";

const DB_PATH = join(
  new URL("../../../../../content/knowledge-base/mirror.db", import.meta.url)
    .pathname,
);

/** `Q|18:65`, `Q|2:5-10`, `Q|2: 5 : 10` — the forms the persona's spec allows. */
const CITATION =
  /Q\|\s*(\d{1,3})\s*:\s*(\d{1,3})(?:\s*[-:]\s*(\d{1,3}))?\s*&?/g;
/** The resolved form: a surah NAME then chapter:verse. Used both to find where a
 *  citation starts on a shared line and — since the persona was taught to write
 *  this form directly — to recognise a citation that never had a `Q|` at all. */
const NAMED_CITATION =
  /([A-Z'][A-Za-z'-]*(?: [A-Za-z'-]+){0,3}) (\d{1,3}):(\d{1,3})(?:-(\d{1,3}))?/;
/** A line that is nothing but a citation. */
const CITATION_ONLY = /^\s*[A-Z'][^\n]*\d{1,3}:\d{1,3}[-\d]*\s*$/;

export interface VerseText {
  arabic: string;
  english: string;
}

/** One verse from the mirror, or null when it is not there. */
function lookupVerse(
  db: Database.Database,
  s: number,
  a: number,
): VerseText | null {
  const row = db
    .prepare(
      "SELECT arabic, pickthall FROM fts_quran WHERE surah = ? AND ayat = ?",
    )
    .get(s, a) as { arabic?: string; pickthall?: string } | undefined;
  if (!row?.arabic) return null;
  return {
    arabic: String(row.arabic).trim(),
    english: String(row.pickthall ?? "").trim(),
  };
}

/** Index of the last Arabic character (with its marks), or -1. */
function lastArabicIndex(text: string): number {
  for (let i = text.length - 1; i >= 0; i--) {
    if (/[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]/.test(text[i])) return i;
  }
  return -1;
}

/** True when a line is Arabic script and carries no English of its own. */
function isBareArabicLine(line: string): boolean {
  const stripped = line.replace(/^\s*>\s?/, "").trim();
  if (!/[؀-ۿ]/.test(stripped)) return false;
  // A line that already pairs the script with a rendering needs nothing added.
  return !/[a-z]{4,}/i.test(stripped);
}

/**
 * Rewrite every citation in a card body, and give each cited verse its English.
 *
 * Line-oriented on purpose: the citation's contract is that it sits on its own
 * line after the verse, so the verse is the line above it and that is where a
 * rendering belongs.
 */
export function resolveQuranCitations(markdown: string): string {
  // Runs for the NAMED form too, not only the machine one. The persona was taught
  // to write "Al-Kahf 18:65" directly, and when it does there is no `Q|` to
  // trigger on — so a verse kept the model's own translation, on one line, outside
  // any quotation: not centred, not on its own row, and not the canonical text.
  if (!CITATION.test(markdown) && !NAMED_CITATION.test(markdown)) {
    CITATION.lastIndex = 0;
    return markdown;
  }
  CITATION.lastIndex = 0;

  // No mirror: the surah names still resolve, the renderings simply do not.
  let db: Database.Database | null;
  try {
    db = new Database(DB_PATH, { readonly: true, fileMustExist: true });
  } catch {
    db = null;
  }

  try {
    const lines = markdown.replace(/\r\n?/g, "\n").split("\n");
    const out: string[] = [];
    /** The blank quote line that separates two paragraphs inside a quotation.
     *  Consecutive `> ` lines are ONE paragraph in markdown (lazy continuation),
     *  so without these the verse, its rendering and its citation render as a
     *  single run-on line — and this is how the editor package serializes a
     *  multi-paragraph quotation, so what is written here survives the trip. */
    const gap = (mark: string) => mark.trimEnd();

    for (const line of lines) {
      // Collected, not assigned: a `let` written inside the replace callback is
      // narrowed to `never` by the compiler, which cannot see the callback run.
      const cites: { surah: number; ayat: number; range: boolean }[] = [];
      const rewritten = line.replace(
        CITATION,
        (whole, s: string, a: string, end?: string) => {
          const surah = Number(s);
          const ayat = Number(a);
          const name = surahName(surah);
          if (!name) return whole; // outside 1..114 — not ours to reinterpret
          cites.push({ surah, ayat, range: Boolean(end) });
          const ref = end ? `${surah}:${ayat}-${end}` : `${surah}:${ayat}`;
          return `${name} ${ref}`;
        },
      );

      // The NAMED form carries the same facts as `Q|18:65` and is now the one the
      // persona writes, so it is parsed here too — by resolving the written name
      // back to its number. A name that does not resolve is left alone: "Chapter
      // 3:4" is not a citation and must not be treated as one.
      if (!cites.length) {
        const named = NAMED_CITATION.exec(rewritten);
        const n = named ? surahNumber(named[1]) : 0;
        if (named && n) {
          cites.push({
            surah: n,
            ayat: Number(named[3]),
            range: Boolean(named[4]),
          });
        }
      }

      const cited = cites.length === 1 ? cites[0] : null;
      const verse =
        db && cited && !cited.range
          ? lookupVerse(db, cited.surah, cited.ayat)
          : null;
      const marker = (l: string) => /^\s*>\s?/.exec(l)?.[0] ?? "";

      // SHAPE 1 — verse and citation on ONE line, which is what the model
      // actually writes most of the time: "> ﴿…﴾ Q|12:105". Split it into the
      // three lines a reader needs, keeping the quotation's own depth so the
      // rendering and the citation stay inside the quote rather than escaping it.
      const citationOnly = CITATION_ONLY.exec(
        rewritten.replace(/^\s*>\s?/, ""),
      );
      if (cited && !citationOnly && /[؀-ۿ]/.test(rewritten)) {
        // ALWAYS a quotation, whatever the model wrote it as. A verse the model
        // set as an ordinary paragraph rendered flush-left and ran the script,
        // the translation and the citation together on one line; as a blockquote
        // it gets the centred, three-row treatment a quotation is meant to have.
        const mark = "> ";
        const bare = rewritten.replace(/^\s*>\s?/, "");
        const at = bare.search(NAMED_CITATION);
        const beforeCite = at >= 0 ? bare.slice(0, at) : bare;
        const citation = at >= 0 ? bare.slice(at).trim() : "";
        // Split the script from whatever rendering the model put beside it: the
        // Arabic ends at its last Arabic character.
        const lastAr = lastArabicIndex(beforeCite);
        const arabic = beforeCite.slice(0, lastAr + 1).trim();
        const modelEnglish = beforeCite.slice(lastAr + 1).trim();
        // The canonical rendering WINS over the model's paraphrase — that is the
        // whole point of having the mushaf in the repo — and the model's is kept
        // only when the mirror cannot answer.
        const english = verse?.english || modelEnglish;
        const parts = [arabic, english, citation].filter(Boolean);
        parts.forEach((part, i) => {
          if (i > 0) out.push(gap(mark));
          out.push(`${mark}${part}`);
        });
        continue;
      }

      // SHAPE 2 — the citation already sits on its own line; the verse is the
      // line above it, and the rendering belongs between them.
      const prev = out[out.length - 1] ?? "";
      if (verse?.english && citationOnly && isBareArabicLine(prev)) {
        const mark = marker(prev) || "> ";
        // Pull the verse line into the quotation if it was not in one.
        if (!marker(prev)) out[out.length - 1] = `${mark}${prev.trim()}`;
        out.push(gap(mark), `${mark}${verse.english}`, gap(mark));
        out.push(`${mark}${rewritten.replace(/^\s*>\s?/, "").trim()}`);
        continue;
      }
      out.push(rewritten);
    }
    return out.join("\n");
  } finally {
    db?.close();
  }
}
