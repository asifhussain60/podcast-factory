/**
 * render-book-pdf.mjs — render a book's book.md into a print PDF.
 *
 * Reuses the site's Playwright chromium (the same one render-mermaid.mjs uses)
 * and the editorial theme tokens, but lays the book out as a clean single-column
 * print document (no nav sidebar). Arabic scripture renders above its English
 * translation, matching the on-screen reader.
 *
 * Book-craft layer (2026-06-11):
 *   - cover page from <book>/book/cover.png when present (full bleed, panel
 *     with title + author from the book's meta.yml);
 *   - chapter-opening pages: numbered "## N. Title" headings become a fresh
 *     page with a "CHAPTER N" eyebrow, the bare title, a hairline rule, and a
 *     drop cap on the opening paragraph; the unnumbered first heading is
 *     treated as the preface;
 *   - Quranic treatment: blockquote paragraphs containing Arabic script get
 *     dir="rtl" + the mushaf styling from book-print.css (Amiri Quran face,
 *     centered, golden frame), translations centered beneath;
 *   - all print CSS lives in src/styles/book-print.css (external single
 *     source of truth), with :root tokens injected from theme.css.
 *
 *   node scripts/render-book-pdf.mjs <book.md> <out.pdf> [theme.css]
 *
 * Exit 0 on success; exit 3 if the chromium binary is missing (actionable
 * message — run `npx playwright install chromium`); exit 1 on other errors.
 */
import { chromium } from 'playwright';
import { readFileSync, mkdirSync, existsSync } from 'node:fs';
import { createServer } from 'node:http';
import path from 'node:path';

const [, , MD_PATH, OUT_PATH, THEME_PATH] = process.argv;
if (!MD_PATH || !OUT_PATH) {
  console.error('usage: render-book-pdf.mjs <book.md> <out.pdf> [theme.css]');
  process.exit(2);
}
const themePath = THEME_PATH || path.resolve(import.meta.dirname, '..', 'src', 'styles', 'theme.css');
const printCssPath = path.resolve(import.meta.dirname, '..', 'src', 'styles', 'book-print.css');
const fontRoot = path.resolve(import.meta.dirname, '..', 'public', 'fonts');

const ARABIC_RE = /[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]/;
const ARABIC_INLINE_RE = /[﴿«]?[\s؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]+[﴾»]?/g;
const NUMBER_WORDS = [
  '', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten',
  'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen',
  'Eighteen', 'Nineteen', 'Twenty', 'Twenty-One', 'Twenty-Two', 'Twenty-Three',
  'Twenty-Four', 'Twenty-Five', 'Twenty-Six', 'Twenty-Seven', 'Twenty-Eight',
  'Twenty-Nine', 'Thirty',
];

function escapeHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function renderInline(text) {
  let s = escapeHtml(text);
  s = s.replace(ARABIC_INLINE_RE, (match) => {
    if (!ARABIC_RE.test(match)) return match;
    const leading = match.match(/^\s*/)?.[0] || '';
    const trailing = match.match(/\s*$/)?.[0] || '';
    const body = match.slice(leading.length, match.length - trailing.length);
    return `${leading}<span class="ar-inline" dir="rtl" lang="ar">${body}</span>${trailing}`;
  });
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, '$1<em>$2</em>');
  return s;
}

function extractToc(md) {
  const items = [];
  const headingRe = /^##\s+(.+)$/gm;
  let match;
  let sawNumbered = false;
  while ((match = headingRe.exec(md)) !== null) {
    const raw = match[1].trim();
    const numbered = raw.match(/^(\d+)\.\s+(.+)$/);
    if (numbered) {
      sawNumbered = true;
      items.push({ label: numbered[1], title: numbered[2].trim() });
    } else if (!sawNumbered && items.length === 0) {
      items.push({ label: items.length === 0 ? 'Preface' : '', title: raw });
    }
  }
  return items;
}

function renderToc(items) {
  if (!items.length) return '';
  const rows = items.map((item) => {
    const label = item.label ? `<span class="toc-label">${escapeHtml(item.label)}</span>` : '';
    return `<li>${label}<span class="toc-title">${renderInline(item.title)}</span></li>`;
  }).join('');
  return `<section class="toc-page"><p class="toc-eyebrow">Contents</p><h2>Contents</h2><ol>${rows}</ol></section>`;
}
/** ASCII-fold a display name (meta.yml authors carry diacritics). */
function asciiFold(s) {
  return s
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[ʻʿ‘’ʼ]/g, "'");
}
/** Read the author display name from the book's meta.yml (best effort). */
function readAuthor(bookContentDir) {
  const metaPath = path.join(bookContentDir, 'meta.yml');
  if (!existsSync(metaPath)) return '';
  const line = readFileSync(metaPath, 'utf-8').split(/\r?\n/).find((l) => /^\s*author:\s*/.test(l));
  if (!line) return '';
  let value = line.replace(/^\s*author:\s*/, '').trim();
  if (
    (value.startsWith('"') && value.endsWith('"'))
    || (value.startsWith("'") && value.endsWith("'"))
  ) {
    value = value.slice(1, -1);
  }
  return asciiFold(value.trim());
}
function readCrosswalk(bookContentDir) {
  const p = path.join(bookContentDir, 'book', 'source-crosswalk.json');
  if (!existsSync(p)) return [];
  try {
    const data = JSON.parse(readFileSync(p, 'utf-8'));
    return Array.isArray(data?.chapters) ? data.chapters : [];
  } catch {
    return [];
  }
}

