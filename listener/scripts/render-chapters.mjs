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
 *         "cards"?:[{"id":…,"markdown":…}, …],
 *         "book_dir"?:…}
 * stdout {"chapters":[{"anchor_key":…,"html":…,"section_key"?:…}, …],
 *         "cards":[{"id":…,"html":…}, …]}
 *
 * Reading stdin rather than taking a path keeps the caller free to render text
 * it assembled in memory, which is what the publish step does after splitting
 * book.md.
 */
import { build } from "esbuild";
import { readFileSync } from "node:fs";

const ADMIN_LIB = new URL(
  "../../plan-dashboard/src/lib/reader/",
  import.meta.url,
).pathname;

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
  return import(
    `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`
  );
}

/**
 * The three readers that say how a book's quotations are set.
 *
 * Plain .mjs with no sibling TypeScript, so unlike the three functions above
 * they need no bundling — but they are still loaded through a computed
 * specifier rather than a static `import`. That is deliberate: this project
 * type-checks its scripts with `checkJs`, and a literal path would pull the
 * admin site's untyped JavaScript into THIS app's compile and fail it on files
 * nobody here maintains. A URL the checker cannot resolve keeps the boundary
 * where the rest of this file already puts it.
 */
const ADMIN_LIB_SCRIPTS = new URL(
  "../../plan-dashboard/scripts/lib/",
  import.meta.url,
);
const { readQuranicRuns, readQuranicRefs } = await import(
  new URL("book-html.mjs", ADMIN_LIB_SCRIPTS).href
);
const { readQuoteKind, flattenQuoteKind } = await import(
  new URL("quote-kind.mjs", ADMIN_LIB_SCRIPTS).href
);
const { readQuoteGroups, flattenQuoteGroups } = await import(
  new URL("quote-groups.mjs", ADMIN_LIB_SCRIPTS).href
);
const { readImageLayout, flattenImageLayout } = await import(
  new URL("image-layout.mjs", ADMIN_LIB_SCRIPTS).href
);

/** @type {{chapters: {anchor_key: string, heading?: string, markdown: string}[], cards?: {id: string, markdown: string}[], book_dir?: string}} */
const payload = JSON.parse(readFileSync(0, "utf8"));
const { renderMarkdown, cardMarkdownToHtml, sectionKeyFromHeading } =
  await loadRenderers();

/**
 * How this book's quotations are set.
 *
 * The reading edition draws four cards — Qur'an, prophetic tradition, verse, and
 * the saying that is the default — and NONE of that is in the markdown. Which
 * Arabic runs the mushaf carries is the audit's answer, which card each of the
 * others takes is a person's, and a Qur'an card is headed by the chapter and
 * verse the audit recorded. All three live in the book's `_system/` folder.
 *
 * These are passed HERE because the print edition passes exactly the same three,
 * from the same three readers. That is the opposite of the rule this file used to
 * state — "defaults throughout, and any option passed only here would be a way
 * for the two to differ" — and it is the same rule underneath: the two surfaces
 * must render one book the same way. Once the printed page started asking these
 * questions, matching it meant asking them too. Without this every quotation in
 * the library publishes as an undifferentiated saying, with no scripture and no
 * references.
 *
 * A caller that sends no `book_dir` gets the old defaults, which is what the
 * contract fixture renders with.
 */
const quoteOptions = payload.book_dir
  ? {
      quranicRuns: readQuranicRuns(payload.book_dir),
      quoteKinds: flattenQuoteKind(readQuoteKind(payload.book_dir)),
      // Added 2026-08-14 — a real gap until now: the merge feature had
      // reached the admin site's own Read tab and the PDF, but never this
      // bridge, so a book publishing a merged card here would still have
      // shown its fragments as separate cards to a reader on the Library.
      quoteGroups: flattenQuoteGroups(readQuoteGroups(payload.book_dir)),
      // Per-image resize/align from the Composer, same reasoning.
      imageLayout: flattenImageLayout(readImageLayout(payload.book_dir)),
      quranicRefs: readQuranicRefs(payload.book_dir),
    }
  : {};

process.stdout.write(
  JSON.stringify({
    chapters: payload.chapters.map((c) => ({
      anchor_key: c.anchor_key,
      html: renderMarkdown(c.markdown, quoteOptions),
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
