/**
 * Render book prose to HTML with the SAME functions the admin site uses.
 *
 * The Listener's build-time dependency on the admin site is three functions from
 * plan-dashboard, all called HERE, at publish time, rather than in the Worker:
 *
 *   renderMarkdown         chapter prose and the blurb (lib/reader/markdown.ts)
 *   cardMarkdownToHtml     a Scholar Companion card's body (…/companion/card-markdown.ts)
 *   sectionKeyFromHeading  the key a chapter's companion notes are FILED under
 *                          (…/companion/keys.ts)
 *
 * The first two are here for the same reason: shipping a markdown parser into
 * the Worker would be a second implementation that can disagree with the printed
 * book, and rendering per request would pay the cost on every read of text that
 * changes only when a book is re-composed.
 *
 * The third is here because it is a KEY RULE, not a renderer. Companion notes are
 * filed under `sectionKeyFromHeading`, which KEEPS the heading's ordinal, while
 * every table in this database keys a chapter by `anchor_key`, which strips it.
 * Deriving that second rule in Python would be one more TS↔Python mirror to keep
 * fixture-pinned; asking the side that already owns it costs nothing.
 *
 * It is TypeScript with sibling imports, so it is bundled through esbuild rather
 * than imported directly — Node can strip types but will not resolve
 * extensionless `.ts` specifiers.
 *
 *   echo '{"chapters":[{"anchor_key":"x","heading":"## 1. Hi","markdown":"# Hi"}]}' \
 *     | node scripts/render-chapters.mjs
 *
 * stdin  {"chapters":[{"anchor_key":…,"heading"?:…,"markdown":…}, …],
 *         "cards"?:[{"id":…,"markdown":…}, …]}
 * stdout {"chapters":[{"anchor_key":…,"html":…,"section_key"?:…}, …],
 *         "cards":[{"id":…,"html":…}, …]}
 *
 * Reading stdin rather than taking a path keeps the caller free to render text
 * it assembled in memory, which is what the publish step does after splitting
 * book.md.
 */
import { build } from "esbuild";
import { readFileSync } from "node:fs";

const ADMIN_LIB = new URL("../../plan-dashboard/src/lib/reader/", import.meta.url).pathname;

/**
 * Bundle the three functions and load them, without touching the filesystem.
 *
 * ONE synthetic entry point re-exporting all three, rather than three builds:
 * they share a module graph, and three bundles would compile the shared parts
 * three times and hand back three unrelated copies of them.
 */
async function loadRenderers() {
  const result = await build({
    stdin: {
      contents: [
        'export { renderMarkdown } from "./markdown";',
        'export { cardMarkdownToHtml } from "./companion/card-markdown";',
        'export { sectionKeyFromHeading } from "./companion/keys";',
      ].join("\n"),
      resolveDir: ADMIN_LIB,
      loader: "ts",
    },
    bundle: true,
    format: "esm",
    platform: "node",
    write: false,
    logLevel: "silent",
  });

  const source = result.outputFiles[0].text;
  return import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
}

/** @type {{chapters: {anchor_key: string, heading?: string, markdown: string}[], cards?: {id: string, markdown: string}[]}} */
const payload = JSON.parse(readFileSync(0, "utf8"));
const { renderMarkdown, cardMarkdownToHtml, sectionKeyFromHeading } = await loadRenderers();

process.stdout.write(
  JSON.stringify({
    chapters: payload.chapters.map((c) => ({
      anchor_key: c.anchor_key,
      // Defaults throughout. The print edition renders with the same defaults,
      // and any option passed only here would be a way for the two to differ.
      html: renderMarkdown(c.markdown),
      // Only for callers that sent a heading. The blurb has none, and an empty
      // key for it would be a key that could collide with a real one.
      ...(typeof c.heading === "string"
        ? { section_key: sectionKeyFromHeading(c.heading) }
        : {}),
    })),
    // `arabicSpans` on, matching the reader that ships these cards in the admin
    // site: the Arabic inside a note is set in its own face and direction. The
    // one caller that turns it off is the rich-text editor's seed, which is not
    // in this path and never will be — nothing here is editable.
    cards: (payload.cards ?? []).map((c) => ({
      id: c.id,
      html: cardMarkdownToHtml(c.markdown, { arabicSpans: true }),
    })),
  }),
);
