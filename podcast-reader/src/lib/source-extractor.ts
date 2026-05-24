/**
 * Discover and load tools/source_extractor/ bundles from the repo's
 * _workspace/kashkole-ksessions/extracted/ tree.
 *
 * Bundle layout (per tools/source_extractor/bundle.py):
 *   <extract-root>/<source>/<NN-shelf-slug>/<MM-book-slug>/
 *     bundle.yml
 *     _README.md
 *     _system/source/<book-slug>.html
 *     _system/source/text/raw-extract.md
 *     _system/source/text/_extraction-notes.md
 *     _system/source/text/_provenance.json
 *     _system/source/images/{NNN.png, NNN.json, vision-tasks.json}
 *
 * We discover the hierarchy and expose a flat list of chapter records for
 * the reader's source-extractor view.
 */

import { readdir, readFile, stat } from 'node:fs/promises';
import { join } from 'node:path';
import yaml from 'js-yaml';
import { getRepoRoot } from './worktree-glob';

const EXTRACT_RELPATH = '_workspace/kashkole-ksessions/extracted';

export interface BundleManifest {
  bundle_schema_version: number;
  source: string;
  source_language: string;
  stage: string;
  shelf: {
    kind: string;
    id: number;
    name: string;
    sort_key: number;
    slug: string;
    prefix: string;
  };
  book: {
    kind: string;
    id: number;
    name: string;
    sort_key: number;
    slug: string;
    prefix: string;
  };
  counts?: {
    sections: number;
    sections_with_content: number;
    inline_images: number;
    curated_citation_refs: number;
  };
}

export interface ChapterRecord {
  /** "kashkole" */
  source: string;
  /** "07-uloom-mabda-wa-maad" */
  shelfSlug: string;
  /** "01-tashkeel-aalam-ruhani" */
  bookSlug: string;
  /** Absolute path to the BOOK_DIR. */
  bookDir: string;
  /** Parsed bundle.yml. */
  manifest: BundleManifest;
}

export interface ShelfGroup {
  source: string;
  shelfSlug: string;
  shelfName: string;
  shelfPrefix: string;
  chapters: ChapterRecord[];
}

export interface SourceGroup {
  source: string;
  shelves: ShelfGroup[];
  chapterCount: number;
}

export function getExtractRoot(): string {
  return join(getRepoRoot(), EXTRACT_RELPATH);
}

async function isDir(p: string): Promise<boolean> {
  try {
    const s = await stat(p);
    return s.isDirectory();
  } catch {
    return false;
  }
}

async function loadManifest(bookDir: string): Promise<BundleManifest | null> {
  try {
    const text = await readFile(join(bookDir, 'bundle.yml'), 'utf-8');
    const parsed = yaml.load(text) as BundleManifest;
    if (!parsed || typeof parsed !== 'object') return null;
    return parsed;
  } catch {
    return null;
  }
}

export async function discoverBundles(): Promise<SourceGroup[]> {
  const root = getExtractRoot();
  if (!(await isDir(root))) return [];

  const sourceGroups: SourceGroup[] = [];

  const sourceDirs = (await readdir(root)).filter((d) => !d.startsWith('.') && !d.startsWith('_'));
  for (const source of sourceDirs.sort()) {
    const sourcePath = join(root, source);
    if (!(await isDir(sourcePath))) continue;

    const shelfDirs = (await readdir(sourcePath)).filter((d) => !d.startsWith('.') && !d.startsWith('_'));
    const shelves: ShelfGroup[] = [];

    for (const shelfDir of shelfDirs.sort()) {
      const shelfPath = join(sourcePath, shelfDir);
      if (!(await isDir(shelfPath))) continue;

      const bookDirs = (await readdir(shelfPath)).filter((d) => !d.startsWith('.') && !d.startsWith('_'));
      const chapters: ChapterRecord[] = [];

      let shelfName = shelfDir;
      let shelfPrefix = '';

      for (const bookDir of bookDirs.sort()) {
        const bookPath = join(shelfPath, bookDir);
        // skip flat-layout legacy artifacts (e.g. files like `03-munbathin.md` and
        // `03-munbathin-images/`); only directories that hold a bundle.yml count.
        if (!(await isDir(bookPath))) continue;

        const manifest = await loadManifest(bookPath);
        if (!manifest) continue;

        chapters.push({
          source,
          shelfSlug: shelfDir,
          bookSlug: bookDir,
          bookDir: bookPath,
          manifest,
        });

        // First book in the shelf supplies the human-readable shelf name + prefix.
        if (!shelfName || shelfName === shelfDir) {
          shelfName = manifest.shelf?.name ?? shelfDir;
          shelfPrefix = manifest.shelf?.prefix ?? '';
        }
      }

      if (chapters.length === 0) continue;
      shelves.push({
        source,
        shelfSlug: shelfDir,
        shelfName,
        shelfPrefix,
        chapters,
      });
    }

    if (shelves.length === 0) continue;
    const chapterCount = shelves.reduce((n, s) => n + s.chapters.length, 0);
    sourceGroups.push({ source, shelves, chapterCount });
  }

  return sourceGroups;
}

export async function findChapter(
  source: string,
  shelfSlug: string,
  bookSlug: string,
): Promise<ChapterRecord | null> {
  const bookDir = join(getExtractRoot(), source, shelfSlug, bookSlug);
  if (!(await isDir(bookDir))) return null;
  const manifest = await loadManifest(bookDir);
  if (!manifest) return null;
  return { source, shelfSlug, bookSlug, bookDir, manifest };
}

export async function loadChapterMarkdown(c: ChapterRecord): Promise<string> {
  return readFile(join(c.bookDir, '_system', 'source', 'text', 'raw-extract.md'), 'utf-8');
}
