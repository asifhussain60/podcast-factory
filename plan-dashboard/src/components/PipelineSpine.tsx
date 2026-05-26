import { useState, useMemo, useEffect, useRef } from 'react';
import AgentCard from './AgentCard';

interface Phase {
  id: string;
  name: string;
  kind: string;
  agent: string | null;
  plain: string;
  duration_minutes: number;
  modules: string[];
}

interface Module {
  id: string;
  name: string;
  plain: string;
}

interface Agent {
  id: string;
  name: string;
  role: string;
  icon: string;
  tone: string;
  plain: string;
  what_it_knows: string;
  boundary_in: string;
  boundary_out: string;
  does_not: string;
  cost_profile: string;
  failure_mode: string;
}

interface Props {
  phases: Phase[];
  modules: Module[];
  agents: Agent[];
}

const KIND_META: Record<string, { label: string; icon: string }> = {
  agentic:    { label: 'Agent',      icon: 'robot' },
  hybrid:     { label: 'Hybrid',     icon: 'shuffle' },
  mechanical: { label: 'Mechanical', icon: 'gear' },
};

const sectionId = (id: string) => `station-${id}`;

export default function PipelineSpine({ phases, modules, agents }: Props) {
  const [active, setActive] = useState<string>(phases[0]?.id ?? '');
  const sectionRefs = useRef<Record<string, HTMLElement | null>>({});

  const moduleMap = useMemo(() => {
    const m = new Map<string, Module>();
    modules.forEach((mod) => m.set(mod.id, mod));
    return m;
  }, [modules]);

  const agentMap = useMemo(() => {
    const m = new Map<string, Agent>();
    agents.forEach((a) => m.set(a.id, a));
    return m;
  }, [agents]);

  // Scrollspy — pick the topmost section whose top has crossed 30% of viewport.
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const onScroll = () => {
      const ids = phases.map((p) => p.id);
      const trigger = window.innerHeight * 0.30;
      let current = ids[0];
      for (const id of ids) {
        const el = sectionRefs.current[id];
        if (!el) continue;
        const top = el.getBoundingClientRect().top;
        if (top - trigger <= 0) current = id; else break;
      }
      setActive(current);
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, [phases]);

  const jumpTo = (id: string) => {
    const el = sectionRefs.current[id];
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <div className="pipeline-shell">
      {/* ── LEFT: sticky mini-rail ─────────────────────────────── */}
      <nav className="pipeline-rail" aria-label="Pipeline stations">
        <div className="pipeline-rail-sticky">
          <span className="eyebrow rail-eyebrow">The pipeline</span>
          <ol className="rail-list">
            {phases.map((p, i) => {
              const meta = KIND_META[p.kind] ?? KIND_META.mechanical;
              const isActive = p.id === active;
              return (
                <li key={p.id} className={`rail-item kind-${p.kind} ${isActive ? 'is-active' : ''}`}>
                  <button type="button" onClick={() => jumpTo(p.id)} className="rail-link">
                    <span className="rail-dot" aria-hidden="true">
                      <i className={`fa-solid fa-${meta.icon}`}></i>
                    </span>
                    <span className="rail-text">
                      <span className="rail-meta">Step {i + 1} · {p.duration_minutes} min</span>
                      <span className="rail-name">{p.name}</span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>
          <div className="rail-foot">
            <span className="rail-foot-line">Scroll the right column to walk through the pipeline. The active step lights up here.</span>
          </div>
        </div>
      </nav>

      {/* ── RIGHT: vertical stack of full station sections ──────── */}
      <main className="pipeline-stations">
        {phases.map((p, i) => {
          const meta = KIND_META[p.kind] ?? KIND_META.mechanical;
          const agent = p.agent ? agentMap.get(p.agent) : null;
          const phaseModules = p.modules.map((m) => moduleMap.get(m)).filter(Boolean) as Module[];
          const isActive = p.id === active;

          return (
            <section
              key={p.id}
              id={sectionId(p.id)}
              ref={(el) => { sectionRefs.current[p.id] = el; }}
              className={`station-section kind-tone-${p.kind} ${isActive ? 'is-active' : ''}`}
            >
              <header className="station-section-head">
                <div className="station-section-numwrap">
                  <span className="station-section-number">{i + 1}</span>
                </div>
                <div className="station-section-headtext">
                  <div className="row station-section-eyebrow-row">
                    <span className="eyebrow">Station {p.id} · {p.duration_minutes} minutes</span>
                    <span className={`kind-badge kind-${p.kind}`}>
                      <i className={`fa-solid fa-${meta.icon}`} aria-hidden="true"></i>
                      {meta.label}
                    </span>
                  </div>
                  <h2 className="station-section-title">{p.name}</h2>
                </div>
              </header>

              <p className="station-section-lede">{p.plain}</p>

              {phaseModules.length > 0 && (
                <div className="station-section-modules">
                  <span className="eyebrow section-sub-eyebrow">What plugs in here</span>
                  <div className="section-module-grid">
                    {phaseModules.map((m) => (
                      <div key={m.id} className="section-module">
                        <div className="section-module-head">
                          <i className="fa-solid fa-puzzle-piece" aria-hidden="true"></i>
                          <strong>{m.name}</strong>
                        </div>
                        <p className="small muted">{m.plain}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {agent && (
                <div className="station-section-agent">
                  <span className="eyebrow section-sub-eyebrow">Who does the work</span>
                  <AgentCard agent={agent} />
                </div>
              )}

              {!agent && p.kind === 'mechanical' && (
                <div className="focus-empty">
                  <i className="fa-solid fa-gear focus-empty-icon" aria-hidden="true"></i>
                  <div>
                    <strong>No agent here — this station is mechanical.</strong>
                    <p className="small muted">A deterministic script does this work the same way for every book. Nothing to reason about, nothing to drift.</p>
                  </div>
                </div>
              )}
            </section>
          );
        })}
      </main>
    </div>
  );
}
