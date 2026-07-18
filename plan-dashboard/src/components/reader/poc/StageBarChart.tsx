import type { StageKind } from "../../../lib/reader/stage-roles";

export interface StageBar {
  label: string;
  value: number;
  kind: StageKind;
}

interface Props {
  bars: StageBar[];
}

/**
 * Words-per-stage bar chart for the Studio transformation dashboard. Plots only
 * the stages captured for this chapter, so the heights honestly track how the
 * text grew and shrank through the pipeline. Adapts the SpendChart SVG idiom:
 * viewBox-only sizing, zero baseline, live <text>, accessibility triple; all
 * colours come from theme tokens via CSS classes (no inline styling).
 */
export default function StageBarChart({ bars }: Props) {
  if (!bars || bars.length === 0) return null;
  const W = 640,
    H = 260;
  const PAD_L = 58,
    PAD_R = 16,
    PAD_T = 26,
    PAD_B = 52;
  const plotW = W - PAD_L - PAD_R;
  const plotH = H - PAD_T - PAD_B;
  const baseY = PAD_T + plotH;
  const max = Math.max(...bars.map((b) => b.value), 1);
  const slot = plotW / bars.length;
  const barW = Math.min(slot * 0.6, 90);
  const ticks = [0.25, 0.5, 0.75, 1];

  return (
    <svg
      className="svg-host sbc"
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-labelledby="sbc-title sbc-desc"
    >
      <title id="sbc-title">Words at each captured pipeline stage</title>
      <desc id="sbc-desc">
        A vertical bar chart of the word count at each transformation stage that
        was captured for this chapter, from earliest to the editable review.
      </desc>

      {/* Gridlines + y-axis value labels (zero baseline). */}
      {ticks.map((f, i) => {
        const y = baseY - plotH * f;
        return (
          <g key={i}>
            <line
              className="sbc-grid"
              x1={PAD_L}
              y1={y}
              x2={W - PAD_R}
              y2={y}
            />
            <text className="sbc-axis" x={PAD_L - 6} y={y + 4} textAnchor="end">
              {Math.round(max * f).toLocaleString()}
            </text>
          </g>
        );
      })}

      {/* Axes + explicit zero baseline label (honest-chart convention). */}
      <line
        className="sbc-axis-line"
        x1={PAD_L}
        y1={baseY}
        x2={W - PAD_R}
        y2={baseY}
      />
      <line
        className="sbc-axis-line"
        x1={PAD_L}
        y1={PAD_T}
        x2={PAD_L}
        y2={baseY}
      />
      <text className="sbc-axis" x={PAD_L - 6} y={baseY + 4} textAnchor="end">
        0
      </text>

      {/* Bars + value + stage labels. */}
      {bars.map((b, i) => {
        const h = (plotH * b.value) / max;
        const cx = PAD_L + slot * i + slot / 2;
        const x = cx - barW / 2;
        const y = baseY - h;
        return (
          <g key={b.label}>
            <rect
              className={`sbc-bar sbc-bar--${b.kind}`}
              x={x}
              y={y}
              width={barW}
              height={Math.max(h, 1)}
              rx={2}
            />
            <text className="sbc-value" x={cx} y={y - 6} textAnchor="middle">
              {b.value.toLocaleString()}
            </text>
            <text
              className="sbc-xlabel"
              x={cx}
              y={baseY + 18}
              textAnchor="middle"
            >
              {b.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
