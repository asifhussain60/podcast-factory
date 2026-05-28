/**
 * PhaseSwimlaneDiagram — L3 Pipeline Phase Sequence
 *
 * Vertical swimlane showing every pipeline station with:
 *   - Phase ID + name
 *   - Service(s) hit (Azure / Anthropic / Google / Local)
 *   - Model tier (Opus / Sonnet / Haiku / Gemini / None)
 *   - Token cost tier (Low / Med / High) — colour-coded row fill
 *   - Two human-halt gates rendered as full-width banners
 *
 * Pure SVG with CSS variables from theme.css. No external deps.
 * Reads future-state phase data (hardcoded here as the snapshot
 * representation feeds PipelineSpine; this component owns L3 detail).
 */

import { useRef, useEffect } from 'react';

interface SwimPhase {
  id: string;
  label: string;
  service: string;
  vendor: 'anthropic' | 'azure' | 'google' | 'local' | 'human';
  model: string;
  cost: 'low' | 'mid' | 'high' | 'zero' | 'gate';
  note?: string;
  isGate?: boolean;
  isFuture?: boolean;    // highlight as new / not yet shipped
}

const PHASES: SwimPhase[] = [
  {
    id: 'P0',
    label: 'Read the source',
    service: 'Azure Document Intelligence + Translator',
    vendor: 'azure',
    model: '—',
    cost: 'low',
    note: 'Branches: pdf → DocIntel / audio → Turboscribe + Translator',
  },
  {
    id: 'P1',
    label: 'Strip the noise',
    service: 'Anthropic (routed: Haiku → Sonnet → Gemini)',
    vendor: 'anthropic',
    model: 'Haiku / Sonnet / Gemini',
    cost: 'low',
    note: 'Model selected per passage complexity; tradition-specific idioms → Gemini',
    isFuture: true,
  },
  {
    id: 'P2',
    label: 'Polish the text',
    service: 'Anthropic Claude',
    vendor: 'anthropic',
    model: 'Sonnet',
    cost: 'low',
  },
  {
    id: 'P3',
    label: 'Learn the names',
    service: 'Local + Anthropic (pre-gate analysis)',
    vendor: 'local',
    model: 'Haiku (analysis)',
    cost: 'low',
    note: 'Phonetics sidecar + pre-gate structural warnings',
  },
  {
    id: 'GATE 1',
    label: 'Source Review Gate',
    service: 'Podcast Reader (Astro site)',
    vendor: 'human',
    model: '—',
    cost: 'gate',
    note: 'Human reviews chapters, noise log, vocabulary gaps. Approves before expensive phases run.',
    isGate: true,
    isFuture: true,
  },
  {
    id: 'P4',
    label: 'Plan the episodes',
    service: 'Anthropic Claude Opus',
    vendor: 'anthropic',
    model: 'Opus',
    cost: 'high',
    note: 'Content-first slicing: ~30-min learning arc per episode',
  },
  {
    id: 'P5',
    label: 'Enrich with context',
    service: 'Anthropic Claude Sonnet',
    vendor: 'anthropic',
    model: 'Sonnet',
    cost: 'mid',
    note: "Tradition firewall active — atoms matched to book\u2019s tradition",
    isFuture: true,
  },
  {
    id: 'P6',
    label: 'Bring in knowledge',
    service: 'Anthropic + Local knowledge base',
    vendor: 'anthropic',
    model: 'Sonnet',
    cost: 'mid',
    note: 'Tradition-tagged atoms (Quran / Hadith / doctrine); missing citations flagged',
    isFuture: true,
  },
  {
    id: 'P7',
    label: 'Cut the pieces',
    service: 'Local (mechanical)',
    vendor: 'local',
    model: '—',
    cost: 'zero',
  },
  {
    id: 'P7f',
    label: 'Write narrator framing',
    service: 'Anthropic Claude Opus',
    vendor: 'anthropic',
    model: 'Opus',
    cost: 'high',
    note: 'Host roles consistent across series; never flip mid-book',
  },
  {
    id: 'P7g',
    label: 'Optimize for teaching',
    service: 'Anthropic Claude Sonnet',
    vendor: 'anthropic',
    model: 'Sonnet',
    cost: 'mid',
    note: 'Arc validation + NotebookLM hygiene — Sonnet only (Gemini kept independent)',
    isFuture: true,
  },
  {
    id: 'P8',
    label: 'Design the slides',
    service: 'Anthropic Claude Sonnet',
    vendor: 'anthropic',
    model: 'Sonnet',
    cost: 'mid',
  },
  {
    id: 'P9',
    label: 'Audit and converge',
    service: 'Claude Challenger + Gemini second-opinion',
    vendor: 'google',
    model: 'Gemini (independent)',
    cost: 'mid',
    note: 'Dual-auditor: Claude + Gemini. Up to 5 passes per chapter.',
    isFuture: true,
  },
  {
    id: 'GATE 2',
    label: 'Publish Review Gate',
    service: 'Podcast Reader (Astro site)',
    vendor: 'human',
    model: '—',
    cost: 'gate',
    note: 'Human sees complete product: episode list, challenger findings, upload checklist.',
    isGate: true,
  },
];

