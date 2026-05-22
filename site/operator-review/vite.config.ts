import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// FastAPI backend lives at localhost:8766 (scripts/podcast/review_server.py).
// Dev server proxies /api/* to it so the browser stays same-origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8766',
        changeOrigin: false,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
})
