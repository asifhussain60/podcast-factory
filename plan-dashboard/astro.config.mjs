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
    plugins: [tailwindcss()],
    optimizeDeps: {
      // React 19 uses a conditional IIFE that Vite's CJS→ESM static analyser
      // can't resolve without explicit pre-bundling — forces esbuild to process
      // these packages and produce proper named ESM exports (e.g. createRoot).
      include: ['react', 'react-dom', 'react-dom/client'],
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
