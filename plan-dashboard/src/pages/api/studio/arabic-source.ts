/**
 * Arabic source API — the Arabic behind one chapter's English paragraphs.
 *
 *   GET /api/studio/arabic-source?slug=X&chapter=Y
 *
 * Returns, for that chapter, every composed paragraph's source-paragraph pairing
 * (keyed by the paragraph fingerprint the Composer holds) plus the Arabic text of
 * each numbered paragraph in the chapter's range. One request per chapter, fetched
 * on first use: baking this into the page payload would ship the whole Arabic
 * source on load for a panel most visits never open.
 *
 * The alignment itself is computed offline by scripts/podcast/align_arabic_paragraphs.py
 * — nothing is inferred here. Absent sidecar, absent Arabic, or an un-numbered
 * edition all return `available: false`, and the Composer simply does not offer the
 * control.
 */
import type { APIRoute } from "astro";
import { findContentDirSync, contentDir } from "../../../lib/content-paths";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";
import {
  loadAlignment,
  parseBlocks,
  resolveArabicSource,
  joinParagraphs,
} from "../../../lib/reader/arabic-source";
import { readFileSync } from "node:fs";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
// The Composer's chapter key: a lowercased heading. Kept as a traversal guard, the
// same shape the companion-notes route applies to its own key.
const CHAPTER_KEY_RE = /^[^/\\.][^/\\]*$/;

export const GET: APIRoute = ({ request }) => {
  const url = new URL(request.url);
  const slug = url.searchParams.get("slug");
  const chapter = url.searchParams.get("chapter");
  if (!slug || !SLUG_RE.test(slug)) return apiError("Missing or invalid slug");
  if (!chapter || !CHAPTER_KEY_RE.test(chapter))
    return apiError("Missing or invalid chapter");

  try {
    const bookDir = findContentDirSync(slug) ?? contentDir(slug);
    const alignment = loadAlignment(bookDir);
    const entry = alignment.get(chapter);
    const sourcePath = resolveArabicSource(bookDir);
    if (!entry || !sourcePath) {
      return apiOk({ slug, chapter, available: false, pairs: [], paragraphs: [] });
    }

    const blocks = parseBlocks(readFileSync(sourcePath, "utf8"), {
      stripFootnoteRefs: true,
    });
    // Every paragraph this chapter can ask for, resolved once. The pairs reference
    // them by number, so the client never needs a second round trip to open a
    // different paragraph in the same chapter.
    const wanted = new Set<number>();
    for (const p of entry.pairs) for (const n of p.source_paras) wanted.add(n);
    const [lo, hi] = entry.sourceParaRange;
    if (Number.isFinite(lo) && Number.isFinite(hi))
      for (let n = lo; n <= hi; n++) wanted.add(n);

    return apiOk({
      slug,
      chapter,
      available: true,
      // Whether the Arabic being served carries its vowel marks, so the reveal can
      // say so rather than leaving a reader wondering why one book is bare.
      vowelled: sourcePath.endsWith(".vowelled.md"),
      sourceParaRange: entry.sourceParaRange,
      pairs: entry.pairs,
      paragraphs: joinParagraphs(blocks, [...wanted]),
    });
  } catch (e) {
    return apiServerError(String(e));
  }
};
