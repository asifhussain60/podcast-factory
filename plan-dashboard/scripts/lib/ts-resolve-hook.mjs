/**
 * ts-resolve-hook.mjs — let `node --test` load the site's own TypeScript.
 *
 * Nothing under `src/` was tested until 2026-07-21, because `npm test` globbed
 * only `scripts/**\/*.test.mjs`. That excluded `book-md-write.ts` — the sole writer
 * into `book/book.md` — and every `src/pages/api/studio/*` route that mutates
 * `content/**`. The most destructive code on the site had no test at all, and it
 * was a glob keeping it that way, not a decision.
 *
 * Node 23.6+ strips TypeScript types natively, so the only thing standing between
 * `node --test` and those files is module resolution: the source uses
 * extensionless relative imports (`./book-fences`), which the ESM resolver
 * rejects. This hook appends the extension the file actually has. It is
 * deliberately a resolve-only shim rather than a second test runner — vitest would
 * mean a new dependency, a second config, and two ways to run a test.
 *
 * Loaded via `--import` from the `test` script; it affects nothing at build or
 * runtime, where Vite does this resolution itself.
 */
import { registerHooks } from "node:module";
import { existsSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, resolve as resolvePath } from "node:path";

const CANDIDATES = [".ts", ".tsx", ".mts", ".js", ".mjs", "/index.ts", "/index.tsx"];

registerHooks({
  resolve(specifier, context, nextResolve) {
    const relative = specifier.startsWith("./") || specifier.startsWith("../");
    const hasExtension = /\.[a-z]+$/i.test(specifier);
    if (relative && !hasExtension && context.parentURL?.startsWith("file:")) {
      const base = resolvePath(dirname(fileURLToPath(context.parentURL)), specifier);
      for (const ext of CANDIDATES) {
        if (existsSync(base + ext)) {
          return { url: pathToFileURL(base + ext).href, shortCircuit: true };
        }
      }
    }
    return nextResolve(specifier, context);
  },
});
