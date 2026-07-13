/**
 * book.visual-layout/v1 — the human-curated visual placement contract (JS side).
 *
 * JS MIRROR of scripts/podcast/_visual_layout.py. The Astro "Book Composer"
 * writes book/visual-layout.json; render-book-pdf.mjs consumes it through this
 * module. Keep the enums, normalization, and schema string in sync with the
 * Python mirror in the same commit.
 *
 * Renderer semantics: flow=wrap -> float (align left|right) with text beside it,
 * requires width_pct<=50; flow=standalone -> centered full-column block;
 * align=center implies standalone. page_fit avoid|before|isolate-plate controls
 * pagination (never split / fresh page / own page).
 */
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

export const SCHEMA = 'book.visual-layout/v1';
export const ALIGNS = ['left', 'center', 'right'];
export const FLOWS = ['wrap', 'standalone'];
export const PAGE_FITS = ['avoid', 'before', 'isolate-plate'];
export const WRAP_MAX_WIDTH_PCT = 50;
export const DEFAULT_WIDTH_PCT = 60;

export function normalizePlacement(raw) {
  const warnings = [];
  const vid = String(raw.visual_id || '').trim();
  const anchor = String(raw.anchor || '').trim();

  let align = String(raw.align || 'center').trim().toLowerCase();
  if (!ALIGNS.includes(align)) { warnings.push(`${vid || '?'}: unknown align -> center`); align = 'center'; }

  let flow = String(raw.flow || 'standalone').trim().toLowerCase();
  if (!FLOWS.includes(flow)) { warnings.push(`${vid || '?'}: unknown flow -> standalone`); flow = 'standalone'; }

  let widthPct = parseInt(raw.width_pct, 10);
  if (!Number.isFinite(widthPct)) widthPct = DEFAULT_WIDTH_PCT;
  widthPct = Math.max(1, Math.min(100, widthPct));

  if (align === 'center' && flow === 'wrap') { warnings.push(`${vid}: center forces standalone`); flow = 'standalone'; }
  if (flow === 'wrap' && widthPct > WRAP_MAX_WIDTH_PCT) {
    warnings.push(`${vid}: wrap width ${widthPct}%>${WRAP_MAX_WIDTH_PCT}% -> standalone`);
    flow = 'standalone';
  }

  let pageFit = String(raw.page_fit || 'avoid').trim().toLowerCase();
  if (!PAGE_FITS.includes(pageFit)) { warnings.push(`${vid}: unknown page_fit -> avoid`); pageFit = 'avoid'; }

  return {
    placement: { visual_id: vid, anchor, align, flow, width_pct: widthPct, caption: String(raw.caption || '').trim(), page_fit: pageFit },
    warnings,
  };
}

export function validateLayout(data) {
  const warnings = [];
  if (!data || typeof data !== 'object') return { placements: [], warnings: ['layout is not an object'] };
  if (data.schema !== SCHEMA) warnings.push(`unexpected schema ${data.schema}`);
  const placements = [];
  for (const raw of data.placements || []) {
    if (!raw || typeof raw !== 'object' || !String(raw.visual_id || '').trim()) {
      warnings.push('placement without a visual_id skipped');
      continue;
    }
    const { placement, warnings: w } = normalizePlacement(raw);
    placements.push(placement);
    warnings.push(...w);
  }
  return { placements, warnings };
}

export function loadLayout(bookContentDir) {
  const p = path.join(bookContentDir, 'book', 'visual-layout.json');
  if (!existsSync(p)) return { placements: [], warnings: [] };
  try {
    return validateLayout(JSON.parse(readFileSync(p, 'utf-8')));
  } catch (e) {
    return { placements: [], warnings: [`visual-layout.json unreadable: ${e.message}`] };
  }
}

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/**
 * Build the <figure> HTML for one placement. `assetSrc` is the URL the render
 * server can serve (e.g. /book/visuals/<file>). `embeddedTitle` (optional) is a
 * title already baked into the asset — when it equals the caption we suppress the
 * <figcaption> to avoid a duplicated caption (the original defect).
 * Width is data-driven, so it rides a CSS custom property on the figure; all
 * enumerable dimensions (flow/align/page_fit) are classes in book-print.css.
 */
export function figureHtml(placement, assetSrc, embeddedTitle = '') {
  const { align, flow, width_pct, caption, page_fit } = placement;
  const classes = ['v2-fig', `flow-${flow}`, `align-${align}`, `page-fit-${page_fit}`];
  // Both raster and SVG assets are served as files and embedded via <img>; the
  // render server serves them from book/visuals/ with the right MIME type.
  const inner = `<img src="${esc(assetSrc)}" alt="${esc(caption)}">`;
  const dupCaption = caption && embeddedTitle && caption.trim().toLowerCase() === embeddedTitle.trim().toLowerCase();
  const cap = caption && !dupCaption ? `<figcaption>${esc(caption)}</figcaption>` : '';
  return `<figure class="${classes.join(' ')}" style="--fig-w:${width_pct}%">${inner}${cap}</figure>`;
}

/**
 * Insert each placement's figure into `bodyHtml` immediately after its anchor
 * chapter <section class="chapter-open">…</section> block (the anchor is the
 * chapter heading text, e.g. "## 2. Title" or its rendered "2. Title").
 * `assetsById` maps visual_id -> { src, embeddedTitle }. Unknown ids are skipped
 * (tolerant of a partial contract). Returns the augmented body HTML.
 */
export function applyLayout(bodyHtml, placements, assetsById) {
  if (!placements.length) return bodyHtml;
  // Group figures by the anchor's chapter number/title so we can inject after
  // the chapter-open section. We match on the <h2> text the renderer emitted.
  const byAnchor = new Map();
  for (const p of placements) {
    const asset = assetsById.get(p.visual_id);
    if (!asset || !asset.src) continue;
    const key = anchorKey(p.anchor);
    if (!byAnchor.has(key)) byAnchor.set(key, []);
    byAnchor.get(key).push(figureHtml(p, asset.src, asset.embeddedTitle || ''));
  }
  if (!byAnchor.size) return bodyHtml;
  // Split on chapter-open sections; append matching figures right after each.
  const chapterRe = /(<section class="chapter-open[^"]*">[\s\S]*?<\/section>)/g;
  return bodyHtml.replace(chapterRe, (block) => {
    const h2 = block.match(/<h2>([\s\S]*?)<\/h2>/);
    if (!h2) return block;
    const key = anchorKey(h2[1]);
    const figs = byAnchor.get(key);
    return figs && figs.length ? `${block}\n${figs.join('\n')}` : block;
  });
}

/** Normalize an anchor / heading to a comparable key: strip markup, "N." prefix, case. */
export function anchorKey(s) {
  return String(s)
    .replace(/<[^>]+>/g, '')
    .replace(/^#{1,6}\s+/, '')
    .replace(/^\d+\.\s*/, '')
    .trim()
    .toLowerCase();
}