const VENDOR_COLORS: Record<SwimPhase['vendor'], string> = {
  anthropic: 'var(--c-vendor-anthropic)',
  azure:     'var(--c-vendor-azure)',
  google:    'var(--c-vendor-google)',
  local:     'var(--c-ink-muted)',
  human:     'var(--c-diag-gate)',
};

const MODEL_COLORS: Record<string, string> = {
  'Opus':                  'var(--c-model-opus)',
  'Sonnet':                'var(--c-model-sonnet)',
  'Haiku':                 'var(--c-model-haiku)',
  'Haiku / Sonnet / Gemini': 'var(--c-model-haiku)',
  'Haiku (analysis)':      'var(--c-model-haiku)',
  'Gemini (independent)':  'var(--c-model-gemini)',
  '—':                     'var(--c-model-none)',
};

const COST_FILLS: Record<SwimPhase['cost'], string> = {
  zero: 'transparent',
  low:  'var(--c-tokens-low)',
  mid:  'var(--c-tokens-mid)',
  high: 'var(--c-tokens-high)',
  gate: 'rgba(160, 96, 45, 0.08)',
};

const COST_LABELS: Record<SwimPhase['cost'], string> = {
  zero: 'No LLM',
  low:  'Low cost',
  mid:  'Mid cost',
  high: 'High cost',
  gate: 'Human',
};

