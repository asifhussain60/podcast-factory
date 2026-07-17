/**
 * preview-pages.mjs — render a LIVE working preview of a book's current edits
 * for the Studio Preview surface (/studio/<slug>/preview).
 *
 * Preview is deliberately NOT the canonical book/book.pdf — it's a working
 * render of whatever is currently saved in book.md / visual-layout.json /
 * citation-style.json, regenerated automatically whenever those sources move
 * past the last preview render. The canonical book.pdf is only ever written by
 * the explicit, confirmed "Generate PDF" action (POST /api/studio/generate-book-pdf,
 * unchanged) — Preview never touches it.
 *
 * Rendering reuses the SAME reliable pipeline as the real PDF — render-book-pdf.mjs
 * (Chromium's native print engine, the one thing proven reliable across this
 * whole effort) — just pointed at a scratch output path. Each page is then
 * rasterized to a PNG via pdftoppm (Poppler — already a dependency of this
 * repo's print-quality gates) and cached under book/_preview-cache/, so plain
 * <img> elements can stack in normal document flow: the browser's ONE
 * scrollbar carries the reader through the whole book (an <iframe>-embedded
 * PDF viewer can't do that — it owns its own internal scroll region — and
 * live in-browser pagination via Paged.js hung/crashed on this environment's
 * Chromium regardless of content, an unresolved library/browser gap).
 */
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readdirSync, rmSync, statSync } from 'node:fs';
import { join } from 'node:path';

const PAGE_RE = /^page-(\d+)\.png$/;
const SCRIPTS_DIR = new URL('..', import.meta.url).pathname;
const RENDER_SCRIPT = join(SCRIPTS_DIR, 'render-book-pdf.mjs');
const THEME_CSS = join(SCRIPTS_DIR, '..', 'src', 'styles', 'theme.css');

function cacheDirFor(bookDir) {
  return join(bookDir, 'book', '_preview-cache');
}

function cachedPageFiles(cacheDir) {
  if (!existsSync(cacheDir)) return [];
  return readdirSync(cacheDir)
    .filter((f) => PAGE_RE.test(f))
    .sort((a, b) => Number(a.match(PAGE_RE)[1]) - Number(b.match(PAGE_RE)[1]));
}

/** Latest mtime across book.md + (when present) visual-layout.json and
 *  citation-style.json — the sources Preview must stay fresh against. */
function sourcesMtimeMs(bookDir) {
  const candidates = [
    join(bookDir, 'book', 'book.md'),
    join(bookDir, 'book', 'visual-layout.json'),
    join(bookDir, 'book', 'citation-style.json'),
  ];
  let latest = 0;
  for (const p of candidates) {
    if (existsSync(p)) latest = Math.max(latest, statSync(p).mtimeMs);
  }
  return latest;
}

/**
 * Ensure book/_preview-cache/page-NNN.png reflects the CURRENT book.md /
 * visual-layout.json / citation-style.json — regenerating the scratch preview
 * PDF (and its page images) only when those sources are newer than the cache.
 * Returns { pageCount, cacheDir, regenerated } — pageCount is 0 when there is
 * no book.md yet. Synchronous; safe to call on every Preview page load (a
 * no-op fs stat comparison when the cache is already fresh).
 */
export function ensurePreviewPageImages(bookDir, { dpi = 90 } = {}) {
  const mdPath = join(bookDir, 'book', 'book.md');
  if (!existsSync(mdPath)) return { pageCount: 0, cacheDir: '', regenerated: false };

  const cacheDir = cacheDirFor(bookDir);
  const scratchPdf = join(cacheDir, 'preview.pdf');
  const sourceMtime = sourcesMtimeMs(bookDir);
  const stale = !existsSync(scratchPdf)
    || statSync(scratchPdf).mtimeMs < sourceMtime
    || cachedPageFiles(cacheDir).length === 0;

  if (stale) {
    rmSync(cacheDir, { recursive: true, force: true });
    mkdirSync(cacheDir, { recursive: true });
    // The unified render always honors visual-layout.json + the v2 pagination CSS.
    execFileSync('node', [RENDER_SCRIPT, mdPath, scratchPdf, THEME_CSS, '1'], { stdio: ['ignore', 'ignore', 'pipe'] });
    execFileSync('pdftoppm', ['-png', '-r', String(dpi), scratchPdf, join(cacheDir, 'page')], {
      stdio: ['ignore', 'ignore', 'pipe'],
    });
  }
  return { pageCount: cachedPageFiles(cacheDir).length, cacheDir, regenerated: stale };
}

/** Resolve the on-disk path for a 1-indexed page number, or null if out of range. */
export function pagePngPath(bookDir, pageNum) {
  const cacheDir = cacheDirFor(bookDir);
  const files = cachedPageFiles(cacheDir);
  const file = files[pageNum - 1];
  return file ? join(cacheDir, file) : null;
}
