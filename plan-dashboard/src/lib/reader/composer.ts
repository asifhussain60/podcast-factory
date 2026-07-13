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

export interface ComposerChapter {
  anchor: string;   // the raw "## N. Title" heading — the placement anchor
  key: string;      // normalized comparable key (mirrors visual-layout anchorKey)
  title: string;    // display title
  html: string;     // rendered chapter body
  paras: number;    // prose-paragraph count (for the anchor_para position control)
}

export interface ComposerVisual {
  id: string;
  type: string;
  caption: string;
  file: string;            // basename in book/visuals/
  src: string;             // servable URL
  suggested_anchor: string;
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
    chapters.push({
      anchor: heading,
      key: anchorKey(heading),
      title: displayTitle,
      html: renderMarkdown(body),
      paras,
    });
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
    cleaned: v.cleaned ?? true,
    embedded_title: v.embedded_title ?? '',
  }));

  const layoutData = await readJson<{ placements?: ComposerPlacement[] }>(
    join(ref.dir, 'book', 'visual-layout.json'), {},
  );
  const placements: ComposerPlacement[] = layoutData.placements ?? [];

  return { slug, title, chapters, visuals, placements, hasBook: true };
}
