/**
 * chapters.ts — chapter + episode discovery for the library viewer.
 *
 * Ported from podcast-reader/src/lib/book-content.ts, adapted to call into
 * the canonical content-paths resolver (so it follows the same source of
 * truth the library index and the orchestrator use).
 */
import { readFile, readdir, stat } from 'node:fs/promises';
import { join } from 'node:path';
import { load as yamlLoad } from 'js-yaml';

import { findContent } from '../content-paths';

export interface BookChapter {
  slug: string;              // 'ch01-the-perfect-and-the-perfection-of-the-soul'
  numericId: number | null;
  title: string;
  filePath: string;
  bytes: number;
}

export interface BookEpisode {
  slug: string;
  episodeNumber: number | null;
  title: string;
  sourceChapterRef: string | null;
  filePath: string;
  contractKeys: string[];
}

export interface BookIndex {
  book: string;
  rootPath: string;
  chapters: BookChapter[];
  episodes: BookEpisode[];
}

async function safeStat(p: string) {
  try { return await stat(p); } catch { return null; }
}

async function discoverChapters(root: string): Promise<BookChapter[]> {
  const dir = join(root, 'chapters');
  let entries: string[];
  try { entries = await readdir(dir); } catch { return []; }

  const out: BookChapter[] = [];
  for (const name of entries) {
    if (!name.endsWith('.txt') && !name.endsWith('.md')) continue;
    if (name.startsWith('.') || name.startsWith('_')) continue;
    const filePath = join(dir, name);
    const slug = name.replace(/\.(txt|md)$/i, '');
    const numMatch = slug.match(/^ch(\d+)/i);
    const numericId = numMatch ? Number(numMatch[1]) : null;

    let title = slug.replace(/^ch\d+-/i, '').replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
    let bytes = 0;
    try {
      const buf = await readFile(filePath, 'utf-8');
      bytes = buf.length;
      const m = buf.match(/^#\s+(.+)$/m);
      if (m) title = m[1].trim();
    } catch { /* noop */ }
    out.push({ slug, numericId, title, filePath, bytes });
  }
  return out.sort((a, b) => (a.numericId ?? 999) - (b.numericId ?? 999));
}

async function discoverEpisodes(root: string): Promise<BookEpisode[]> {
  const dir = join(root, 'chapter-contracts');
  let entries: string[];
  try { entries = await readdir(dir); } catch { return []; }

  const out: BookEpisode[] = [];
  for (const name of entries) {
    if (!name.endsWith('.yml') && !name.endsWith('.yaml')) continue;
    if (name.startsWith('.') || name.startsWith('_')) continue;
    const filePath = join(dir, name);
    const slug = name.replace(/\.(yml|yaml)$/i, '');
    try {
      const raw = await readFile(filePath, 'utf-8');
      const parsed = yamlLoad(raw) as Record<string, unknown> | null;
      if (!parsed || typeof parsed !== 'object') {
        out.push({ slug, episodeNumber: null, title: slug.replace(/-/g, ' '), sourceChapterRef: null, filePath, contractKeys: [] });
        continue;
      }
      out.push({
        slug,
        episodeNumber: typeof parsed.episode_number === 'number' ? parsed.episode_number : null,
        title: typeof parsed.title === 'string' ? parsed.title : slug.replace(/-/g, ' '),
        sourceChapterRef:
          typeof parsed.chapter_ref === 'string'
            ? parsed.chapter_ref
            : typeof parsed.source_chapter_ref === 'string' || typeof parsed.source_chapter_ref === 'number'
              ? String(parsed.source_chapter_ref)
              : null,
        filePath,
        contractKeys: Object.keys(parsed),
      });
    } catch { /* noop */ }
  }
  return out.sort((a, b) => (a.episodeNumber ?? 999) - (b.episodeNumber ?? 999));
}

export async function loadBookIndex(slug: string): Promise<BookIndex | null> {
  const ref = await findContent(slug);
  if (!ref) return null;
  const s = await safeStat(ref.dir);
  if (!s?.isDirectory()) return null;

  const [chapters, episodes] = await Promise.all([
    discoverChapters(ref.dir),
    discoverEpisodes(ref.dir),
  ]);
  return { book: slug, rootPath: ref.dir, chapters, episodes };
}

export async function loadChapterSource(filePath: string): Promise<string> {
  return readFile(filePath, 'utf-8');
}
