/**
 * book-md.ts — PUT /api/studio/book-md   body { slug, chapterKey, markdown }
 *
 * The Book Composer's chapter editor writes here. It replaces ONE chapter's body
 * in book/book.md — the composed reading edition the Composer previews — leaving
 * the `## Heading` line and every other chapter untouched. `chapterKey` is the
 * normalized heading key (mirrors lib/reader/composer.ts anchorKey); `markdown`
 * is the chapter body only (no heading), from the TipTap serializer.
 *
 * book.md is the last-mile reading edition (composed by a rare, manual, cached
 * LLM pass); a hand-edit here is durable in normal use. The prior file is kept as
 * book.md.bak (once) so the original is always recoverable.
 */
import type { APIRoute } from "astro";
import { readFileSync, writeFileSync, existsSync, copyFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { findContentDirSync } from "../../../lib/content-paths";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";
import { preserveFences } from "../../../lib/reader/book-fences";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

/** Normalize a heading to a comparable key — mirror of composer.ts anchorKey. */
function anchorKey(s: string): string {
  return s
    .replace(/<[^>]+>/g, "")
    .replace(/^#{1,6}\s+/, "")
    .replace(/^\d+\.\s*/, "")
    .trim()
    .toLowerCase();
}

/**
 * The compose cache file backing one chapter heading, or null when the heading
 * carries no chapter number.
 *
 * `_book_compose.py` writes `## <bk_index>. <title>` and caches that chapter's
 * prose at `book/_chunks/book/bk-<NN>.md` (zero-padded to 2). The preface is the
 * unnumbered heading and caches as `preface.md`. Keep this mapping in step with
 * `_book_compose.py` — it is the contract that makes a Composer edit durable.
 */
function chunkPathFor(
  bookDir: string,
  heading: string,
  isFirstHeading: boolean,
): string | null {
  const chunks = join(bookDir, "book", "_chunks", "book");
  const numbered = heading.match(/^##\s+(\d+)\.\s+/);
  if (numbered) {
    const n = Number(numbered[1]);
    if (!Number.isFinite(n) || n < 0) return null;
    return join(chunks, `bk-${String(n).padStart(2, "0")}.md`);
  }
  // ONLY the first unnumbered heading is the preface. A later unnumbered heading
  // is an in-flow source heading that owns no chunk — mirroring it into
  // preface.md would corrupt a different chapter's cache, so return null.
  return isFirstHeading ? join(chunks, "preface.md") : null;
}

export const PUT: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return apiError("Invalid JSON body");
  }

  const slug = String(body.slug ?? "").trim();
  const chapterKey = String(body.chapterKey ?? "")
    .trim()
    .toLowerCase();
  const markdown = String(body.markdown ?? "").trim();

  if (!SLUG_RE.test(slug)) return apiError("Invalid slug");
  if (!chapterKey) return apiError("Missing chapterKey");
  if (!markdown) return apiError("Content is empty — nothing to save");

  const bookDir = findContentDirSync(slug);
  if (!bookDir) return apiError(`Book not found: ${slug}`, 404);
  const bookMd = join(bookDir, "book", "book.md");
  if (!existsSync(bookMd)) return apiError("book.md not found", 404);

  try {
    const lines = readFileSync(bookMd, "utf-8").split("\n");
    // Locate the target chapter's heading and the start of the next chapter.
    let start = -1;
    let end = lines.length;
    let firstHeading = -1;
    for (let i = 0; i < lines.length; i += 1) {
      if (!/^##\s+/.test(lines[i])) continue;
      if (firstHeading === -1) firstHeading = i;
      if (start === -1 && anchorKey(lines[i]) === chapterKey) start = i;
      else if (start !== -1) {
        end = i;
        break;
      }
    }
    if (start === -1) return apiError(`Chapter not found: ${chapterKey}`, 404);

    if (!existsSync(`${bookMd}.bak`)) copyFileSync(bookMd, `${bookMd}.bak`);

    const head = lines.slice(0, start + 1); // through the heading line
    const tail = lines.slice(end); // from the next heading (or EOF)

    // Keep the pipeline's machine fences (editorial / bridge / study-summary)
    // alive across this edit. The rich-text round trip cannot carry an HTML
    // comment, so without this the markers are stripped and the Python phases
    // silently stop protecting and stop replacing those asides. See
    // lib/reader/book-fences.ts for the full rationale.
    const previousBody = lines.slice(start + 1, end).join("\n");
    const fences = preserveFences(previousBody, markdown);

    const rebuilt = [...head, "", fences.body, "", ...tail]
      .join("\n")
      .replace(/\n{3,}/g, "\n\n");
    writeFileSync(bookMd, rebuilt.endsWith("\n") ? rebuilt : `${rebuilt}\n`);

    // Durability: book.md is a DERIVED artifact. 0book-compose reassembles it
    // from book/_chunks/book/bk-NN.md, reusing any chunk that already exists
    // (scripts/podcast/_book_compose.py) — so an edit written only to book.md is
    // reverted the next time that phase runs. Mirroring the saved body into its
    // chunk makes the edit survive, using the cache the composer already honours
    // rather than inventing a new sidecar. Best-effort by design: the chunk dir
    // is a local build cache (gitignored), so a book composed elsewhere simply
    // has nothing to mirror into and the save still succeeds.
    const chunk = chunkPathFor(bookDir, lines[start], start === firstHeading);
    let chunkMirrored = false;
    if (chunk && existsSync(dirname(chunk))) {
      try {
        writeFileSync(chunk, `${fences.body.trim()}\n`);
        chunkMirrored = true;
      } catch {
        chunkMirrored = false; // never fail the save over the cache mirror
      }
    }

    return apiOk({ slug, chapterKey, path: bookMd, fences, chunkMirrored });
  } catch (e) {
    return apiServerError(`Save failed: ${String(e)}`);
  }
};
