/**
 * The one HTML-text escaper for the site's markdown renderers.
 *
 * WHAT IT ESCAPES, and the one thing it deliberately does not: `&`, `<`, `>` and
 * the double quote — enough to be safe in HTML text content and inside a
 * double-quoted attribute. NOT the apostrophe. Escaping it to `&#39;` is
 * unnecessary in both positions and actively breaks downstream pattern matching:
 * "Abu Ya'qub" becomes "Abu Ya&#39;qub", which the Arabic detector can no longer
 * see through. That rationale used to live as a comment on one of three
 * identical copies, so two of the three read as arbitrary.
 *
 * WHY THIS FILE EXISTS. `escapeHtml` was written six times across this site in
 * two different behaviours — three escaping the four characters above and three
 * escaping only `&`, `<`, `>`. Nothing was wrong at any call site (every 3-char
 * caller interpolates in text position, never into an attribute), but six copies
 * and two answers meant no reader could tell which one they were getting without
 * checking, and the next divergence would be silent.
 *
 * WHAT IT DOES NOT ABSORB, on purpose. The three 3-character copies stay where
 * they are: `scripts/lib/book-html.mjs` is plain `.mjs` consumed by the print
 * renderer, `src/scripts/book-composer.ts` declares its copy INSIDE a function in
 * a browser bundle, and `src/components/corpus/CorpusExplorer.tsx` is a React
 * island. Pulling them onto this module would mean changing what they emit
 * (adding quote-escaping) and crossing a module boundary, to fix a duplication
 * that is currently harmless — the wrong trade. If they are ever unified, that
 * is a deliberate change to rendered output and wants its own verification.
 *
 * Consolidating the three identical copies was safe precisely because they were
 * identical: byte-for-byte the same replacements in the same order, so the
 * printed book and the Podcast Factory Library render exactly as before. The
 * Library's golden-file fixture is what proves it rather than the claim.
 */
export function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
