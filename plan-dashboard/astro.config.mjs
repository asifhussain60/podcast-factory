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
    optimizeDeps: {
      // React 19 uses a conditional IIFE that Vite's CJS→ESM static analyser
      // can't resolve without explicit pre-bundling — forces esbuild to process
      // these packages and produce proper named ESM exports (e.g. createRoot).
      // The TipTap family + diff are the heavy editor deps behind StudioPoc (the
      // Edit & Enrich rich editor); pre-bundling them at server start stops Vite
      // from re-optimizing mid-session, which was 504-ing the editor chunks
      // ("Outdated Optimize Dep") and blanking Edit & Enrich (2026-06-15).
      // gsap + gsap/ScrollTrigger drive the homepage's NarrativeScroll island —
      // same failure mode: mid-session re-optimize 504'd them and blanked the home
      // page after a server restart with an open tab (2026-07-14).
      include: [
        'react', 'react-dom', 'react-dom/client',
        '@tiptap/react', '@tiptap/starter-kit', '@tiptap/core',
        '@tiptap/pm/state', '@tiptap/pm/view', 'diff',
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
