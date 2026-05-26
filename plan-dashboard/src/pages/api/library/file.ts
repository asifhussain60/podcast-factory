import type { APIRoute } from 'astro';
import { readFile, stat } from 'node:fs/promises';
import { extname, join, normalize, resolve } from 'node:path';
import { findContent } from '../../../lib/content-paths';

export const prerender = false;

const TEXT_EXTS = new Set(['md', 'txt', 'yml', 'yaml', 'json', 'jsonl', 'html', 'csv', 'log']);
const MIME: Record<string, string> = {
  md: 'text/markdown; charset=utf-8',
  txt: 'text/plain; charset=utf-8',
  yml: 'text/plain; charset=utf-8',
  yaml: 'text/plain; charset=utf-8',
  json: 'application/json; charset=utf-8',
  jsonl: 'application/jsonl; charset=utf-8',
  html: 'text/html; charset=utf-8',
  csv: 'text/csv; charset=utf-8',
  log: 'text/plain; charset=utf-8',
  pdf: 'application/pdf',
  m4a: 'audio/mp4',
  mp3: 'audio/mpeg',
  wav: 'audio/wav',
  png: 'image/png',
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  svg: 'image/svg+xml',
};

function mimeFor(ext: string): string {
  return MIME[ext.toLowerCase()] ?? 'application/octet-stream';
}

export const GET: APIRoute = async ({ url }) => {
  const slug = url.searchParams.get('slug');
  const relPath = url.searchParams.get('path');
  if (!slug || !relPath) {
    return new Response('missing slug or path', { status: 400 });
  }

  const ref = await findContent(slug);
  if (!ref) return new Response('content not found', { status: 404 });

  // Resolve target and verify it stays inside the content directory.
  const target = resolve(ref.dir, normalize(relPath));
  const dir = resolve(ref.dir);
  if (!target.startsWith(dir + '/') && target !== dir) {
    return new Response('path escapes content dir', { status: 400 });
  }

  let s;
  try { s = await stat(target); } catch {
    return new Response('not found', { status: 404 });
  }
  if (!s.isFile()) return new Response('not a file', { status: 400 });

  const ext = extname(target).toLowerCase().replace(/^\./, '');
  const mime = mimeFor(ext);

  if (TEXT_EXTS.has(ext) && s.size < 5 * 1024 * 1024) {
    // Render text inline so the user can read in-browser
    const text = await readFile(target, 'utf-8');
    if (ext === 'md') {
      // Wrap markdown in a minimal HTML shell so it's readable directly.
      const escaped = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
      const body = `<!doctype html><html><head><meta charset="utf-8"><title>${target.split('/').pop()}</title><style>body{font-family:ui-monospace,Menlo,monospace;font-size:13px;line-height:1.55;background:#f7f4ee;color:#1f1d18;padding:24px;max-width:920px;margin:0 auto;white-space:pre-wrap;}</style></head><body>${escaped}</body></html>`;
      return new Response(body, { status: 200, headers: { 'content-type': 'text/html; charset=utf-8' } });
    }
    return new Response(text, { status: 200, headers: { 'content-type': mime } });
  }

  // Binary or large file — stream as-is (small downloads OK for now).
  const buf = await readFile(target);
  return new Response(buf, { status: 200, headers: { 'content-type': mime, 'content-length': String(buf.byteLength) } });
};
