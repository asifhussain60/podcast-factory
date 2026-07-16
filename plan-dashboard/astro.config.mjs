// @ts-check
import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import node from '@astrojs/node';
import tailwindcss from '@tailwindcss/vite';

// Default port this site binds when `--port` is not passed (mirrors server.port
// below). Used to key the per-server dependency-optimization cache.
const DEFAULT_PORT = 4322;

// Resolve THIS server instance's port from the CLI (`astro dev --port <n>`),
// falling back to $PORT and then DEFAULT_PORT. `astro build`/`check` have no
// --port and land on DEFAULT_PORT, which is fine — they don't run concurrently
// with a dev server on the same cache.
function resolveInstancePort() {
  const argv = process.argv;
  const i = argv.indexOf('--port');
  if (i >= 0 && argv[i + 1]) return argv[i + 1];
  const eq = argv.find((a) => a.startsWith('--port='));
  if (eq) return eq.slice('--port='.length);
  return process.env.PORT || String(DEFAULT_PORT);
}

// Give EACH dev-server instance its OWN Vite dependency-optimization cache dir,
// keyed by port, instead of the single shared node_modules/.vite. This is the
// root fix for the recurring "Cannot read properties of null (reading
// 'useContext' / 'useRef')" blanked-island failures: two Vite dev servers (the
// site on :4322 + a Claude preview on :4323, or the site + an ephemeral smoke
// server) sharing one node_modules/.vite race on re-optimization and rewrite
// the optimized react/react-dom chunks out from under an already-served tab —
// leaving a second React instance whose hook dispatcher is null. Per-port dirs
// make that race structurally impossible while still reusing a warm cache on
// restart of the same port. VITE_CACHE_DIR still overrides for full control.
const CACHE_DIR = process.env.VITE_CACHE_DIR || `node_modules/.vite-port-${resolveInstancePort()}`;

export default defineConfig({
  output: 'server',
  adapter: node({ mode: 'standalone' }),
  integrations: [react()],
  devToolbar: { enabled: false },
  vite: {
    // Per-server optimize cache (see CACHE_DIR above). Two dev servers sharing
    // the default node_modules/.vite race on re-optimization and corrupt it —
    // surfacing as "jsxDEV is not a function" / "504 Outdated Optimize Dep" /
    // null-hook blanked islands. Keying by port isolates them automatically.
    cacheDir: CACHE_DIR,
    plugins: [tailwindcss()],
    // Force a SINGLE React instance across every dep. A nested dependency that
    // resolves its own copy of react/react-dom makes hooks read from the wrong
    // instance and return null — surfacing as "Cannot read properties of null
    // (reading 'useContext' / 'useRef')" and a blanked island (e.g. /corpus,
    // Edit & Enrich). dedupe collapses them to one copy so this can't happen.
    resolve: { dedupe: ['react', 'react-dom'] },
    optimizeDeps: {
      // React 19 uses a conditional IIFE that Vite's CJS→ESM static analyser
      // can't resolve without explicit pre-bundling — forces esbuild to process
      // these packages and produce proper named ESM exports (e.g. createRoot).
      // Pre-bundle EVERY third-party dep imported by a client React island. If a
      // dep is discovered mid-session (first time an island loads), Vite
      // re-optimizes and invalidates already-served chunk URLs, 504-ing them
      // ("Outdated Optimize Dep") for any open tab — which blanks the island
      // (Edit & Enrich 2026-06-15; homepage NarrativeScroll + Edit palette
      // 2026-07-14). This list = the full set of bare specifiers imported under
      // src/components + src/scripts (node: builtins excluded); keep it in sync
      // when a new island dependency is added.
      include: [
        'react', 'react-dom', 'react-dom/client', 'lucide-react',
        '@tiptap/react', '@tiptap/starter-kit', '@tiptap/core',
        '@tiptap/pm/model', '@tiptap/pm/state', '@tiptap/pm/view', 'diff',
        'cmdk', '@radix-ui/react-toast',
        '@dnd-kit/core', '@dnd-kit/sortable', '@dnd-kit/utilities',
        '@orama/orama',
        'gsap', 'gsap/ScrollTrigger',
      ],
    },
    server: {
      fs: {
        allow: ['..', '../..'],
      },
    },
    ssr: {
      // Native Node addons must not be bundled — Vite passes them through as-is
      external: ['better-sqlite3'],
    },
  },
  server: {
    port: 4322,
    host: 'localhost',
  },
});
