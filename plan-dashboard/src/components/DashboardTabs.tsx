import { useState } from 'react';
import SpendChart from './SpendChart';
import type { RoadmapStep, Wave, Debt, BookInFlight, BookShipped, RecentCommit } from '../lib/plan/types';
import { STATUS_PILL, STATUS_LABEL } from '../lib/plan/status-badges';

interface Props {
  roadmap: RoadmapStep[];
  waves: Wave[];
  debt: Debt[];
  booksInFlight: BookInFlight[];
  booksShipped: BookShipped[];
  recentCommits: RecentCommit[];
  burn30d: number[];
  phaseTime: Record<string, number>;
  convergeAvg: number;
  shipFirstTry: number;
}

export default function DashboardTabs(props: Props) {
  const [tab, setTab] = useState<'roadmap' | 'current' | 'metrics'>('roadmap');

  return (
    <div className="stack">
      <div className="tabbar" role="tablist">
        <button className={`tab ${tab === 'roadmap' ? 'is-active' : ''}`} onClick={() => setTab('roadmap')} role="tab">The roadmap</button>
        <button className={`tab ${tab === 'current' ? 'is-active' : ''}`} onClick={() => setTab('current')} role="tab">What's running right now</button>
        <button className={`tab ${tab === 'metrics' ? 'is-active' : ''}`} onClick={() => setTab('metrics')} role="tab">Health metrics</button>
      </div>

      {tab === 'roadmap' && <RoadmapTab waves={props.waves} roadmap={props.roadmap} />}
      {tab === 'current' && <CurrentTab booksInFlight={props.booksInFlight} booksShipped={props.booksShipped} recentCommits={props.recentCommits} debt={props.debt} />}
      {tab === 'metrics' && <MetricsTab burn30d={props.burn30d} phaseTime={props.phaseTime} convergeAvg={props.convergeAvg} shipFirstTry={props.shipFirstTry} />}
    </div>
  );
}

