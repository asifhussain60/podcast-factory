import { useState, useMemo } from 'react';
import AgentCard from './AgentCard';
import AgentHoverBadge from './AgentHoverBadge';

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

export default function PipelineSpine({ phases, modules, agents }: Props) {
  const [active, setActive] = useState<string>(phases[0]?.id ?? '');

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

  const activePhase = phases.find((p) => p.id === active) ?? phases[0];
  const activeModules = (activePhase?.modules ?? []).map((id) => moduleMap.get(id)).filter(Boolean) as Module[];
  const activeAgent = activePhase?.agent ? agentMap.get(activePhase.agent) : null;

  return (
    <div className="stack">
      <div className="spine-legend">
        <span className="kind-badge kind-agentic"><i className="fa-solid fa-robot" aria-hidden="true"></i> Agent-driven</span>
        <span className="kind-badge kind-hybrid"><i className="fa-solid fa-shuffle" aria-hidden="true"></i> Hybrid — agent + vendor service</span>
        <span className="kind-badge kind-mechanical"><i className="fa-solid fa-gear" aria-hidden="true"></i> Mechanical script</span>
      </div>

      <div className="spine-layout">
        <div className="spine-grid">
          <div className="spine-line" aria-hidden="true"></div>

          {phases.map((p, i) => {
            const isActive = p.id === active;
            const leftSide = i % 2 === 0;
            const kindMeta = KIND_META[p.kind] ?? KIND_META.mechanical;
            const agent = p.agent ? agentMap.get(p.agent) : null;
            const phaseModules = p.modules.map((m) => moduleMap.get(m)).filter(Boolean) as Module[];

            return (
              <div
                key={p.id}
                className={`spine-row ${leftSide ? 'is-left' : 'is-right'} ${isActive ? 'is-active' : ''}`}
              >
                <div className="spine-row-card-wrap">
                  <button
                    type="button"
                    className={`station-card kind-${p.kind} ${isActive ? 'is-active' : ''}`}
                    onClick={() => setActive(p.id)}
                    aria-pressed={isActive}
                  >
                    <header className="station-card-head">
                      <span className={`kind-badge kind-${p.kind}`}>
                        <i className={`fa-solid fa-${kindMeta.icon}`} aria-hidden="true"></i>
                        {kindMeta.label}
                      </span>
                      <span className="station-meta">{p.id} · {p.duration_minutes} min</span>
                    </header>

                    <h4 className="station-name">{p.name}</h4>

                    {phaseModules.length > 0 && (
                      <div className="station-chips">
                        {phaseModules.map((m) => (
                          <span key={m.id} className="chip" title={m.plain}>
                            <i className="fa-solid fa-puzzle-piece" aria-hidden="true"></i>
                            {m.name}
                          </span>
                        ))}
                      </div>
                    )}
                  </button>

                  {agent && (
                    <div className="station-agent-line">
                      <AgentHoverBadge agent={agent} />
                    </div>
                  )}
                </div>

                <div className="spine-marker-cell">
                  <div className={`spine-marker ${isActive ? 'is-active' : ''}`}>
                    <span>{i + 1}</span>
                  </div>
                </div>

                <div className="spine-row-card-wrap"></div>
              </div>
            );
          })}

          <div className="spine-cap top"><span className="eyebrow">A book enters</span></div>
          <div className="spine-cap bottom"><span className="eyebrow">A podcast leaves</span></div>
        </div>

        <aside className="focus-pane">
          <div className={`focus-card kind-tone-${activePhase?.kind}`}>
            <div className="focus-card-head">
              <span className="focus-card-eyebrow">
                Station {activePhase?.id} · {activePhase?.duration_minutes} minutes
              </span>
              <span className={`kind-badge kind-${activePhase?.kind} is-lg`}>
                <i className={`fa-solid fa-${(KIND_META[activePhase?.kind ?? 'mechanical']).icon}`} aria-hidden="true"></i>
                {(KIND_META[activePhase?.kind ?? 'mechanical']).label}
              </span>
            </div>
            <h3 className="focus-card-title">{activePhase?.name}</h3>
            <p className="focus-card-lede">{activePhase?.plain}</p>

            {activeModules.length > 0 && (
              <div className="focus-modules">
                <span className="eyebrow">Modules at this station</span>
                <div className="focus-module-grid">
                  {activeModules.map((m) => (
                    <div key={m.id} className="focus-module">
                      <div className="focus-module-head">
                        <i className="fa-solid fa-puzzle-piece" aria-hidden="true"></i>
                        <strong>{m.name}</strong>
                      </div>
                      <p className="small muted">{m.plain}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {activeAgent && <AgentCard agent={activeAgent} />}

          {!activeAgent && activePhase?.kind === 'mechanical' && (
            <div className="focus-empty">
              <i className="fa-solid fa-gear focus-empty-icon" aria-hidden="true"></i>
              <div>
                <strong>No agent here.</strong>
                <p className="small muted">A deterministic script does this work the same way for every book.</p>
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
