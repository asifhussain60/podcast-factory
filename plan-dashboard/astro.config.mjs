// @ts-check
import { fileURLToPath } from 'node:url';
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
    //
    // ProseMirror is deduped for a DIFFERENT and harsher reason than React: it
    // compares plugin keys and node types by IDENTITY, so a second copy is not a
    // degradation but a hard throw ("Adding different instances of a keyed
    // plugin" / "Invalid content for node"). The packages/* workspace symlink
    // makes a nested copy reachable in a way it was not before, so these are
    // pinned the same way react is.
    resolve: {
      dedupe: [
        'react', 'react-dom',
        '@tiptap/core', '@tiptap/pm', '@tiptap/starter-kit',
        'prosemirror-model', 'prosemirror-state', 'prosemirror-view',
      ],
      // Resolve the in-repo editor package to its SOURCE rather than its built
      // dist/. Both routes work — pre-bundling the linked workspace dep was
      // measured at 32/32 routes clean too — so this is a choice, not a
      // workaround:
      //
      //   - dist/ resolution makes `npm run build:packages` a prerequisite for
      //     `astro dev` on every fresh checkout AND after every package edit.
      //     That is a trap nobody remembers until the dev server won't start.
      //   - source resolution gives HMR while editing the package.
      //
      // The cost is that the published dist/ path is not exercised in-repo; the
      // package's own `npm pack` + install-into-a-scratch-dir check covers it.
      //
      // The ARRAY form with anchored regexes, not the object form. A plain
      // string alias key matches by PREFIX, so `@asifhussain/prose-editor`
      // would also capture `@asifhussain/prose-editor/styles.css` and rewrite
      // it to `.../src/index.ts/styles.css` — a path that cannot exist. That
      // failure does not surface as a build error: the dev server answered the
      // compose route with a 302 to /edit, and because the smoke check follows
      // redirects it reported the route clean while the page was in fact
      // unreachable. Anchored patterns make each subpath explicit.
      alias: [
        {
          find: /^@asifhussain\/prose-editor$/,
          replacement: fileURLToPath(
            new URL('./packages/prose-editor/src/index.ts', import.meta.url),
          ),
        },
        {
          find: /^@asifhussain\/prose-editor\/styles\.css$/,
          replacement: fileURLToPath(
            new URL(
              './packages/prose-editor/styles/prose-editor.css',
              import.meta.url,
            ),
          ),
        },
      ],
    },
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
        '@tiptap/pm/model', '@tiptap/pm/state', '@tiptap/pm/view',
        // Reached only through packages/prose-editor. Type-only today, so it is
        // erased before the bundler sees it — listed anyway so the day someone
        // adds a value import there is not the day a route 504s. A host-side
        // test asserts every bare import in packages/*/src appears here.
        '@tiptap/pm/transform',
        'diff',
        'cmdk', '@radix-ui/react-toast',
        '@dnd-kit/core', '@dnd-kit/sortable', '@dnd-kit/utilities',
        '@orama/orama',
        'gsap', 'gsap/ScrollTrigger',
        // NOTE: @asifhussain/prose-editor is deliberately ABSENT — aliased to
        // source above, it is first-party code, not a dep to pre-bundle.
      ],
      // React's CJS entry points branch on process.env.NODE_ENV at require time:
      //
      //   if (process.env.NODE_ENV === 'production')
      //     module.exports = require('./cjs/react-jsx-dev-runtime.production.js')
      //   else
      //     module.exports = require('./cjs/react-jsx-dev-runtime.development.js')
      //
      // rolldown (Vite 8's dep optimizer) evaluates that branch while pre-bundling
      // and, with NODE_ENV unset, resolved it to the PRODUCTION file — whose entire
      // body is `exports.jsxDEV = void 0`. Every client island then died on
      // "_jsxDEV is not a function" the moment it rendered, on every route with a
      // React island, while the SSR HTML still returned 200. Vite defines NODE_ENV
      // for app code but not for this pre-bundling pass, so it is set explicitly.
      //
      // Reading through to process.env keeps `astro build` (which sets NODE_ENV to
      // production) on the production branch — only an unset NODE_ENV, i.e. dev,
      // falls back to development.
      rolldownOptions: {
        transform: {
          define: {
            'process.env.NODE_ENV': JSON.stringify(
              process.env.NODE_ENV || 'development',
            ),
          },
        },
      },
    },
    server: {
      fs: {
        allow: ['..', '../..'],
        // The allow above opens the repo to Vite's /@fs/ handler, and Vite's
        // default deny covers .env* but not Wrangler's secrets file — so
        // GET /@fs/<repo>/listener/.dev.vars served the Podcast Factory
        // Library's local secrets (2026-09-03). Pinned by
        // scripts/astro-config-fs-deny.test.mjs.
        deny: ['**/.dev.vars', '**/.dev.vars.*', '**/.wrangler/**'],
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
