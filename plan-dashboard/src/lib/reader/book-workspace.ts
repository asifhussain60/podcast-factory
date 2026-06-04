import { readFileSync, readdirSync } from 'node:fs';
import { renderMarkdown } from './markdown';
import { loadGlossary } from './glossary';
import { readReview } from './stage-review';
import { buildStageMetrics, writeMetricsLedger, type StageMetric } from './stage-metrics';

export interface ChapterDef {
  id: string;
  title: string;
}

export interface StageDef {
  id: string;
  label: string;
  slice: string;
}

export interface WorkspaceStage {
  id: string;
  label: string;
  slice: string;
  available: boolean;
  html: string;
}

export interface WorkspaceChapter {
  slug: string;
  title: string;
  stages: WorkspaceStage[];
  metrics: StageMetric[];
  reviewed: Record<string, { approved: boolean; approved_at?: string | null }>;
  finalized: { at: string } | null;
}

export interface BookWorkspace {
  slug: string;
  chapters: WorkspaceChapter[];
  cockpitChapters: ChapterDef[];
  glossary: Awaited<ReturnType<typeof loadGlossary>>;
  loadError: string;
}

export const AYYUHAL_WALAD_SLUG = 'ayyuhal-walad';

export const AYYUHAL_WALAD_CHAPTERS: ChapterDef[] = [
  { id: 'ch01-frame-and-the-problem-of-knowledge', title: 'The Frame and the Problem of Knowledge' },
  { id: 'ch02-the-disciplines-of-the-path', title: 'The Disciplines of the Path' },
  { id: 'ch03-the-guiding-shaykh-and-final-counsels', title: 'The Guiding Shaykh and Final Counsels' },
];

// Canonical pipeline stage order — MIRROR of Python `_stage_gate.STAGE_ORDER`
// (scripts/podcast/_stage_gate.py) with `literary` inserted before `narrator`.
// Keep both sides in sync in the same commit when the stage set changes.
export const STAGE_DEFS: StageDef[] = [
  { id: 'source', label: 'Source', slice: 'Slice 1 (intake)' },
  { id: 'core', label: 'Core', slice: 'Slice 1 (intake)' },
  { id: 'denoised', label: 'Denoised', slice: 'Slice 2 (noise-strip)' },
  { id: 'normalized', label: 'Normalized', slice: 'Normalize (house voice)' },
  { id: 'augmented', label: 'Augmented', slice: 'Slice 4 (knowledge)' },
  { id: 'literary', label: 'Literary', slice: 'Literary transformation' },
  { id: 'narrator', label: 'Narrator', slice: 'Lecture additions (Shaykh)' },
];

/**
 * A coherent set of stage artifacts under one stage-root directory. The live
 * book uses `_stages/`; archived runs (e.g. an earlier episode structure) keep
 * their complete stage set under `_archive/<name>/_stages/` with their own
 * chapter IDs. Lineages are kept distinct (their chapter boundaries differ) and
 * are surfaced VIEW-ONLY in the progression panel — never merged per-chapter.
 */
export interface Lineage {
  id: string;
  label: string;
  stageRoot: string;
  chapters: ChapterDef[];
}

/** Title-case a chapter directory id: "ch01-frame-and-first-counsel" → "Frame and First Counsel". */
function chapterIdToTitle(id: string): string {
  const minor = new Set(['and', 'the', 'of', 'a', 'an', 'to', 'in', 'for']);
  return id
    .replace(/^ch\d+[-_]?/i, '')
    .replace(/[-_]+/g, ' ')
    .trim()
    .split(' ')
    .map((w, i) => (i > 0 && minor.has(w.toLowerCase()) ? w.toLowerCase() : w.charAt(0).toUpperCase() + w.slice(1)))
    .join(' ');
}

function listSubdirs(dir: URL): string[] {
  try {
    return readdirSync(dir, { withFileTypes: true })
      .filter((d) => d.isDirectory())
      .map((d) => d.name)
      .sort();
  } catch {
    return [];
  }
}