function renderSourceCrosswalk(items) {
  if (!items.length) return '';
  const rows = items.map((item) => {
    const n = item.index ? String(item.index) : '';
    const range = item.arabic_source_page_range || item.source_page_range || '';
    const heads = Array.isArray(item.source_headings) && item.source_headings.length
      ? item.source_headings.slice(0, 3).join('; ')
      : (item.source_excerpt || '').slice(0, 140);
    return `<tr><td>${escapeHtml(n)}</td><td>${renderInline(item.title || '')}</td>`
      + `<td>${escapeHtml(range)}</td><td>${renderInline(heads || '')}</td></tr>`;
  }).join('');
  return '<section class="crosswalk-page"><p class="toc-eyebrow">Source Crosswalk</p>'
    + '<h2>Source Crosswalk</h2>'
    + '<table><thead><tr><th>Ch.</th><th>Chapter</th><th>Arabic pages</th><th>Source signal</th></tr></thead>'
    + `<tbody>${rows}</tbody></table></section>`;
}

/** Minimal renderer matching markdown.ts behaviour for book.md (headings,
 *  paragraphs, blockquotes, and raw HTML blocks like <figure class="book-diagram">). */
function renderMd(md, crosswalkByIndex = new Map()) {
  const lines = md.replace(/\r\n/g, '\n').split('\n');
  const out = [];
  let para = [];
  let quote = [];
  let inHtmlBlock = false;
  let chapterJustOpened = false;
  let sawH2 = false;

  const flushPara = () => {
    if (!para.length) return;
    const cls = chapterJustOpened ? ' class="ch-first"' : '';
    chapterJustOpened = false;
    out.push(`<p${cls}>${renderInline(para.join(' '))}</p>`);
    para = [];
  };
  const flushQuote = () => {
    if (!quote.length) return;
    const paras = []; let cur = [];
    for (const l of quote) { if (l.trim() === '') { if (cur.length) { paras.push(cur.join(' ')); cur = []; } } else cur.push(l); }
    if (cur.length) paras.push(cur.join(' '));
    const hasArabic = paras.some((p) => ARABIC_RE.test(p));
    if (hasArabic) {
      // Mushaf treatment: Arabic lines RTL + Amiri, translations centered below.
      const inner = [];
      paras.forEach((p, i) => {
        if (ARABIC_RE.test(p)) {
          // Strip a stray trailing ASCII period — Latin punctuation has no
          // place at the end of an Arabic line (bidi renders it mid-air).
          const cleaned = p.trim().replace(/\.\s*$/, '');
          inner.push(`<p class="ar" dir="rtl" lang="ar">${renderInline(cleaned)}</p>`);
          if (i < paras.length - 1) inner.push('<hr class="quran-divider">');
        } else {
          inner.push(`<p class="tr">${renderInline(p)}</p>`);
        }
      });
      out.push(`<blockquote class="quran">${inner.join('')}</blockquote>`);
    } else {
      out.push(`<blockquote>${paras.map((p) => `<p>${renderInline(p)}</p>`).join('') || '<p></p>'}</blockquote>`);
    }
    quote = [];
  };

  for (const line of lines) {
    // Raw HTML block pass-through: <figure class="book-diagram">...</figure>
    if (inHtmlBlock) {
      out.push(line);
      if (line.trimEnd().toLowerCase() === '</figure>') inHtmlBlock = false;
      continue;
    }
    if (line.trimStart().toLowerCase().startsWith('<figure')) {
      flushPara(); flushQuote();
      out.push(line);
      inHtmlBlock = !line.includes('</figure>');
      continue;
    }
    const h = line.match(/^(#{1,6})\s+(.+)$/);
    if (h) {
      flushPara(); flushQuote();
      const level = h[1].length;
      const text = h[2].trim();
      if (level === 2) {
        // Book-style chapter opening. "N. Title" → CHAPTER N eyebrow + bare
        // title; the unnumbered first h2 is the preface. Later unnumbered H2s
        // are internal source headings and must stay in the prose flow.
        const isFirstH2 = !sawH2;
        const numbered = text.match(/^(\d+)\.\s+(.+)$/);
        let eyebrow;
        let title;
        if (numbered) {
          const n = parseInt(numbered[1], 10);
          eyebrow = `Chapter ${NUMBER_WORDS[n] || numbered[1]}`;
          title = numbered[2];
        } else {
          eyebrow = sawH2 ? '' : 'Preface';
          title = text;
        }
        if (numbered || isFirstH2) {
          const sourceRange = numbered
            ? (crosswalkByIndex.get(parseInt(numbered[1], 10))?.arabic_source_page_range
                || crosswalkByIndex.get(parseInt(numbered[1], 10))?.source_page_range
                || '')
            : '';
          sawH2 = true;
          chapterJustOpened = true;
          out.push(
            `<section class="chapter-open${isFirstH2 ? ' first-chapter-open' : ''}">`
            + (eyebrow ? `<p class="ch-eyebrow">${escapeHtml(eyebrow)}</p>` : '')
            + `<h2>${renderInline(title)}</h2>`
            + (sourceRange ? `<p class="ch-source">Arabic source ${escapeHtml(sourceRange)}</p>` : '')
            + '<hr class="ch-rule">'
            + '</section>',
          );
        } else {
          out.push(`<h3 class="section-heading">${renderInline(text)}</h3>`);
        }
      } else {
        out.push(`<h${level}>${renderInline(text)}</h${level}>`);
      }
      continue;
    }
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
  const tocItems = extractToc(body);
  const rootTokens = existsSync(themePath) ? themeRoot(readFileSync(themePath, 'utf-8')) : '';
  const printCss = readFileSync(printCssPath, 'utf-8');

  // Static-asset root: the book's content dir (parent of book/), so markdown
  // can reference e.g. <img src="slide-deck/_pages/page-02.png">. Fonts are
  // served from plan-dashboard/public/fonts at /fonts/.
  const assetRoot = path.resolve(path.dirname(MD_PATH), '..');
  const author = readAuthor(assetRoot);
  const crosswalk = readCrosswalk(assetRoot);
  const crosswalkByIndex = new Map(crosswalk.map((item) => [Number(item.index), item]));
  const coverPath = path.join(path.dirname(MD_PATH), 'cover.png');
  const hasCover = existsSync(coverPath);

  const coverHtml = hasCover
    ? `<section class="cover"><img src="/book/cover.png" alt="">`
      + `<div class="cover-panel"><h1>${escapeHtml(title)}</h1>`
      + (author ? `<p class="cover-author">${escapeHtml(author)}</p>` : '')
      + `</div></section>`
    : '';
  const titlePage =
    `<section class="title-page"><p class="eyebrow">Reading edition</p>`
    + `<h1>${escapeHtml(title)}</h1>`
    + (author ? `<p class="title-author">${escapeHtml(author)}</p>` : '')
    + `<hr class="title-rule">`
    + `<div class="disclaimer-panel">Generated using podcast-factory AI. Verify content; AI can make mistakes.</div>`
    + `</section>`;

  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><style>
    :root {${rootTokens}}
${printCss}
  </style></head><body>
    ${coverHtml}
    ${titlePage}
    ${renderToc(tocItems)}
    ${renderSourceCrosswalk(crosswalk)}
    ${renderMd(body, crosswalkByIndex)}
  </body></html>`;

  const MIME = { '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.svg': 'image/svg+xml', '.ttf': 'font/ttf', '.woff2': 'font/woff2' };
  const server = createServer((req, res) => {
    const reqPath = decodeURIComponent((req.url || '/').split('?')[0]);
    if (reqPath === '/' || reqPath === '') {
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(html);
      return;
    }
    // Font route: /fonts/** → plan-dashboard/public/fonts/**
    const root = reqPath.startsWith('/fonts/') ? path.dirname(fontRoot) : assetRoot;
    const resolved = path.resolve(root, '.' + reqPath);
    const type = MIME[path.extname(resolved).toLowerCase()];
    // Traversal guard: only files under the allowed root, known types only.
    if (!resolved.startsWith(root + path.sep) || !type || !existsSync(resolved)) {
      res.writeHead(404); res.end('not found');
      return;
    }
    res.writeHead(200, { 'Content-Type': type });
    res.end(readFileSync(resolved));
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
    // Wait for ALL @font-face fonts (self-hosted Source Serif 4 + Amiri) to finish
    // loading before paginating. Without this, font-display:swap can paginate with
    // a fallback font and swap after — making page/line breaks non-deterministic.
    await page.evaluate(() => document.fonts.ready);
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
