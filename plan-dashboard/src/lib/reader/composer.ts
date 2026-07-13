/**
 * composer.ts — loader for the Book Composer (Book Pipeline v2).
 *
 * The Composer is where a human curates how the decoupled visual candidates
 * (book/visuals/index.json) are placed in the reading edition. It reads three
 * things and projects them for the view:
 *   - book.md            -> chapters (anchor + title + rendered body)
 *   - visuals/index.json -> the candidate asset palette
 *   - visual-layout.json -> the current curated placements (may be absent)
 *
 * The human's edits are saved back to book/visual-layout.json via
 * /api/studio/visual-layout (PUT); the renderer (render-book-pdf.mjs) consumes
 * that contract. Read-only here — persistence is the API route's job.
 */
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { findContent } from '../content-paths';
import { renderMarkdown } from './markdown';

export interface ComposerCitation {
  ar: string;       // Arabic-script line (plain text)
  tr: string;       // translation / following line (plain text; '' if none)
}

export interface ComposerChapter {
  anchor: string;   // the raw "## N. Title" heading — the placement anchor
  key: string;      // normalized comparable key (mirrors visual-layout anchorKey)
  title: string;    // display title
  html: string;     // rendered chapter body
  paras: number;    // prose-paragraph count (for the anchor_para position control)
  citations: ComposerCitation[]; // Arabic-bearing verses/hadith detected in this chapter
}

/** Pull the Arabic-bearing quotation blocks out of rendered chapter HTML.
 *  markdown.ts tags them as `<blockquote class="quran"><p class="ar">…<p class="tr">…`,
 *  so the Citations tab can list a chapter's verses without a new data artifact. */
function extractCitations(html: string): ComposerCitation[] {
  const out: ComposerCitation[] = [];
  const strip = (s: string) => s.replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
  const blocks = html.match(/<blockquote class="quran">[\s\S]*?<\/blockquote>/g) ?? [];
  for (const b of blocks) {
    const ar = strip((b.match(/<p class="ar"[^>]*>([\s\S]*?)<\/p>/) ?? ['', ''])[1]);
    const tr = strip((b.match(/<p class="tr"[^>]*>([\s\S]*?)<\/p>/) ?? ['', ''])[1]);
    if (ar) out.push({ ar, tr });
  }
  return out;
}

export interface ComposerVisual {
  id: string;
  type: string;
  caption: string;
  file: string;            // basename in book/visuals/
  src: string;             // servable URL
  suggested_anchor: string;
  chapter: string;         // resolved chapter key (for the palette's chapter filter); '' = unassigned
  cleaned: boolean;
  embedded_title: string;
}

export interface ComposerPlacement {
  visual_id: string;
  anchor: string;
  anchor_para: number | null;
  align: 'left' | 'center' | 'right';
  flow: 'wrap' | 'standalone';
  width_pct: number;
  caption: string;
  page_fit: 'avoid' | 'before' | 'isolate-plate';
}

export interface ComposerView {
  slug: string;
  title: string;
  chapters: ComposerChapter[];
  visuals: ComposerVisual[];
  placements: ComposerPlacement[];
  hasBook: boolean;
}

/** Normalize an anchor/heading to a comparable key — mirror of visual-layout.mjs anchorKey. */
export function anchorKey(s: string): string {
  return String(s)
    .replace(/<[^>]+>/g, '')
    .replace(/^#{1,6}\s+/, '')
    .replace(/^\d+\.\s*/, '')
    .trim()
    .toLowerCase();
}

async function readJson<T>(path: string, fallback: T): Promise<T> {
  try {
    return JSON.parse(await readFile(path, 'utf-8')) as T;
  } catch {
    return fallback;
  }
}

export async function loadComposer(slug: string): Promise<ComposerView | null> {
  const ref = await findContent(slug);
  if (!ref) return null;

  let md: string;
  try {
    md = await readFile(join(ref.dir, 'book', 'book.md'), 'utf-8');
  } catch {
    return { slug, title: slug, chapters: [], visuals: [], placements: [], hasBook: false };
  }

  const titleMatch = md.match(/^#\s+(.+)$/m);
  const title = titleMatch ? titleMatch[1].trim() : slug;

  // Split into chapters on "## " headings.
  const chapters: ComposerChapter[] = [];
  // Lowercased raw bodies keyed by chapter — used to resolve a visual whose
  // suggested_anchor is a passage phrase (slides) rather than a heading (diagrams).
  const bodyByKey: { key: string; lc: string }[] = [];
  const parts = md.split(/^(##\s+.+)$/m);
  for (let i = 1; i < parts.length; i += 2) {
    const heading = parts[i].trim();
    const body = (parts[i + 1] ?? '').trim();
    const displayTitle = heading.replace(/^##\s+\d*\.?\s*/, '').trim();
    // Prose-paragraph count: blank-line-separated blocks that aren't a blockquote,
    // heading, or HTML block — mirrors what applyLayout counts as a paragraph.
    const paras = body
      .split(/\n\s*\n/)
      .filter((b) => b.trim() && !/^\s*[>#<]/.test(b)).length;
    const key = anchorKey(heading);
    const html = renderMarkdown(body);
    chapters.push({ anchor: heading, key, title: displayTitle, html, paras, citations: extractCitations(html) });
    bodyByKey.push({ key, lc: body.toLowerCase() });
  }

  // A visual's chapter: a diagram anchors by heading (direct key match); a slide
  // anchors by a quoted passage phrase, so fall back to the chapter whose body
  // contains that phrase. '' means unassigned (e.g. a book-level title slide).
  const chapterKeys = new Set(chapters.map((c) => c.key));
  function resolveChapter(suggested: string): string {
    const k = anchorKey(suggested);
    if (!k) return '';
    if (chapterKeys.has(k)) return k;
    const needle = suggested.trim().toLowerCase().slice(0, 60);
    if (!needle) return '';
    return bodyByKey.find((b) => b.lc.includes(needle))?.key ?? '';
  }

  const indexData = await readJson<{ visuals?: ComposerVisual[] }>(
    join(ref.dir, 'book', 'visuals', 'index.json'), {},
  );
  const visuals: ComposerVisual[] = (indexData.visuals ?? []).map((v) => ({
    id: v.id,
    type: v.type ?? 'diagram',
    caption: v.caption ?? '',
    file: v.file,
    src: `/api/studio/visual-asset?slug=${encodeURIComponent(slug)}&file=${encodeURIComponent(v.file)}`,
    suggested_anchor: v.suggested_anchor ?? '',
    chapter: resolveChapter(v.suggested_anchor ?? ''),
    cleaned: v.cleaned ?? true,
    embedded_title: v.embedded_title ?? '',
  }));

  const layoutData = await readJson<{ placements?: ComposerPlacement[] }>(
    join(ref.dir, 'book', 'visual-layout.json'), {},
  );
  const placements: ComposerPlacement[] = layoutData.placements ?? [];

  return { slug, title, chapters, visuals, placements, hasBook: true };
}
