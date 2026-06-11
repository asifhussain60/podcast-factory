/**
 * PipelineOverviewRail
 * ─────────────────────
 * A rich SVG pipeline flowchart showing all phases as colour-coded nodes with
 * animated flow particles, zoom/pan, and a hover tooltip.
 *
 * Colour scheme:  mechanical=grey  hybrid=blue  agentic=green  gate=amber
 * Layout: single horizontal rail; horizontally scrollable when narrow.
 *
 * Styling contract (repo DoD): zero static style props. Kind colours flow
 * through `k-<kind>` classes that set --por-k in pipeline-overview-rail.css;
 * the dynamic zoom factor + natural width flow through --por-zoom/--por-w
 * custom properties set by a ref callback. Data-driven SVG paint (fill/stroke
 * per kind) uses presentation attributes, which are not inline styles.
 */
import { useState, useRef, useEffect, useCallback } from 'react';
import '../styles/pipeline-overview-rail.css';

interface Phase {
  id: string;
  name: string;
  kind: string;
  agent: string | null;
  plain: string;
  duration_minutes?: number;
  modules?: string[];
}

interface Props {
  phases: Phase[];
}

const KIND_COLOR: Record<string, string> = {
  mechanical: '#87827a',
  hybrid:     '#5b8dd9',
  agentic:    '#4a7c4a',
  gate:       '#c08020',
};

const KIND_BG: Record<string, string> = {
  mechanical: 'rgba(135,130,122,0.08)',
  hybrid:     'rgba(91,141,217,0.10)',
  agentic:    'rgba(74,124,74,0.10)',
  gate:       'rgba(192,128,32,0.12)',
};

const KIND_LABEL: Record<string, string> = {
  mechanical: 'Mechanical',
  hybrid:     'Hybrid',
  agentic:    'Agentic',
  gate:       'Human Gate',
};

const kindClass = (kind: string) => `k-${kind in KIND_COLOR ? kind : 'mechanical'}`;

// ── Layout constants ──────────────────────────────────────────────────────
const NODE_W    = 100;
const NODE_H    = 68;
const GAP       = 24;
const STEP      = NODE_W + GAP;
const RAIL_Y    = 24;   // top of nodes
const SVG_H     = NODE_H + RAIL_Y + 48;  // total SVG height

function wrapText(text: string, maxLen: number): string[] {
  const words = text.split(/\s+/);
  const lines: string[] = [];
  let line = '';
  for (const w of words) {
    if ((line + ' ' + w).trim().length > maxLen) {
      if (line) lines.push(line);
      line = w;
    } else {
      line = line ? line + ' ' + w : w;
    }
    if (lines.length >= 2) break;
  }
  if (line && lines.length < 2) lines.push(line);
  return lines;
}

