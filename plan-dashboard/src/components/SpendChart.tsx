interface Props { values: number[]; }

export default function SpendChart({ values }: Props) {
  const W = 760, H = 200, PAD = 32;
  if (!values || values.length === 0) return null;
  const max = Math.max(...values, 0.001);
  const barW = (W - PAD * 2) / values.length;
  return (
    <svg className="svg-host spend-chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Last thirty days of combined spend">
      <line className="edge" x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} />
      <line className="edge" x1={PAD} y1={PAD} x2={PAD} y2={H - PAD} />
      {[0.25, 0.5, 0.75, 1].map((f, i) => {
        const y = H - PAD - (H - PAD * 2) * f;
        return (
          <g key={i}>
            <line className="edge is-dashed" x1={PAD} y1={y} x2={W - PAD} y2={y} />
            <text x={PAD - 6} y={y + 4} className="label-sm chart-axis-lbl">${(max * f).toFixed(0)}</text>
          </g>
        );
      })}
      {values.map((v, i) => {
        const h = ((H - PAD * 2) * v) / max;
        const x = PAD + i * barW + 1;
        const y = H - PAD - h;
        return <rect key={i} x={x} y={y} width={Math.max(barW - 2, 1)} height={Math.max(h, 0)} className="spend-bar" />;
      })}
      <text x={PAD} y={H - 8} className="label-sm">30 days ago</text>
      <text x={W - PAD} y={H - 8} className="label-sm chart-axis-end">today</text>
    </svg>
  );
}
