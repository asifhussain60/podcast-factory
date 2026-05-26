import { useState, useMemo } from 'react';
import AgentCard from './AgentCard';

type Kind = 'agentic' | 'mechanical' | 'hybrid';

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

const ROW_H = 130;
const SPINE_X = 380;
const STATION_R = 18;
const VIEW_W = 760;
const CARD_W = 280;
const CARD_H = 92;

const KIND_LABEL: Record<string, string> = {
  agentic: 'Agent',
  mechanical: 'Mechanical',
  hybrid: 'Hybrid',
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

  const viewH = phases.length * ROW_H + 80;
  const activePhase = phases.find((p) => p.id === active) ?? phases[0];
  const activeModules = (activePhase?.modules ?? []).map((id) => moduleMap.get(id)).filter(Boolean) as Module[];
  const activeAgent = activePhase?.agent ? agentMap.get(activePhase.agent) : null;

  return (
    <div className="stack">
      <div className="spine-legend">
        <span className="kind-badge kind-agentic"><i className="fa-solid fa-robot" aria-hidden="true"></i> Agent-driven</span>
        <span className="kind-badge kind-hybrid"><i className="fa-solid fa-shuffle" aria-hidden="true"></i> Hybrid — agent plus a vendor service</span>
        <span className="kind-badge kind-mechanical"><i className="fa-solid fa-gear" aria-hidden="true"></i> Mechanical script</span>
      </div>

      <div className="spine-layout">
        <svg className="svg-host" viewBox={`0 0 ${VIEW_W} ${viewH}`} role="img" aria-label="Pipeline stations from top to bottom">
          <line className="spine" x1={SPINE_X} y1={40} x2={SPINE_X} y2={viewH - 40} />

          {phases.map((p, i) => {
            const y = 60 + i * ROW_H;
            const isActive = p.id === active;
            const leftSide = i % 2 === 0;
            const cardX = leftSide ? 40 : SPINE_X + 60;
            const connectorStart = leftSide ? cardX + CARD_W : cardX;
            const connectorEnd = SPINE_X + (leftSide ? -STATION_R : STATION_R);
            const tickDirection = leftSide ? -1 : 1;
            const kindClass = `kind-${p.kind}-card`;
            const pillBgClass = `kind-pill-bg-${p.kind}`;
            const pillTxClass = `kind-pill-tx-${p.kind}`;
            const pillX = cardX + CARD_W - 78;
            const cardY = y - CARD_H / 2;

            return (
              <g key={p.id} onClick={() => setActive(p.id)} role="button" aria-label={`Focus station ${p.name}`}>
                <line className={`edge ${isActive ? 'is-strong' : ''}`} x1={connectorStart} y1={y} x2={connectorEnd} y2={y} />

                {p.modules.map((_, k) => (
                  <circle key={k} cx={connectorEnd + tickDirection * (10 + k * 12)} cy={y} r={3} className="module-tick" />
                ))}

                <rect className={`node-card ${kindClass} ${isActive ? 'is-active' : ''}`} x={cardX} y={cardY} width={CARD_W} height={CARD_H} rx={8} />

                {/* kind pill in top-right of card */}
                <rect className={pillBgClass} x={pillX} y={cardY + 8} width={70} height={16} rx={8} />
                <text x={pillX + 35} y={cardY + 19} className={pillTxClass} textAnchor="middle">{KIND_LABEL[p.kind]}</text>

                <text x={cardX + 14} y={cardY + 18} className="label-eyebrow">{p.id} · {p.duration_minutes} min</text>
                <text x={cardX + 14} y={cardY + 42} className="t-title">{p.name}</text>
                <text x={cardX + 14} y={cardY + 62} className="label-sm">{p.modules.length} module{p.modules.length === 1 ? '' : 's'} plug in</text>

                {p.agent && (
                  <g>
                    <rect className={`agent-badge ${agentMap.get(p.agent)?.tone === 'gold' ? 'tone-gold' : ''}`} x={cardX + 14} y={cardY + CARD_H - 24} width={CARD_W - 28} height={18} rx={9} />
                    <text x={cardX + 24} y={cardY + CARD_H - 11} className="agent-badge-text">
                      <tspan className={`agent-badge-icon ${agentMap.get(p.agent)?.tone === 'gold' ? 'tone-gold' : ''}`}>● </tspan>
                      Driven by {agentMap.get(p.agent)?.name ?? p.agent}
                    </text>
                  </g>
                )}

                <circle className="station-ring" cx={SPINE_X} cy={y} r={STATION_R} />
                <text x={SPINE_X} y={y + 4} className="t-station-num">{i + 1}</text>
              </g>
            );
          })}

          <text x={SPINE_X} y={20} className="label-eyebrow spine-cap">A book enters</text>
          <text x={SPINE_X} y={viewH - 14} className="label-eyebrow spine-cap">A podcast leaves</text>
        </svg>

        <div className="stack focus-pane">
          <div className="card">
            <div className="row-between">
              <span className="eyebrow">Station {activePhase?.id} — {activePhase?.duration_minutes} minutes</span>
              <span className={`kind-badge kind-${activePhase?.kind}`}>
                <i className={`fa-solid fa-${activePhase?.kind === 'agentic' ? 'robot' : activePhase?.kind === 'hybrid' ? 'shuffle' : 'gear'}`} aria-hidden="true"></i>
                {' '}{KIND_LABEL[activePhase?.kind ?? 'mechanical']}
              </span>
            </div>
            <h3 className="card-title">{activePhase?.name}</h3>
            <p>{activePhase?.plain}</p>
          </div>

          {activeAgent && <AgentCard agent={activeAgent} />}

          {!activeAgent && activePhase?.kind === 'mechanical' && (
            <div className="card card-tight">
              <p className="muted small">
                <i className="fa-solid fa-gear" aria-hidden="true"></i>{' '}
                This station is mechanical — no agent, no reasoning. A deterministic script runs the same way for every book.
              </p>
            </div>
          )}

          {activeModules.length > 0 && (
            <div className="stack-tight">
              <span className="eyebrow">Modules plugged into this station</span>
              {activeModules.map((m) => (
                <div key={m.id} className="card card-tight">
                  <strong>{m.name}</strong>
                  <p className="small muted">{m.plain}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
