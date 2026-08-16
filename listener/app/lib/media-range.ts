/**
 * A single HTTP byte range, which is all a media element ever asks for.
 *
 * Shared between `routes/media.$slug.$.tsx` (the R2-backed production and
 * fallback path) and `scripts/local-media-plugin.mts` (the disk-backed local
 * dev path, 2026-08-16) — the two need to answer the exact same "which bytes
 * did the browser ask for" question, and a scrubbed-through episode is where a
 * second, slightly different implementation would first show up as a glitch.
 * Plain TS with no Worker-only or Node-only imports, so it loads in both the
 * workerd bundle and the plain-Node Vite dev process.
 *
 * Returns null for an absent, malformed or unsatisfiable header — the caller
 * then serves the whole object, which is what a client that sent nonsense
 * deserves and what every media element handles.
 */
export function parseRange(
  header: string | null,
  size: number,
): { offset: number; length: number } | null {
  if (header === null) return null;

  const match = /^bytes=(\d*)-(\d*)$/.exec(header.trim());
  if (match === null) return null;

  const [, rawStart, rawEnd] = match;

  // `bytes=-500` means the LAST 500 bytes, not "from 0 to 500".
  if (rawStart === "") {
    const length = Number(rawEnd);
    if (!Number.isFinite(length) || length <= 0) return null;
    const capped = Math.min(length, size);
    return { offset: size - capped, length: capped };
  }

  const offset = Number(rawStart);
  if (!Number.isFinite(offset) || offset >= size) return null;

  const end = rawEnd === "" ? size - 1 : Math.min(Number(rawEnd), size - 1);
  if (!Number.isFinite(end) || end < offset) return null;

  return { offset, length: end - offset + 1 };
}
