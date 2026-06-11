import { useId } from 'react';

interface Props {
  values: number[];
  vendor?: 'anthropic' | 'google' | 'azure' | 'github';
}

const WIDTH = 220;
const HEIGHT = 32;

export default function Sparkline({ values, vendor = 'anthropic' }: Props) {
  // Per-instance IDs: this component renders once per vendor service, and
  // duplicate ids would leave every instance after the first unlabelled to AT.
  const uid = useId();
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
  const titleId = `${uid}-title`;
  const descId = `${uid}-desc`;
  return (
    <svg className={klass} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-labelledby={`${titleId} ${descId}`}>
      <title id={titleId}>Last thirty days of spend</title>
      <desc id={descId}>A sparkline showing how spend changed over the last thirty days.</desc>
      <line className="axis" x1={0} y1={HEIGHT - 1} x2={WIDTH} y2={HEIGHT - 1} />
      <path d={path} />
    </svg>
  );
}
