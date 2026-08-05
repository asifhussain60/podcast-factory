import { useId } from "react";

/**
 * The Podcast Factory mark: an open book with a microphone standing in its gutter.
 *
 * This is a redrawing of `brand/podcast-factory-logo.png`, not a copy of it. The
 * raster cannot be used in the interface for two reasons: at 28px — the size the
 * reader's sticky header asks for — its 1px strokes turn to mush, and its navy
 * ink is very nearly invisible on the dark theme's #0b0f0e. Drawn as vector, the
 * two colours become `currentColor` and the accent token, so the mark inverts
 * with the palette and stays crisp at any size.
 *
 * The colour split follows the file: the left page and its waveform are the
 * accent (the logo's electric blue), the right page, its waveform and the
 * microphone are ink (the logo's deep navy).
 *
 * The microphone's grille is cut out with a mask rather than painted in white.
 * White would be right only on the light theme; a hole is right on all of them,
 * because whatever the mark is sitting on shows through.
 *
 * `compact` is for 24px and below, where the waveform bars and the grille slots
 * are smaller than a device pixel and read as dirt. It drops both and thickens
 * what remains, which is the same reduction the marks this replaces used.
 */
export function Mark({
  size = 40,
  compact = false,
  className,
}: {
  size?: number;
  compact?: boolean;
  className?: string;
}) {
  const slots = useId();

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 96 96"
      fill="none"
      aria-hidden="true"
      focusable="false"
      className={className}
    >
      <mask id={slots}>
        <rect width="96" height="96" fill="#fff" />
        {compact ? null : (
          <>
            <rect x="42.5" y="34" width="11" height="2.6" rx="1.3" />
            <rect x="42.5" y="40" width="11" height="2.6" rx="1.3" />
            <rect x="42.5" y="46" width="11" height="2.6" rx="1.3" />
          </>
        )}
      </mask>

      {/* ---- Left page, accent ------------------------------------------- */}
      <g
        stroke="var(--l-accent)"
        strokeWidth={compact ? 4 : 3}
        strokeLinejoin="round"
        strokeLinecap="round"
      >
        <path d="M13 20 L13 66 C27 69 39 74 46.5 80 L46.5 34 C39 28 27 23 13 20 Z" />
        {compact ? null : <path d="M8 26 L8 70" strokeWidth="4" />}
      </g>

      {/* ---- Right page, ink --------------------------------------------- */}
      <g
        stroke="currentColor"
        strokeWidth={compact ? 4 : 3}
        strokeLinejoin="round"
        strokeLinecap="round"
      >
        <path d="M83 20 L83 66 C69 69 57 74 49.5 80 L49.5 34 C57 28 69 23 83 20 Z" />
        {compact ? null : <path d="M88 26 L88 70" strokeWidth="4" />}
      </g>

      {/* ---- Waveform, one colour per page -------------------------------- */}
      {compact ? null : (
        <>
          <g fill="var(--l-accent)">
            <rect x="19" y="40" width="3" height="5" rx="1.5" />
            <rect x="25" y="35" width="3" height="15" rx="1.5" />
            <rect x="31" y="31" width="3" height="23" rx="1.5" />
            <rect x="37" y="36" width="3" height="13" rx="1.5" />
          </g>
          <g fill="currentColor">
            <rect x="56" y="36" width="3" height="13" rx="1.5" />
            <rect x="62" y="31" width="3" height="23" rx="1.5" />
            <rect x="68" y="35" width="3" height="15" rx="1.5" />
            <rect x="74" y="40" width="3" height="5" rx="1.5" />
          </g>
        </>
      )}

      {/* ---- Microphone, ink ---------------------------------------------- */}
      <g stroke="currentColor" strokeLinecap="round" fill="none">
        <rect
          x="40"
          y="24"
          width="16"
          height="34"
          rx="8"
          fill="currentColor"
          stroke="none"
          mask={`url(#${slots})`}
        />
        <path
          d="M34 46 L34 50 A14 14 0 0 0 62 50 L62 46"
          strokeWidth={compact ? 4 : 3.2}
        />
        <path d="M48 64 L48 74" strokeWidth={compact ? 4 : 3.2} />
        <path d="M39 75.5 L57 75.5" strokeWidth={compact ? 4 : 3.2} />
      </g>
    </svg>
  );
}
