import { useState, useEffect } from 'react';

interface RoadmapStep {
  id: string; wave: string; title: string; status: string;
  depends_on: string[];
}
interface Wave { id: string; name: string; plain: string; }
interface Debt { id: string; severity: string; title: string; plain: string; }
interface BookFlight { slug: string; title: string; phase: string; phase_status: string; cost_to_date_usd: number; }

interface SnapData {
  roadmap: RoadmapStep[];
  waves: Wave[];
  books_in_flight: BookFlight[];
  debt: Debt[];
  metrics: { burn_30d_usd: number[] };
  source_commit: string;
}

interface Props extends SnapData {
  activePage: 'plan' | 'live';
}

export default function PlannerSidenav({ activePage, ...initialSnap }: Props) {
  const [snap, setSnap] = useState<SnapData>({ ...initialSnap });
  const [animated, setAnimated] = useState(false);

  // SSE hook — Base.astro dispatches 'podcastSnapshot' CustomEvent
  useEffect(() => {
    const handler = (e: Event) => {
      const data = (e as CustomEvent<SnapData>).detail;
      setSnap(data);
    };
    window.addEventListener('podcastSnapshot', handler);
    return () => window.removeEventListener('podcastSnapshot', handler);
  }, []);

  // Trigger bar animation on mount and on every new snapshot
  useEffect(() => {
    setAnimated(false);
    const id = requestAnimationFrame(() => setAnimated(true));
    return () => cancelAnimationFrame(id);
  }, [snap.source_commit]);

  const { roadmap, waves, books_in_flight, debt, metrics } = snap;

  // Factory status
  const isRunning = books_in_flight.length > 0;
  const isBlocked = !isRunning && debt.some(d => d.severity === 'P0');
  const statusClass = isRunning ? 's-running' : isBlocked ? 's-blocked' : 's-idle';
  const statusLabel = isRunning
    ? `Running · ${books_in_flight.length}`
    : isBlocked ? 'Blocked' : 'Idle';

  // Master progress
  const total = roadmap.length;
  const done = roadmap.filter(s => s.status === 'complete').length;
  const inProgress = roadmap.filter(s => s.status === 'in_progress').length;
  const ready = roadmap.filter(s => s.status === 'ready').length;
  const masterPct = total > 0 ? done / total : 0;

  // Wave breakdown
  const waveRows = waves.map((w, idx) => {
    const steps = roadmap.filter(s => s.wave === w.id);
    const wDone = steps.filter(s => s.status === 'complete').length;
    const allComplete = steps.length > 0 && wDone === steps.length;
    const allPending = steps.every(s => s.status === 'pending');
    const wStatus = allComplete ? 'complete' : allPending ? 'future' : 'active';
    const pct = steps.length > 0 ? wDone / steps.length : 0;
    return { ...w, steps, wDone, wStatus, pct, idx };
  });

  // What's next — first 'ready' step in wave order, else first in_progress
  let nextStep: RoadmapStep | null = null;
  for (const w of waveRows) {
    const r = w.steps.find(s => s.status === 'ready');
    if (r) { nextStep = r; break; }
  }
  if (!nextStep) {
    for (const w of waveRows) {
      const ip = w.steps.find(s => s.status === 'in_progress');
      if (ip) { nextStep = ip; break; }
    }
  }

  // Debt counts
  const p0 = debt.filter(d => d.severity === 'P0').length;
  const p1 = debt.filter(d => d.severity === 'P1').length;

  // 30d spend total
  const spend30 = metrics.burn_30d_usd.reduce((a, b) => a + b, 0);

  return (
    <nav className="planner-sidebar" aria-label="Planner overview">

      {/* 1 — Factory status */}
      <div className="planner-sb-section">
        <span className="planner-sb-label">Factory</span>
        <div className={`planner-status-badge ${statusClass}`}>
          <span className="planner-status-dot" aria-hidden="true" />
          {statusLabel}
        </div>
        <p className="planner-sub-line">
          {books_in_flight.length} in flight · {done} steps done
        </p>
      </div>

      {/* 2 — Master progress */}
      <div className="planner-sb-section">
        <span className="planner-sb-label">Overall Progress</span>
        <div className="planner-prog-fraction">
          {done}{' '}
          <span className="planner-prog-denom">/ {total}</span>
        </div>
        <div className="planner-prog-bar-wrap">
          <div
            className="planner-prog-bar-fill"
            data-animated={animated ? 'true' : 'false'}
            style={{ '--fill-pct': masterPct } as React.CSSProperties}
            role="progressbar"
            aria-valuenow={done}
            aria-valuemin={0}
            aria-valuemax={total}
          />
        </div>
        <p className="planner-prog-sub">
          {done} done · {inProgress} active · {ready} ready · {total - done - inProgress - ready} up next
        </p>
      </div>

      {/* 3 — Wave breakdown */}
      <div className="planner-sb-section">
        <span className="planner-sb-label">Waves</span>
        <div className="stack-tight">
          {waveRows.map((w) => (
            <a
              key={w.id}
              href={`/plan#wave-${w.id}`}
              className={[
                'planner-wave-row',
                w.wStatus === 'complete' ? 'is-complete' : '',
                w.wStatus === 'active'   ? 'is-active'   : '',
                w.wStatus === 'future'   ? 'is-future'   : '',
              ].filter(Boolean).join(' ')}
            >
              <div className="planner-wave-row-top">
                <span className={`planner-wave-badge s-${w.wStatus}`}>{w.id}</span>
                <span className="planner-wave-name">{w.name}</span>
                <span className="planner-wave-count">{w.wDone}/{w.steps.length}</span>
              </div>
              <div className="planner-wave-bar-wrap">
                <div
                  className={[
                    'planner-wave-bar-fill',
                    w.wStatus === 'complete' ? 's-complete' : '',
                    w.wStatus === 'future'   ? 's-future'   : '',
                  ].filter(Boolean).join(' ')}
                  data-animated={animated ? 'true' : 'false'}
                  style={{
                    '--fill-pct': Math.max(w.pct, 0.02),
                    transitionDelay: `${w.idx * 80}ms`,
                  } as React.CSSProperties}
                />
              </div>
            </a>
          ))}
        </div>
      </div>

      {/* 4 — What's next */}
      {nextStep && (
        <div className="planner-sb-section">
          <span className="planner-sb-label">Next Up</span>
          <div className="planner-next-card">
            <div className="planner-next-id">{nextStep.id}</div>
            <p className="planner-next-title">{nextStep.title}</p>
          </div>
        </div>
      )}

      {/* 5 — Debt pulse (only when there are issues) */}
      {(p0 > 0 || p1 > 0) && (
        <div className="planner-sb-section">
          <a href="/live" className={`planner-debt-line${p0 > 0 ? ' has-p0' : ''}`}>
            <i className="fa-solid fa-triangle-exclamation" aria-hidden="true" />
            {p0 + p1} issue{p0 + p1 !== 1 ? 's' : ''}
            {p0 > 0 && <span className="planner-debt-count">P0: {p0}</span>}
            {p1 > 0 && <span className="planner-debt-count">P1: {p1}</span>}
          </a>
        </div>
      )}

      {/* 6 — Nav links */}
      <div className="planner-nav-links">
        <a href="/plan" className={`sidenav-link${activePage === 'plan' ? ' is-active' : ''}`}>
          <i className="fa-solid fa-map fa-fw planner-nav-icon" aria-hidden="true" />
          Plan Design
        </a>
        <a href="/live" className={`sidenav-link${activePage === 'live' ? ' is-active' : ''}`}>
          <i className="fa-solid fa-bolt fa-fw planner-nav-icon" aria-hidden="true" />
          Live Execution
        </a>
      </div>

      {/* Footer */}
      <div className="planner-sb-footer">
        ${spend30.toFixed(0)} / 30d
      </div>
    </nav>
  );
}
