/**
 * The standalone build — for a host with NO module bundler.
 *
 * This exists because the app this package's design was drawn from is a .NET /
 * AngularJS site whose scripts are listed in a server-side bundle config and
 * whose npm is tooling-only. A bare-ESM package with peer dependencies is not
 * installable there at all. So a second artifact bundles TipTap and ProseMirror
 * IN and exposes one global, which drops into such a host as a single line.
 *
 * The ESM build (plain `tsc`) stays the primary artifact; this one is a
 * convenience for hosts that cannot consume it.
 */
import { defineConfig } from "vite";
import { fileURLToPath } from "node:url";

export default defineConfig({
  build: {
    outDir: "dist/standalone",
    emptyOutDir: true,
    // `true`, not "esbuild": Vite 8 minifies with oxc, and naming esbuild
    // explicitly makes it a separate install this package refuses to require.
    minify: true,
    lib: {
      entry: fileURLToPath(new URL("./src/index.ts", import.meta.url)),
      name: "ProseEditor",
      formats: ["iife"],
      fileName: () => "prose-editor.global.js",
    },
    rollupOptions: {
      // Nothing external: the whole point is that the host installs nothing.
      external: [],
      output: { extend: true },
    },
  },
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
});
