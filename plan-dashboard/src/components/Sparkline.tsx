interface Props {
  values: number[];
  vendor?: 'anthropic' | 'google' | 'azure' | 'github';
  width?: number;
  height?: number;
}

export default function Sparkline({ values, vendor = 'anthropic', width = 220, height = 32 }: Props) {
  if (!values || values.length === 0) return null;
  const max = Math.max(...values, 0.001);
  const min = Math.min(...values, 0);
  const range = max - min || 1;
  const stepX = width / Math.max(values.length - 1, 1);
  const path = values
    .map((v, i) => {
      const x = i * stepX;
      const y = height - ((v - min) / range) * (height - 2) - 1;
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
  const klass = `spark is-${vendor}`;
  return (
    <svg className={klass} width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Last thirty days of spend">
      <line className="axis" x1={0} y1={height - 1} x2={width} y2={height - 1} />
      <path d={path} />
    </svg>
  );
}
