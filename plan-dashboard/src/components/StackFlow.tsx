import VendorLogo from './VendorLogo';

/**
 * The horizontal stack-flow diagram for the infrastructure view.
 *
 * Five lanes left to right. A book PDF enters on the left, an audio podcast
 * leaves on the right. Each lane between is a vendor; each card under the
 * vendor names the specific service that handles its slice.
 *
 * Pure SVG. All sizing, colors, fonts come from theme.css.
 */
export default function StackFlow() {
  const W = 1240, H = 380;

  // Lane geometry — 5 lanes, evenly spaced
  const lanes = [
    { x: 100, label: 'Input', vendor: 'source' as const, name: 'Source PDF', services: ['Scanned book', 'Any language'] },
    { x: 340, label: 'Step 1 · Read', vendor: 'azure' as const, name: 'Microsoft Azure', services: ['Document Intelligence', 'Translator', 'Speech'] },
    { x: 620, label: 'Step 2 · Think', vendor: 'anthropic' as const, name: 'Anthropic', services: ['Claude Opus', 'Claude Sonnet', 'Claude Haiku'] },
    { x: 900, label: 'Step 3 · Voice', vendor: 'notebooklm' as const, name: 'NotebookLM', services: ['Audio Overview'] },
    { x: 1140, label: 'Output', vendor: 'output' as const, name: 'Published podcast', services: ['Catalog + RSS'] },
  ];

  const LANE_W = 200, CARD_X_OFFSET = -LANE_W / 2;
  const LANE_Y = 60;
  const CONNECT_Y = LANE_Y + 110;

  return (
    <svg className="svg-host stack-flow" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Stack flow from input book to published podcast">
      <defs>
        <marker id="sf-arrow" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto" className="arrow-strong">
          <polygon points="0 0, 10 3.5, 0 7" />
        </marker>
      </defs>

      {/* Connector arrows between lanes */}
      {lanes.slice(0, -1).map((lane, i) => {
        const next = lanes[i + 1];
        const x1 = lane.x + 56;
        const x2 = next.x - 56;
        return (
          <g key={`c-${i}`}>
            <line x1={x1} y1={CONNECT_Y} x2={x2 - 4} y2={CONNECT_Y} className="edge is-strong" markerEnd="url(#sf-arrow)" />
            <text x={(x1 + x2) / 2} y={CONNECT_Y - 10} className="label-eyebrow flow-label" textAnchor="middle">
              {i === 0 ? 'pages' : i === 1 ? 'clean text' : i === 2 ? 'framing' : 'audio'}
            </text>
          </g>
        );
      })}

      {lanes.map((lane) => {
        const cardX = lane.x + CARD_X_OFFSET;
        return (
          <g key={lane.label}>
            {/* Step label above */}
            <text x={lane.x} y={LANE_Y - 10} className="label-eyebrow flow-step-label" textAnchor="middle">{lane.label}</text>

            {/* Vendor logo centered on lane */}
            <g transform={`translate(${lane.x - 28}, ${LANE_Y + 80})`}>
              <VendorLogo vendor={lane.vendor} size={56} />
            </g>

            {/* Vendor name */}
            <text x={lane.x} y={LANE_Y + 160} className="t-vendor-head">{lane.name}</text>

            {/* Service list */}
            <rect x={cardX} y={LANE_Y + 175} width={LANE_W} height={lane.services.length * 22 + 14} rx={8} className="node-card flow-card" />
            {lane.services.map((svc, j) => (
              <text key={svc} x={lane.x} y={LANE_Y + 195 + j * 22} className="flow-service" textAnchor="middle">{svc}</text>
            ))}
          </g>
        );
      })}
    </svg>
  );
}
