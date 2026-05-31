import { readFileSync } from 'node:fs';
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
  { id: 'ch01-frame-and-first-counsel', title: 'The Frame and the First Counsel' },
  { id: 'ch02-hatim-eight-benefits', title: "Hatim's Eight Benefits" },
  { id: 'ch03-the-path', title: 'The Path' },
  { id: 'ch04-four-cautions', title: 'The Four Cautions' },
  { id: 'ch05-method-and-closing-prayer', title: 'Method & Closing Prayer' },
];

export const AYYUHAL_WALAD_STAGE_DEFS: StageDef[] = [
  { id: 'source', label: 'Source', slice: 'Slice 1 (intake)' },
  { id: 'core', label: 'Core', slice: 'Slice 1 (intake)' },
  { id: 'denoised', label: 'Denoised', slice: 'Slice 2 (noise-strip)' },
  { id: 'normalized', label: 'Normalized', slice: 'Normalize (house voice)' },
  { id: 'augmented', label: 'Augmented', slice: 'Slice 4 (knowledge)' },
  { id: 'narrator', label: 'Narrator', slice: 'Lecture additions (Shaykh)' },
];

function readIfExists(url: URL): string | null {
  try {
    return readFileSync(url, 'utf8');
  } catch {
    return null;
  }
}

function loadStageText(base: URL, chapterId: string, stageId: string): string | null {
  if (stageId === 'narrator') {
    const clean = readIfExists(new URL(`_stages/${chapterId}/additions-narrator-clean.md`, base));
    if (clean) return clean;
    return readIfExists(new URL(`_stages/${chapterId}/additions-narrator.md`, base));
  }

  for (const ext of ['md', 'txt']) {
    const text = readIfExists(new URL(`_stages/${chapterId}/${stageId}.${ext}`, base));
    if (text) return text;
  }

  if (stageId === 'augmented') {
    return readIfExists(new URL(`chapters/${chapterId}.txt`, base));
  }

  return null;
}

export async function loadBookWorkspace(
  slug: string,
  chapterDefs: ChapterDef[],
  stageDefs: StageDef[],
): Promise<BookWorkspace> {
  const base = new URL(`../../../../content/drafts/books/${slug}/`, import.meta.url);

  const chapters = chapterDefs.map((chapterDef) => {
    const stageTexts = stageDefs.map((stageDef) => {
      const text = loadStageText(base, chapterDef.id, stageDef.id);
      return {
        ...stageDef,
        available: !!text,
        text: text ?? '',
      };
    });

    const metrics = buildStageMetrics(
      stageTexts.map((stage) => ({ id: stage.id, available: stage.available, text: stage.text })),
    );
    writeMetricsLedger(slug, chapterDef.id, metrics);

    const stages = stageTexts.map((stage) => ({
      id: stage.id,
      label: stage.label,
      slice: stage.slice,
      available: stage.available,
      html: stage.available ? renderMarkdown(stage.text) : '',
    }));

    return {
      slug: chapterDef.id,
      title: chapterDef.title,
      stages,
      metrics,
      reviewed: readReview(slug, chapterDef.id).stages,
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