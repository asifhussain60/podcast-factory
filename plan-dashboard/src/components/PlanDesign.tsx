import { useState, useEffect } from 'react';

interface RoadmapStep {
  id: string; wave: string; title: string; status: string; tier: string;
  depends_on: string[]; last_touched?: string; plain?: string; tools?: string[];
}
interface Wave { id: string; name: string; plain: string; }

interface Props {
  roadmap: RoadmapStep[];
  waves: Wave[];
}

const STATUS_BADGE: Record<string, string> = {
  complete:    'is-ok',
  in_progress: 'is-flight',
  ready:       'is-ready',
  blocked:     'is-blocked',
  pending:     'is-future',
};

const STATUS_LABEL: Record<string, string> = {
  complete:    'Done',
  in_progress: 'In progress',
  ready:       'Ready',
  blocked:     'Blocked',
  pending:     'Up next',
};

export default function PlanDesign({ roadmap, waves }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [animated, setAnimated] = useState(false);

  useEffect(() => {
    const id = requestAnimationFrame(() => setAnimated(true));
    return () => cancelAnimationFrame(id);
  }, []);

  const byWave = (id: string) => roadmap.filter(s => s.wave === id);
  const toggle = (id: string) => setExpanded(prev => prev === id ? null : id);
  const blocksOf = (id: string) => roadmap.filter(s => s.depends_on.includes(id));

  return (
    <div className="stack">
      {waves.map((w) => {
        const steps = byWave(w.id);
        const done   = steps.filter(s => s.status === 'complete').length;
        const flight = steps.filter(s => s.status === 'in_progress').length;
        const pct    = steps.length > 0 ? done / steps.length : 0;
        const allComplete = done === steps.length;

        return (
          <div key={w.id} className="wave-band" id={`wave-${w.id}`}>
            <div className="row-between">
              <h3>Wave {w.id} — {w.name}</h3>
              <span className="small muted">{done} of {steps.length} done · {flight} in flight</span>
            </div>
            <p className="small muted">{w.plain}</p>

            {/* Wave progress bar */}
            <div className="wave-prog-wrap" style={{ marginBottom: 'var(--sp-3)' }}>
              <div
                className={`wave-prog-fill${allComplete ? ' s-complete' : ''}`}
                data-animated={animated ? 'true' : 'false'}
                style={{ '--fill-pct': Math.max(pct, 0.02) } as React.CSSProperties}
              />
            </div>

            <div className="stack-tight wave-steps">
              {steps.map((s) => {
                const needs   = s.depends_on.map(dep => roadmap.find(r => r.id === dep)).filter(Boolean) as RoadmapStep[];
                const unlocks = blocksOf(s.id);
                const isExp   = expanded === s.id;

                return (
                  <div key={s.id} className={`step-row${isExp ? ' is-expanded' : ''}`}>

                    {/* Hover card (CSS 400ms delay) */}
                    {!isExp && (needs.length > 0 || unlocks.length > 0 || (s.tools && s.tools.length > 0)) && (
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
                      className="step-row-header"
                      aria-expanded={isExp}
                      onClick={() => toggle(s.id)}
                    >
                      <span className="step-id-cell">
                        <span className="step-id">Step {s.id}</span>
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
                    {isExp && s.plain && (
                      <div className="step-detail">
                        <p className="step-detail-what">{s.plain}</p>
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
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
