/**
 * book.ts — loader for the companion reading edition (PDF path).
 *
 * Reads content/<Bucket>/<slug>/book/book.md and projects it into a renderable
 * shape for the Studio Book view. Mirrors the pattern of loadBookIndex in
 * chapters.ts: resolve via the canonical content-paths resolver, read the file,
 * render through the shared markdown renderer (which folds scholarly transliteration
 * to plain English and leaves Arabic script untouched).
 */
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { findContent } from "../content-paths";
import { renderMarkdown } from "./markdown";
// The TOC id IS the key Companion notes are filed under — one rule, one module,
// so a note can never be written under a key this reader does not look up.
import { sectionKeyFromHeading } from "./companion/keys";
// Same readers the PDF renderer uses, so the LIVE reader cannot disagree with the
// printed page about how a book's quotations are set. Node-only module; this
// loader runs server-side.
import {
  readCitationFamily,
  readTranslationFont,
  readArabicFont,
  readQuranicRuns,
} from "../../../scripts/lib/book-html.mjs";

export interface BookTocEntry {
  id: string; // anchor id, matches renderMarkdown's heading slug
  title: string; // the `## ` heading text
}

export interface BookView {
  slug: string;
  title: string; // the book's `# ` title
  html: string; // rendered body (h1 stripped — shown in the page header instead)
  toc: BookTocEntry[];
  /** The book's citation/quote family and translation face from
   *  book/citation-style.json. The caller stamps them on the prose container as
   *  `style-<family> tr-<font>`, the same hooks the PDF puts on <body> — without
   *  them this surface rendered every book in the base look regardless of the
   *  choice made in the Composer. '' = unset (falls back to the base look and the
   *  default translation face). */
  citationFamily: string;
  translationFont: string;
  /** The NON-Qur'anic Arabic face; '' falls back to Scheherazade New. */
  arabicFont: string;
}

export async function loadBook(slug: string): Promise<BookView | null> {
  const ref = await findContent(slug);
  if (!ref) return null;

  const mdPath = join(ref.dir, "book", "book.md");
  let md: string;
  try {
    md = await readFile(mdPath, "utf-8");
  } catch {
    return null; // no reading edition generated yet
  }

  const titleMatch = md.match(/^#\s+(.+)$/m);
  const title = titleMatch ? titleMatch[1].trim() : slug;

  // TOC from the `## ` headings (preface + chapters).
  const toc: BookTocEntry[] = [];
  for (const m of md.matchAll(/^##\s+(.+)$/gm)) {
    const t = m[1].trim();
    toc.push({ id: sectionKeyFromHeading(t), title: t });
  }

  // Strip the leading `# ` title line from the body — the page header shows it.
  const body = md.replace(/^#\s+.+$\n?/m, "");

  const bookDir = join(ref.dir, "book");
  return {
    slug,
    title,
    // Scripture is set in the Uthmanic face and everything else in Scheherazade,
    // from the same audit provenance the printed page uses.
    html: renderMarkdown(body, {
      quranicRuns: readQuranicRuns(ref.dir) as Set<string>,
    }),
    toc,
    citationFamily: String(readCitationFamily(bookDir) ?? ""),
    translationFont: String(readTranslationFont(bookDir) ?? ""),
    arabicFont: String(readArabicFont(bookDir) ?? ""),
  };
}
