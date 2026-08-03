/**
 * Render book prose to HTML with the SAME function the print edition uses.
 *
 * The Listener's one build-time dependency on the admin site is
 * `renderMarkdown` from plan-dashboard/src/lib/reader/markdown.ts. It is called
 * here, at publish time, rather than in the Worker, for two reasons: shipping a
 * markdown parser into the Worker would be a second implementation that can
 * disagree with the printed book, and rendering per request would pay the cost
 * on every read of text that changes only when a book is re-composed.
 *
 * It is TypeScript with sibling imports, so it is bundled through esbuild rather
 * than imported directly — Node can strip types but will not resolve
 * extensionless `.ts` specifiers.
 *
 *   echo '{"chapters":[{"anchor_key":"x","markdown":"# Hi"}]}' \
 *     | node scripts/render-chapters.mjs
 *
 * stdin  {"chapters":[{"anchor_key":…,"markdown":…}, …]}
 * stdout {"chapters":[{"anchor_key":…,"html":…}, …]}
 *
 * Reading stdin rather than taking a path keeps the caller free to render text
 * it assembled in memory, which is what the publish step does after splitting
 * book.md.
 */
import { build } from "esbuild";
import { readFileSync } from "node:fs";

const RENDERER = new URL(
  "../../plan-dashboard/src/lib/reader/markdown.ts",
  import.meta.url,
).pathname;

/** Bundle the renderer and load it, without touching the filesystem. */
async function loadRenderer() {
  const result = await build({
    entryPoints: [RENDERER],
    bundle: true,
    format: "esm",
    platform: "node",
    write: false,
    logLevel: "silent",
  });

  const source = result.outputFiles[0].text;
  return import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
}

/** @type {{chapters: {anchor_key: string, markdown: string}[]}} */
const payload = JSON.parse(readFileSync(0, "utf8"));
const { renderMarkdown } = await loadRenderer();

process.stdout.write(
  JSON.stringify({
    chapters: payload.chapters.map((c) => ({
      anchor_key: c.anchor_key,
      // Defaults throughout. The print edition renders with the same defaults,
      // and any option passed only here would be a way for the two to differ.
      html: renderMarkdown(c.markdown),
    })),
  }),
);
