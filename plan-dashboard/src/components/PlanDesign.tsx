import { useState, useEffect } from 'react';
import { planVisualManifest } from '../lib/plan/visualManifest';
import StepDiagram from './StepDiagram';

interface RoadmapStep {
  id: string; wave: string; title: string; status: string; tier: string;
  depends_on: string[]; last_touched?: string; plain?: string; tools?: string[];
}
interface Wave { id: string; name: string; plain: string; }
interface WaveEvent {
  ts: string;
  wave: number;
  wave_letter?: string;
  event_type: string;
  status: string;
  message: string;
}

interface Props {
  roadmap: RoadmapStep[];
  waves: Wave[];
  waveEvents?: WaveEvent[];
}

const STATUS_BADGE: Record<string, string> = {
  complete:    'is-ok',
  in_progress: 'is-flight',
  ready:       'is-ready',
  blocked:     'is-blocked',
  failed:      'is-blocked',
  pending:     'is-future',
};

const STATUS_LABEL: Record<string, string> = {
  complete:    'Done',
  in_progress: 'In progress',
  ready:       'Ready',
  blocked:     'Blocked',
  failed:      'Failed',
  pending:     'Up next',
};

const STATUS_HEADER: Record<string, string> = {
  complete:    'is-complete',
  in_progress: 'is-processing',
  blocked:     'is-failed',
  failed:      'is-failed',
};

const STATUS_DOT: Record<string, string> = {
  complete:    'is-ok',
  in_progress: 'is-flight',
  blocked:     'is-fail',
  failed:      'is-fail',
  ready:       'is-ready',
  pending:     'is-idle',
};

