/**
 * content-paths.ts — TypeScript mirror of scripts/podcast/_paths.py.
 *
 * Single source of truth for content paths in the Podcast Factory Astro Site.
 * Mirrors scripts/podcast/_paths.py — update both (Python + this file) together
 * when the on-disk layout changes.
 *
 * LAYOUT (type-first, locked 2026-06-04):
 *   content/<Bucket>/<slug>/        Bucket ∈ {Islamic, Technical, Fiction, Guides}
 *   content/_system/                cross-cutting plumbing (shared/archive/knowledge-base/podcast/catalog)
 * Draft-vs-published is a `status` field in <slug>/_system/orchestrator-state.json
 * (default 'draft'), NOT a folder. Legacy content/<stage>/<category>/<slug>/ is
 * still resolved as a fallback so a partial migration cannot break the reader.
 */
import { readdir, stat, readFile } from 'node:fs/promises';
import { existsSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { join, resolve } from 'node:path';

// Derive repo root from this file's location: src/lib/ → ../../ → repo root.
const DEFAULT_REPO_ROOT = resolve(fileURLToPath(import.meta.url), '..', '..', '..', '..');

export function getRepoRoot(): string {
  return process.env.PODCAST_FACTORY_ROOT ?? DEFAULT_REPO_ROOT;
}

// ── Type-first buckets (2026-06-04) ──────────────────────────────────────────
export const BUCKETS = ['Islamic', 'Technical', 'Fiction', 'Guides'] as const;
export type Bucket = (typeof BUCKETS)[number];

export type Status = 'draft' | 'published' | 'archived';

// ── Legacy category axis (retained for the optional kind tag + fallback scan) ─
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

/** Categories currently active for content creation. */
export const ACTIVE_CATEGORIES: readonly Category[] = ['books', 'lectures', 'asbaaq'];

/** Legacy category → bucket, for transitional callers passing a category. */
const CATEGORY_TO_BUCKET: Record<string, Bucket> = {
  books: 'Islamic', lectures: 'Islamic', letters: 'Islamic',
  asbaaq: 'Islamic', interviews: 'Islamic', articles: 'Islamic',
  documents: 'Islamic', sites: 'Guides', explainers: 'Guides',
};

export interface ContentRef {
  bucket: Bucket;
  status: Status;
  slug: string;
  dir: string;
  /** @deprecated legacy axis — derived for back-compat (status→stage). */
  stage: Stage;
  /** @deprecated legacy axis — best-effort during transition. */
  category: Category;
}

function bucketRoot(bucket: Bucket): string {
  return join(getRepoRoot(), 'content', bucket);
}

function legacyStageRoot(stage: Stage): string {
  return join(getRepoRoot(), 'content', stage);
}

function statusToStage(status: Status): Stage {
  return status === 'published' ? 'published' : 'drafts';
}

async function isDir(p: string): Promise<boolean> {
  try {
    const s = await stat(p);
    return s.isDirectory();
  } catch {
    return false;
  }
}

/** Read the publication status from a book dir's orchestrator-state.json. */
export async function statusOf(dir: string): Promise<Status> {
  try {
    const raw = await readFile(join(dir, '_system', 'orchestrator-state.json'), 'utf-8');
    const s = JSON.parse(raw).status;
    if (s === 'draft' || s === 'published' || s === 'archived') return s;
  } catch {
    /* fall through */
  }
  return 'draft';
}

function resolveBucket(bucket?: Bucket, category?: Category | string): Bucket {
  if (bucket) return bucket;
  if (category) return CATEGORY_TO_BUCKET[String(category).toLowerCase()] ?? 'Islamic';
  return 'Islamic';
}

function isDirSync(p: string): boolean {
  try { return statSync(p).isDirectory(); } catch { return false; }
}

/**
 * Synchronous sibling of findContent: return the on-disk directory for `slug`,
 * or null. Mirrors the bucket-first + legacy-fallback resolution of findContent
 * (and _paths.find_content). Exists for the synchronous Studio loaders that must
 * not hardcode the old content/drafts/books path (which the 2026-06-04 restructure
 * removed). Prefer the async findContent in async contexts.
 */
export function findContentDirSync(slug: string): string | null {
  for (const bucket of BUCKETS) {
    const dir = join(bucketRoot(bucket), slug);
    if (isDirSync(dir)) return dir;
  }
  for (const stage of ['drafts', 'published'] as Stage[]) {
    for (const cat of ALLOWED_CATEGORIES) {
      const dir = join(legacyStageRoot(stage), cat, slug);
      if (isDirSync(dir)) return dir;
    }
    const flat = join(legacyStageRoot(stage), slug);
    if (!(ALLOWED_CATEGORIES as readonly string[]).includes(slug) && isDirSync(flat)) return flat;
  }
  return null;
}

/**
 * Canonical directory for a piece of content: content/<Bucket>/<slug>.
 * Back-compat signature: the 2nd arg may be a Bucket (preferred) or a legacy
 * Stage (ignored); a category maps to a bucket. Does NOT check existence.
 */
export function contentDir(slug: string, bucketOrStage?: Bucket | Stage, category?: Category): string {
  if (!slug || slug.includes('/')) {
    throw new Error(`content-paths: invalid slug ${JSON.stringify(slug)}`);
  }
  const maybeBucket = (BUCKETS as readonly string[]).includes(bucketOrStage as string)
    ? (bucketOrStage as Bucket)
    : undefined;
  return join(bucketRoot(resolveBucket(maybeBucket, category)), slug);
}

export function bucketDir(bucket: Bucket): string {
  return bucketRoot(bucket);
}

/** Legacy: content/<stage>/<category>. Retained for transitional callers. */
export function categoryRoot(category: Category, stage: Stage = 'drafts'): string {
  return join(legacyStageRoot(stage), category);
}

export function archiveRoot(): string {
  const next = join(getRepoRoot(), 'content', '_system', 'archive');
  return existsSync(next) ? next : join(getRepoRoot(), 'content', '_archive');
}

export async function findContent(slug: string): Promise<ContentRef | null> {
  // Type-first (preferred).
  for (const bucket of BUCKETS) {
    const dir = join(bucketRoot(bucket), slug);
    if (await isDir(dir)) {
      const status = await statusOf(dir);
      return { bucket, status, slug, dir, stage: statusToStage(status), category: 'books' };
    }
  }
  // Legacy: drafts/<cat>/<slug>, then published/<cat>/<slug>.
  for (const stage of ['drafts', 'published'] as Stage[]) {
    for (const cat of ALLOWED_CATEGORIES) {
      const dir = join(legacyStageRoot(stage), cat, slug);
      if (await isDir(dir)) {
        return { bucket: CATEGORY_TO_BUCKET[cat] ?? 'Islamic', status: statusFromStage(stage), slug, dir, stage, category: cat };
      }
    }
  }
  // Legacy flat fallback (drafts/<slug>/).
  const flat = join(legacyStageRoot('drafts'), slug);
  if (
    !(ALLOWED_CATEGORIES as readonly string[]).includes(slug) &&
    slug !== 'BOOKS' && slug !== 'LECTURES' &&
    (await isDir(flat))
  ) {
    return { bucket: 'Islamic', status: 'draft', slug, dir: flat, stage: 'drafts', category: 'books' };
  }
  return null;
}

function statusFromStage(stage: Stage): Status {
  return stage === 'published' ? 'published' : 'draft';
}

export async function listContent(opts: { bucket?: Bucket; stage?: Stage; category?: Category } = {}): Promise<ContentRef[]> {
  const seen = new Set<string>();
  const out: ContentRef[] = [];
  const buckets: readonly Bucket[] = opts.bucket ? [opts.bucket] : BUCKETS;

  // Type-first.
  for (const bucket of buckets) {
    const br = bucketRoot(bucket);
    if (!(await isDir(br))) continue;
    let entries: string[];
    try { entries = await readdir(br); } catch { continue; }
    for (const slug of entries.sort()) {
      if (slug.startsWith('.') || slug.startsWith('_')) continue;
      const dir = join(br, slug);
      if (!(await isDir(dir))) continue;
      if (seen.has(dir)) continue;
      seen.add(dir);
      const status = await statusOf(dir);
      out.push({ bucket, status, slug, dir, stage: statusToStage(status), category: 'books' });
    }
  }

  // Legacy fallback (only when not filtering to a specific new bucket).
  if (opts.bucket) return out;
  const cats: readonly Category[] = opts.category ? [opts.category] : ALLOWED_CATEGORIES;
  for (const stage of ['drafts', 'published'] as Stage[]) {
    const sr = legacyStageRoot(stage);
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
        out.push({ bucket: CATEGORY_TO_BUCKET[cat] ?? 'Islamic', status: statusFromStage(stage), slug, dir, stage, category: cat });
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
        out.push({ bucket: 'Islamic', status: 'draft', slug: name, dir, stage: 'drafts', category: 'books' });
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
