/**
 * library.ts — data layer for the /library portal.
 *
 * Reads from content/<stage>/<category>/<slug>/ via the content-paths
 * resolver and projects each piece of content into a shape the portal UI
 * can render. Read-only here; mutations go through src/lib/library-mutate.ts.
 */
import { readdir, readFile, stat } from 'node:fs/promises';
import { basename, extname, join } from 'node:path';
import {
  ACTIVE_CATEGORIES,
  ALLOWED_CATEGORIES,
  categoryLabel,
  contentDir,
  findContent,
  listContent,
  slugToTitle,
  type Category,
  type ContentRef,
  type Stage,
} from './content-paths';

export type { Category, ContentRef, Stage } from './content-paths';
export { ACTIVE_CATEGORIES, ALLOWED_CATEGORIES, categoryLabel, slugToTitle, findContent, contentDir } from './content-paths';

export interface ContentSummary {
  ref: ContentRef;
  title: string;
  category: Category;
  stage: Stage;
  publicationStatus: 'draft' | 'published' | 'in_progress' | 'unknown';
  hasMeta: boolean;
  hasChapters: boolean;
  hasEpisodes: boolean;
  hasSlideDecks: boolean;
  hasSource: boolean;
  hasAudio: boolean;
  chapterCount: number;
  episodeCount: number;
  audioCount: number;
}

export interface FileEntry {
  name: string;
  path: string;
  relPath: string;       // path relative to the content root, for display
  bytes: number;
  modified: string;      // ISO string
  ext: string;
  isDir: boolean;
}

async function safeStat(p: string) {
  try { return await stat(p); } catch { return null; }
}

async function listFiles(dir: string, rootForRel: string): Promise<FileEntry[]> {
  let names: string[];
  try { names = await readdir(dir); } catch { return []; }
  const out: FileEntry[] = [];
  for (const name of names.sort()) {
    if (name === '.DS_Store') continue;
    const full = join(dir, name);
    const s = await safeStat(full);
    if (!s) continue;
    out.push({
      name,
      path: full,
      relPath: full.startsWith(rootForRel) ? full.slice(rootForRel.length + 1) : full,
      bytes: s.size,
      modified: s.mtime.toISOString(),
      ext: extname(name).toLowerCase().replace(/^\./, ''),
      isDir: s.isDirectory(),
    });
  }
  return out;
}

async function fileExists(p: string): Promise<boolean> {
  const s = await safeStat(p);
  return !!s && s.isFile();
}

async function dirExists(p: string): Promise<boolean> {
  const s = await safeStat(p);
  return !!s && s.isDirectory();
}

async function countByExt(dir: string, exts: string[]): Promise<number> {
  let names: string[];
  try { names = await readdir(dir); } catch { return 0; }
  return names.filter((n) => exts.some((e) => n.endsWith(e))).length;
}

export async function summarize(ref: ContentRef): Promise<ContentSummary> {
  const metaPath = join(ref.dir, 'meta.yml');
  const chaptersDir = join(ref.dir, 'chapters');
  const episodesDir = join(ref.dir, 'episodes');
  const slidesDir = join(ref.dir, '_system', 'slide-decks');
  const sourceDir = join(ref.dir, '_system', 'source');
  const m4aDir = join(ref.dir, 'm4a');

  const title = await readTitleFromMeta(metaPath) ?? slugToTitle(ref.slug);
  const publicationStatus = await readPublicationStatusFromMeta(metaPath);

  return {
    ref,
    title,
    category: ref.category,
    stage: ref.stage,
    publicationStatus,
    hasMeta: await fileExists(metaPath),
    hasChapters: await dirExists(chaptersDir),
    hasEpisodes: await dirExists(episodesDir),
    hasSlideDecks: await dirExists(slidesDir),
    hasSource: await dirExists(sourceDir),
    hasAudio: await dirExists(m4aDir),
    chapterCount: await countByExt(chaptersDir, ['.txt', '.md']),
    episodeCount: await countByExt(episodesDir, ['.txt']),
    audioCount: await countByExt(m4aDir, ['.m4a', '.mp3', '.wav']),
  };
}

async function readPublicationStatusFromMeta(metaPath: string): Promise<'draft' | 'published' | 'in_progress' | 'unknown'> {
  if (!(await fileExists(metaPath))) return 'unknown';
  try {
    const text = await readFile(metaPath, 'utf-8');
    // Match `status:` under `publication:` block
    const m = text.match(/^publication:[\s\S]*?^\s+status:\s*(\S+)/m);
    if (!m) return 'unknown';
    const raw = m[1].trim();
    if (raw === 'published') return 'published';
    if (raw === 'in_progress') return 'in_progress';
    if (raw === 'draft') return 'draft';
    return 'draft'; // treat any unknown value as draft
  } catch {
    return 'unknown';
  }
}

