/**
 * Discover content/drafts/<slug>/ — the pipeline workshop where books in
 * flight live (post-intake, pre-publish).
 *
 * For the reader's "Podcast Drafts" navigation path, we expose a flat list
 * of drafts with metadata extracted from `_system/source/text/`.
 */
import { readFile, stat } from 'node:fs/promises';
import { join } from 'node:path';
import { listContent, type Category, type Stage } from './content-paths';

export interface DraftRecord {
  slug: string;
  draftDir: string;
  category: Category;
  stage: Stage;
  displayTitle: string;
  hasRefinedEnglish: boolean;
  hasRawExtract: boolean;
  hasPhonetics: boolean;
}

async function fileExists(p: string): Promise<boolean> {
  try {
    const s = await stat(p);
    return s.isFile();
  } catch {
    return false;
  }
}

function slugToTitle(slug: string): string {
  return slug
    .split('-')
    .map((w) => {
      if (w.length === 0) return w;
      if (w === 'al' || w === 'the' || w === 'and' || w === 'of' || w === 'to') return w;
      return w[0].toUpperCase() + w.slice(1);
    })
    .join(' ')
    .replace(/(^|\s)(\w)/g, (_m, p1, p2) => p1 + p2.toUpperCase());
}

export async function discoverDrafts(): Promise<DraftRecord[]> {
  const refs = await listContent({ stage: 'drafts' });
  const out: DraftRecord[] = [];
  for (const ref of refs) {
    const textDir = join(ref.dir, '_system', 'source', 'text');
    const hasRefinedEnglish = await fileExists(join(textDir, 'refined-english.md'));
    const hasRawExtract = await fileExists(join(textDir, 'raw-extract.md'));
    const hasPhonetics = await fileExists(join(textDir, '_phonetics.md'));
    // Only surface drafts that have at least one text artifact
    if (!hasRefinedEnglish && !hasRawExtract) continue;
    out.push({
      slug: ref.slug,
      draftDir: ref.dir,
      category: ref.category,
      stage: ref.stage,
      displayTitle: slugToTitle(ref.slug),
      hasRefinedEnglish,
      hasRawExtract,
      hasPhonetics,
    });
  }
  return out;
}

export async function findDraft(slug: string): Promise<DraftRecord | null> {
  const drafts = await discoverDrafts();
  return drafts.find((d) => d.slug === slug) ?? null;
}

export async function loadDraftRefinedEnglish(draft: DraftRecord): Promise<string | null> {
  if (!draft.hasRefinedEnglish) return null;
  return readFile(
    join(draft.draftDir, '_system', 'source', 'text', 'refined-english.md'),
    'utf-8',
  );
}

export async function loadDraftRawExtract(draft: DraftRecord): Promise<string | null> {
  if (!draft.hasRawExtract) return null;
  return readFile(
    join(draft.draftDir, '_system', 'source', 'text', 'raw-extract.md'),
    'utf-8',
  );
}
