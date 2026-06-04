/**
 * book.ts — loader for the companion reading edition (PDF path).
 *
 * Reads content/<Bucket>/<slug>/book/book.md and projects it into a renderable
 * shape for the Studio Book view. Mirrors the pattern of loadBookIndex in
 * chapters.ts: resolve via the canonical content-paths resolver, read the file,
 * render through the shared markdown renderer (which folds scholarly transliteration
 * to plain English and leaves Arabic script untouched).
 */
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { findContent } from '../content-paths';
import { renderMarkdown } from './markdown';

export interface BookTocEntry {
  id: string;     // anchor id, matches renderMarkdown's heading slug
  title: string;  // the `## ` heading text
}

export interface BookView {
  slug: string;
  title: string;     // the book's `# ` title
  html: string;      // rendered body (h1 stripped — shown in the page header instead)
  toc: BookTocEntry[];
}

/** Same slug rule renderMarkdown uses for heading ids (markdown.ts) — keep in sync. */
function headingSlug(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-')
    .slice(0, 80);
}

export async function loadBook(slug: string): Promise<BookView | null> {
  const ref = await findContent(slug);
  if (!ref) return null;

  const mdPath = join(ref.dir, 'book', 'book.md');
  let md: string;
  try {
    md = await readFile(mdPath, 'utf-8');
  } catch {
    return null; // no reading edition generated yet
  }

  const titleMatch = md.match(/^#\s+(.+)$/m);
  const title = titleMatch ? titleMatch[1].trim() : slug;

  // TOC from the `## ` headings (preface + chapters).
  const toc: BookTocEntry[] = [];
  for (const m of md.matchAll(/^##\s+(.+)$/gm)) {
    const t = m[1].trim();
    toc.push({ id: headingSlug(t), title: t });
  }

  // Strip the leading `# ` title line from the body — the page header shows it.
  const body = md.replace(/^#\s+.+$\n?/m, '');

  return { slug, title, html: renderMarkdown(body), toc };
}