export default function PlanDesign({ roadmap, waves, waveEvents = [] }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [animated, setAnimated] = useState(false);

  useEffect(() => {
    const id = requestAnimationFrame(() => setAnimated(true));
    return () => cancelAnimationFrame(id);
  }, []);

  const byWave = (id: string) => roadmap.filter(s => s.wave === id);
  const toggle = (id: string) => setExpanded(prev => prev === id ? null : id);
  const blocksOf = (id: string) => roadmap.filter(s => s.depends_on.includes(id));
  const showHoverCards = expanded === null;

  const isMobilizationStep = (id: string) => /^[A-Z]0$/.test(id);

  const renderStep = (s: RoadmapStep) => {
    const needs   = s.depends_on.map(dep => roadmap.find(r => r.id === dep)).filter(Boolean) as RoadmapStep[];
    const unlocks = blocksOf(s.id);
    const isExp   = expanded === s.id;
    const headerState = STATUS_HEADER[s.status] ?? '';

    return (
      <div key={s.id} className={`step-row${isExp ? ' is-expanded' : ''}`}>

        {/* Hover card (CSS 400ms delay) */}
        {showHoverCards && !isExp && (needs.length > 0 || unlocks.length > 0 || (s.tools && s.tools.length > 0)) && (
          <div className="step-hover-card" role="tooltip" aria-hidden="true">
            {needs.length > 0 && (
              <div className="hover-section">
                <span className="hover-label">Needs</span>
                <div className="hover-chips">
                  {needs.map(dep => <span key={dep.id} className="hover-chip">{dep.title}</span>)}
                </div>
              </div>
            )}
            {unlocks.length > 0 && (
              <div className="hover-section">
                <span className="hover-label">Unlocks</span>
                <div className="hover-chips">
                  {unlocks.map(u => <span key={u.id} className="hover-chip">{u.title}</span>)}
                </div>
              </div>
            )}
            {s.tools && s.tools.length > 0 && (
              <div className="hover-section">
                <span className="hover-label">Built with</span>
                <div className="hover-chips">
                  {s.tools.map(t => (
                    <span key={t} className={`hover-chip tool-chip tool-${t.toLowerCase()}`}>{t}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Row header */}
        <button
          className={`step-row-header${headerState ? ` ${headerState}` : ''}`}
          aria-expanded={isExp}
          onClick={() => toggle(s.id)}
        >
          <span className="step-id-cell">
            <span className="step-id-with-dot">
              <span
                className={`step-status-dot ${STATUS_DOT[s.status] ?? 'is-idle'}`}
                aria-hidden="true"
              />
              <span className="step-id">Step {s.id}</span>
            </span>
            <span className={`tier-badge tier-${s.tier?.toLowerCase() ?? 't1'}`}>{s.tier}</span>
          </span>
          <span className="step-title">{s.title}</span>
          <span className={`step-badge ${STATUS_BADGE[s.status] ?? 'is-future'}`}>
            {STATUS_LABEL[s.status] ?? s.status}
          </span>
          <span className="small muted step-touched">{s.last_touched ?? '—'}</span>
          <span className="step-chevron" aria-hidden="true">{isExp ? '▲' : '▼'}</span>
        </button>

        {/* Expand panel */}
        {isExp && (
          <div className="step-detail">
            <p className="step-detail-what">{s.plain ?? 'No narrative text yet.'}</p>

            <StepDiagram stepId={s.id} />

            <div className="step-detail-meta">
              {needs.length > 0 && (
                <div className="detail-row">
                  <span className="detail-label">Needs</span>
                  <div className="detail-chips">
                    {needs.map(dep => <span key={dep.id} className="detail-chip">{dep.title}</span>)}
                  </div>
                </div>
              )}
              {unlocks.length > 0 && (
                <div className="detail-row">
                  <span className="detail-label">Unlocks</span>
                  <div className="detail-chips">
                    {unlocks.map(u => <span key={u.id} className="detail-chip">{u.title}</span>)}
                  </div>
                </div>
              )}
              {s.tools && s.tools.length > 0 && (
                <div className="detail-row">
                  <span className="detail-label">Built with</span>
                  <div className="detail-chips">
                    {s.tools.map(t => (
                      <span key={t} className={`detail-chip tool-chip tool-${t.toLowerCase()}`}>{t}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="stack">
      {waveEvents.length > 0 && (
        <div className="wave-events-card">
          <div className="row-between">
            <h3>Autonomous Wave Execution</h3>
            <span className="small muted">Live governance log</span>
          </div>
          <div className="wave-events-list">
            {waveEvents.map((evt, idx) => (
              <div key={`${evt.ts}-${idx}`} className="wave-event-row">
                <span className={`wave-event-pill s-${evt.status}`}>{evt.status}</span>
                <span className="wave-event-time">{evt.ts.replace('T', ' ').replace('Z', ' UTC')}</span>
                <span className="wave-event-wave">Wave {evt.wave_letter ?? evt.wave}</span>
                <span className="wave-event-msg">{evt.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {waves.flatMap((w) => {
        const steps = byWave(w.id);
        const mobilizationSteps = steps.filter(s => isMobilizationStep(s.id));
        const waveSteps = steps.filter(s => !isMobilizationStep(s.id));
        const done   = waveSteps.filter(s => s.status === 'complete').length;
        const flight = waveSteps.filter(s => s.status === 'in_progress').length;
        const pct    = waveSteps.length > 0 ? done / waveSteps.length : 0;
        const allComplete = waveSteps.length > 0 && done === waveSteps.length;
        const isExpanded = !allComplete;

        const items: React.ReactNode[] = [];

        // Render mobilization steps as a top-level section BEFORE the wave,
        // so they appear as a peer (not buried inside the wave band).
        if (mobilizationSteps.length > 0) {
          items.push(
            <div key={`prewave-${w.id}`} className="prewave-band" id={`prewave-${w.id}`}>
              <div className="row-between">
                <h3>{planVisualManifest.preWaveTerm} · Before Wave {w.id}</h3>
                <span className="small muted">
                  {mobilizationSteps.filter(s => s.status === 'complete').length} of {mobilizationSteps.length} done
                </span>
              </div>
              <p className="small muted">Pre-wave setup that must be in place before core wave execution starts.</p>
              <div className="stack-tight wave-steps">
                {mobilizationSteps.map(renderStep)}
              </div>
            </div>
          );
        }

        items.push(
          <div key={w.id} className={`wave-band${allComplete ? ' is-collapsed' : ''}`} id={`wave-${w.id}`}>
            <div className="row-between wave-band-header">
              <h3>
                Wave {w.id} — {w.name}
                {allComplete && <span className="wave-done-stamp" aria-label="wave complete">DONE</span>}
              </h3>
              <span className="small muted">{done} of {waveSteps.length} done · {flight} in flight</span>
            </div>

            {isExpanded && (
              <>
                <p className="small muted">{w.plain}</p>
                <p className="small muted">Wave-end cleanup and direct merge to develop are mandatory closeout gates.</p>

                {/* Wave progress bar */}
                <div className="wave-prog-wrap">
                  <div
                    className={`wave-prog-fill${allComplete ? ' s-complete' : ''}`}
                    data-animated={animated ? 'true' : 'false'}
                    style={{ '--fill-pct': Math.max(pct, 0.02) } as React.CSSProperties}
                  />
                </div>

                <div className="stack-tight wave-steps">
                  {waveSteps.map(renderStep)}
                </div>
              </>
            )}
          </div>
        );

        return items;
      })}
    </div>
  );
}
