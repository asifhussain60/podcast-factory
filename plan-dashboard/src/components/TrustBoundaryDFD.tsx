/**
 * TrustBoundaryDFD — L2 Containers & Data Flow with Trust Boundaries
 *
 * Vertical DFD showing:
 *   - Operator initiates
 *   - Local Mac boundary (two containers: pipeline Python + Astro site)
 *   - Four HTTPS egress paths to external trust zones
 *   - Auth method on every arrow
 *
 * Audience: Technical (Architect).
 * References L1 C4ContextDiagram — does NOT redraw the system overview.
 * Pure SVG — no external deps.
 */

interface TrustZone {
  id: string;
  label: string;
  sublabel: string;
  color: string;
  x: number;  // centre-x
}

const ZONES: TrustZone[] = [
  { id: 'anthropic', label: 'Anthropic API', sublabel: 'claude-opus-4-7 / sonnet / haiku', color: 'var(--c-vendor-anthropic)', x: 100 },
  { id: 'azure',     label: 'Azure AI',      sublabel: 'docintel · translator · speech',   color: 'var(--c-vendor-azure)',     x: 320 },
  { id: 'google',    label: 'Google AI',     sublabel: 'gemini · notebooklm',              color: 'var(--c-vendor-google)',    x: 560 },
  { id: 'github',    label: 'GitHub',        sublabel: 'actions · pages · releases',       color: 'var(--c-vendor-github)',    x: 780 },
];

