/**
 * stage-metrics.ts — per-stage transformation metrics for the Studio stage tabs (WC8).
 *
 * Each pipeline stage (Source -> Denoised -> Core -> Normalized -> Augmented) is measured and
 * compared to the previous AVAILABLE stage, so the editor can show what each step did:
 *   - Denoised vs Source  => "% noise removed"      (the number Asif asked to track)
 *   - Core vs Denoised     => dedup / intersection reduction
 *   - Normalized vs Core   => re-voicing (length-neutral-ish)
 *   - Augmented vs Normalized => enrichment growth (positive delta)
 *
 * Metrics are also persisted to content/drafts/books/<slug>/_system/stage-metrics.json as a
 * durable ledger the pipeline + dashboards can read.
 */
import { writeFileSync, mkdirSync } from 'node:fs';
import { join, dirname } from 'node:path';

const REPO_ROOT = join(new URL(import.meta.url).pathname, '../../../../../');

export interface StageCounts {
  words: number;
  chars: number;
  sentences: number;
}
export interface StageMetric extends StageCounts {
  id: string;
  available: boolean;
  /** % change in words vs the previous available stage (negative = reduction). null if no prior. */
  deltaPct: number | null;
  /** id of the stage this was compared against. */
  comparedTo: string | null;
}

/** Strip light markdown/html so counts reflect prose, not syntax. */
function toPlain(text: string): string {
  return text
    .replace(/<[^>]+>/g, ' ')
    .replace(/[#*_>`~]+/g, ' ')
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/\s+/g, ' ')
    .trim();
}

export function countText(text: string): StageCounts {
  const plain = toPlain(text);
  const words = plain ? plain.split(/\s+/).length : 0;
  const sentences = (plain.match(/[.!?؟](\s|$)/g) || []).length;
  return { words, chars: plain.length, sentences };
}

/** Build metrics for an ordered stage list; each available stage is compared to the prior one. */
export function buildStageMetrics(
  stages: { id: string; available: boolean; text: string }[],
): StageMetric[] {
  let prior: { id: string; counts: StageCounts } | null = null;
  return stages.map((s) => {
    if (!s.available) {
      return { id: s.id, available: false, words: 0, chars: 0, sentences: 0, deltaPct: null, comparedTo: null };
    }
    const counts = countText(s.text);
    const deltaPct = prior && prior.counts.words > 0
      ? Math.round(((counts.words - prior.counts.words) / prior.counts.words) * 1000) / 10
      : null;
    const comparedTo = prior ? prior.id : null;
    prior = { id: s.id, counts };
    return { id: s.id, available: true, ...counts, deltaPct, comparedTo };
  });
}

export function writeMetricsLedger(slug: string, chapter: string, metrics: StageMetric[]): void {
  const p = join(REPO_ROOT, 'content', 'drafts', 'books', slug, '_system', 'stage-metrics.json');
  const payload = {
    slug,
    chapter,
    measured_at: new Date().toISOString().replace(/\.\d+Z$/, 'Z'),
    stages: metrics,
    // Convenience: the headline "% noise removed" (Denoised vs Source), when both exist.
    noise_removed_pct: metrics.find((m) => m.id === 'denoised' && m.comparedTo === 'source')?.deltaPct ?? null,
  };
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, JSON.stringify(payload, null, 2), 'utf8');
}
