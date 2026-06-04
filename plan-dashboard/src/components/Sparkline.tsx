interface Props {
  values: number[];
  vendor?: 'anthropic' | 'google' | 'azure' | 'github';
}

const WIDTH = 220;
const HEIGHT = 32;

export default function Sparkline({ values, vendor = 'anthropic' }: Props) {
  if (!values || values.length === 0) return null;
  const max = Math.max(...values, 0.001);
  const min = Math.min(...values, 0);
  const range = max - min || 1;
  const stepX = WIDTH / Math.max(values.length - 1, 1);
  const path = values
    .map((v, i) => {
      const x = i * stepX;
      const y = HEIGHT - ((v - min) / range) * (HEIGHT - 2) - 1;
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
  const klass = `spark is-${vendor}`;
  return (
    <svg className={klass} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-labelledby="sparkline-title sparkline-desc">
      <title id="sparkline-title">Last thirty days of spend</title>
      <desc id="sparkline-desc">A sparkline showing how spend changed over the last thirty days.</desc>
      <line className="axis" x1={0} y1={HEIGHT - 1} x2={WIDTH} y2={HEIGHT - 1} />
      <path d={path} />
    </svg>
  );
}
