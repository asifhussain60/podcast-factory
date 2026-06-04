interface Layer { id: number; name: string; plain: string; }
interface Props { layers: Layer[]; }

export default function LayerStack({ layers }: Props) {
  const W = 760, ROW = 64, H = layers.length * (ROW + 12) + 40;
  return (
    <svg className="svg-host" viewBox={`0 0 ${W} ${H}`} role="img" aria-labelledby="layer-stack-title layer-stack-desc">
      <title id="layer-stack-title">The six layers, bottom to top</title>
      <desc id="layer-stack-desc">A stacked diagram showing the six system layers from the bottom up.</desc>
      <defs>
        <marker id="arrow-up" markerWidth="8" markerHeight="6" refX="4" refY="3" orient="auto" className="arrow-soft">
          <polygon points="0 6, 4 0, 8 6" />
        </marker>
      </defs>
      {layers.slice().reverse().map((l, i) => {
        const y = 20 + i * (ROW + 12);
        return (
          <g key={l.id}>
            <rect className="node-card" x={20} y={y} width={W - 40} height={ROW} rx={8} />
            <text x={40} y={y + 22} className="t-title">Layer {l.id} · {l.name}</text>
            <text x={40} y={y + 44} className="label-sm">{l.plain}</text>
            {i < layers.length - 1 && (
              <line className="edge" x1={W / 2} y1={y + ROW} x2={W / 2} y2={y + ROW + 12} markerEnd="url(#arrow-up)" />
            )}
          </g>
        );
      })}
    </svg>
  );
}