export default function TrustBoundaryDFD() {
  const W = 940;
  const H = 540;

  // Rows
  const OP_Y   = 56;
  const PIPE_Y = 200;   // Pipeline Python container
  const SITE_Y = 320;   // Astro site container
  const EXT_Y  = 460;   // External trust zones

  const CONT_W = 260, CONT_H = 72;
  const ZONE_W = 160, ZONE_H = 64;
  const PIPE_X = W / 2 - CONT_W - 20;
  const SITE_X = W / 2 + 20;

  const LOCAL_PAD = 20;
  const LOCAL_X = PIPE_X - LOCAL_PAD;
  const LOCAL_W = (SITE_X + CONT_W + LOCAL_PAD) - LOCAL_X;
  const LOCAL_H = (SITE_Y + CONT_H + LOCAL_PAD) - (PIPE_Y - LOCAL_PAD);

  // Egress arrows: pipeline → external zones
  const egressArrows = [
    {
      from: { x: PIPE_X + CONT_W / 2, y: PIPE_Y + CONT_H },
      to: { x: ZONES[0].x, y: EXT_Y - ZONE_H / 2 },
      label: 'HTTPS', auth: 'API key · .env', zone: ZONES[0],
    },
    {
      from: { x: PIPE_X + CONT_W / 2, y: PIPE_Y + CONT_H },
      to: { x: ZONES[1].x, y: EXT_Y - ZONE_H / 2 },
      label: 'HTTPS', auth: 'API key · .env', zone: ZONES[1],
    },
    {
      from: { x: SITE_X + CONT_W / 2, y: SITE_Y + CONT_H },
      to: { x: ZONES[2].x, y: EXT_Y - ZONE_H / 2 },
      label: 'HTTPS', auth: 'Browser session', zone: ZONES[2],
    },
    {
      from: { x: PIPE_X + CONT_W / 2, y: PIPE_Y + CONT_H },
      to: { x: ZONES[3].x, y: EXT_Y - ZONE_H / 2 },
      label: 'git push', auth: 'PAT · .env', zone: ZONES[3],
    },
  ];

  return (
    <div className="overflow-x-auto w-full">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        style={{ minWidth: '660px' }}
        role="img"
        aria-label="Data flow diagram with trust boundaries — containers and external egress paths"
      >
        <defs>
          {ZONES.map((z) => (
            <marker key={`dfd-m-${z.id}`} id={`dfd-arr-${z.id}`} markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
              <polygon points="0 0, 8 3, 0 6" fill={z.color} />
            </marker>
          ))}
          <marker id="dfd-arr-op" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
            <polygon points="0 0, 8 3, 0 6" fill="var(--c-ink-dim)" />
          </marker>
          <marker id="dfd-arr-site-pipe" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
            <polygon points="0 0, 8 3, 0 6" fill="var(--c-diag-local)" />
          </marker>
        </defs>

        {/* ── External trust zone band ── */}
        <rect x={0} y={EXT_Y - ZONE_H / 2 - 14} width={W} height={ZONE_H + 32} rx={6}
          fill="var(--c-diag-zone)" stroke="var(--c-diag-zone-stroke)" strokeWidth="1" strokeDasharray="6,3" />
        <text x={6} y={EXT_Y - ZONE_H / 2 + 1} fontSize="10" fontWeight="700" fill="var(--c-ink-muted)" letterSpacing="0.07em">
          EXTERNAL — HTTPS EGRESS
        </text>

        {/* ── Local Mac boundary box ── */}
        <rect x={LOCAL_X} y={PIPE_Y - LOCAL_PAD} width={LOCAL_W} height={LOCAL_H} rx={8}
          fill="rgba(74,124,74,0.04)" stroke="var(--c-diag-local)" strokeWidth="1.5" strokeDasharray="8,4" />
        <text x={LOCAL_X + 8} y={PIPE_Y - LOCAL_PAD + 16} fontSize="10" fontWeight="700" fill="var(--c-diag-local)" letterSpacing="0.07em">
          LOCAL MAC — TRUST BOUNDARY
        </text>

        {/* ── Operator ── */}
        <circle cx={W / 2} cy={OP_Y - 12} r={11} fill="var(--c-bg-card)" stroke="var(--c-ink-dim)" strokeWidth="1.5" />
        <line x1={W / 2} y1={OP_Y - 1} x2={W / 2} y2={OP_Y + 20} stroke="var(--c-ink-dim)" strokeWidth="1.5" />
        <line x1={W / 2 - 12} y1={OP_Y + 8} x2={W / 2 + 12} y2={OP_Y + 8} stroke="var(--c-ink-dim)" strokeWidth="1.5" />
        <line x1={W / 2} y1={OP_Y + 20} x2={W / 2 - 9} y2={OP_Y + 36} stroke="var(--c-ink-dim)" strokeWidth="1.5" />
        <line x1={W / 2} y1={OP_Y + 20} x2={W / 2 + 9} y2={OP_Y + 36} stroke="var(--c-ink-dim)" strokeWidth="1.5" />
        <text x={W / 2} y={OP_Y + 52} textAnchor="middle" fontSize="13" fontWeight="700" fill="var(--c-ink)">Operator</text>

        {/* Operator → Pipeline arrow */}
        <line x1={W / 2} y1={OP_Y + 38} x2={PIPE_X + CONT_W / 2} y2={PIPE_Y - 4}
          stroke="var(--c-ink-dim)" strokeWidth="1.5" markerEnd="url(#dfd-arr-op)" />
        <text x={(W / 2 + PIPE_X + CONT_W / 2) / 2 + 6} y={(OP_Y + 38 + PIPE_Y - 4) / 2} fontSize="10" fill="var(--c-ink-muted)">
          triggers
        </text>

        {/* Operator → Astro site arrow */}
        <line x1={W / 2} y1={OP_Y + 38} x2={SITE_X + CONT_W / 2} y2={SITE_Y - 4}
          stroke="var(--c-ink-dim)" strokeWidth="1.5" markerEnd="url(#dfd-arr-op)" />
        <text x={(W / 2 + SITE_X + CONT_W / 2) / 2 - 12} y={(OP_Y + 38 + SITE_Y - 4) / 2} fontSize="10" fill="var(--c-ink-muted)">
          reviews
        </text>

        {/* ── Pipeline Python container ── */}
        <rect x={PIPE_X} y={PIPE_Y} width={CONT_W} height={CONT_H} rx={6}
          fill="var(--c-bg-elev)" stroke="var(--c-accent)" strokeWidth="1.5"
          filter="drop-shadow(0 1px 4px rgba(31,29,24,0.08))" />
        <text x={PIPE_X + CONT_W / 2} y={PIPE_Y + 24} textAnchor="middle" fontSize="14" fontWeight="700" fill="var(--c-ink)">
          Pipeline (Python)
        </text>
        <text x={PIPE_X + CONT_W / 2} y={PIPE_Y + 42} textAnchor="middle" fontSize="11" fill="var(--c-ink-muted)">
          14 stations · all LLM calls
        </text>
        <text x={PIPE_X + CONT_W / 2} y={PIPE_Y + 58} textAnchor="middle" fontSize="11" fill="var(--c-ink-muted)">
          state in SQLite + filesystem
        </text>

        {/* ── Astro site container ── */}
        <rect x={SITE_X} y={SITE_Y} width={CONT_W} height={CONT_H} rx={6}
          fill="var(--c-bg-elev)" stroke="var(--c-planner)" strokeWidth="1.5"
          filter="drop-shadow(0 1px 4px rgba(31,29,24,0.08))" />
        <text x={SITE_X + CONT_W / 2} y={SITE_Y + 24} textAnchor="middle" fontSize="14" fontWeight="700" fill="var(--c-ink)">
          Astro Site (Node)
        </text>
        <text x={SITE_X + CONT_W / 2} y={SITE_Y + 42} textAnchor="middle" fontSize="11" fill="var(--c-ink-muted)">
          Review gates · chapter reader
        </text>
        <text x={SITE_X + CONT_W / 2} y={SITE_Y + 58} textAnchor="middle" fontSize="11" fill="var(--c-ink-muted)">
          plan dashboard · local only
        </text>

        {/* Pipeline ↔ Astro internal arrow */}
        <line x1={PIPE_X + CONT_W} y1={PIPE_Y + CONT_H / 2}
              x2={SITE_X} y2={PIPE_Y + CONT_H / 2 + 40}
              stroke="var(--c-diag-local)" strokeWidth="1.5" markerEnd="url(#dfd-arr-site-pipe)" />
        <text x={(PIPE_X + CONT_W + SITE_X) / 2} y={PIPE_Y + CONT_H / 2 + 30} textAnchor="middle" fontSize="10" fill="var(--c-diag-local)">
          JSON snapshots
        </text>

        {/* ── Egress arrows ── */}
        {egressArrows.map((a, i) => (
          <g key={i}>
            <line
              x1={a.from.x} y1={a.from.y} x2={a.to.x} y2={a.to.y}
              stroke={a.zone.color} strokeWidth="1.5" strokeDasharray="5,3" opacity="0.8"
              markerEnd={`url(#dfd-arr-${a.zone.id})`}
            />
            {/* Auth label mid-point */}
            <text
              x={(a.from.x + a.to.x) / 2 + 4}
              y={(a.from.y + a.to.y) / 2}
              fontSize="10"
              fill={a.zone.color}
              opacity="0.85"
            >
              {a.auth}
            </text>
          </g>
        ))}

        {/* ── External zone boxes ── */}
        {ZONES.map((z) => (
          <g key={z.id}>
            <rect
              x={z.x - ZONE_W / 2} y={EXT_Y - ZONE_H / 2}
              width={ZONE_W} height={ZONE_H}
              rx={5} fill="var(--c-bg-card)" stroke={z.color} strokeWidth="1.5"
            />
            <rect x={z.x - ZONE_W / 2} y={EXT_Y - ZONE_H / 2} width={ZONE_W} height={5} rx={3} fill={z.color} />
            <text x={z.x} y={EXT_Y - ZONE_H / 2 + 20} textAnchor="middle" fontSize="12" fontWeight="700" fill="var(--c-ink)">
              {z.label}
            </text>
            <text x={z.x} y={EXT_Y - ZONE_H / 2 + 36} textAnchor="middle" fontSize="10" fill="var(--c-ink-muted)">
              {z.sublabel}
            </text>
          </g>
        ))}
      </svg>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 mt-3 text-sm" style={{ color: 'var(--c-ink-dim)' }}>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-7 h-0.5 border-dashed border border-green-700 opacity-60" />
          Internal (local only — no egress)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-7 h-0.5 border-dashed" style={{ borderColor: 'var(--c-vendor-anthropic)' }} />
          Encrypted egress (HTTPS) · carries content
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-7 h-0.5 border-dashed" style={{ borderColor: 'var(--c-vendor-github)' }} />
          Code push (no content PII)
        </span>
      </div>
    </div>
  );
}
