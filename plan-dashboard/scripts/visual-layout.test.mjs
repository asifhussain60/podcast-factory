/**
 * Self-checking test for visual-layout.mjs (no test runner in this project).
 * Run: node scripts/visual-layout.test.mjs   (exit 0 = pass, 1 = fail)
 * Kept in sync with scripts/podcast/tests/test_visual_layout.py.
 */
import assert from 'node:assert/strict';
import {
  SCHEMA, WRAP_MAX_WIDTH_PCT, normalizePlacement, validateLayout,
  figureHtml, applyLayout, anchorKey,
} from './visual-layout.mjs';

let n = 0;
const t = (_name, fn) => { fn(); n++; };

// ── normalization mirrors the Python side ──
t('center forces standalone', () => {
  const { placement } = normalizePlacement({ visual_id: 'a', align: 'center', flow: 'wrap' });
  assert.equal(placement.flow, 'standalone');
});
t('wide wrap promoted to standalone', () => {
  const { placement, warnings } = normalizePlacement({ visual_id: 'a', align: 'left', flow: 'wrap', width_pct: 80 });
  assert.equal(placement.flow, 'standalone');
  assert.ok(warnings.some((w) => w.includes(`>${WRAP_MAX_WIDTH_PCT}`)));
});
t('valid wrap kept', () => {
  const { placement, warnings } = normalizePlacement({ visual_id: 'a', align: 'left', flow: 'wrap', width_pct: 40 });
  assert.equal(placement.flow, 'wrap');
  assert.equal(placement.width_pct, 40);
  assert.deepEqual(warnings, []);
});
t('width clamped', () => {
  assert.equal(normalizePlacement({ visual_id: 'a', width_pct: 999 }).placement.width_pct, 100);
  assert.equal(normalizePlacement({ visual_id: 'a', width_pct: -5 }).placement.width_pct, 1);
});
t('validate skips id-less placement', () => {
  const { placements } = validateLayout({ schema: SCHEMA, placements: [{ anchor: 'x' }, { visual_id: 'ok' }] });
  assert.equal(placements.length, 1);
  assert.equal(placements[0].visual_id, 'ok');
});

// ── figure HTML ──
t('figure wrap-left carries classes + width var', () => {
  const html = figureHtml({ align: 'left', flow: 'wrap', width_pct: 40, caption: 'A tree', page_fit: 'avoid' }, '/book/visuals/x.svg');
  assert.ok(html.includes('flow-wrap'));
  assert.ok(html.includes('align-left'));
  assert.ok(html.includes('--fig-w:40%'));
  assert.ok(html.includes('<figcaption>A tree</figcaption>'));
});
t('caption suppressed when it duplicates embedded title', () => {
  const html = figureHtml({ align: 'center', flow: 'standalone', width_pct: 60, caption: 'The Seven', page_fit: 'avoid' }, '/book/visuals/x.png', 'the seven');
  assert.ok(!html.includes('<figcaption>'));
});
t('empty caption -> no figcaption', () => {
  const html = figureHtml({ align: 'center', flow: 'standalone', width_pct: 60, caption: '', page_fit: 'avoid' }, '/x.png');
  assert.ok(!html.includes('<figcaption>'));
});

// ── anchor matching + injection ──
t('anchorKey normalizes markup + numbering', () => {
  assert.equal(anchorKey('## 2. Patience'), 'patience');
  assert.equal(anchorKey('<h2>2. Patience</h2>'), 'patience');
});
t('applyLayout injects figure after matching chapter-open', () => {
  const body = '<section class="chapter-open"><h2>2. Patience</h2></section>\n<p>text</p>';
  const placements = [{ visual_id: 'f1', anchor: '## 2. Patience', align: 'center', flow: 'standalone', width_pct: 60, caption: 'c', page_fit: 'avoid' }];
  const assets = new Map([['f1', { src: '/book/visuals/f1.svg' }]]);
  const out = applyLayout(body, placements, assets);
  assert.ok(out.includes('v2-fig'));
  assert.ok(out.indexOf('v2-fig') > out.indexOf('</h2>'));
  assert.ok(out.indexOf('v2-fig') < out.indexOf('<p>text'));
});
t('applyLayout skips unknown visual id (partial contract tolerant)', () => {
  const body = '<section class="chapter-open"><h2>2. Patience</h2></section>';
  const placements = [{ visual_id: 'missing', anchor: '## 2. Patience', align: 'center', flow: 'standalone', width_pct: 60, caption: '', page_fit: 'avoid' }];
  const out = applyLayout(body, placements, new Map());
  assert.equal(out, body);
});
t('applyLayout no-ops with empty placements', () => {
  const body = '<section class="chapter-open"><h2>X</h2></section>';
  assert.equal(applyLayout(body, [], new Map()), body);
});

console.log(`visual-layout.mjs: ${n} tests passed`);