function RoadmapTab({ waves, roadmap }: { waves: Wave[]; roadmap: RoadmapStep[] }) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const byWave = (id: string) => roadmap.filter((s) => s.wave === id);
  const toggle = (id: string) => setExpanded((prev) => (prev === id ? null : id));
  const blocksOf = (id: string) => roadmap.filter((s) => s.depends_on.includes(id));

  return (
    <div className="stack">
      <p>
        The plan is broken into five waves. Each wave delivers something independently useful. Steps within a wave
        follow each other; later waves wait on the foundations laid by earlier ones.
      </p>
      {waves.map((w) => {
        const steps = byWave(w.id);
        const done = steps.filter((s) => s.status === 'complete').length;
        const flight = steps.filter((s) => s.status === 'in_progress').length;
        return (
          <div key={w.id} className="wave-band">
            <div className="row-between">
              <h3>Wave {w.id} — {w.name}</h3>
              <span className="small muted">{done} of {steps.length} done · {flight} in flight</span>
            </div>
            <p className="small muted">{w.plain}</p>
            <div className="stack-tight wave-steps">
              {steps.map((s) => {
                const needs = s.depends_on.map(dep => roadmap.find(r => r.id === dep)).filter(Boolean) as RoadmapStep[];
                const unlocks = blocksOf(s.id);
                const isExpanded = expanded === s.id;
                return (
                  <div key={s.id} className={`step-row ${isExpanded ? 'is-expanded' : ''}`}>

                    {/* Layer 2 — hover card (CSS-driven, 400ms delay) */}
                    {!isExpanded && (
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
                              {s.tools.map(t => <span key={t} className={`hover-chip tool-chip tool-${t.toLowerCase()}`}>{t}</span>)}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Layer 1 — always-visible header */}
                    <button
                      className="step-row-header"
                      aria-expanded={isExpanded}
                      onClick={() => toggle(s.id)}
                    >
                      <span className="step-id-cell">
                        <span className="step-id">Step {s.id}</span>
                        <span className={`tier-badge tier-${s.tier.toLowerCase()}`}>{s.tier}</span>
                      </span>
                      <span className="step-title">{s.title}</span>
                      <span className={`pill ${STATUS_PILL[s.status] ?? 'is-future'}`}>{STATUS_LABEL[s.status] ?? s.status}</span>
                      <span className="small muted step-touched">{s.last_touched ?? '—'}</span>
                      <span className="step-chevron" aria-hidden="true">{isExpanded ? '▲' : '▼'}</span>
                    </button>

                    {/* Layer 3 — click-expanded structured detail */}
                    {isExpanded && s.plain && (
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
                                {s.tools.map(t => <span key={t} className={`detail-chip tool-chip tool-${t.toLowerCase()}`}>{t}</span>)}
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

function CurrentTab({ booksInFlight, booksShipped, recentCommits, debt }: { booksInFlight: BookInFlight[]; booksShipped: BookShipped[]; recentCommits: RecentCommit[]; debt: Debt[]; }) {
  return (
    <div className="stack">
      <section className="stack">
        <h3>Books moving through the factory right now</h3>
        {booksInFlight.length === 0 && <p className="muted small">Nothing in flight at the moment.</p>}
        <div className="grid-2">
          {booksInFlight.map((b) => (
            <div key={b.slug} className="card stack-tight">
              <span className="eyebrow">{b.kind.replace(/-/g, ' ')}</span>
              <h3 className="card-title">{b.title}</h3>
              <p className="small muted">At station: {b.phase}</p>
              <div className="row-between">
                <span className="pill is-flight">{b.phase_status}</span>
                <span className="small muted">${b.cost_to_date_usd.toFixed(2)} so far</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="stack">
        <h3>Already in the catalog</h3>
        <table className="data">
          <thead><tr><th>Title</th><th>Shipped</th><th>Episodes</th><th>Cost</th></tr></thead>
          <tbody>
            {booksShipped.map((b) => (
              <tr key={b.slug}>
                <td>{b.title}</td>
                <td>{b.shipped}</td>
                <td>{b.episodes}</td>
                <td>${b.cost_total_usd.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="stack">
        <h3>Known issues we're working around</h3>
        {debt.map((d) => (
          <div key={d.id} className="card card-tight">
            <div className="row-between">
              <strong>{d.title}</strong>
              <span className={`pill ${d.severity === 'P0' ? 'is-blocked' : 'is-flight'}`}>{d.severity}</span>
            </div>
            <p className="small muted">{d.plain}</p>
          </div>
        ))}
      </section>

      <section className="stack">
        <h3>Recent changes</h3>
        <table className="data">
          <thead><tr><th>Date</th><th>What changed</th></tr></thead>
          <tbody>
            {recentCommits.map((c) => (<tr key={c.sha}><td>{c.date}</td><td>{c.subject}</td></tr>))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function MetricsTab({ burn30d, phaseTime, convergeAvg, shipFirstTry }: { burn30d: number[]; phaseTime: Record<string, number>; convergeAvg: number; shipFirstTry: number; }) {
  const total30 = burn30d.reduce((a, b) => a + b, 0);
  return (
    <div className="stack">
      <section className="stack spend-hero">
        <span className="eyebrow">Combined spend, last thirty days</span>
        <p className="small muted">Daily total across every outside service. Empty days are days nothing ran.</p>
        <SpendChart values={burn30d} />
        <p className="small muted">${total30.toFixed(2)} over the last 30 days · ${(total30 / 30).toFixed(2)} per day on average</p>
      </section>

      <section className="grid-2">
        <div className="card metric">
          <span className="metric-label">Quality review passes per book on average</span>
          <span className="metric-value">{convergeAvg.toFixed(1)}</span>
          <span className="card-sub">How many times the reviewer sends a book back before it converges.</span>
        </div>
        <div className="card metric">
          <span className="metric-label">Ship on the first try</span>
          <span className="metric-value">{shipFirstTry}%</span>
          <span className="card-sub">Share of books that make it through without a human override.</span>
        </div>
      </section>

      <section className="stack">
        <h3>How long each station takes on average</h3>
        <table className="data">
          <thead><tr><th>Station</th><th>Minutes</th></tr></thead>
          <tbody>
            {Object.entries(phaseTime).map(([name, min]) => (
              <tr key={name}><td>{name}</td><td>{min}</td></tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
