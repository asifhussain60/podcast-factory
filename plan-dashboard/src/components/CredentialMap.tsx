/**
 * CredentialMap — L4 Credentials & Auth Boundary Map
 *
 * Bipartite layout:
 *   Left column:  Where every secret lives (storage location)
 *   Right column: Which external service it authorises
 *   Arrows:       Coloured by risk tier (green=low / amber=managed / red=attention)
 *
 * Audience: Architect / security reviewer.
 * Pure SVG — no external deps.
 */

interface Cred {
  id: string;
  storage: string;       // e.g. "macOS Keychain"
  key: string;           // credential label
  risk: 'low' | 'managed' | 'attention';
  service: string;       // right-side target
  serviceColor: string;
  note?: string;
}

const CREDS: Cred[] = [
  {
    id: 'anthropic-key',
    storage: '.env file (git-ignored)',
    key: 'ANTHROPIC_API_KEY',
    risk: 'managed',
    service: 'Anthropic API',
    serviceColor: 'var(--c-vendor-anthropic)',
    note: 'No rotation policy — manual. Rotated on suspicion.',
  },
  {
    id: 'azure-speech',
    storage: '.env file (git-ignored)',
    key: 'AZURE_SPEECH_KEY',
    risk: 'managed',
    service: 'Azure Speech',
    serviceColor: 'var(--c-vendor-azure)',
    note: 'Azure portal key — 90-day recommended rotation.',
  },
  {
    id: 'azure-docintel',
    storage: '.env file (git-ignored)',
    key: 'AZURE_DOCINTEL_KEY',
    risk: 'managed',
    service: 'Azure Document Intelligence',
    serviceColor: 'var(--c-vendor-azure)',
    note: 'Same rotation recommendation as speech key.',
  },
  {
    id: 'azure-translator',
    storage: '.env file (git-ignored)',
    key: 'AZURE_TRANSLATOR_KEY',
    risk: 'managed',
    service: 'Azure Translator',
    serviceColor: 'var(--c-vendor-azure)',
    note: 'Shared or dedicated resource key.',
  },
  {
    id: 'github-pat',
    storage: '.env file (git-ignored)',
    key: 'GITHUB_TOKEN',
    risk: 'attention',
    service: 'GitHub',
    serviceColor: 'var(--c-vendor-github)',
    note: 'PAT with repo write scope — highest privilege here.',
  },
  {
    id: 'google-session',
    storage: 'Browser session (no local key)',
    key: '(browser cookie)',
    risk: 'low',
    service: 'Google / NotebookLM',
    serviceColor: 'var(--c-vendor-google)',
    note: 'Human-only surface. No API key stored on disk.',
  },
];

const RISK_COLORS: Record<Cred['risk'], string> = {
  low:       'var(--c-diag-local)',
  managed:   'var(--c-diag-managed)',
  attention: 'var(--c-diag-external)',
};

const RISK_LABELS: Record<Cred['risk'], string> = {
  low:       'Low — no secret on disk',
  managed:   'Managed — .env, git-ignored',
  attention: 'Attention — high-privilege key',
};

