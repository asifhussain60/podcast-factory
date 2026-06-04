import { useState } from 'react';
import { stageRole } from '../../../lib/reader/stage-roles';
import type { EnrichmentSummary } from '../../../lib/reader/enrichment-ledger';
import StageBarChart, { type StageBar } from './StageBarChart';

interface DashStage {
  id: string;
  label: string;
  available: boolean;
}
interface DashMetric {
  id: string;
  available: boolean;
  words: number;
  deltaPct: number | null;
  comparedTo: string | null;
}

interface Props {
  chapterTitle: string;
  stages: DashStage[];
  metrics: DashMetric[];
  enrichment: EnrichmentSummary | null;
  glossaryCount: number;
}

/**
 * Collapsible "Transformation" band shown above the reading pane. Charts how the
 * text was reshaped through the pipeline — words at each captured stage, plus the
 * three headline numbers Asif tracks: % noise removed, data augmented, and wisdom
 * corpus integrated. Collapsed by default so the chapter text leads (coffee-test);
 * every number is read from real ledgers, and missing stages are shown as "not
 * captured" rather than faked.
 */
export default function TransformationDashboard({
  chapterTitle,
  stages,
  metrics,
  enrichment,
  glossaryCount,
}: Props) {
  const [open, setOpen] = useState(false);

  // Bar chart: only stages captured for this chapter, in pipeline order.
  const bars: StageBar[] = metrics
    .filter((m) => m.available && m.words > 0)
    .map((m) => ({
      label: stages.find((s) => s.id === m.id)?.label ?? m.id,
      value: m.words,
      kind: stageRole(m.id).kind,
    }));

  // % noise removed — denoised measured against core (a reduction).
  const denoised = metrics.find((m) => m.id === 'denoised' && m.comparedTo === 'core');
  const noisePct =
    denoised && denoised.available && denoised.deltaPct !== null && denoised.deltaPct < 0
      ? Math.abs(denoised.deltaPct)
      : null;

  // Data augmented — words gained during enrichment (book-level ledger).
  const wordsAdded = enrichment ? enrichment.wordsAfter - enrichment.wordsBefore : null;
  const growthPct =
    enrichment && enrichment.wordsBefore > 0
      ? Math.round(((enrichment.wordsAfter - enrichment.wordsBefore) / enrichment.wordsBefore) * 1000) / 10
      : null;

  // Collapsed-row teaser — whatever real signal we have.
  const teaserParts: string[] = [];
  if (growthPct !== null) teaserParts.push(`+${growthPct}% augmented`);
  if (enrichment && enrichment.atomsUsed > 0) teaserParts.push(`${enrichment.atomsUsed} wisdom atoms`);
  if (noisePct !== null) teaserParts.push(`${noisePct}% noise removed`);
  const teaser = teaserParts.length ? teaserParts.join(' · ') : 'See how the text was reshaped';

  return (
    <section className="txd" aria-label="Transformation dashboard">
      <button
        type="button"
        className={`txd-toggle${open ? ' is-open' : ''}`}
        aria-expanded={open}
        aria-controls="txd-panel"
        onClick={() => setOpen((v) => !v)}
      >
        <span className="txd-toggle-caret" aria-hidden="true">{open ? '▾' : '▸'}</span>
        <span className="txd-toggle-label">Transformation</span>
        <span className="txd-toggle-teaser">{teaser}</span>
      </button>

      {open && (
        <div className="txd-panel" id="txd-panel">
          <div className="txd-grid">
            <figure className="txd-chart diagram-container">
              {bars.length > 0 ? (
                <StageBarChart bars={bars} />
              ) : (
                <p className="txd-empty">No stage word-counts captured for this chapter yet.</p>
              )}
              <figcaption>
                Word count at each captured stage of “{chapterTitle}”, earliest to review.
              </figcaption>
            </figure>

            <div className="txd-chips">
              <div className="txd-chip">
                <span className="txd-chip-value">{noisePct !== null ? `${noisePct}%` : '—'}</span>
                <span className="txd-chip-label">Noise removed</span>
                <span className="txd-chip-sub">
                  {noisePct !== null ? 'denoised vs raw' : 'not captured this run'}
                </span>
              </div>
              <div className="txd-chip">
                <span className="txd-chip-value">
                  {wordsAdded !== null ? `${wordsAdded >= 0 ? '+' : ''}${wordsAdded.toLocaleString()}` : '—'}
                </span>
                <span className="txd-chip-label">Words augmented</span>
                <span className="txd-chip-sub">
                  {growthPct !== null ? `+${growthPct}% of source` : 'no enrichment ledger'}
                </span>
              </div>
              <div className="txd-chip">
                <span className="txd-chip-value">{enrichment ? enrichment.atomsUsed.toLocaleString() : '—'}</span>
                <span className="txd-chip-label">Wisdom integrated</span>
                <span className="txd-chip-sub">
                  {enrichment
                    ? `${enrichment.sectionsEnriched} sections · of ${enrichment.corpusSize.toLocaleString()} in corpus`
                    : 'no enrichment ledger'}
                </span>
              </div>
            </div>
          </div>

          <dl className="txd-legend">
            {stages.map((s) => {
              const role = stageRole(s.id);
              if (!role.role) return null;
              return (
                <div className="txd-legend-row" key={s.id}>
                  <dt className={`txd-legend-term${s.available ? '' : ' is-uncaptured'}`}>
                    <span className={`txd-legend-dot txd-legend-dot--${role.kind}`} aria-hidden="true" />
                    {s.label}
                  </dt>
                  <dd>{role.role} <span className="txd-legend-tool">· {role.tool}</span></dd>
                </div>
              );
            })}
          </dl>

          {glossaryCount > 0 && (
            <p className="txd-foot">
              {glossaryCount} Arabic term{glossaryCount === 1 ? '' : 's'} carried in the “Show Arabic” overlay.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
