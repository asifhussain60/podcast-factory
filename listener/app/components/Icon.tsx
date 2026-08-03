import type { IconDefinition } from "@fortawesome/free-solid-svg-icons";

/**
 * A Font Awesome icon, rendered as inline SVG.
 *
 * This deliberately does NOT use `@fortawesome/react-fontawesome`. That package
 * pulls in `fontawesome-svg-core`, which carries a global icon library, a CSS
 * injector and a DOM watcher — machinery for looking icons up by name at
 * runtime. Every icon on this site is known at build time, so none of it earns
 * its bytes. Importing the definitions directly lets the bundler drop every
 * glyph we do not name; what ships is the handful of path strings below and
 * this component.
 *
 * It also cannot be a webfont. Font Awesome's icon fonts are ~100 KB per style
 * for a set we use nine glyphs from, and this site self-hosts everything — a
 * CDN link is not on the table.
 *
 * Sized in `em` so an icon always matches the text it sits beside: put one in a
 * pill and it is pill-sized, put one in a heading and it is heading-sized, with
 * nothing to keep in sync.
 *
 * Decorative by default. These icons sit NEXT to their own label everywhere
 * they appear — never instead of it — so announcing them would make a screen
 * reader read every fact twice. Pass a `title` only where an icon genuinely
 * stands alone.
 */
export function Icon({
  icon,
  title,
  className,
}: {
  icon: IconDefinition;
  /** Give the icon an accessible name. Omit when a visible label is adjacent. */
  title?: string;
  className?: string;
}) {
  const [width, height, , , path] = icon.icon;
  const d = Array.isArray(path) ? path.join(" ") : path;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className={className === undefined ? "pf-icon" : `pf-icon ${className}`}
      fill="currentColor"
      role={title === undefined ? "presentation" : "img"}
      aria-hidden={title === undefined ? true : undefined}
      aria-label={title}
      focusable="false"
    >
      <path d={d} />
    </svg>
  );
}
