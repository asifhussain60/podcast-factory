// svg-normalize.mjs — reduce an SVG to what identifies the DIAGRAM, ignoring platform-dependent geometry.
//
// Numbers INSIDE tags (attribute values: coordinates, sizes, path data, transforms) are replaced with `#`; text BETWEEN
// tags (labels, the <style> block) is kept exactly. So a coordinate that moved by a fraction of a pixel between Chromium
// on macOS and on Linux does not register, while a changed label, node, edge, ordering, class name or style does.

const TAG = /(<[^>]*>)/g;
const NUMBER = /-?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?/gi;

export function normalizeSvg(svg) {
  return svg
    .split(TAG)
    .map((part) => (part.startsWith("<") ? part.replace(NUMBER, "#") : part))
    .join("")
    .replace(/>\s+</g, "><")
    .trim();
}

/** Where two SVGs first diverge, with a little context from each — or null when they are identical. For the check's
 *  failure output: "STALE" alone says nothing about WHAT differs, which is what made this hard to diagnose from CI. */
export function describeDifference(committed, rendered, context = 90) {
  const a = normalizeSvg(committed);
  const b = normalizeSvg(rendered);
  if (a === b) return null;
  let i = 0;
  while (i < a.length && i < b.length && a[i] === b[i]) i += 1;
  const from = Math.max(0, i - 30);
  return {
    index: i,
    committed: a.slice(from, i + context),
    rendered: b.slice(from, i + context),
  };
}
