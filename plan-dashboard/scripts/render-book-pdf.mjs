/**
 * render-book-pdf.mjs — render a book's book.md into a print PDF.
 *
 * Reuses the site's Playwright chromium (the same one render-mermaid.mjs uses)
 * and the editorial theme tokens, but lays the book out as a clean single-column
 * print document (no nav sidebar). Arabic scripture renders above its English
 * translation, matching the on-screen reader.
 *
 *   node scripts/render-book-pdf.mjs <book.md> <out.pdf> [theme.css]
 *
 * Exit 0 on success; exit 3 if the chromium binary is missing (actionable
 * message — run `npx playwright install chromium`); exit 1 on other errors.
 */
import { chromium } from 'playwright';
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { createServer } from 'node:http';
import path from 'node:path';

const [, , MD_PATH, OUT_PATH, THEME_PATH] = process.argv;
if (!MD_PATH || !OUT_PATH) {
  console.error('usage: render-book-pdf.mjs <book.md> <out.pdf> [theme.css]');
  process.exit(2);
}
const themePath = THEME_PATH || path.resolve(import.meta.dirname, '..', 'src', 'styles', 'theme.css');

function escapeHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function renderInline(text) {
  let s = escapeHtml(text);
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, '$1<em>$2</em>');
  return s;
}
/** Minimal renderer matching markdown.ts behaviour for book.md (headings,
 *  paragraphs, and blockquotes split on blank lines → Arabic over English). */
function renderMd(md) {
  const lines = md.replace(/\r\n/g, '\n').split('\n');
  const out = [];
  let para = [];
  let quote = [];
  const flushPara = () => { if (para.length) { out.push(`<p>${renderInline(para.join(' '))}</p>`); para = []; } };
  const flushQuote = () => {
    if (!quote.length) return;
    const paras = []; let cur = [];
    for (const l of quote) { if (l.trim() === '') { if (cur.length) { paras.push(cur.join(' ')); cur = []; } } else cur.push(l); }
    if (cur.length) paras.push(cur.join(' '));
    out.push(`<blockquote>${paras.map((p) => `<p>${renderInline(p)}</p>`).join('') || '<p></p>'}</blockquote>`);
    quote = [];
  };
  for (const line of lines) {
    const h = line.match(/^(#{1,6})\s+(.+)$/);
    if (h) { flushPara(); flushQuote(); out.push(`<h${h[1].length}>${renderInline(h[2])}</h${h[1].length}>`); continue; }
    const q = line.match(/^>\s?(.*)$/);
    if (q) { flushPara(); quote.push(q[1]); continue; }
    if (quote.length) flushQuote();
    if (line.trim() === '') { flushPara(); continue; }
    para.push(line);
  }
  flushPara(); flushQuote();
  return out.join('\n');
}

function themeRoot(css) {
  const m = css.match(/:root\s*\{([^}]*)\}/);
  return m ? m[1] : '';
}

async function main() {
  const md = readFileSync(MD_PATH, 'utf-8');
  const titleMatch = md.match(/^#\s+(.+)$/m);
  const title = titleMatch ? titleMatch[1].trim() : path.basename(MD_PATH, '.md');
  const body = md.replace(/^#\s+.+$\n?/m, '');
  const rootTokens = existsSync(themePath) ? themeRoot(readFileSync(themePath, 'utf-8')) : '';

  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><style>
    :root {${rootTokens}}
    @page { margin: 2.2cm 2cm; }
    html { font-size: 19.2px; }
    body {
      font-family: "Source Serif 4", "Iowan Old Style", "Charter", Georgia, "Times New Roman", serif;
      font-size: 1rem; line-height: 1.62; color: var(--c-ink, #1f1d18); background: #fff;
    }
    .title-page { display: flex; flex-direction: column; justify-content: center; align-items: center;
      text-align: center; min-height: 86vh; page-break-after: always; }
    .title-page .eyebrow { font-family: var(--font-ui, system-ui, sans-serif); text-transform: uppercase;
      letter-spacing: 0.12em; font-size: 0.8rem; color: var(--c-accent, #8b4513); margin-bottom: 0.6rem; }
    .title-page h1 { font-size: 2.4rem; line-height: 1.2; margin: 0; color: var(--c-ink, #1f1d18); }
    h2 { font-size: 1.6rem; margin: 1.8rem 0 0.9rem; padding-bottom: 0.3rem;
      border-bottom: 1px solid var(--c-rule-soft, #ebe6da); page-break-after: avoid; }
    h3 { font-size: 1.25rem; margin: 1.3rem 0 0.6rem; page-break-after: avoid; }
    p { margin: 0 0 0.8rem; }
    blockquote { margin: 1rem 0; padding: 0.6rem 1.1rem; border-left: 3px solid var(--c-accent, #8b4513);
      background: var(--c-bg-card, #fffdf8); page-break-inside: avoid; }
    blockquote p { margin: 0.3rem 0; }
    blockquote p:first-child { font-size: 1.3rem; line-height: 1.85; }
  </style></head><body>
    <section class="title-page"><p class="eyebrow">Reading edition</p><h1>${escapeHtml(title)}</h1></section>
    ${renderMd(body)}
  </body></html>`;

  const server = createServer((_req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(html);
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const { port } = server.address();

  let browser;
  try {
    browser = await chromium.launch();
  } catch (err) {
    server.close();
    const first = String(err.message || err).split('\n')[0];
    console.error(`book-pdf: chromium unavailable — ${first}`);
    console.error('  Run `npx playwright install chromium` in plan-dashboard/, then retry.');
    process.exit(3);
  }
  try {
    const page = await browser.newPage();
    page.on('pageerror', (e) => console.error('  [pageerror]', e.message));
    await page.goto(`http://127.0.0.1:${port}/`, { waitUntil: 'networkidle' });
    mkdirSync(path.dirname(OUT_PATH), { recursive: true });
    await page.pdf({ path: OUT_PATH, format: 'A4', printBackground: true,
      margin: { top: '0', right: '0', bottom: '0', left: '0' } });
    console.log(`book-pdf: wrote ${OUT_PATH}`);
  } finally {
    await browser.close();
    server.close();
  }
}

main().catch((e) => { console.error('book-pdf: ' + (e?.stack || e)); process.exit(1); });
