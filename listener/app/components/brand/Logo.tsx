import { Mark } from "./mark";

/**
 * The site's identity, in one component.
 *
 * There used to be three candidate marks here behind a `DEFAULT_MARK` switch and
 * a `/brand` page to compare them on. The mark is chosen now — it is the one in
 * `brand/podcast-factory-logo.png` — so the switch, the alternatives and the
 * comparison page are gone.
 *
 * The wordmark is set rather than drawn. Keeping it as live text means it takes
 * the theme's ink and accent, scales with the mark instead of pixelating, and
 * stays selectable and translatable; the logo file's own lettering is a geometric
 * sans that IBM Plex Sans sits close enough to at these sizes.
 */
export function Logo({
  size = 40,
  wordmark = true,
}: {
  size?: number;
  /** Hide the lettering where there is no room for it — a favicon-like slot. */
  wordmark?: boolean;
}) {
  return (
    <span className="pf-logo" style={{ "--pf-logo-size": `${size}px` } as React.CSSProperties}>
      <Mark size={size} compact={size <= 24} />

      {wordmark ? (
        <span className="pf-logo__word" aria-hidden="true">
          <span className="pf-logo__word-a">Podcast</span>
          <span className="pf-logo__word-b">Factory</span>
        </span>
      ) : null}

      {/* The lettering above is aria-hidden, so the name is announced exactly
          once whether or not it is on screen. */}
      <span className="sr-only">Podcast Factory</span>
    </span>
  );
}