export default function PhaseSwimlaneDiagram() {
  const containerRef = useRef<HTMLDivElement>(null);

  // Column widths (px in a 1240-wide canvas)
  const COL_PHASE   = 72;
  const COL_NAME    = 200;
  const COL_SERVICE = 320;
  const COL_MODEL   = 170;
  const COL_COST    = 90;
  const COL_NOTE    = 288;
  const TOTAL_W     = COL_PHASE + COL_NAME + COL_SERVICE + COL_MODEL + COL_COST + COL_NOTE; // 1140

  const HEADER_H = 36;
  const ROW_H    = 52;
  const GATE_H   = 68;

  const rows = PHASES;
  const totalH = HEADER_H + rows.reduce((h, r) => h + (r.isGate ? GATE_H : ROW_H), 0) + 24;

  // Column x-starts
  const xPhase   = 0;
  const xName    = xPhase + COL_PHASE;
  const xService = xName + COL_NAME;
  const xModel   = xService + COL_SERVICE;
  const xCost    = xModel + COL_MODEL;
  const xNote    = xCost + COL_COST;

  // Build rows layout
  let cursor = HEADER_H;
  const rowLayouts = rows.map((r) => {
    const h = r.isGate ? GATE_H : ROW_H;
    const y = cursor;
    cursor += h;
    return { ...r, y, h };
  });

  const HEADERS = [
    { label: 'Phase', x: xPhase, w: COL_PHASE },
    { label: 'Station', x: xName, w: COL_NAME },
    { label: 'Service', x: xService, w: COL_SERVICE },
    { label: 'Model', x: xModel, w: COL_MODEL },
    { label: 'Cost tier', x: xCost, w: COL_COST },
    { label: 'Notes', x: xNote, w: COL_NOTE },
  ];

  return (
    <div ref={containerRef} className="swimlane-host" style={{ overflowX: 'auto', width: '100%' }}>
      <svg
        viewBox={`0 0 ${TOTAL_W} ${totalH}`}
        style={{ width: '100%', minWidth: '760px', fontFamily: 'var(--font-body)', fontSize: '14px' }}
        role="img"
        aria-label="Pipeline phase sequence swimlane — L3 detail view"
      >
        <defs>
          <marker id="sl-arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
            <polygon points="0 0, 8 3, 0 6" fill="var(--c-rule)" />
          </marker>
          <filter id="sl-shadow" x="-5%" y="-10%" width="110%" height="120%">
            <feDropShadow dx="0" dy="1" stdDeviation="1" floodOpacity="0.10" />
          </filter>
          {/* Stripe pattern for future-state rows */}
          <pattern id="future-stripe" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="6" stroke="var(--c-amber)" strokeWidth="1" strokeOpacity="0.25" />
          </pattern>
        </defs>

        {/* ── Header row ── */}
        <rect x={0} y={0} width={TOTAL_W} height={HEADER_H} fill="var(--c-bg-sunken)" />
        {HEADERS.map((h) => (
          <text
            key={h.label}
            x={h.x + 10}
            y={HEADER_H - 10}
            fill="var(--c-ink-muted)"
            fontSize="12"
            fontWeight="600"
            letterSpacing="0.06em"
            style={{ textTransform: 'uppercase' }}
          >
            {h.label.toUpperCase()}
          </text>
        ))}
        <line x1={0} y1={HEADER_H} x2={TOTAL_W} y2={HEADER_H} stroke="var(--c-rule)" strokeWidth="1.5" />

        {/* ── Phase rows ── */}
        {rowLayouts.map((row, i) => {
          const mid = row.y + row.h / 2;
          const isAlt = i % 2 === 1 && !row.isGate;

          return (
            <g key={row.id}>
              {/* Row background */}
              <rect
                x={0}
                y={row.y}
                width={TOTAL_W}
                height={row.h}
                fill={row.isGate ? COST_FILLS.gate : isAlt ? 'var(--c-bg-sunken)' : 'var(--c-bg-card)'}
                opacity={0.7}
              />
              {/* Cost-tier fill overlay on service+model columns */}
              {!row.isGate && (
                <rect
                  x={xService}
                  y={row.y + 2}
                  width={COL_SERVICE + COL_MODEL + COL_COST}
                  height={row.h - 4}
                  fill={COST_FILLS[row.cost]}
                  rx={3}
                />
              )}
              {/* Future-state stripe overlay */}
              {row.isFuture && (
                <rect
                  x={0}
                  y={row.y}
                  width={TOTAL_W}
                  height={row.h}
                  fill="url(#future-stripe)"
                />
              )}

              {/* Gate: full-width banner */}
              {row.isGate ? (
                <>
                  <rect
                    x={6}
                    y={row.y + 4}
                    width={TOTAL_W - 12}
                    height={row.h - 8}
                    rx={4}
                    fill="none"
                    stroke="var(--c-diag-gate)"
                    strokeWidth="1.5"
                    strokeDasharray="5,3"
                    filter="url(#sl-shadow)"
                  />
                  {/* Gate icon */}
                  <text x={16} y={mid + 5} fontSize="18" fill="var(--c-diag-gate)">✋</text>
                  {/* Gate label */}
                  <text x={46} y={mid - 6} fontSize="15" fontWeight="700" fill="var(--c-diag-gate)">
                    {row.label}
                  </text>
                  <text x={46} y={mid + 12} fontSize="13" fill="var(--c-ink-dim)">
                    {row.note}
                  </text>
                  {/* Gate badge */}
                  <rect x={TOTAL_W - 120} y={mid - 14} width={110} height={22} rx={4} fill="var(--c-diag-gate)" opacity={0.12} />
                  <text x={TOTAL_W - 65} y={mid + 3} fontSize="12" fontWeight="600" fill="var(--c-diag-gate)" textAnchor="middle">
                    HUMAN HALT
                  </text>
                </>
              ) : (
                <>
                  {/* Phase ID badge */}
                  <rect
                    x={xPhase + 6}
                    y={row.y + (row.h - 24) / 2}
                    width={COL_PHASE - 14}
                    height={24}
                    rx={3}
                    fill={VENDOR_COLORS[row.vendor]}
                    opacity={0.15}
                  />
                  <text
                    x={xPhase + COL_PHASE / 2}
                    y={mid + 5}
                    fontSize="11"
                    fontWeight="700"
                    fill={VENDOR_COLORS[row.vendor]}
                    textAnchor="middle"
                  >
                    {row.id}
                  </text>

                  {/* Phase name */}
                  <text x={xName + 10} y={mid - (row.note ? 6 : 0)} fontSize="14" fontWeight="600" fill="var(--c-ink)">
                    {row.label}
                  </text>
                  {/* Future-state badge */}
                  {row.isFuture && (
                    <>
                      <rect x={xName + 10} y={mid + 8} width={46} height={14} rx={3} fill="var(--c-amber)" opacity={0.18} />
                      <text x={xName + 33} y={mid + 19} fontSize="10" fontWeight="700" fill="var(--c-amber)" textAnchor="middle">
                        FUTURE
                      </text>
                    </>
                  )}

                  {/* Service */}
                  <text x={xService + 10} y={mid + 5} fontSize="13" fill="var(--c-ink-dim)">
                    {row.service}
                  </text>

                  {/* Model pill */}
                  {row.model !== '—' && (
                    <>
                      <rect
                        x={xModel + 8}
                        y={mid - 11}
                        width={COL_MODEL - 16}
                        height={22}
                        rx={11}
                        fill={MODEL_COLORS[row.model] ?? 'var(--c-model-sonnet)'}
                        opacity={0.18}
                      />
                      <text
                        x={xModel + COL_MODEL / 2}
                        y={mid + 4}
                        fontSize="12"
                        fontWeight="600"
                        fill={MODEL_COLORS[row.model] ?? 'var(--c-model-sonnet)'}
                        textAnchor="middle"
                      >
                        {row.model}
                      </text>
                    </>
                  )}
                  {row.model === '—' && (
                    <text x={xModel + COL_MODEL / 2} y={mid + 5} fontSize="12" fill="var(--c-model-none)" textAnchor="middle">
                      —
                    </text>
                  )}

                  {/* Cost chip */}
                  <text
                    x={xCost + COL_COST / 2}
                    y={mid + 5}
                    fontSize="11"
                    fontWeight="600"
                    fill={
                      row.cost === 'high' ? 'var(--c-red)' :
                      row.cost === 'mid'  ? 'var(--c-amber)' :
                      row.cost === 'low'  ? 'var(--c-green)' :
                      'var(--c-ink-muted)'
                    }
                    textAnchor="middle"
                  >
                    {COST_LABELS[row.cost]}
                  </text>

                  {/* Note */}
                  {row.note && (
                    <foreignObject x={xNote + 8} y={row.y + 4} width={COL_NOTE - 16} height={row.h - 8}>
                      <div
                        xmlns="http://www.w3.org/1999/xhtml"
                        style={{
                          fontSize: '12px',
                          color: 'var(--c-ink-muted)',
                          lineHeight: '1.4',
                          display: 'flex',
                          alignItems: 'center',
                          height: '100%',
                        }}
                      >
                        {row.note}
                      </div>
                    </foreignObject>
                  )}
                </>
              )}

              {/* Row divider */}
              <line x1={0} y1={row.y + row.h} x2={TOTAL_W} y2={row.y + row.h} stroke="var(--c-rule-soft)" strokeWidth="0.75" />
            </g>
          );
        })}

        {/* Column dividers */}
        {[xName, xService, xModel, xCost, xNote].map((x) => (
          <line key={x} x1={x} y1={0} x2={x} y2={totalH} stroke="var(--c-rule-soft)" strokeWidth="0.75" />
        ))}

        {/* Outer border */}
        <rect x={0} y={0} width={TOTAL_W} height={totalH} fill="none" stroke="var(--c-rule)" strokeWidth="1" rx={3} />
      </svg>

      {/* Legend */}
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '16px',
        marginTop: '14px',
        fontSize: '13px',
        color: 'var(--c-ink-dim)',
      }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ width: 28, height: 10, background: 'var(--c-tokens-low)', display: 'inline-block', borderRadius: 2 }} />
          Low-cost LLM call
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ width: 28, height: 10, background: 'var(--c-tokens-mid)', display: 'inline-block', borderRadius: 2 }} />
          Medium-cost
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ width: 28, height: 10, background: 'var(--c-tokens-high)', display: 'inline-block', borderRadius: 2 }} />
          High-cost (Opus)
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ width: 28, height: 10, background: 'url(#future-stripe)', display: 'inline-block', borderRadius: 2, border: '1px dashed var(--c-amber)' }} />
          Future-state phase (not yet shipped)
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ fontSize: '16px' }}>✋</span>
          Human-halt gate
        </span>
      </div>
    </div>
  );
}