/**
 * Discover archived stage lineages for a book by scanning
 * `content/drafts/books/<slug>/_archive/<name>/_stages/`. Each archive folder
 * that contains a populated `_stages/` becomes a view-only lineage whose
 * chapter list is read from the stage subdirectories. Returns [] when none.
 */
export function discoverArchivedLineages(slug: string): Lineage[] {
  const archiveBase = new URL(`../../../../content/drafts/books/${slug}/_archive/`, import.meta.url);
  const lineages: Lineage[] = [];
  for (const name of listSubdirs(archiveBase)) {
    const stagesUrl = new URL(`${name}/_stages/`, archiveBase);
    const chapterIds = listSubdirs(stagesUrl);
    if (chapterIds.length === 0) continue;
    lineages.push({
      id: `archive-${name}`,
      label: `Archived · ${name.replace(/[-_]+/g, ' ')}`,
      stageRoot: `_archive/${name}/_stages`,
      chapters: chapterIds.map((id) => ({ id, title: chapterIdToTitle(id) })),
    });
  }
  return lineages;
}

function readIfExists(url: URL): string | null {
  try {
    return readFileSync(url, 'utf8');
  } catch {
    return null;
  }
}

function loadStageText(base: URL, chapterId: string, stageId: string, stageRoot: string): string | null {
  if (stageId === 'narrator') {
    const clean = readIfExists(new URL(`${stageRoot}/${chapterId}/additions-narrator-clean.md`, base));
    if (clean) return clean;
    return readIfExists(new URL(`${stageRoot}/${chapterId}/additions-narrator.md`, base));
  }

  for (const ext of ['md', 'txt']) {
    const text = readIfExists(new URL(`${stageRoot}/${chapterId}/${stageId}.${ext}`, base));
    if (text) return text;
  }

  // The live `_stages/` root lets the plain chapter text stand in for "Augmented"
  // when no augmented artifact was written. Archive lineages are self-contained,
  // so the fallback only applies to the canonical `_stages` root.
  if (stageId === 'augmented' && stageRoot === '_stages') {
    return readIfExists(new URL(`chapters/${chapterId}.txt`, base));
  }

  return null;
}

export interface LoadWorkspaceOpts {
  /** Stage-root directory under the book dir. Default `_stages`; archives pass their own. */
  stageRoot?: string;
  /** Persist the per-chapter metrics ledger to disk. Default true; archives pass false
   *  so a view-only lineage never clobbers the live book's stage-metrics.json. */
  writeLedger?: boolean;
}

export async function loadBookWorkspace(
  slug: string,
  chapterDefs: ChapterDef[],
  stageDefs: StageDef[],
  opts: LoadWorkspaceOpts = {},
): Promise<BookWorkspace> {
  const { stageRoot = '_stages', writeLedger = true } = opts;
  const base = new URL(`../../../../content/drafts/books/${slug}/`, import.meta.url);

  const chapters = chapterDefs.map((chapterDef) => {
    const stageTexts = stageDefs.map((stageDef) => {
      const text = loadStageText(base, chapterDef.id, stageDef.id, stageRoot);
      return {
        ...stageDef,
        available: !!text,
        text: text ?? '',
      };
    });

    const metrics = buildStageMetrics(
      stageTexts.map((stage) => ({ id: stage.id, available: stage.available, text: stage.text })),
    );
    if (writeLedger) writeMetricsLedger(slug, chapterDef.id, metrics);

    const stages = stageTexts.map((stage) => ({
      id: stage.id,
      label: stage.label,
      slice: stage.slice,
      available: stage.available,
      html: stage.available ? renderMarkdown(stage.text) : '',
    }));

    const review = readReview(slug, chapterDef.id);
    return {
      slug: chapterDef.id,
      title: chapterDef.title,
      stages,
      metrics,
      reviewed: review.stages,
      finalized: review.finalized ?? null,
    };
  });

  return {
    slug,
    chapters,
    cockpitChapters: chapterDefs,
    glossary: await loadGlossary(slug),
    loadError: chapters.some((chapter) => chapter.stages.some((stage) => stage.available))
      ? ''
      : `No stage artifacts found for ${slug}.`,
  };
}