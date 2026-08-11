/**
 * book-images.ts — point an illustration at something this site can serve.
 *
 * `book.md` writes `images/<session>/<guid>.jpg`, relative to `book/`. That is
 * correct where it is written: the PDF is built in that directory, so the printed
 * page resolves it as-is and must keep it. Nothing serves that directory over
 * HTTP, so every browser surface has to rewrite it, and this is the one place
 * that decides how.
 *
 * ONE FUNCTION, CALLED BY EVERY BROWSER SURFACE — the Composer's read mode and
 * the reader view both. Not because the rewrite is hard, but because the failure
 * is silent: a surface that forgets it renders a broken picture and reports
 * nothing, which is exactly how sixty-three illustrations reached a review page
 * as the literal text `![](images/213/….jpg)`.
 *
 * Deliberately NOT inside `renderMarkdown` or `renderMd`. Those two are shared
 * with the printed book precisely so the page and the PDF cannot disagree about
 * what a paragraph looks like, and a site-only URL rule inside them would be the
 * first thing they disagreed about. `_listener_book._media_image_srcs` is the
 * same decision made on the same reasoning for the Podcast Factory Library, which
 * points the same src at its own gated `/media/` route.
 */

/** `src="images/…"` — a book asset, and the only src shape this rewrites. */
const BOOK_IMAGE_SRC = /(<img\b[^>]*?\bsrc=")images\/([^"]+)(")/gi;

/**
 * Rewrite every book-relative illustration onto the studio image route.
 *
 * An absolute src — another route, another origin, a data URI — is left exactly
 * as it is. It is not a book asset, and prefixing the route onto it would ask the
 * server for a file that was never on disk.
 */
export function serveBookImages(html: string, slug: string): string {
  return html.replace(
    BOOK_IMAGE_SRC,
    (_m, head: string, path: string, tail: string) =>
      `${head}/api/studio/book-image?slug=${encodeURIComponent(slug)}&path=${encodeURIComponent(path)}${tail}`,
  );
}
