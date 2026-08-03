/* The three candidate marks, built as real SVG so they can be judged in situ
 * rather than from a picture. Asif picks one; `DEFAULT_MARK` in ./Logo.tsx is
 * the single line that changes.
 *
 * All three: pure geometry, no gradients, no raster, no figurative content, and
 * nothing borrowed from sacred textual apparatus. The mark inherits
 * `currentColor` so it works on every theme; accent parts reference --l-accent.
 */

export type MarkProps = {
  /** Rendered size in px. The viewBox is square, so this is width and height. */
  size?: number;
  className?: string;
  /** Drop the interlacing / thin detail that collapses below ~24px. */
  compact?: boolean;
};

/* ── Concept 1 — Strapwork ────────────────────────────────────────────────
 * An eight-fold girih knot reduced to a single interlaced ribbon: two implied
 * squares drawn only as line, never as fill. The strands alternate over and
 * under — the breaks in the octagon are what read as "under", so no background
 * colour is faked anywhere and the mark sits correctly on any surface.
 * The continuous line is a quiet metaphor for an unbroken chain of narration.
 */
export function Strapwork({ size = 40, className, compact = false }: MarkProps) {
  // The octagon's crossings sit only ~21 units apart, so the break that reads
  // as "this strand passes under" has to be won carefully: too narrow and the
  // mark reads as a cog rather than a weave. A 13-unit break against a 5-unit
  // stroke leaves ~8 units of ribbon between the two breaks on each edge.
  const stroke = compact ? 7 : 5;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 96 96"
      fill="none"
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M84 48 L48 84 L12 48 L48 12 Z"
        stroke="currentColor"
        strokeWidth={stroke}
        strokeLinejoin="round"
      />
      {compact ? (
        <rect
          x="22.54"
          y="22.54"
          width="50.92"
          height="50.92"
          stroke="currentColor"
          strokeWidth={stroke}
          strokeLinejoin="round"
        />
      ) : (
        <>
          <path
            d="M65.04 22.54 L73.46 22.54 L73.46 73.46 L65.04 73.46"
            stroke="currentColor"
            strokeWidth={stroke}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
          <path
            d="M30.96 22.54 L22.54 22.54 L22.54 73.46 L30.96 73.46"
            stroke="currentColor"
            strokeWidth={stroke}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
          <path
            d="M43.96 22.54 L52.04 22.54"
            stroke="currentColor"
            strokeWidth={stroke}
            strokeLinecap="round"
          />
          <path
            d="M43.96 73.46 L52.04 73.46"
            stroke="currentColor"
            strokeWidth={stroke}
            strokeLinecap="round"
          />
        </>
      )}
      <circle cx="48" cy="48" r={compact ? 10 : 9} fill="var(--l-accent)" />
    </svg>
  );
}

/* ── Concept 2 — Colophon ─────────────────────────────────────────────────
 * Sound becoming text: five rounded bars on a shared baseline (a level meter),
 * whose rhythm continues to the right as three rules of decreasing length (a
 * paragraph). Eight rectangles, one optical baseline. Says "podcast" and "book"
 * in one glyph with no cultural risk, and survives a 16px reduction intact.
 * `playing` animates the bars, so the header mark doubles as a transport state.
 */
export function Colophon({
  size = 40,
  className,
  compact = false,
  playing = false,
}: MarkProps & { playing?: boolean }) {
  const bars = compact
    ? [
        { x: 8, h: 30, y: 44 },
        { x: 24, h: 58, y: 16 },
        { x: 40, h: 40, y: 34 },
      ]
    : [
        { x: 6, h: 22, y: 52 },
        { x: 18, h: 42, y: 32 },
        { x: 30, h: 58, y: 16 },
        { x: 42, h: 34, y: 40 },
        { x: 54, h: 14, y: 60 },
      ];
  const rules = compact
    ? [
        { y: 58, w: 26 },
        { y: 70, w: 18 },
      ]
    : [
        { y: 54, w: 22 },
        { y: 62, w: 17 },
        { y: 70, w: 12 },
      ];
  const barW = compact ? 10 : 8;
  const ruleX = compact ? 60 : 70;

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 96 96"
      className={`${className ?? ""}${playing ? " is-playing" : ""}`}
      aria-hidden="true"
      focusable="false"
    >
      {bars.map((b, i) => (
        <rect
          key={b.x}
          x={b.x}
          y={b.y}
          width={barW}
          height={b.h}
          rx={barW / 2}
          fill="currentColor"
          style={playing ? { animationDelay: `${i * 110}ms` } : undefined}
        />
      ))}
      {rules.map((r) => (
        <rect
          key={r.y}
          x={ruleX}
          y={r.y}
          width={r.w}
          height={4}
          rx={2}
          fill="var(--l-accent)"
        />
      ))}
    </svg>
  );
}

/* ── Concept 3 — Qalam ────────────────────────────────────────────────────
 * A reed pen nib abstracted to a single oblique parallelogram split by its
 * slit, at the head of three rules. Read one way it is a pen starting a
 * paragraph; read another, a playhead at the head of a track. The instrument of
 * the manuscript tradition, and a tool rather than a being.
 */
export function Qalam({ size = 40, className, compact = false }: MarkProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 96 96"
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      <polygon points="28,16 38,16 20,72 10,72" fill="currentColor" />
      <polygon points="42,16 52,16 34,72 24,72" fill="currentColor" />
      {(compact
        ? [
            { y: 52, w: 34 },
            { y: 66, w: 24 },
          ]
        : [
            { y: 46, w: 32 },
            { y: 58, w: 24 },
            { y: 70, w: 16 },
          ]
      ).map((r) => (
        <rect key={r.y} x={58} y={r.y} width={r.w} height={4} rx={2} fill="currentColor" />
      ))}
    </svg>
  );
}
