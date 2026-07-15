// @ts-check
import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import node from '@astrojs/node';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  output: 'server',
  adapter: node({ mode: 'standalone' }),
  integrations: [react()],
  devToolbar: { enabled: false },
  vite: {
    // Allow a second dev server (e.g. the Claude preview on :4323) to use its
    // OWN dependency-optimization cache via VITE_CACHE_DIR. Two dev servers
    // sharing the default node_modules/.vite race on re-optimization and corrupt
    // it — surfacing as "jsxDEV is not a function" / "504 Outdated Optimize Dep".
    cacheDir: process.env.VITE_CACHE_DIR || undefined,
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
