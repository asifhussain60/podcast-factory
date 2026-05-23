/**
 * Discover the chapters and episodes for a given book in a worktree.
 *
 * In kitab-al-riyad (the v1 pilot), the layout is:
 *
 *   <worktree>/content/podcast/library/books/<book>/
 *   ├── chapters/                  # source book chapters (.txt, markdown-flavoured)
 *   │   └── ch01-the-perfect-...txt
 *   ├── chapter-contracts/         # podcast episode contracts (.yml)
 *   │   └── the-perfect-and-the-perfection-of-the-soul.yml
 *   ├── episodes/                  # rendered episode artifacts
 *   ├── transcripts/               # transcript material
 *   └── _system/                   # internal scratch
 *
 * Episodes have a numeric `episode_number` and reference a source chapter
 * via `source_chapter_ref`. One source chapter may produce multiple episodes
 * (sectioned via `section_index`), so the relationship is many-to-one.
 */

import { readdir, readFile, stat } from 'node:fs/promises';
import { basename, join } from 'node:path';
import { load as yamlLoad } from 'js-yaml';

import { getWorktreesRoot } from './worktree-glob';

export interface BookChapter {
  slug: string;              // 'ch01-the-perfect-and-the-perfection-of-the-soul'
  numericId: number | null;  // 1, 2, ... or null if no chNN prefix
  title: string;             // first '# ...' line if present, else from filename
  filePath: string;
  bytes: number;
}

export interface BookEpisode {
  slug: string;                       // 'the-perfect-and-the-perfection-of-the-soul'
  episodeNumber: number | null;
  title: string;
  sourceChapterRef: string | null;    // 'ch11-...' or numeric ref like '9'
  filePath: string;
  contractKeys: string[];             // top-level keys present in the YAML
}

export interface BookIndex {
  worktree: string;
  book: string;
  rootPath: string;
  chapters: BookChapter[];
  episodes: BookEpisode[];
}

function bookRoot(worktree: string, book: string): string {
  return join(getWorktreesRoot(), worktree, 'content', 'podcast', 'library', 'books', book);
}

export async function loadBookIndex(worktree: string, book: string): Promise<BookIndex | null> {
  const root = bookRoot(worktree, book);
  try {
    const s = await stat(root);
    if (!s.isDirectory()) return null;
  } catch {
    return null;
  }

  const [chapters, episodes] = await Promise.all([
    discoverChapters(root),
    discoverEpisodes(root),
  ]);

  return { worktree, book, rootPath: root, chapters, episodes };
}

async function discoverChapters(root: string): Promise<BookChapter[]> {
  const dir = join(root, 'chapters');
  let entries: string[];
  try {
    entries = await readdir(dir);
  } catch {
    return [];
  }

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
    } catch {
      // ignore
    }
    out.push({ slug, numericId, title, filePath, bytes });
  }

  return out.sort((a, b) => (a.numericId ?? 999) - (b.numericId ?? 999));
}

async function discoverEpisodes(root: string): Promise<BookEpisode[]> {
  const dir = join(root, 'chapter-contracts');
  let entries: string[];
  try {
    entries = await readdir(dir);
  } catch {
    return [];
  }

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
        out.push({
          slug,
          episodeNumber: null,
          title: slug.replace(/-/g, ' '),
          sourceChapterRef: null,
          filePath,
          contractKeys: [],
        });
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
    } catch {
      // ignore malformed YAML for now
    }
  }

  return out.sort((a, b) => (a.episodeNumber ?? 999) - (b.episodeNumber ?? 999));
}

export async function loadChapterSource(filePath: string): Promise<string> {
  return readFile(filePath, 'utf-8');
}

export function chapterTitleFromSlug(slug: string): string {
  return slug.replace(/^ch\d+-/i, '').replace(/-/g, ' ');
}

export { basename };
