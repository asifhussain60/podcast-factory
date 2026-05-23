// @ts-check
import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import node from '@astrojs/node';
import tailwindcss from '@tailwindcss/vite';

// https://astro.build/config
export default defineConfig({
  output: 'server',
  adapter: node({ mode: 'standalone' }),
  integrations: [react()],
  vite: {
    plugins: [tailwindcss()],
    server: {
      // Allow reading from outside the project (worktree content).
      fs: {
        allow: [
          '..', // parent dir (podcast-factory)
          '../..', // grandparent (~/PROJECTS)
        ],
      },
    },
  },
  server: {
    port: 4321,
    host: 'localhost',
  },
});