export default function PipelineOverviewRail({ phases }: Props) {
  const [hoveredId, setHoveredId]     = useState<string | null>(null);
  const [selectedId, setSelectedId]   = useState<string | null>(null);
  const [tooltip, setTooltip]         = useState<{ x: number; y: number; phase: Phase } | null>(null);
  const [zoom, setZoom]               = useState(1);
  const [reducedMotion, setReducedMotion] = useState(false);
  const svgRef                        = useRef<SVGSVGElement>(null);

  // SMIL animations can't be paused from CSS — honour reduced-motion by not
  // rendering the moving particles at all.
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    setReducedMotion(mq.matches);
    const onChange = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, []);

  const totalW   = phases.length * STEP + GAP;
  const svgW     = totalW;

  // Arrow edge (between node right edge and next node left edge)
  const arrowY   = RAIL_Y + NODE_H / 2;
  const connY    = arrowY;

  // Zoom in/out
  const zoomIn  = useCallback(() => setZoom(z => Math.min(2.0, z + 0.15)), []);
  const zoomOut = useCallback(() => setZoom(z => Math.max(0.4, z - 0.15)), []);
  const zoomReset = useCallback(() => setZoom(1), []);

  // Dynamic sizing/zoom via custom properties (external CSS consumes them).
  useEffect(() => {
    const el = svgRef.current;
    if (!el) return;
    el.style.setProperty('--por-w', `${svgW}px`);
    el.style.setProperty('--por-zoom', String(zoom));
  }, [svgW, zoom]);

  // Ctrl+scroll zoom
  useEffect(() => {
    const el = svgRef.current?.parentElement;
    if (!el) return;
    const handler = (e: WheelEvent) => {
      if (!e.ctrlKey && !e.metaKey) return;
      e.preventDefault();
      setZoom(z => Math.max(0.4, Math.min(2.0, z - e.deltaY * 0.001)));
    };
    el.addEventListener('wheel', handler, { passive: false });
    return () => el.removeEventListener('wheel', handler);
  }, []);

  const handleNodeClick = (phase: Phase) => {
    setSelectedId(id => id === phase.id ? null : phase.id);
    // Scroll PipelineSpine to matching phase if it exists
    const el = document.getElementById(`phase-${phase.id}`);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  const handleNodeHover = (phase: Phase, i: number, entering: boolean) => {
    if (entering) {
      setHoveredId(phase.id);
      setTooltip({
        x: GAP + i * STEP,
        y: RAIL_Y + NODE_H + 8,
        phase,
      });
    } else {
      setHoveredId(null);
      setTooltip(null);
    }
  };

  return (
    <div className="por-wrap">
      {/* Zoom controls */}
      <div className="por-controls">
        <div className="por-legend">
          {Object.keys(KIND_COLOR).map((kind) => (
            <span key={kind} className="por-legend-item">
              <span className={`por-legend-dot ${kindClass(kind)}`} />
              {KIND_LABEL[kind]}
            </span>
          ))}
        </div>
        <div className="por-zoom-bar">
          <button className="por-zoom-btn" onClick={zoomOut} aria-label="Zoom out">−</button>
          <span className="por-zoom-level">{Math.round(zoom * 100)}%</span>
          <button className="por-zoom-btn" onClick={zoomIn} aria-label="Zoom in">+</button>
          <button className="por-zoom-btn" onClick={zoomReset} aria-label="Reset" title="Reset zoom">⌂</button>
        </div>
      </div>

      {/* SVG rail */}
      <div className="por-svg-frame">
        <svg
          ref={svgRef}
          className="por-svg"
          viewBox={`0 0 ${svgW} ${SVG_H}`}
          role="img"
          aria-labelledby="pipeline-overview-title pipeline-overview-desc"
        >
          <title id="pipeline-overview-title">Pipeline overview rail</title>
          <desc id="pipeline-overview-desc">A horizontal rail diagram showing each pipeline phase, how phases connect, and which external services they call.</desc>
          <defs>
            {/* Arrow marker */}
            <marker id="por-arr" viewBox="0 0 10 10" refX="8" refY="5"
                    markerWidth="5" markerHeight="5" orient="auto">
              <path d="M0,1 L9,5 L0,9 Z" fill="#87827a"/>
            </marker>
            {/* Glow filter for hovered nodes */}
            <filter id="por-glow" x="-25%" y="-25%" width="150%" height="150%">
              <feGaussianBlur stdDeviation="4" result="blur"/>
              <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
            </filter>

            {/* Per-connection gradient (from-kind → to-kind color) */}
            {phases.slice(0, -1).map((p, i) => {
              const next = phases[i + 1];
              return (
                <linearGradient key={`lg${i}`} id={`por-lg${i}`} x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%"   stopColor={KIND_COLOR[p.kind]    || '#888'}/>
                  <stop offset="100%" stopColor={KIND_COLOR[next.kind] || '#888'}/>
                </linearGradient>
              );
            })}

            {/* Per-edge particle paths (invisible, used as motionPath) */}
            {phases.slice(0, -1).map((_p, i) => {
              const x1 = GAP + i * STEP + NODE_W;
              const x2 = GAP + (i + 1) * STEP;
              return <path key={`mp${i}`} id={`por-mp${i}`} d={`M${x1},${connY} L${x2},${connY}`} fill="none" stroke="none"/>;
            })}
          </defs>

          {/* ── Connection arrows ── */}
          {phases.slice(0, -1).map((p, i) => {
            const x1 = GAP + i * STEP + NODE_W;
            const x2 = GAP + (i + 1) * STEP - 6;
            return (
              <line
                key={`conn${i}`}
                className="por-conn"
                x1={x1} y1={connY} x2={x2} y2={connY}
                stroke={`url(#por-lg${i})`}
                strokeWidth={selectedId ? (selectedId === p.id || selectedId === phases[i+1].id ? 2.5 : 0.5) : 1.8}
                opacity={selectedId ? (selectedId === p.id || selectedId === phases[i+1].id ? 1 : 0.2) : 0.7}
                markerEnd="url(#por-arr)"
              />
            );
          })}

          {/* ── Animated particles along each connection (skipped under
                 prefers-reduced-motion: SMIL ignores CSS) ── */}
          {!reducedMotion && phases.slice(0, -1).map((p, i) => {
            const col = KIND_COLOR[p.kind] || '#888';
            const dur = `${2.2 + i * 0.07}s`;
            return (
              <circle
                key={`par${i}`}
                className="por-particle"
                r="3"
                fill={col}
                opacity={selectedId && selectedId !== p.id && selectedId !== phases[i+1].id ? 0 : 0.9}
                filter="url(#por-glow)"
              >
                <animateMotion dur={dur} begin={`${i * 0.22}s`} repeatCount="indefinite" calcMode="linear">
                  <mpath href={`#por-mp${i}`}/>
                </animateMotion>
                <animate attributeName="opacity"
                  values="0;0;1;1;0;0"
                  keyTimes="0;0.05;0.15;0.85;0.95;1"
                  dur={dur}
                  begin={`${i * 0.22}s`}
                  repeatCount="indefinite"/>
              </circle>
            );
          })}

          {/* ── Phase nodes ── */}
          {phases.map((phase, i) => {
            const x   = GAP + i * STEP;
            const y   = RAIL_Y;
            const col = KIND_COLOR[phase.kind]  || '#888';
            const bg  = KIND_BG[phase.kind]     || 'rgba(135,130,122,0.06)';
            const isGate   = phase.kind === 'gate';
            const isActive = hoveredId === phase.id || selectedId === phase.id;
            const isDimmed = !!selectedId && selectedId !== phase.id;

            const nameLines = wrapText(phase.name, 11);

            return (
              <g
                key={phase.id}
                className={`por-node ${kindClass(phase.kind)}${isActive ? ' is-active' : ''}`}
                transform={`translate(${x},${y})`}
                opacity={isDimmed ? 0.2 : 1}
                onClick={() => handleNodeClick(phase)}
                onMouseEnter={() => handleNodeHover(phase, i, true)}
                onMouseLeave={() => handleNodeHover(phase, i, false)}
                role="button"
                aria-label={`${phase.name} — ${KIND_LABEL[phase.kind]}`}
                tabIndex={0}
              >
                {/* Shadow */}
                <rect x={2} y={2} width={NODE_W} height={NODE_H} rx={7}
                      fill="rgba(0,0,0,0.08)"/>
                {/* Background */}
                <rect className="por-node-bg" width={NODE_W} height={NODE_H} rx={7}
                      fill={bg}
                      stroke={isActive ? col : 'rgba(135,130,122,0.3)'}
                      strokeWidth={isActive ? 2.5 : 1.2}
                      filter={isActive ? 'url(#por-glow)' : undefined}
                />
                {/* Top accent bar */}
                <rect width={NODE_W} height={5} rx={7} fill={col} opacity={0.7}/>
                <rect x={0} y={5} width={NODE_W} height={7} fill={col} opacity={0.12}/>

                {/* Phase ID badge */}
                <rect x={6} y={10} width={30} height={15} rx={3}
                      fill={col} opacity={0.15}/>
                <text className="por-badge-text" x={21} y={21} textAnchor="middle">
                  {phase.id}
                </text>

                {/* Phase name (2 lines max) */}
                {nameLines.map((line, li) => (
                  <text key={li}
                        className="por-name-text"
                        x={NODE_W / 2}
                        y={isGate ? 43 + li * 13 : 38 + li * 13}
                        textAnchor="middle">
                    {line}
                  </text>
                ))}

                {/* Duration badge */}
                {phase.duration_minutes && (
                  <text className="por-dur-text" x={NODE_W - 6} y={NODE_H - 7} textAnchor="end">
                    ~{phase.duration_minutes}m
                  </text>
                )}

                {/* Gate diamond marker */}
                {isGate && (
                  <polygon
                    points={`${NODE_W/2},14 ${NODE_W/2+9},22 ${NODE_W/2},30 ${NODE_W/2-9},22`}
                    fill={col} opacity={0.25}
                  />
                )}

                {/* Hover ring */}
                {isActive && (
                  <rect x={-2} y={-2} width={NODE_W + 4} height={NODE_H + 4} rx={9}
                        fill="none" stroke={col} strokeWidth={1.5} opacity={0.4}
                        strokeDasharray="4 3"/>
                )}
              </g>
            );
          })}

          {/* ── Tooltip ── */}
          {tooltip && (
            <foreignObject
              className="por-tooltip-fo"
              x={Math.min(tooltip.x, svgW - 200)}
              y={tooltip.y}
              width={200}
              height={100}
            >
              <div className="por-tooltip">
                <strong>{tooltip.phase.name}</strong>
                <span className={`por-tooltip-kind ${kindClass(tooltip.phase.kind)}`}>
                  {KIND_LABEL[tooltip.phase.kind]}
                  {tooltip.phase.agent ? ` · ${tooltip.phase.agent}` : ''}
                </span>
                <p>{(tooltip.phase.plain || '').slice(0, 100)}{(tooltip.phase.plain || '').length > 100 ? '…' : ''}</p>
              </div>
            </foreignObject>
          )}
        </svg>
      </div>

      {/* Selected phase detail strip */}
      {selectedId && (() => {
        const p = phases.find(ph => ph.id === selectedId);
        if (!p) return null;
        return (
          <div className={`por-selected-strip ${kindClass(p.kind)}`}>
            <div className="por-strip-header">
              <strong className="por-strip-id">{p.id}</strong>
              <span className="por-strip-name">{p.name}</span>
              <span className="por-strip-kind">{KIND_LABEL[p.kind]}</span>
              {p.duration_minutes && (
                <span className="por-strip-dur">~{p.duration_minutes} min</span>
              )}
              <button className="por-strip-close" onClick={() => setSelectedId(null)} aria-label="Close">×</button>
            </div>
            <p className="por-strip-plain">{p.plain}</p>
            {p.modules && p.modules.length > 0 && (
              <div className="por-strip-modules">
                {p.modules.map(m => (
                  <span key={m} className="por-module-chip">{m}</span>
                ))}
              </div>
            )}
          </div>
        );
      })()}
    </div>
  );
}
