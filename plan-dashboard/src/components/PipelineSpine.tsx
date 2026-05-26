import { useState, useMemo } from 'react';

interface Phase {
  id: string;
  name: string;
  plain: string;
  duration_minutes: number;
  modules: string[];
}

interface Module {
  id: string;
  name: string;
  plain: string;
}

interface Props {
  phases: Phase[];
  modules: Module[];
}

const ROW_H = 110;
const SPINE_X = 380;
const STATION_R = 18;
const VIEW_W = 760;

export default function PipelineSpine({ phases, modules }: Props) {
  const [active, setActive] = useState<string | null>(phases[0]?.id ?? null);

  const moduleMap = useMemo(() => {
    const m = new Map<string, Module>();
    modules.forEach((mod) => m.set(mod.id, mod));
    return m;
  }, [modules]);

  const viewH = phases.length * ROW_H + 80;
  const activePhase = phases.find((p) => p.id === active) ?? phases[0];
  const activeModules = (activePhase?.modules ?? []).map((id) => moduleMap.get(id)).filter(Boolean) as Module[];

  return (
    <div className="stack">
      <div className="grid-2">
        <svg className="svg-host" viewBox={`0 0 ${VIEW_W} ${viewH}`} role="img" aria-label="Pipeline stations from top to bottom">
          <line className="spine" x1={SPINE_X} y1={40} x2={SPINE_X} y2={viewH - 40} />

          {phases.map((p, i) => {
            const y = 60 + i * ROW_H;
            const isActive = p.id === active;
            const leftSide = i % 2 === 0;
            const cardX = leftSide ? 40 : SPINE_X + 60;
            const cardW = 280;
            const connectorStart = leftSide ? cardX + cardW : cardX;
            const connectorEnd = SPINE_X + (leftSide ? -STATION_R : STATION_R);
            const tickDirection = leftSide ? -1 : 1;

            return (
              <g key={p.id} onClick={() => setActive(p.id)} role="button" aria-label={`Focus station ${p.name}`}>
                <line className={`edge ${isActive ? 'is-strong' : ''}`} x1={connectorStart} y1={y} x2={connectorEnd} y2={y} />

                {p.modules.map((_, k) => (
                  <circle key={k} cx={connectorEnd + tickDirection * (10 + k * 12)} cy={y} r={3} className="module-tick" />
                ))}

                <rect className={`node-card ${isActive ? 'is-active' : ''}`} x={cardX} y={y - 38} width={cardW} height={76} rx={8} />
                <text x={cardX + 14} y={y - 18} className="label-eyebrow">{p.id} · {p.duration_minutes} min</text>
                <text x={cardX + 14} y={y + 2} className="t-title">{p.name}</text>
                <text x={cardX + 14} y={y + 22} className="label-sm">{p.modules.length} module{p.modules.length === 1 ? '' : 's'} plug in</text>

                <circle className="station-ring" cx={SPINE_X} cy={y} r={STATION_R} />
                <text x={SPINE_X} y={y + 4} className="t-station-num">{i + 1}</text>
              </g>
            );
          })}

          <text x={SPINE_X} y={20} className="label-eyebrow spine-cap">A book enters</text>
          <text x={SPINE_X} y={viewH - 14} className="label-eyebrow spine-cap">A podcast leaves</text>
        </svg>

        <div className="stack">
          <div className="card">
            <span className="eyebrow">Station {activePhase?.id} — {activePhase?.duration_minutes} minutes</span>
            <h3 className="card-title">{activePhase?.name}</h3>
            <p>{activePhase?.plain}</p>
          </div>

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

          {activeModules.length === 0 && (
            <div className="card card-tight">
              <p className="muted small">This station is mechanical — no pluggable modules. The same code runs for every book.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
