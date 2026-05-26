/**
 * content-paths.ts — TypeScript mirror of scripts/podcast/_paths.py.
 *
 * Single source of truth for mapping (stage, category, slug) → directory on
 * the reader side. Update both this file AND _paths.py together when the
 * on-disk layout changes.
 *
 * LAYOUT (locked 2026-05-26):
 *
 *   content/
 *     drafts/
 *       books/<slug>/
 *       lectures/<slug>/
 *       asbaaq/<slug>/
 *       ...
 *     published/
 *       books/<slug>/
 *       lectures/<slug>/
 *       ...
 *     _shared/
 *     _archive/<date>/<slug>/
 *
 * LEGACY: a partial migration may leave some books at the old flat
 * ``content/drafts/<slug>/``. ``findContent()`` falls back to that shape so
 * the reader doesn't break mid-migration.
 */
import { readdir, stat } from 'node:fs/promises';
import { join } from 'node:path';
import { getRepoRoot } from './worktree-glob';

export type Stage = 'drafts' | 'published';

export const ALLOWED_CATEGORIES = [
  'books',
  'articles',
  'documents',
  'lectures',
  'interviews',
  'letters',
  'asbaaq',
] as const;

export type Category = (typeof ALLOWED_CATEGORIES)[number];

export interface ContentRef {
  stage: Stage;
  category: Category;
  slug: string;
  dir: string;
}

function stageRoot(stage: Stage): string {
  return join(getRepoRoot(), 'content', stage);
}

export function contentDir(slug: string, stage: Stage = 'drafts', category: Category = 'books'): string {
  if (!slug || slug.includes('/')) {
    throw new Error(`content-paths: invalid slug ${JSON.stringify(slug)}`);
  }
  if (!ALLOWED_CATEGORIES.includes(category)) {
    throw new Error(`content-paths: unknown category ${JSON.stringify(category)}`);
  }
  return join(stageRoot(stage), category, slug);
}

export function categoryRoot(category: Category, stage: Stage = 'drafts'): string {
  return join(stageRoot(stage), category);
}

async function isDir(p: string): Promise<boolean> {
  try {
    const s = await stat(p);
    return s.isDirectory();
  } catch {
    return false;
  }
}

/** Locate ``slug`` across all (stage, category) combos. Canonical first, then legacy flat. */
export async function findContent(slug: string): Promise<ContentRef | null> {
  for (const stage of ['drafts', 'published'] as Stage[]) {
    for (const cat of ALLOWED_CATEGORIES) {
      const p = join(stageRoot(stage), cat, slug);
      if (await isDir(p)) return { stage, category: cat, slug, dir: p };
    }
  }
  // Legacy flat fallback
  const flat = join(stageRoot('drafts'), slug);
  if (
    !ALLOWED_CATEGORIES.includes(slug as Category) &&
    slug !== 'BOOKS' && slug !== 'LECTURES' &&
    (await isDir(flat))
  ) {
    return { stage: 'drafts', category: 'books', slug, dir: flat };
  }
  return null;
}

/** Yield every (stage, category, slug, dir) currently on disk. Honors canonical AND legacy flat. */
export async function listContent(opts: { stage?: Stage; category?: Category } = {}): Promise<ContentRef[]> {
  const stages: Stage[] = opts.stage ? [opts.stage] : ['drafts', 'published'];
  const cats: readonly Category[] = opts.category ? [opts.category] : ALLOWED_CATEGORIES;
  const seen = new Set<string>();
  const out: ContentRef[] = [];

  for (const stage of stages) {
    const sr = stageRoot(stage);
    if (!(await isDir(sr))) continue;
    // Canonical
    for (const cat of cats) {
      const catDir = join(sr, cat);
      if (!(await isDir(catDir))) continue;
      let entries: string[];
      try {
        entries = await readdir(catDir);
      } catch {
        continue;
      }
      for (const slug of entries.sort()) {
        if (slug.startsWith('.') || slug.startsWith('_')) continue;
        const dir = join(catDir, slug);
        if (!(await isDir(dir))) continue;
        if (seen.has(dir)) continue;
        seen.add(dir);
        out.push({ stage, category: cat, slug, dir });
      }
    }
    // Legacy flat (drafts only, books category)
    if (stage === 'drafts' && (opts.category === undefined || opts.category === 'books')) {
      let entries: string[];
      try {
        entries = await readdir(sr);
      } catch {
        continue;
      }
      for (const name of entries.sort()) {
        if (name.startsWith('.') || name.startsWith('_')) continue;
        if ((ALLOWED_CATEGORIES as readonly string[]).includes(name)) continue;
        if (name === 'BOOKS' || name === 'LECTURES') continue;
        const dir = join(sr, name);
        if (!(await isDir(dir))) continue;
        if (seen.has(dir)) continue;
        seen.add(dir);
        out.push({ stage, category: 'books', slug: name, dir });
      }
    }
  }
  return out;
}
