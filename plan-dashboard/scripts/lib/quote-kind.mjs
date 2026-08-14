/**
 * quote-kind.mjs — read which KIND of quotation each block is.
 *
 * The reading edition draws four cards: Qur'an, hadith, poem, and the plain
 * quote that is the default. Only the first can be decided by machine — a run
 * either appears in the canonical mushaf or it does not — and it is decided in
 * `readQuranicRuns`, never here. Nothing in a text can tell a prophetic
 * tradition from an imam's saying from a line of verse, so the other three are
 * DECLARED by a person and recorded in `_system/quote-kind.json`. Reading a
 * lead-in sentence for "the Prophet said" was tried and rejected: on a religious
 * edition an inferred attribution is a claim nobody made.
 *
 * book.md is never touched, for the same reason text-align.mjs and
 * text-colour.mjs give: markdown has no syntax for this, the print renderer
 * escapes raw HTML, and inventing a delimiter would put new characters into the
 * file every Python phase reads as text.
 *
 * THE KEY IS THE QUOTATION'S OWN FIRST LINE, VERBATIM — not a hash. That is the
 * same choice `readQuranicRuns` makes one file over, and for the same reason:
 * the alternative is a fingerprint computed in three languages, which becomes a
 * fold table that has to be kept in step forever with a silent misclassification
 * as the failure mode. A line is a plain string both renderers already hold at
 * the moment they decide the block's class, so the two cannot disagree. A quote
 * whose first line is edited loses its kind and falls back to the default card,
 * which is the conservative direction: it never dresses a saying as scripture,
 * and it never labels a passage with an attribution the human did not give it.
 */
import { existsSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import path from "node:path";

/** The kinds a person may declare. `quran` is deliberately NOT here: it is the
 *  audit's answer, and a second way to assert it would be a second answer that
 *  has to agree with the first. `quote` is the default and is stored only when
 *  a human explicitly sets a block back to it. */
export const QUOTE_KIND_IDS = ["hadith", "poem", "quote"];

/** Kinds whose card never names a speaker, however a book declares one. Scripture
 *  heads itself with the surah the audit resolved, and a prophetic tradition is
 *  already the claim that the Prophet said it — printing a name under either is a
 *  second answer to a question the card has already answered (Asif, 2026-08-11). */
const ANON_KINDS = new Set(["quran", "hadith"]);

/** The speaker a card prints beside its kind, or "" — the whole decision, so the
 *  two renderers cannot answer it differently and neither has to remember which
 *  kinds are exempt. `declared` is a flattened first-line -> declaration map. */
export function speakerFor(declared, lines, kind) {
  if (ANON_KINDS.has(kind)) return "";
  return declared?.[quoteKindKey(lines)]?.by ?? "";
}

/** What each kind is CALLED on its card's header. Here rather than in either
 *  renderer because both draw the header and a book cannot have a tradition
 *  labelled two ways. The Qur'an is absent: its header carries the chapter and
 *  verse the audit resolved, which is not a fixed word. */
export const QUOTE_KIND_LABEL = {
  hadith: "Prophetic tradition",
  poem: "Verse",
  quote: "Saying",
};

/**
 * `_system/quote-kind.json` → { chapterKey: { firstLine: { kind, by? } } }.
 *
 * `bookDir` is the book's root (the folder holding `_system/` and `book/`).
 * Anything unreadable, absent or malformed yields {} — an edition renders every
 * quotation in the default card rather than failing to render.
 *
 * TWO FORMS OF A DECLARATION, and both stay valid. `"…": "hadith"` is the whole
 * of schema v1 and is what the one book with declarations holds today;
 * `"…": {"kind": "hadith", "by": "The Prophet"}` adds WHO SAID IT, which the
 * card prints at the right of its header. The speaker is optional and is only
 * ever typed by a person: nothing infers it from the prose, for the reason at
 * the top of this file. A malformed entry is dropped rather than guessed at, so
 * the block falls back to the default card and never to an attribution nobody
 * wrote. Normalised to the object form HERE so neither renderer has to ask
 * which shape it was given.
 */
export function readQuoteKind(bookDir) {
  const p = path.join(bookDir, "_system", "quote-kind.json");
  if (!existsSync(p)) return {};
  try {
    const raw = JSON.parse(readFileSync(p, "utf-8"));
    const out = {};
    for (const [chapter, blocks] of Object.entries(raw?.chapters ?? {})) {
      if (!blocks || typeof blocks !== "object") continue;
      const kept = {};
      for (const [line, declared] of Object.entries(blocks)) {
        const kind =
          typeof declared === "string" ? declared : (declared?.kind ?? "");
        if (!QUOTE_KIND_IDS.includes(kind)) continue;
        const by =
          typeof declared === "string" ? "" : String(declared?.by ?? "").trim();
        kept[String(line).trim()] = by ? { kind, by } : { kind };
      }
      if (Object.keys(kept).length) out[chapter] = kept;
    }
    return out;
  } catch {
    return {};
  }
}

/** Every chapter's declarations flattened into ONE first-line -> kind map.
 *
 *  The print renderer walks the whole book in one pass and sees quotations, not
 *  chapters, at the point it decides a block's classes. Flattening is safe for
 *  the same reason it is in text-align.mjs: the key is the quotation's own text,
 *  so two chapters can only collide by containing a byte-identical quotation —
 *  in which case they are the same quotation and want the same card. */
export function flattenQuoteKind(byChapter) {
  const flat = {};
  for (const blocks of Object.values(byChapter ?? {}))
    Object.assign(flat, blocks);
  return flat;
}

/** The key for one quotation: its first non-empty line, trimmed.
 *
 *  CALLERS PASS THE BLOCK'S RAW LINES, never its paragraphs. Both renderers join
 *  a quotation's consecutive lines into paragraphs before rendering them, so a
 *  three-line poem is ONE paragraph and keying on it asks for a string no human
 *  ever wrote and this store never holds. That is not hypothetical: the
 *  three-bayt poem in `ayyuhal-walad` was declared verse, filed under its first
 *  line as every declaration is, and rendered as a plain saying until the
 *  renderers were corrected on 2026-08-09.
 *
 *  Kept here rather than inlined at each call site so the two renderers cannot
 *  drift on what "first line" means — a blank leading line, which a blockquote
 *  picks up whenever the author left one, must not change a block's identity. */
export function quoteKindKey(lines) {
  for (const p of lines ?? []) {
    const line = String(p ?? "").trim();
    if (line) return line;
  }
  return "";
}

/**
 * Write (or clear) ONE declaration, added 2026-08-14 for the Composer's
 * card-type control — the first thing in this file that writes rather than
 * reads. Everything else in this store is still a human's own word: the
 * caller supplies the exact `kind`/`by` a person picked from a menu, this
 * function only persists it. `kind: ""` (or any id outside QUOTE_KIND_IDS)
 * DELETES the entry instead of writing a bad one — the same "malformed is
 * absent" posture `readQuoteKind` already takes on the way in.
 *
 * Read-modify-write, not an append, so two declarations in the same chapter
 * never race each other out — the Composer calls this once per menu pick and
 * awaits the response before the next click can fire.
 */
export function writeQuoteKind(bookDir, chapterKey, firstLine, kind, by) {
  const chapter = String(chapterKey ?? "").trim();
  const line = String(firstLine ?? "").trim();
  if (!chapter || !line)
    throw new Error("chapterKey and firstLine are required");
  const dir = path.join(bookDir, "_system");
  const p = path.join(dir, "quote-kind.json");
  const store = {
    schema: "book.quote-kind/v1",
    chapters: readQuoteKind(bookDir),
  };
  const id = String(kind ?? "");
  const speaker = String(by ?? "").trim();
  if (QUOTE_KIND_IDS.includes(id)) {
    const entry = speaker ? { kind: id, by: speaker } : { kind: id };
    store.chapters[chapter] = {
      ...(store.chapters[chapter] ?? {}),
      [line]: entry,
    };
  } else if (store.chapters[chapter]) {
    delete store.chapters[chapter][line];
    if (!Object.keys(store.chapters[chapter]).length)
      delete store.chapters[chapter];
  }
  mkdirSync(dir, { recursive: true });
  writeFileSync(p, JSON.stringify(store, null, 2) + "\n", "utf-8");
  return store;
}
