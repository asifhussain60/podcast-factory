/**
 * stage-review.ts — per-chapter, per-stage review state for the Studio write-back loop (WC8).
 *
 * The Studio editor is the pipeline's human-review cockpit: when a slice halts on a chapter,
 * the reviewer reads/marks/edits the stage artifact in the editor and APPROVES it. Approval
 * is recorded here, at content/drafts/books/<slug>/_system/review/<chapter>.json, and the
 * orchestrator reads it to decide whether to resume past that stage's halt.
 *
 * This is finer-grained than the book-level review-gate.json (the final pre-publish gate);
 * the two compose — every stage approved -> the book gate can be approved.
 */
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs';
import { join, dirname } from 'node:path';

const REPO_ROOT = join(new URL(import.meta.url).pathname, '../../../../../');

function reviewPath(slug: string, chapter: string): string {
  return join(REPO_ROOT, 'content', 'drafts', 'books', slug, '_system', 'review', `${chapter}.json`);
}

export interface StageReview {
  approved: boolean;
  approved_at: string | null;
  notes?: string;
}
export interface ChapterReview {
  slug: string;
  chapter: string;
  stages: Record<string, StageReview>;
}

export function readReview(slug: string, chapter: string): ChapterReview {
  const p = reviewPath(slug, chapter);
  if (!existsSync(p)) return { slug, chapter, stages: {} };
  try {
    const parsed = JSON.parse(readFileSync(p, 'utf8')) as ChapterReview;
    return { slug, chapter, stages: parsed.stages ?? {} };
  } catch {
    return { slug, chapter, stages: {} };
  }
}

export function setStageReview(
  slug: string,
  chapter: string,
  stage: string,
  approved: boolean,
  notes?: string,
): ChapterReview {
  const review = readReview(slug, chapter);
  const now = new Date().toISOString().replace(/\.\d+Z$/, 'Z');
  review.stages[stage] = {
    approved,
    approved_at: approved ? now : null,
    ...(notes !== undefined ? { notes } : {}),
  };
  const p = reviewPath(slug, chapter);
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, JSON.stringify(review, null, 2), 'utf8');
  return review;
}
