// render-mermaid.mjs — WC6d build-time Mermaid renderer.
//
// The site is SSR (output: 'server'), so we do NOT run a browser per request.
// Instead this script renders each Mermaid definition to a static inline-SVG
// file ONCE (via the Playwright chromium already installed for screenshots),
// writing to src/generated/mermaid/<id>.svg. The <Mermaid id> Astro component
// then reads the precomputed SVG and inlines it — zero client JS, zero
// per-request browser work, fully Cortex-compliant (vertical, uncapped, real
// <text>, viewBox-only).
//
// Diagrams are defined in src/diagrams/<id>.mmd (one Mermaid definition each).
// Run: npm run mermaid:render

import { chromium } from 'playwright';
import { readdir, readFile, writeFile, mkdir } from 'node:fs/promises';
import { existsSync, readFileSync } from 'node:fs';
import { createServer } from 'node:http';
import path from 'node:path';

const ROOT       = path.resolve(import.meta.dirname, '..');
const SRC_DIR    = path.join(ROOT, 'src', 'diagrams');
const OUT_DIR    = path.join(ROOT, 'src', 'generated', 'mermaid');
const MERMAID_JS = path.join(ROOT, 'node_modules', 'mermaid', 'dist', 'mermaid.min.js');

// Theme variables mapped to the editorial-modern palette (theme.css). Mermaid
// bakes colours into the SVG, so we pass the literal hex values the theme uses;
// the colour theme itself is never changed.
const THEME_VARIABLES = {
  background:         'transparent',
  primaryColor:       '#fffdf8', // --c-bg-card
  primaryTextColor:   '#1f1d18', // --c-ink
  primaryBorderColor: '#8b4513', // --c-accent
  secondaryColor:     '#efeae0', // --c-bg-sunken
  tertiaryColor:      '#f7f4ee', // --c-bg
  lineColor:          '#87827a', // --c-ink-muted
  textColor:          '#1f1d18', // --c-ink
  fontFamily:         "'Lato', system-ui, sans-serif",
  fontSize:           '16px',
};

async function main() {
  if (!existsSync(SRC_DIR)) {
    console.error(`no diagrams dir at ${SRC_DIR} — nothing to render`);
    process.exit(0);
  }
  await mkdir(OUT_DIR, { recursive: true });

  const files = (await readdir(SRC_DIR)).filter((f) => f.endsWith('.mmd'));
  if (files.length === 0) {
    console.log('no .mmd files found');
    return;
  }

  // file:// module imports are CORS-blocked (origin "null"). Serve the mermaid
  // bundle + a loader page over http://localhost so the ESM import is allowed.
  const mermaidJs = readFileSync(MERMAID_JS);
  // mermaid.min.js is an IIFE bundle that assigns globalThis.mermaid — load it
  // as a classic script (not a module), then drive it from window.mermaid.
  const loaderHtml = `<!doctype html><html><head><meta charset="utf-8"></head><body>
    <script src="/mermaid.min.js"></script>
    <script>
      mermaid.initialize({
        startOnLoad: false,
        securityLevel: 'loose',
        theme: 'base',
        themeVariables: ${JSON.stringify(THEME_VARIABLES)},
        flowchart: { useMaxWidth: true, htmlLabels: false },
        sequence:  { useMaxWidth: true },
      });
      window.__renderMermaid = async (id, def) => (await mermaid.render(id, def)).svg;
      window.__ready = true;
    </script>
  </body></html>`;

  const server = createServer((req, res) => {
    if (req.url === '/mermaid.min.js') {
      res.writeHead(200, { 'Content-Type': 'text/javascript' });
      res.end(mermaidJs);
    } else {
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(loaderHtml);
    }
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const { port } = server.address();

  const browser = await chromium.launch();
  const page = await browser.newPage();
  page.on('pageerror', (e) => console.error('  [pageerror]', e.message));
  page.on('console', (m) => { if (m.type() === 'error') console.error('  [console]', m.text()); });

  await page.goto(`http://127.0.0.1:${port}/`);
  await page.waitForFunction('window.__ready === true', { timeout: 30000 });

  let ok = 0;
  for (const file of files) {
    const id = path.basename(file, '.mmd');
    const def = await readFile(path.join(SRC_DIR, file), 'utf8');
    try {
      let svg = await page.evaluate(
        ([gid, gdef]) => window.__renderMermaid('m_' + gid, gdef),
        [id.replace(/[^a-z0-9]/gi, ''), def],
      );
      // Cortex hygiene: the root <svg> carries width="100%" + inline
      // style="max-width:..." — strip them so the .diagram-figure container
      // controls sizing (viewBox stays, driving aspect ratio). The SVG-scoped
      // <style> block (mermaid's theming) is left intact as diagram content.
      svg = svg.replace(/(<svg\b[^>]*?)\s+width="[^"]*"/, '$1')
               .replace(/(<svg\b[^>]*?)\s+height="[^"]*"/, '$1')
               .replace(/(<svg\b[^>]*?)\s+style="[^"]*"/, '$1');
      await writeFile(path.join(OUT_DIR, `${id}.svg`), svg, 'utf8');
      console.log(`  rendered ${id}.svg (${svg.length} bytes)`);
      ok++;
    } catch (err) {
      console.error(`  FAILED ${id}: ${err.message}`);
    }
  }

  await browser.close();
  server.close();
  console.log(`mermaid render complete: ${ok}/${files.length}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