async function readTitleFromMeta(metaPath: string): Promise<string | null> {
  if (!(await fileExists(metaPath))) return null;
  try {
    const text = await readFile(metaPath, 'utf-8');
    // Best-effort: pull the first `title:` line. Don't require a full YAML parser here.
    const m = text.match(/^\s*title\s*:\s*(.+)$/m);
    if (!m) return null;
    return m[1].trim().replace(/^['"]/, '').replace(/['"]$/, '');
  } catch {
    return null;
  }
}

export interface DetailView {
  summary: ContentSummary;
  meta: Record<string, string>;
  chapters: FileEntry[];
  episodes: FileEntry[];
  slideDecks: { slug: string; files: FileEntry[] }[];
  audio: FileEntry[];
  audits: FileEntry[];
  sourceFiles: FileEntry[];
  glossary: { exists: boolean; path: string };
  state: { exists: boolean; phase?: string; phaseStatus?: string; lastCompleted?: string };
}

async function parseLooseYaml(text: string): Promise<Record<string, string>> {
  const out: Record<string, string> = {};
  for (const line of text.split(/\r?\n/)) {
    const m = line.match(/^([a-zA-Z0-9_]+)\s*:\s*(.+)$/);
    if (!m) continue;
    out[m[1]] = m[2].trim().replace(/^['"]/, '').replace(/['"]$/, '');
  }
  return out;
}

export async function loadDetail(slug: string): Promise<DetailView | null> {
  const ref = await findContent(slug);
  if (!ref) return null;
  const summary = await summarize(ref);

  // meta
  let meta: Record<string, string> = {};
  const metaPath = join(ref.dir, 'meta.yml');
  if (await fileExists(metaPath)) {
    try { meta = await parseLooseYaml(await readFile(metaPath, 'utf-8')); } catch { /* noop */ }
  }

  // chapters / episodes / audio
  const chapters = (await listFiles(join(ref.dir, 'chapters'), ref.dir))
    .filter((f) => !f.isDir && (f.ext === 'txt' || f.ext === 'md'));
  const episodes = (await listFiles(join(ref.dir, 'episodes'), ref.dir))
    .filter((f) => !f.isDir && f.ext === 'txt');
  const audio = (await listFiles(join(ref.dir, 'm4a'), ref.dir))
    .filter((f) => !f.isDir && ['m4a', 'mp3', 'wav'].includes(f.ext));

  // slide-decks: one subdir per chapter
  const slideRoot = join(ref.dir, '_system', 'slide-decks');
  const slideDecks: { slug: string; files: FileEntry[] }[] = [];
  if (await dirExists(slideRoot)) {
    for (const e of await listFiles(slideRoot, ref.dir)) {
      if (e.isDir) {
        const files = await listFiles(e.path, ref.dir);
        slideDecks.push({ slug: e.name, files });
      }
    }
  }

  // audits
  const audits = (await listFiles(join(ref.dir, 'audits'), ref.dir))
    .filter((f) => !f.isDir);

  // source files
  const sourceText = join(ref.dir, '_system', 'source', 'text');
  const sourceFiles = (await listFiles(sourceText, ref.dir))
    .filter((f) => !f.isDir && ['md', 'txt', 'json'].includes(f.ext));

  // glossary
  const glossaryPath = join(ref.dir, '_system', 'glossary.yml');
  const glossary = { exists: await fileExists(glossaryPath), path: glossaryPath };

  // state
  const statePath = join(ref.dir, '_system', 'orchestrator-state.json');
  const state: DetailView['state'] = { exists: await fileExists(statePath) };
  if (state.exists) {
    try {
      const j = JSON.parse(await readFile(statePath, 'utf-8'));
      state.phase = j.phase;
      state.phaseStatus = j.phase_status;
      state.lastCompleted = j.last_completed_phase;
    } catch { /* noop */ }
  }

  return { summary, meta, chapters, episodes, slideDecks, audio, audits, sourceFiles, glossary, state };
}

export async function listAllSummaries(): Promise<ContentSummary[]> {
  const refs = await listContent();
  const out: ContentSummary[] = [];
  for (const ref of refs) {
    out.push(await summarize(ref));
  }
  return out;
}

export function groupByCategory(summaries: ContentSummary[]): Map<Category, ContentSummary[]> {
  const m = new Map<Category, ContentSummary[]>();
  for (const cat of ACTIVE_CATEGORIES) m.set(cat, []);
  for (const s of summaries) {
    if (!m.has(s.category)) m.set(s.category, []);
    m.get(s.category)!.push(s);
  }
  return m;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

export function formatModified(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const day = 24 * 60 * 60 * 1000;
  if (diffMs < day) {
    return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  }
  if (diffMs < 7 * day) {
    return `${Math.floor(diffMs / day)} d ago`;
  }
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}