export default function CredentialMap() {
  const W = 900;
  const LEFT_X = 60;
  const RIGHT_X = 640;
  const COL_W = 220;
  const ROW_H = 62;
  const HEADER_H = 40;

  const totalH = HEADER_H + CREDS.length * ROW_H + 20;

  return (
    <div className="overflow-x-auto w-full">
      <svg
        viewBox={`0 0 ${W} ${totalH}`}
        className="w-full"
        style={{ minWidth: '560px' }}
        role="img"
        aria-label="Credential and auth boundary map — where secrets live and what they authorise"
      >
        <defs>
          {['low', 'managed', 'attention'].map((r) => (
            <marker key={`cm-${r}`} id={`cm-arr-${r}`} markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
              <polygon points="0 0, 7 2.5, 0 5" fill={RISK_COLORS[r as Cred['risk']]} />
            </marker>
          ))}
        </defs>

        {/* Column headers */}
        <rect x={LEFT_X - 8} y={0} width={COL_W + 16} height={HEADER_H} rx={4}
          fill="var(--c-bg-sunken)" />
        <text x={LEFT_X + COL_W / 2} y={HEADER_H - 10} textAnchor="middle" fontSize="12" fontWeight="700"
          fill="var(--c-ink-muted)" letterSpacing="0.06em">
          WHERE IT LIVES
        </text>

        <rect x={RIGHT_X - 8} y={0} width={COL_W + 16} height={HEADER_H} rx={4}
          fill="var(--c-bg-sunken)" />
        <text x={RIGHT_X + COL_W / 2} y={HEADER_H - 10} textAnchor="middle" fontSize="12" fontWeight="700"
          fill="var(--c-ink-muted)" letterSpacing="0.06em">
          WHAT IT AUTHORISES
        </text>

        {/* Middle column header — pipeline surface */}
        <text x={W / 2} y={HEADER_H - 10} textAnchor="middle" fontSize="11" fill="var(--c-ink-muted)">
          used by Pipeline
        </text>

        {CREDS.map((c, i) => {
          const y = HEADER_H + i * ROW_H + 4;
          const midY = y + ROW_H / 2 - 4;
          const riskColor = RISK_COLORS[c.risk];

          return (
            <g key={c.id}>
              {/* Left card — storage */}
              <rect x={LEFT_X - 8} y={y} width={COL_W + 16} height={ROW_H - 8} rx={4}
                fill="var(--c-bg-card)" stroke={riskColor} strokeWidth="1.2" />
              {/* Risk indicator bar */}
              <rect x={LEFT_X - 8} y={y} width={4} height={ROW_H - 8} rx={3} fill={riskColor} />
              <text x={LEFT_X + 4} y={y + 20} fontSize="11" fontWeight="700" fill="var(--c-ink)">
                {c.key}
              </text>
              <text x={LEFT_X + 4} y={y + 36} fontSize="11" fill="var(--c-ink-muted)">
                {c.storage}
              </text>

              {/* Arrow through middle */}
              <line
                x1={LEFT_X + COL_W + 10}
                y1={midY}
                x2={RIGHT_X - 16}
                y2={midY}
                stroke={riskColor}
                strokeWidth="1.5"
                markerEnd={`url(#cm-arr-${c.risk})`}
              />
              {/* Note on arrow */}
              {c.note && (
                <foreignObject
                  x={LEFT_X + COL_W + 14}
                  y={midY - 22}
                  width={RIGHT_X - LEFT_X - COL_W - 40}
                  height={36}
                >
                  <div
                    xmlns="http://www.w3.org/1999/xhtml"
                    style={{
                      fontSize: '10px',
                      color: 'var(--c-ink-muted)',
                      lineHeight: '1.3',
                      textAlign: 'center',
                    }}
                  >
                    {c.note}
                  </div>
                </foreignObject>
              )}

              {/* Right card — service */}
              <rect x={RIGHT_X - 8} y={y} width={COL_W + 16} height={ROW_H - 8} rx={4}
                fill="var(--c-bg-card)" stroke={c.serviceColor} strokeWidth="1.2" />
              <rect x={RIGHT_X + COL_W + 8} y={y} width={4} height={ROW_H - 8} rx={3} fill={c.serviceColor} />
              <text x={RIGHT_X + 4} y={y + 24} fontSize="13" fontWeight="700" fill="var(--c-ink)">
                {c.service}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="flex flex-wrap gap-5 mt-3 text-sm" style={{ color: 'var(--c-ink-dim)' }}>
        {(['low', 'managed', 'attention'] as Cred['risk'][]).map((r) => (
          <span key={r} className="flex items-center gap-2">
            <span className="inline-block w-3 h-3 rounded-sm" style={{ background: RISK_COLORS[r] }} />
            {RISK_LABELS[r]}
          </span>
        ))}
      </div>
    </div>
  );
}
