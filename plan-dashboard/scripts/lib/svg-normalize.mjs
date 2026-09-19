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
