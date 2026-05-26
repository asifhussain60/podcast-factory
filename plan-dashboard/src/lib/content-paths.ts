/**
 * content-paths.ts — TypeScript mirror of scripts/podcast/_paths.py.
 *
 * Identical contract to podcast-reader/src/lib/content-paths.ts. Update all
 * three (Python + reader + dashboard) together when the on-disk layout
 * changes. Single source of truth for mapping (stage, category, slug) → dir.
 *
 * LAYOUT (locked 2026-05-26):
 *   content/<stage>/<category>/<slug>/
 *     stage    ∈ {drafts, published}
 *     category ∈ ALLOWED_CATEGORIES
 *     slug     — kebab-case
 */
import { readdir, stat } from 'node:fs/promises';
import { homedir } from 'node:os';
import { join } from 'node:path';

const DEFAULT_REPO_ROOT = join(homedir(), 'PROJECTS', 'podcast-factory');

export function getRepoRoot(): string {
  return process.env.PODCAST_FACTORY_ROOT ?? DEFAULT_REPO_ROOT;
}

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

/** Categories currently active for content creation. Other categories in
 * ALLOWED_CATEGORIES exist in the schema but are not yet surfaced to the user. */
export const ACTIVE_CATEGORIES: readonly Category[] = ['books', 'lectures', 'asbaaq'];

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

export function archiveRoot(): string {
  return join(getRepoRoot(), 'content', '_archive');
}

async function isDir(p: string): Promise<boolean> {
  try {
    const s = await stat(p);
    return s.isDirectory();
  } catch {
    return false;
  }
}

export async function findContent(slug: string): Promise<ContentRef | null> {
  for (const stage of ['drafts', 'published'] as Stage[]) {
    for (const cat of ALLOWED_CATEGORIES) {
      const p = join(stageRoot(stage), cat, slug);
      if (await isDir(p)) return { stage, category: cat, slug, dir: p };
    }
  }
  // Legacy flat fallback (drafts/<slug>/ from pre-2026-05-26 layout)
  const flat = join(stageRoot('drafts'), slug);
  if (
    !(ALLOWED_CATEGORIES as readonly string[]).includes(slug) &&
    slug !== 'BOOKS' && slug !== 'LECTURES' &&
    (await isDir(flat))
  ) {
    return { stage: 'drafts', category: 'books', slug, dir: flat };
  }
  return null;
}

export async function listContent(opts: { stage?: Stage; category?: Category } = {}): Promise<ContentRef[]> {
  const stages: Stage[] = opts.stage ? [opts.stage] : ['drafts', 'published'];
  const cats: readonly Category[] = opts.category ? [opts.category] : ALLOWED_CATEGORIES;
  const seen = new Set<string>();
  const out: ContentRef[] = [];

  for (const stage of stages) {
    const sr = stageRoot(stage);
    if (!(await isDir(sr))) continue;
    for (const cat of cats) {
      const catDir = join(sr, cat);
      if (!(await isDir(catDir))) continue;
      let entries: string[];
      try { entries = await readdir(catDir); } catch { continue; }
      for (const slug of entries.sort()) {
        if (slug.startsWith('.') || slug.startsWith('_')) continue;
        const dir = join(catDir, slug);
        if (!(await isDir(dir))) continue;
        if (seen.has(dir)) continue;
        seen.add(dir);
        out.push({ stage, category: cat, slug, dir });
      }
    }
    if (stage === 'drafts' && (opts.category === undefined || opts.category === 'books')) {
      let entries: string[];
      try { entries = await readdir(sr); } catch { continue; }
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

export function slugToTitle(slug: string): string {
  const lowercaseWords = new Set(['al', 'the', 'and', 'of', 'to', 'in', 'a', 'an']);
  return slug
    .split('-')
    .map((w, i) => {
      if (!w) return w;
      if (i > 0 && lowercaseWords.has(w)) return w;
      return w[0].toUpperCase() + w.slice(1);
    })
    .join(' ');
}

export function categoryLabel(category: Category): string {
  switch (category) {
    case 'books': return 'Book';
    case 'lectures': return 'Lecture';
    case 'asbaaq': return 'Sabaq';
    case 'articles': return 'Article';
    case 'documents': return 'Document';
    case 'interviews': return 'Interview';
    case 'letters': return 'Letter';
  }
}

export function categoryPlural(category: Category): string {
  switch (category) {
    case 'books': return 'Books';
    case 'lectures': return 'Lectures';
    case 'asbaaq': return 'Asbaaq';
    case 'articles': return 'Articles';
    case 'documents': return 'Documents';
    case 'interviews': return 'Interviews';
    case 'letters': return 'Letters';
  }
}
