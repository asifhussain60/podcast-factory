/**
 * C4ContextDiagram — L1 System Context (C4 Model level 1)
 *
 * Three-row vertical layout, top to bottom:
 *   Row 1: Operator (you — running the pipeline)
 *   Row 2: Podcast Factory System (the boundary of this codebase)
 *   Row 3: Five external trust zones (Anthropic / Azure / Google / NotebookLM / GitHub)
 *
 * Audience: Executive (VP). Plain-English labels only. No acronyms.
 * Pure SVG — no external deps.
 */

export default function C4ContextDiagram() {
  const W = 1040;
  const H = 500;

  // Geometry
  const ROW1_Y = 60;    // Operator row center-y
  const ROW2_Y = 220;   // System box center-y
  const ROW3_Y = 400;   // External zones row center-y

  const SYS_W = 360, SYS_H = 100;
  const SYS_X = W / 2 - SYS_W / 2;

  const ACTOR_W = 120;
  const ZONE_W = 150, ZONE_H = 76;

  // Five external zones — x-centers spread across full width
  const zones = [
    { id: 'anthropic', label: 'Anthropic', sub: 'AI reasoning engine', color: 'var(--c-vendor-anthropic)', x: 100 },
    { id: 'azure',     label: 'Azure AI',   sub: 'PDF reading + translation', color: 'var(--c-vendor-azure)', x: 280 },
    { id: 'google',    label: 'Google AI',  sub: 'Audio generation + audit', color: 'var(--c-vendor-google)', x: 520 },
    { id: 'notebooklm',label: 'NotebookLM', sub: 'Final podcast episodes',   color: 'var(--c-vendor-notebooklm)', x: 750 },
    { id: 'github',    label: 'GitHub',     sub: 'Published catalog',        color: 'var(--c-vendor-github)', x: 950 },
  ];

  // Arrows from system to each zone
  const arrowData = zones.map((z) => ({
    x1: W / 2,
    y1: ROW2_Y + SYS_H / 2,
    x2: z.x,
    y2: ROW3_Y - ZONE_H / 2,
    label: z.id === 'anthropic' ? 'HTTPS · API key' :
           z.id === 'azure'     ? 'HTTPS · API key' :
           z.id === 'google'    ? 'HTTPS · session' :
           z.id === 'notebooklm'? 'HTTPS · browser' :
           'git push · token',
    color: z.color,
  }));

  return (
    <div className="overflow-x-auto w-full">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        style={{ minWidth: '680px' }}
        role="img"
        aria-label="C4 system context: Podcast Factory and its five external trust zones"
      >
        <defs>
          <marker id="c4-arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
            <polygon points="0 0, 8 3, 0 6" fill="var(--c-ink-muted)" />
          </marker>
          {zones.map((z) => (
            <marker key={`m-${z.id}`} id={`arr-${z.id}`} markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
              <polygon points="0 0, 8 3, 0 6" fill={z.color} />
            </marker>
          ))}
        </defs>

        {/* ── Row 3 background — external trust zone band ── */}
        <rect x={0} y={ROW3_Y - 52} width={W} height={ZONE_H + 32} rx={6}
          fill="var(--c-diag-zone)" stroke="var(--c-diag-zone-stroke)" strokeWidth="1" strokeDasharray="6,3" />
        <text x={8} y={ROW3_Y - 38} fontSize="11" fontWeight="700" fill="var(--c-ink-muted)" letterSpacing="0.08em">
          EXTERNAL TRUST ZONES — DATA LEAVES YOUR LAPTOP
        </text>

        {/* ── Arrows (behind boxes) ── */}
        {arrowData.map((a, i) => (
          <g key={i}>
            <line x1={a.x1} y1={a.y1} x2={a.x2} y2={a.y2}
              stroke={a.color} strokeWidth="1.5" strokeDasharray="5,3" opacity="0.7"
              markerEnd={`url(#arr-${zones[i].id})`} />
            <text
              x={(a.x1 + a.x2) / 2 + 6}
              y={(a.y1 + a.y2) / 2}
              fontSize="10"
              fill="var(--c-ink-muted)"
              transform={`rotate(-${Math.atan2(a.y2 - a.y1, a.x2 - a.x1) * 180 / Math.PI}, ${(a.x1 + a.x2) / 2 + 6}, ${(a.y1 + a.y2) / 2})`}
            >
              {a.label}
            </text>
          </g>
        ))}

        {/* ── Row 1: Operator ── */}
        <g>
          {/* Stick figure */}
          <circle cx={W / 2} cy={ROW1_Y - 14} r={12} fill="var(--c-bg-card)" stroke="var(--c-ink-dim)" strokeWidth="1.5" />
          <line x1={W / 2} y1={ROW1_Y - 2} x2={W / 2} y2={ROW1_Y + 22} stroke="var(--c-ink-dim)" strokeWidth="1.5" />
          <line x1={W / 2 - 14} y1={ROW1_Y + 8} x2={W / 2 + 14} y2={ROW1_Y + 8} stroke="var(--c-ink-dim)" strokeWidth="1.5" />
          <line x1={W / 2} y1={ROW1_Y + 22} x2={W / 2 - 10} y2={ROW1_Y + 40} stroke="var(--c-ink-dim)" strokeWidth="1.5" />
          <line x1={W / 2} y1={ROW1_Y + 22} x2={W / 2 + 10} y2={ROW1_Y + 40} stroke="var(--c-ink-dim)" strokeWidth="1.5" />
          {/* Label below */}
          <text x={W / 2} y={ROW1_Y + 56} textAnchor="middle" fontSize="14" fontWeight="700" fill="var(--c-ink)">You</text>
          <text x={W / 2} y={ROW1_Y + 72} textAnchor="middle" fontSize="12" fill="var(--c-ink-muted)">Upload books · approve gates · review output</text>
        </g>

        {/* Arrow: operator → system */}
        <line x1={W / 2} y1={ROW1_Y + 44}
              x2={W / 2} y2={ROW2_Y - SYS_H / 2 - 4}
              stroke="var(--c-ink-dim)" strokeWidth="1.5" markerEnd="url(#c4-arrow)" />
        <text x={W / 2 + 6} y={(ROW1_Y + 44 + ROW2_Y - SYS_H / 2) / 2 + 4} fontSize="11" fill="var(--c-ink-muted)">
          operates
        </text>

        {/* ── Row 2: System box ── */}
        <rect x={SYS_X} y={ROW2_Y - SYS_H / 2} width={SYS_W} height={SYS_H} rx={8}
          fill="var(--c-bg-card)" stroke="var(--c-accent)" strokeWidth="2"
          filter="drop-shadow(0 2px 8px rgba(31,29,24,0.10))" />
        <rect x={SYS_X} y={ROW2_Y - SYS_H / 2} width={SYS_W} height={28} rx={8}
          fill="var(--c-accent)" opacity="0.12" />
        <text x={W / 2} y={ROW2_Y - SYS_H / 2 + 18} textAnchor="middle" fontSize="11" fontWeight="700" fill="var(--c-accent)" letterSpacing="0.06em">
          SYSTEM
        </text>
        <text x={W / 2} y={ROW2_Y + 4} textAnchor="middle" fontSize="17" fontWeight="700" fill="var(--c-ink)">
          Podcast Factory
        </text>
        <text x={W / 2} y={ROW2_Y + 22} textAnchor="middle" fontSize="12" fill="var(--c-ink-dim)">
          Runs on your laptop · nothing shared
        </text>
        <text x={W / 2} y={ROW2_Y + 38} textAnchor="middle" fontSize="12" fill="var(--c-ink-dim)">
          without your explicit step-by-step approval
        </text>

        {/* ── Row 3: External zones ── */}
        {zones.map((z) => (
          <g key={z.id}>
            <rect
              x={z.x - ZONE_W / 2}
              y={ROW3_Y - ZONE_H / 2}
              width={ZONE_W}
              height={ZONE_H}
              rx={6}
              fill="var(--c-bg-card)"
              stroke={z.color}
              strokeWidth="1.5"
            />
            {/* Vendor colour bar */}
            <rect x={z.x - ZONE_W / 2} y={ROW3_Y - ZONE_H / 2} width={ZONE_W} height={6} rx={3} fill={z.color} />
            <text x={z.x} y={ROW3_Y - ZONE_H / 2 + 22} textAnchor="middle" fontSize="13" fontWeight="700" fill="var(--c-ink)">
              {z.label}
            </text>
            <text x={z.x} y={ROW3_Y - ZONE_H / 2 + 38} textAnchor="middle" fontSize="11" fill="var(--c-ink-muted)">
              {z.sub}
            </text>
          </g>
        ))}

        {/* Local mac boundary label */}
        <text x={8} y={22} fontSize="11" fontWeight="700" fill="var(--c-diag-local)" letterSpacing="0.08em">
          YOUR LAPTOP — CONTROLLED ENVIRONMENT
        </text>
        <rect x={2} y={4} width={W - 4} height={ROW3_Y - 62} rx={6}
          fill="none" stroke="var(--c-diag-local)" strokeWidth="1.5" strokeDasharray="8,4" opacity="0.5" />
      </svg>
    </div>
  );
}
